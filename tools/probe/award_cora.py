#!/usr/bin/env python3
"""Award CORA credits for completed probe conversations."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.probe import rate_governor

EVENT_TYPE = "probe_conversation_complete"
BASE_POINTS = 10
SPECIFIC_GAP_BONUS = 5
VALIDATED_CORRECTION_BONUS = 10
DEFAULT_CLOSE_AFTER = timedelta(hours=72)


@dataclass(frozen=True)
class ProbeAward:
    probe_id: str
    tester_identifier: str
    points: int
    base_points: int
    specific_gap_bonus: int
    validated_correction_bonus: int
    message_count: int
    completed_spark: bool
    corrections_triggered: int
    inserted: bool


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def connect_from_env() -> Any:
    return rate_governor.connect_from_env()


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


def ensure_schema(conn: Any) -> None:
    """Apply the narrow idempotent migration this awarder requires."""
    with conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS brain_index")
        cur.execute("ALTER TABLE brain_index.probe_sessions ADD COLUMN IF NOT EXISTS tester_identifier TEXT")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS brain_index.cora_ledger (
                id BIGSERIAL PRIMARY KEY,
                event_type TEXT NOT NULL,
                tester_identifier TEXT NOT NULL,
                points INT NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (source_type, source_id)
            )
            """
        )


def _json_notes(value: Any) -> dict[str, Any]:
    if not isinstance(value, str):
        return {}
    first = value.splitlines()[0] if value.strip() else ""
    try:
        data = json.loads(first)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _tester_identifier(explicit: Any, notes: Any) -> str | None:
    if explicit:
        return str(explicit).strip() or None
    data = _json_notes(notes)
    for key in ("tester_identifier", "email", "handle", "telegram_handle"):
        value = data.get(key)
        if value:
            return str(value).strip() or None
    return None


def _specific_gap_reported(notes: Any, last_message: Any) -> bool:
    data = _json_notes(notes)
    for key in ("specific_gap_reported", "gap_reported", "correction_reported"):
        if data.get(key) is True:
            return True
    if data.get("report_type") in {"gap", "correction"}:
        return True
    gaps = data.get("gaps")
    if isinstance(gaps, list) and any(str(gap).strip() for gap in gaps):
        return True
    text = f"{notes or ''}\n{last_message or ''}".lower()
    return any(marker in text for marker in ("specific gap:", "gap:", "correction:", "wrong because", "should say"))


def _parse_time(value: Any) -> datetime | None:
    return rate_governor.parse_time(value)


def _is_closed(*, completed_spark: bool, last_message_at: Any, initiated_at: Any, now: datetime, close_after: timedelta) -> bool:
    if completed_spark:
        return True
    marker = _parse_time(last_message_at) or _parse_time(initiated_at)
    return bool(marker and marker <= now - close_after)


def _fetch_candidate_rows(conn: Any, *, now: datetime, close_after: timedelta) -> list[tuple[Any, ...]]:
    columns = _table_columns(conn, "probe_sessions")
    message_expr = "message_count" if "message_count" in columns else "drop_off_message"
    tester_expr = "tester_identifier" if "tester_identifier" in columns else "NULL AS tester_identifier"
    cutoff = now - close_after
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT probe_id,
                   {tester_expr},
                   notes,
                   COALESCE(completed_spark, false) AS completed_spark,
                   COALESCE({message_expr}, 0) AS message_count,
                   COALESCE(corrections_triggered, 0) AS corrections_triggered,
                   last_message_at,
                   initiated_at,
                   last_message
              FROM brain_index.probe_sessions
             WHERE (
                    COALESCE(completed_spark, false) = true
                    OR COALESCE({message_expr}, 0) >= 5
                   )
               AND (
                    COALESCE(completed_spark, false) = true
                    OR COALESCE(last_message_at, initiated_at) <= %s
                   )
             ORDER BY initiated_at ASC
            """,
            (cutoff,),
        )
        return list(cur.fetchall())


def _insert_award(conn: Any, award: ProbeAward, *, now: datetime) -> bool:
    metadata = {
        "event_type": EVENT_TYPE,
        "base_points": award.base_points,
        "specific_gap_bonus": award.specific_gap_bonus,
        "validated_correction_bonus": award.validated_correction_bonus,
        "message_count": award.message_count,
        "completed_spark": award.completed_spark,
        "corrections_triggered": award.corrections_triggered,
    }
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO brain_index.cora_ledger
                (event_type, tester_identifier, points, source_type, source_id, metadata, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_type, source_id) DO NOTHING
            RETURNING id
            """,
            (
                EVENT_TYPE,
                award.tester_identifier,
                award.points,
                "probe_sessions",
                award.probe_id,
                json.dumps(metadata, sort_keys=True),
                now,
            ),
        )
        return cur.fetchone() is not None


def award_cora(
    *,
    conn: Any | None = None,
    connector: Any = connect_from_env,
    now: datetime | None = None,
    close_after: timedelta = DEFAULT_CLOSE_AFTER,
) -> list[ProbeAward]:
    current = now or utc_now()
    own_conn = conn is None
    db = conn or connector()
    try:
        ensure_schema(db)
        awards: list[ProbeAward] = []
        for row in _fetch_candidate_rows(db, now=current, close_after=close_after):
            (
                probe_id,
                tester_identifier_value,
                notes,
                completed_spark,
                message_count,
                corrections_triggered,
                last_message_at,
                initiated_at,
                last_message,
            ) = row
            completed = bool(completed_spark)
            count = int(message_count or 0)
            if not completed and count < 5:
                continue
            if not _is_closed(
                completed_spark=completed,
                last_message_at=last_message_at,
                initiated_at=initiated_at,
                now=current,
                close_after=close_after,
            ):
                continue
            tester = _tester_identifier(tester_identifier_value, notes)
            if not tester:
                continue
            correction_count = int(corrections_triggered or 0)
            gap_bonus = SPECIFIC_GAP_BONUS if _specific_gap_reported(notes, last_message) else 0
            correction_bonus = VALIDATED_CORRECTION_BONUS if correction_count > 0 else 0
            pending = ProbeAward(
                probe_id=str(probe_id),
                tester_identifier=tester,
                points=BASE_POINTS + gap_bonus + correction_bonus,
                base_points=BASE_POINTS,
                specific_gap_bonus=gap_bonus,
                validated_correction_bonus=correction_bonus,
                message_count=count,
                completed_spark=completed,
                corrections_triggered=correction_count,
                inserted=False,
            )
            inserted = _insert_award(db, pending, now=current)
            if inserted:
                awards.append(
                    ProbeAward(
                        probe_id=pending.probe_id,
                        tester_identifier=pending.tester_identifier,
                        points=pending.points,
                        base_points=pending.base_points,
                        specific_gap_bonus=pending.specific_gap_bonus,
                        validated_correction_bonus=pending.validated_correction_bonus,
                        message_count=pending.message_count,
                        completed_spark=pending.completed_spark,
                        corrections_triggered=pending.corrections_triggered,
                        inserted=True,
                    )
                )
        return awards
    finally:
        if own_conn and hasattr(db, "close"):
            db.close()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Award CORA credits for closed probe conversations.")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    awards = award_cora()
    if args.json:
        print(json.dumps({"awarded": len(awards), "awards": [award.__dict__ for award in awards]}, sort_keys=True))
    else:
        print(f"cora_probe_awards: awarded={len(awards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
