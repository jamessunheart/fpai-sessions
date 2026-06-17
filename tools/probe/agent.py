#!/usr/bin/env python3
"""Probe Agent: contact manually seeded people at a self-governed rate."""
from __future__ import annotations

import argparse
import importlib.util as _ilu
import json
import os
import re
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.probe import rate_governor

DEFAULT_DISABLE_FILE = Path(os.environ.get("PROBE_DISABLE_FILE", "/opt/fpai-build/.probe_disabled"))
DEFAULT_OPS_LEDGER = rate_governor.DEFAULT_OPS_LEDGER
DEFAULT_VOICE = REPO_ROOT / "core" / "STATE" / "OUTREACH_VOICE.md"
PITCH_WORDS = re.compile(r"\b(feature|features|upsell|buy|purchase|subscribe|pricing|sale|sales|offer|demo)\b", re.I)
QUOTED_RE = re.compile(r'"([^"]+)"')
SECTION_RE = re.compile(r"^## (?P<heading>[^\n]+)\n(?P<body>.*?)(?=^## |\Z)", re.M | re.S)


@dataclass(frozen=True)
class PoolMember:
    id: int
    pool: str
    handle: str
    platform: str
    name: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class ProbeRunResult:
    disabled: bool
    rate: int
    attempted: int
    sent: int
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def disabled(disable_file: Path = DEFAULT_DISABLE_FILE) -> bool:
    return os.environ.get("PROBE_DISABLE") == "1" or disable_file.exists()


def connect_from_env() -> Any:
    return rate_governor.connect_from_env()


def _pool_gate(conn: Any, pool: str, *, now: datetime) -> bool:
    if pool == "warm":
        return True
    prior = "warm" if pool == "adjacent" else "adjacent"
    since = now - timedelta(days=7)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT completed_spark, completed_onboarding
              FROM brain_index.probe_sessions
             WHERE pool = %s AND initiated_at >= %s
            """,
            (prior, since),
        )
        rows = list(cur.fetchall())
    if not rows:
        return False
    completed = sum(1 for row in rows if bool(row[0]) or bool(row[1]))
    return completed / len(rows) > 0.60


def select_pool_members(conn: Any, *, limit: int, now: datetime) -> list[PoolMember]:
    if limit <= 0:
        return []
    selected: list[PoolMember] = []
    cutoff = now - timedelta(days=30)
    for pool in ("warm", "adjacent", "cold"):
        if not _pool_gate(conn, pool, now=now):
            continue
        remaining = limit - len(selected)
        if remaining <= 0:
            break
        try:
            pool_columns = _table_columns(conn, "probe_pool")
        except Exception:
            pool_columns = set()
        metadata_expr = "metadata" if "metadata" in pool_columns else "NULL AS metadata"
        source_expr = "source" if "source" in pool_columns else "NULL AS source"
        score_gate = "AND COALESCE(discovery_score, 0.5) >= 0.4" if "discovery_score" in pool_columns else ""
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, pool, handle, platform, {metadata_expr}, {source_expr}
                  FROM brain_index.probe_pool
                 WHERE pool = %s
                   AND COALESCE(do_not_contact, false) = false
                   AND (last_probed_at IS NULL OR last_probed_at < %s)
                   {score_gate}
                 ORDER BY last_probed_at NULLS FIRST, id ASC
                 LIMIT %s
                """,
                (pool, cutoff, remaining),
            )
            for row in cur.fetchall():
                metadata = row[4] if len(row) > 4 else None
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        metadata = {}
                if not isinstance(metadata, dict):
                    metadata = {}
                source = str(row[5] or metadata.get("source") or "") if len(row) > 5 else str(metadata.get("source") or "")
                if str(row[3]) == "telegram" and source.startswith("telegram_") and os.environ.get("TELETHON_DM_ENABLED") != "1":
                    continue
                selected.append(PoolMember(int(row[0]), str(row[1]), str(row[2]), str(row[3]), metadata.get("name"), source or None))
    return selected


def sanitize_opener(text: str) -> str:
    line = " ".join(str(text).strip().split())
    if not line:
        line = fallback_opener()
    if "stop to opt out" in line.lower():
        return line
    parts = re.split(r"(?<=[.!?])\s+", line)
    line = " ".join(parts[:3]).strip()
    if PITCH_WORDS.search(line):
        line = fallback_opener()
    return line


def fallback_opener() -> str:
    return (
        "I'm Sunheart AI. Sunheart built me around one question: what does your full potential "
        "actually look like - and what's in the way? I grow from every real conversation. "
        "Want to find out what yours looks like?"
    )


