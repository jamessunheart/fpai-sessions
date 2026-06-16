#!/usr/bin/env python3
"""Live system smoke tests for the FPAI build/brain pipeline.

The default CLI is intentionally live: it touches the brain DB with a canary
decision, sends one Telegram self-check message, reads continuity/build state,
and records every check in the ops ledger. Unit tests inject fakes so this file
can be tested without production credentials.
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
CURATOR_ROOT = REPO_ROOT / "SERVICES" / "sunheart-brain"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
DEFAULT_DAILY_COUNT = Path(os.environ.get("FPAI_DAILY_COUNT", "/opt/fpai-build/.daily_count"))
DEFAULT_WORKTREES = Path(os.environ.get("FPAI_WORKTREES", "/opt/fpai-build/worktrees"))
DEFAULT_EXPECTED_OUTPUTS = REPO_ROOT / "tools" / "test" / "expected_outputs.json"

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"


class SmokeFailure(RuntimeError):
    pass


class SmokeWarning(RuntimeError):
    pass


@dataclass
class SmokeResult:
    test_id: str
    name: str
    status: str
    detail: str
    latency_ms: int


@dataclass
class SmokeContext:
    repo_root: Path = REPO_ROOT
    ops_ledger: Path = DEFAULT_OPS_LEDGER
    daily_count: Path = DEFAULT_DAILY_COUNT
    worktrees_dir: Path = DEFAULT_WORKTREES
    expected_outputs: Path = DEFAULT_EXPECTED_OUTPUTS
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    db_connect: Callable[[], Any] | None = None
    telegram_send: Callable[[str], bool] | None = None
    alert_send: Callable[[str], bool] | None = None
    subprocess_run: Callable[..., subprocess.CompletedProcess] = subprocess.run


def _ensure_curator_path(repo_root: Path) -> None:
    path = str(repo_root / "SERVICES" / "sunheart-brain")
    if path not in sys.path:
        sys.path.insert(0, path)


def _default_db_connect() -> Any:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - depends on live host deps
        raise SmokeFailure(f"psycopg unavailable: {exc}") from exc
    dsn = os.environ.get(
        "BRAIN_INDEX_DB_URL",
        "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
    )
    return psycopg.connect(dsn, autocommit=True)


def _execute_fetchone(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def _execute_fetchall(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> list[Any]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def _execute(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> None:
    with conn.cursor() as cur:
        cur.execute(sql, params)


def _connect(ctx: SmokeContext) -> Any:
    return (ctx.db_connect or _default_db_connect)()


async def _default_telegram_send(text: str) -> bool:
    _ensure_curator_path(REPO_ROOT)
    from curator import telegram

    return await telegram.send(text, parse_mode="HTML")


def send_telegram(ctx: SmokeContext, text: str) -> bool:
    if ctx.telegram_send:
        return bool(ctx.telegram_send(text))
    return bool(asyncio.run(_default_telegram_send(text)))


def send_alert(ctx: SmokeContext, text: str) -> bool:
    if os.environ.get("SMOKE_TEST_SILENT") == "1":
        return False
    if ctx.alert_send:
        return bool(ctx.alert_send(text))
    return send_telegram(ctx, text)


def append_ops_row(ctx: SmokeContext, row: dict[str, Any]) -> None:
    ctx.ops_ledger.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "ts": ctx.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "smoke_test",
        "cost": "$0",
        "artifact": "tools/test/smoke_test.py",
        "next": "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    data.update(row)
    with ctx.ops_ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, sort_keys=True) + "\n")


def log_result(ctx: SmokeContext, result: SmokeResult) -> None:
    event = {
        PASS: "smoke_pass",
        WARN: "smoke_warn",
        FAIL: "smoke_fail",
    }.get(result.status, "smoke_result")
    append_ops_row(
        ctx,
        {
            "event": event,
            "test_id": result.test_id,
            "test_name": result.name,
            "status": result.status,
            "detail": result.detail,
            "latency_ms": result.latency_ms,
        },
    )


def _recent_enough(value: datetime, now: datetime, seconds: int) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return now - value <= timedelta(seconds=seconds)


def test_decision_roundtrip(ctx: SmokeContext) -> str:
    now = ctx.now()
    question = f"SMOKE_TEST canary {now.strftime('%Y%m%dT%H%M%SZ')}"
    conn = _connect(ctx)
    try:
        row = _execute_fetchone(
            conn,
            """
            INSERT INTO brain_index.decisions (question, status)
            VALUES (%s, 'awaiting')
            RETURNING id::text, status, created_at
            """,
            (question,),
        )
        if not row:
            raise SmokeFailure("canary insert returned no row")
        decision_id, status, created_at = row
        readback = _execute_fetchone(
            conn,
            """
            SELECT id::text, status, created_at
              FROM brain_index.decisions
             WHERE id = %s AND question LIKE 'SMOKE_TEST canary %'
            """,
            (decision_id,),
        )
        if not readback:
            raise SmokeFailure("canary decision was not readable")
        if not readback[0] or readback[1] != "awaiting":
            raise SmokeFailure(f"bad canary readback id/status: {readback[0]} / {readback[1]}")
        if not _recent_enough(readback[2] or created_at, now, 300):
            raise SmokeFailure("canary created_at is not recent")
        return f"canary decision roundtrip ok ({decision_id})"
    finally:
        try:
            _execute(
                conn,
                "DELETE FROM brain_index.decisions WHERE question LIKE 'SMOKE_TEST canary %' AND status = 'awaiting'",
            )
        finally:
            close = getattr(conn, "close", None)
            if close:
                close()


def test_telegram_roundtrip(ctx: SmokeContext) -> str:
    stamp = ctx.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    ok = send_telegram(ctx, f"[SMOKE TEST {stamp}] System self-check. No action needed.")
    if not ok:
        raise SmokeFailure("Telegram send returned false")
    return "Telegram send accepted"


def test_thread_read(ctx: SmokeContext) -> str:
    conn = _connect(ctx)
    try:
        row = _execute_fetchone(
            conn,
            """
            SELECT COUNT(*)::int
              FROM brain_index.tg_messages
             WHERE at > NOW() - INTERVAL '24 hours'
            """,
        )
    finally:
        close = getattr(conn, "close", None)
        if close:
            close()
    count = int(row[0] if row else 0)
    if count <= 0:
        raise SmokeFailure("no conversation activity in 24h - bot may be down")
    return f"{count} Telegram message rows in last 24h"


def _daily_count_date(path: Path) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SmokeFailure(f"{path} is empty")
    return text.split()[0]


def _pending_decisions_count(ctx: SmokeContext) -> int:
    try:
        conn = _connect(ctx)
        try:
            row = _execute_fetchone(
                conn,
                """
                SELECT COUNT(*)::int
                  FROM brain_index.decisions
                 WHERE status = 'answered'
                   AND COALESCE(needs_build, false) = true
                   AND COALESCE(build_status, '') NOT IN ('built', 'merged')
                """,
            )
        finally:
            close = getattr(conn, "close", None)
            if close:
                close()
        return int(row[0] if row else 0)
    except Exception:
        return 1


def test_build_loop_liveness(ctx: SmokeContext) -> str:
    today = ctx.now().strftime("%Y-%m-%d")
    if not ctx.daily_count.exists():
        raise SmokeFailure(f"{ctx.daily_count} missing")
    seen_date = _daily_count_date(ctx.daily_count)
    if seen_date != today:
        raise SmokeFailure(f"daily_count date is {seen_date}, expected {today} UTC")
    pending = _pending_decisions_count(ctx)
    cutoff = ctx.now().timestamp() - (26 * 60 * 60)
    touched = [
        p for p in ctx.worktrees_dir.iterdir()
        if p.is_dir() and p.stat().st_mtime >= cutoff
    ] if ctx.worktrees_dir.exists() else []
    if not touched and pending > 0:
        raise SmokeFailure("no build worktree touched in last 26h while decisions are pending")
    suffix = "no pending decisions" if not touched else f"{len(touched)} recent worktrees"
    return f"daily_count current; {suffix}"


def test_curator_import_chain(ctx: SmokeContext) -> str:
    _ensure_curator_path(ctx.repo_root)
    started = time.monotonic()
    modules = ["curator", "curator.decisions", "curator.telegram", "curator.corrections"]
    for name in modules:
        importlib.import_module(name)
    elapsed = time.monotonic() - started
    if elapsed > 5:
        raise SmokeWarning(f"curator import chain slow: {elapsed:.2f}s")
    return f"curator imports ok in {elapsed:.2f}s"


def test_ops_ledger_write(ctx: SmokeContext) -> str:
    stamp = ctx.now().strftime("%Y%m%dT%H%M%SZ")
    detail = f"smoke test probe {stamp}"
    script = ctx.repo_root / "tools" / "build_loop" / "ops_log.py"
    env = os.environ.copy()
    env["OPS_LEDGER"] = str(ctx.ops_ledger)
    ctx.subprocess_run(
        [sys.executable, str(script), "smoke", "test_event", detail, "$0", "", ""],
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.time() + 2
    while time.time() < deadline:
        if ctx.ops_ledger.exists() and detail in ctx.ops_ledger.read_text(encoding="utf-8", errors="replace"):
            return "ops ledger write/read ok"
        time.sleep(0.05)
    raise SmokeFailure("ops ledger test event did not appear within 2 seconds")


def _normalize_decision_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.startswith("SPEC_"):
        text = text[5:]
    if text.startswith("d"):
        return text[:4]
    if text.isdigit():
        return f"d{int(text):03d}"
    return text


def _decision_ids_from_registry(registry_path: Path) -> set[str]:
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    out: set[str] = set()
    for row in data.get("active_builds", []):
        if row.get("status") not in {"done", "merged"}:
            continue
        for key in ("id", "slug"):
            did = _normalize_decision_id(row.get(key))
            if did.startswith("d") and len(did) == 4:
                out.add(did)
    return out


def _decision_ids_from_db(ctx: SmokeContext) -> set[str]:
    try:
        conn = _connect(ctx)
        try:
            rows = _execute_fetchall(
                conn,
                """
                SELECT id::text
                  FROM brain_index.decisions
                 WHERE status = 'answered'
                   AND COALESCE(needs_build, false) = false
                """,
            )
        finally:
            close = getattr(conn, "close", None)
            if close:
                close()
    except Exception:
        return set()
    return {
        did for did in (_normalize_decision_id(row[0]) for row in rows)
        if did.startswith("d") and len(did) == 4
    }


def test_spec_registry_gap(ctx: SmokeContext) -> str:
    expected = json.loads(ctx.expected_outputs.read_text(encoding="utf-8")) if ctx.expected_outputs.exists() else {}
    built_ids = _decision_ids_from_registry(ctx.repo_root / "core" / "BUILD" / "REGISTRY.json")
    built_ids.update(_decision_ids_from_db(ctx))
    checked = 0
    missing: list[str] = []
    for did in sorted(built_ids):
        paths = expected.get(did, [])
        if not paths:
            continue
        checked += len(paths)
        for rel in paths:
            if not (ctx.repo_root / rel).exists():
                missing.append(f"{did} claims built but {rel} missing")
    if missing:
        raise SmokeFailure("; ".join(missing[:5]))
    return f"{checked} expected built files checked"


SMOKE_TESTS: list[tuple[str, str, Callable[[SmokeContext], str]]] = [
    ("1", "decision queue write/read roundtrip", test_decision_roundtrip),
    ("2", "Telegram send roundtrip", test_telegram_roundtrip),
    ("3", "thread read conversation continuity", test_thread_read),
    ("4", "build loop liveness", test_build_loop_liveness),
    ("5", "curator module import chain", test_curator_import_chain),
    ("6", "ops ledger write", test_ops_ledger_write),
    ("7", "spec-vs-registry gap check", test_spec_registry_gap),
]


def run_one(ctx: SmokeContext, test_id: str, name: str, fn: Callable[[SmokeContext], str]) -> SmokeResult:
    started = time.monotonic()
    try:
        detail = fn(ctx)
        status = PASS
    except SmokeWarning as exc:
        detail = str(exc)
        status = WARN
    except Exception as exc:
        detail = str(exc)
        status = FAIL
    latency_ms = int((time.monotonic() - started) * 1000)
    result = SmokeResult(test_id=test_id, name=name, status=status, detail=detail, latency_ms=latency_ms)
    log_result(ctx, result)
    if result.status == FAIL:
        send_alert(ctx, f"SMOKE TEST FAIL {test_id}: {name}\n{detail}")
    return result


def run_all(ctx: SmokeContext, tests: Iterable[tuple[str, str, Callable[[SmokeContext], str]]] = SMOKE_TESTS) -> list[SmokeResult]:
    if os.environ.get("SMOKE_TEST_DISABLE") == "1":
        append_ops_row(ctx, {"event": "smoke_skipped", "detail": "SMOKE_TEST_DISABLE=1", "status": "SKIP"})
        append_ops_row(
            ctx,
            {
                "event": "smoke_test",
                "status": "SKIP",
                "detail": "SMOKE_TEST_DISABLE=1",
                "passed": 0,
                "warnings": 0,
                "failures": 0,
                "total": 0,
            },
        )
        return []
    results = [run_one(ctx, test_id, name, fn) for test_id, name, fn in tests]
    failures = [r for r in results if r.status == FAIL]
    warnings = [r for r in results if r.status == WARN]
    append_ops_row(
        ctx,
        {
            "event": "smoke_test",
            "status": FAIL if failures else (WARN if warnings else PASS),
            "detail": "; ".join(r.detail for r in failures[:3]) or f"all {len(results)} smoke checks passed",
            "passed": sum(1 for r in results if r.status == PASS),
            "warnings": len(warnings),
            "failures": len(failures),
            "total": len(results),
        },
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run live FPAI system smoke tests")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--json", action="store_true", help="print JSON results")
    args = parser.parse_args(argv)
    ctx = SmokeContext(ops_ledger=args.ops_ledger)
    results = run_all(ctx)
    payload = [r.__dict__ for r in results]
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for r in results:
            print(f"{r.status} test {r.test_id}: {r.name} ({r.latency_ms}ms) - {r.detail}")
    return 1 if any(r.status == FAIL for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
