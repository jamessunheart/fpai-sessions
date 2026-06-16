#!/usr/bin/env python3
"""Self-regulating rate governor for probe outreach cycles."""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))
MAX_RATE = 50
START_RATE = 3
CORRECTION_LIMIT = 5


@dataclass(frozen=True)
class RateDecision:
    count: int
    reason: str
    completion_rate: float | None = None
    history_count: int = 0
    last_rate: int = START_RATE


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def read_jsonl(path: Path, *, since: datetime | None = None) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip():
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if since:
            ts = parse_time(row.get("ts") or row.get("timestamp") or row.get("created_at") or row.get("at"))
            if ts and ts < since:
                continue
        rows.append(row)
    return rows


def smoke_failed_recently(rows: Iterable[dict[str, Any]], *, now: datetime) -> bool:
    cutoff = now - timedelta(hours=6)
    for row in rows:
        ts = parse_time(row.get("ts") or row.get("timestamp") or row.get("created_at") or row.get("at"))
        if ts and ts < cutoff:
            continue
        event = str(row.get("event") or row.get("type") or "").lower()
        status = str(row.get("status") or "").upper()
        if event == "smoke_fail" or (event == "smoke_test" and status == "FAIL"):
            return True
    return False


def last_probe_rate(rows: Iterable[dict[str, Any]]) -> int:
    for row in reversed(list(rows)):
        if str(row.get("event") or row.get("type")) != "probe_rate":
            continue
        try:
            count = int(row.get("count"))
        except (TypeError, ValueError):
            continue
        if count > 0:
            return count
    return START_RATE


def connect_from_env() -> Any:
    dsn = os.environ.get("BRAIN_INDEX_DB_URL") or os.environ.get("DATABASE_URL") or os.environ.get("DB_URL")
    if not dsn:
        raise RuntimeError("missing database DSN; set BRAIN_INDEX_DB_URL, DATABASE_URL, or DB_URL")
    try:
        import psycopg  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on live host deps
        raise RuntimeError("psycopg is required on the live host") from exc
    return psycopg.connect(dsn, autocommit=True, connect_timeout=3)


def probe_history(conn: Any, *, now: datetime) -> tuple[int, int]:
    since = now - timedelta(days=7)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT completed_spark, completed_onboarding
              FROM brain_index.probe_sessions
             WHERE initiated_at >= %s
            """,
            (since,),
        )
        rows = list(cur.fetchall())
    completed = sum(1 for row in rows if bool(row[0]) or bool(row[1]))
    return len(rows), completed


def corrections_today(conn: Any, *, now: datetime) -> int:
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    total = 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(corrections_triggered), 0)::int
              FROM brain_index.probe_sessions
             WHERE initiated_at >= %s
            """,
            (start,),
        )
        row = cur.fetchone()
        total += int(row[0] or 0) if row else 0
    return total


def decide_rate(
    *,
    conn: Any,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    now: datetime | None = None,
    correction_limit: int = CORRECTION_LIMIT,
    ops_rows: list[dict[str, Any]] | None = None,
) -> RateDecision:
    current = now or utc_now()
    rows = ops_rows if ops_rows is not None else read_jsonl(ops_ledger, since=current - timedelta(days=7))
    if smoke_failed_recently(rows, now=current):
        return RateDecision(0, "smoke_fail_recent", last_rate=last_probe_rate(rows))
    correction_count = corrections_today(conn, now=current)
    if correction_count > correction_limit:
        return RateDecision(0, "correction_limit_exceeded", last_rate=last_probe_rate(rows))
    history_count, completed = probe_history(conn, now=current)
    last_rate = last_probe_rate(rows)
    if history_count == 0:
        return RateDecision(START_RATE, "no_history_start", None, 0, last_rate)
    completion = completed / history_count
    if completion >= 0.60:
        return RateDecision(min(last_rate * 2, MAX_RATE), "completion_at_or_above_60", completion, history_count, last_rate)
    if completion >= 0.30:
        return RateDecision(last_rate, "completion_30_to_60_hold", completion, history_count, last_rate)
    return RateDecision(0, "completion_below_30_pause_surface_gap", completion, history_count, last_rate)


def log_rate_decision(ops_ledger: Path, decision: RateDecision, *, now: datetime | None = None) -> bool:
    row = {
        "ts": (now or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": "probe_rate",
        "type": "probe_rate",
        "count": decision.count,
        "reason": decision.reason,
        "completion_rate": decision.completion_rate,
        "history_count": decision.history_count,
        "last_rate": decision.last_rate,
        "surface": "council" if "surface_gap" in decision.reason else "probe",
        "cost": "$0",
        "loop": "probe",
    }
    try:
        ops_ledger.parent.mkdir(parents=True, exist_ok=True)
        with ops_ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def govern(
    *,
    conn: Any | None = None,
    connector: Callable[[], Any] = connect_from_env,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    now: datetime | None = None,
    log: bool = True,
) -> RateDecision:
    own_conn = conn is None
    try:
        db = conn or connector()
    except Exception:
        decision = RateDecision(0, "db_unavailable")
        if log:
            log_rate_decision(ops_ledger, decision, now=now)
        return decision
    try:
        decision = decide_rate(conn=db, ops_ledger=ops_ledger, now=now)
        if log:
            log_rate_decision(ops_ledger, decision, now=now)
        return decision
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Return the next probe outreach count.")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    decision = govern(ops_ledger=args.ops_ledger)
    if args.json:
        print(json.dumps(decision.__dict__, sort_keys=True))
    else:
        print(decision.count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