def canonical_section_message(voice_path: Path, heading: str) -> str | None:
    if not voice_path.exists():
        return None
    text = voice_path.read_text(encoding="utf-8", errors="replace")
    for match in SECTION_RE.finditer(text):
        if match.group("heading").strip().lower() != heading.lower():
            continue
        quotes = QUOTED_RE.findall(match.group("body"))
        if quotes:
            return " ".join(quotes[0].split())
        body = " ".join(match.group("body").split())
        return body or None
    return None


def spark_opening_message(voice_path: Path = DEFAULT_VOICE) -> str | None:
    return canonical_section_message(voice_path, "Spark Opening")


def canonical_outreach_message(voice_path: Path = DEFAULT_VOICE) -> str | None:
    message = canonical_section_message(voice_path, "Primary Message")
    text = voice_path.read_text(encoding="utf-8", errors="replace") if voice_path.exists() else ""
    matches = QUOTED_RE.findall(text)
    if not message and matches:
        message = max((" ".join(match.split()) for match in matches), key=len)
    elif not message:
        message = " ".join(text.split())
    if not message:
        return None
    if "stop to opt out" not in message.lower():
        message = f"{message} Reply STOP to opt out."
    return message


def compose_opener(member: PoolMember, *, voice_path: Path = DEFAULT_VOICE, runner: Callable[..., Any] = subprocess.run) -> str:
    canonical = canonical_outreach_message(voice_path)
    if canonical:
        return canonical
    voice = voice_path.read_text(encoding="utf-8", errors="replace")[:4000] if voice_path.exists() else ""
    prompt = (
        "Write one warm, genuine outreach opener for this probe. Do not pitch features, sell, upsell, or explain the product. "
        "Ask one honest question and keep it <= 3 sentences.\n\n"
        f"Voice guide:\n{voice}\n\n"
        f"Pool: {member.pool}\nPlatform: {member.platform}\nHandle: {member.handle}\n"
    )
    try:
        result = runner(
            ["claude", "-p", "--effort", "low", prompt],
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
    except Exception:
        return fallback_opener()
    if getattr(result, "returncode", 1) != 0:
        return fallback_opener()
    return sanitize_opener(getattr(result, "stdout", ""))


def record_probe_session(conn: Any, *, probe_id: str, member: PoolMember, opener: str, now: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO brain_index.probe_sessions
                (probe_id, pool, initiated_at, last_message_at, engaged, drop_off_message, completed_spark,
                 completed_onboarding, quality_score, corrections_triggered, last_message, notes)
            VALUES (%s, %s, %s, NULL, false, NULL, false, false, NULL, 0, NULL, %s)
            """,
            (
                probe_id,
                member.pool,
                now,
                json.dumps({
                    "pool_member_id": member.id,
                    "platform": member.platform,
                    "handle": member.handle,
                    "name": member.name,
                    "opener": opener,
                    "send_status": "pending",
                }),
            ),
        )


def mark_probed(conn: Any, *, member: PoolMember, now: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE brain_index.probe_pool SET last_probed_at = %s WHERE id = %s", (now, member.id))


def _delivery_sent(delivery: Any) -> bool:
    if isinstance(delivery, bool):
        return delivery
    return bool(getattr(delivery, "sent", False))


def _delivery_notes(delivery: Any) -> dict[str, Any]:
    if isinstance(delivery, bool):
        return {}
    notes: dict[str, Any] = {}
    for key in ("reason", "message_id", "sent_at", "dry_run", "disabled"):
        if hasattr(delivery, key):
            value = getattr(delivery, key)
            if value is not None:
                notes[key] = value
    return notes


def update_send_status(conn: Any, *, probe_id: str, delivery: Any) -> None:
    sent = _delivery_sent(delivery)
    meta = _delivery_notes(delivery)
    if sent:
        status = "sent"
    elif meta.get("dry_run"):
        status = "dry_run"
    elif meta.get("disabled"):
        status = "disabled"
    else:
        status = "send_failed"
    extra = "\nsend_status=" + status
    if meta:
        extra += "\ndelivery=" + json.dumps(meta, sort_keys=True)
    try:
        session_columns = _table_columns(conn, "probe_sessions")
    except Exception:
        session_columns = set()
    if {"sent_at", "message_id"}.issubset(session_columns):
        sql = """
            UPDATE brain_index.probe_sessions
               SET notes = COALESCE(notes, '') || %s,
                   sent_at = COALESCE(%s, sent_at),
                   message_id = COALESCE(%s, message_id)
             WHERE probe_id = %s
            """
        params = (extra, meta.get("sent_at"), meta.get("message_id"), probe_id)
    else:
        sql = "UPDATE brain_index.probe_sessions SET notes = COALESCE(notes, '') || %s WHERE probe_id = %s"
        params = (extra, probe_id)
    with conn.cursor() as cur:
        cur.execute(sql, params)


def default_send(member: PoolMember, opener: str) -> Any:
    """Send through Hermes if installed; otherwise fail closed."""
    if member.platform == "email":
        try:
            from tools.hermes.email_adapter import send_member_email
        except Exception:
            return False
        return send_member_email(member.handle, opener, name=member.name)
    gateway_path = REPO_ROOT / "SERVICES" / "sunheart-brain" / "curator" / "hermes" / "gateway.py"
    try:
        spec = _ilu.spec_from_file_location("fpai_probe_hermes_gateway", gateway_path)
        gateway = _ilu.module_from_spec(spec) if spec and spec.loader else None
        if gateway is None:
            return False
        spec.loader.exec_module(gateway)
        send_message = gateway.send_message
    except Exception:
        return False
    try:
        return bool(send_message(platform=member.platform, handle=member.handle, text=opener))
    except Exception:
        return False


def run_probe_cycle(
    *,
    conn: Any | None = None,
    connector: Callable[[], Any] = connect_from_env,
    sender: Callable[[PoolMember, str], bool] = default_send,
    opener_composer: Callable[[PoolMember], str] | None = None,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    disable_file: Path = DEFAULT_DISABLE_FILE,
    now: datetime | None = None,
) -> ProbeRunResult:
    if disabled(disable_file):
        return ProbeRunResult(True, 0, 0, 0, "disabled")
    current = now or utc_now()
    own_conn = conn is None
    try:
        db = conn or connector()
    except Exception:
        return ProbeRunResult(False, 0, 0, 0, "db_unavailable")
    try:
        try:
            refresh_session_outcomes(conn=db, now=current)
        except Exception:
            pass
        decision = rate_governor.govern(conn=db, ops_ledger=ops_ledger, now=current)
        if decision.count <= 0:
            return ProbeRunResult(False, 0, 0, 0, decision.reason)
        members = select_pool_members(db, limit=decision.count, now=current)
        sent = 0
        composer = opener_composer or compose_opener
        for member in members:
            opener = sanitize_opener(composer(member))
            if member.platform == "email":
                try:
                    from tools.hermes.email_adapter import disabled_by_env, is_live_enabled
                except Exception:
                    continue
                if disabled_by_env() or not is_live_enabled():
                    sender(member, opener)
                    continue
            probe_id = f"probe_{current.strftime('%Y%m%dT%H%M%SZ')}_{member.id}_{uuid.uuid4().hex[:8]}"
            record_probe_session(db, probe_id=probe_id, member=member, opener=opener, now=current)
            mark_probed(db, member=member, now=current)
            delivery = sender(member, opener)
            update_send_status(db, probe_id=probe_id, delivery=delivery)
            if _delivery_sent(delivery):
                sent += 1
        return ProbeRunResult(False, decision.count, len(members), sent, decision.reason)
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()


def evaluate_due_sessions(
    *,
    conn: Any,
    now: datetime | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> int:
    current = now or utc_now()
    cutoff = current - timedelta(hours=24)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, probe_id, notes
             FROM brain_index.probe_sessions
             WHERE quality_score IS NULL
               AND COALESCE(last_message_at, initiated_at) <= %s
             ORDER BY initiated_at ASC
             LIMIT 25
            """,
            (cutoff,),
        )
        rows = list(cur.fetchall())
    updated = 0
    for session_id, probe_id, notes in rows:
        prompt = (
            "Rate this conversation 0.0-1.0 for: (1) did Spark route them clearly, "
            "(2) did they seem to understand what to do next, (3) did anything confuse them. "
            "JSON: {score: float, gaps: [str], highlight: str}\n\n"
            f"probe_id: {probe_id}\nnotes: {notes}"
        )
        try:
            result = runner(["claude", "-p", "--effort", "medium", prompt], text=True, capture_output=True, timeout=90, check=False)
            data = json.loads((getattr(result, "stdout", "") or "").strip())
            score = max(0.0, min(1.0, float(data["score"])))
        except Exception:
            continue
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE brain_index.probe_sessions SET quality_score = %s, notes = COALESCE(notes, '') || %s WHERE id = %s",
                (score, "\nquality_eval=" + json.dumps(data, sort_keys=True), session_id),
            )
        updated += 1
    return updated


def _json_notes(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {}
    first = value.splitlines()[0] if value.strip() else ""
    try:
        data = json.loads(first)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _table_columns(conn: Any, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
              FROM information_schema.columns
             WHERE table_schema = 'brain_index'
               AND table_name = %s
            """,
            (table,),
        )
        return {str(row[0]) for row in cur.fetchall()}


def _row_value(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None


def _message_matches_handle(row: dict[str, Any], handle: str) -> bool:
    target = str(handle or "").lstrip("@").lower()
    if not target:
        return False
    for key in ("handle", "username", "from_username", "sender_username", "telegram_handle", "user_id", "from_user_id", "chat_id"):
        value = row.get(key)
        if value is not None and str(value).lstrip("@").lower() == target:
            return True
    return False


def _completion_from_messages(messages: list[dict[str, Any]]) -> tuple[bool, int | None, bool, bool, datetime | None, str | None]:
    if not messages:
        return False, None, False, False, None, None
    texts = [str(_row_value(row, ("text", "message", "content", "body")) or "") for row in messages]
    joined = "\n".join(texts).lower()
    last = messages[-1]
    last_at = rate_governor.parse_time(_row_value(last, ("at", "created_at", "timestamp", "ts")))
    last_message = texts[-1][:1000] if texts else None
    completed_spark = "spark" in joined and any(word in joined for word in ("complete", "completed", "next step", "routed"))
    completed_onboarding = any(phrase in joined for phrase in ("proof step", "action step", "clear next step", "next action"))
    return True, len(messages), completed_spark, completed_onboarding, last_at, last_message


def refresh_session_outcomes(conn: Any, *, now: datetime | None = None) -> int:
    current = now or utc_now()
    since = current - timedelta(days=30)
    try:
        columns = _table_columns(conn, "tg_messages")
    except Exception:
        return 0
    if not columns:
        return 0
    time_col = next((c for c in ("at", "created_at", "timestamp", "ts") if c in columns), None)
    select_cols = sorted(columns.intersection({
        "at", "created_at", "timestamp", "ts", "text", "message", "content", "body",
        "role", "handle", "username", "from_username", "sender_username", "telegram_handle",
        "user_id", "from_user_id", "chat_id",
    }))
    if not select_cols:
        return 0
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, initiated_at, notes
              FROM brain_index.probe_sessions
             WHERE initiated_at >= %s
               AND (engaged IS DISTINCT FROM true OR completed_spark IS DISTINCT FROM true)
            """,
            (since,),
        )
        sessions = list(cur.fetchall())
    updated = 0
    for session_id, initiated_at, notes in sessions:
        handle = _json_notes(notes).get("handle")
        if not handle:
            continue
        sql = "SELECT " + ", ".join(f'"{c}"' for c in select_cols) + ' FROM brain_index.tg_messages'
        params: tuple[Any, ...] = ()
        if time_col:
            sql += f' WHERE "{time_col}" >= %s ORDER BY "{time_col}" ASC LIMIT 200'
            params = (initiated_at,)
        else:
            sql += " LIMIT 200"
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = [dict(zip(select_cols, row)) for row in cur.fetchall()]
        matched = [row for row in rows if _message_matches_handle(row, str(handle))]
        engaged, drop_off, spark, onboarding, last_at, last_message = _completion_from_messages(matched)
        if not engaged:
            continue
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE brain_index.probe_sessions
                   SET engaged = true,
                       drop_off_message = %s,
                       completed_spark = completed_spark OR %s,
                       completed_onboarding = completed_onboarding OR %s,
                       last_message_at = COALESCE(%s, last_message_at),
                       last_message = COALESCE(%s, last_message)
                 WHERE id = %s
                """,
                (drop_off, spark, onboarding, last_at, last_message, session_id),
            )
        updated += 1
    return updated


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one probe outreach cycle.")
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--disable-file", type=Path, default=DEFAULT_DISABLE_FILE)
    parser.add_argument("--pull-fp-champions", action="store_true", help="pull FP Game Champions into probe_pool before sending")
    parser.add_argument("--evaluate-due", action="store_true", help="also evaluate sessions silent for 24h")
    parser.add_argument("--sync-outcomes", action="store_true", help="sync probe outcomes from brain_index.tg_messages before evaluation")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if disabled(args.disable_file):
        result = ProbeRunResult(True, 0, 0, 0, "disabled")
        if args.json:
            data = result.__dict__.copy()
            data["evaluated"] = 0
            print(json.dumps(data, sort_keys=True))
        else:
            print("probe: disabled")
        return 0
    pulled = None
    if args.pull_fp_champions:
        try:
            from tools.outreach.fp_champions_puller import pull_into_probe_pool

            pulled = pull_into_probe_pool()
        except Exception as exc:
            pulled = {"fetched": 0, "inserted": 0, "error": exc.__class__.__name__}
    result = run_probe_cycle(ops_ledger=args.ops_ledger, disable_file=args.disable_file)
    evaluated = 0
    if args.evaluate_due and not result.disabled and result.reason != "db_unavailable":
        conn = connect_from_env()
        try:
            if args.sync_outcomes:
                refresh_session_outcomes(conn=conn)
            evaluated = evaluate_due_sessions(conn=conn)
        finally:
            conn.close()
    if args.json:
        data = result.__dict__.copy()
        data["evaluated"] = evaluated
        if pulled is not None:
            data["fp_champions_pull"] = pulled
        print(json.dumps(data, sort_keys=True))
    else:
        print(f"probe: sent={result.sent} attempted={result.attempted} rate={result.rate} reason={result.reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
