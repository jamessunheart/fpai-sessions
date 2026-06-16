#!/usr/bin/env python3
"""Probe signal helpers for horizon scanner and morning digest wiring."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.probe import rate_governor


@dataclass(frozen=True)
class ProbeSummary:
    sent: int
    engaged: int
    completed_spark: int
    avg_quality: float | None
    next_rate: int
    reason: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def daily_summary(conn: Any, *, now: datetime | None = None, ops_ledger: Path = rate_governor.DEFAULT_OPS_LEDGER) -> ProbeSummary:
    current = now or utc_now()
    start = current - timedelta(days=1)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*)::int,
                COUNT(*) FILTER (WHERE engaged IS TRUE)::int,
                COUNT(*) FILTER (WHERE completed_spark IS TRUE)::int,
                AVG(quality_score)
              FROM brain_index.probe_sessions
             WHERE initiated_at >= %s
            """,
            (start,),
        )
        sent, engaged, completed, avg_quality = cur.fetchone()
    decision = rate_governor.decide_rate(conn=conn, ops_ledger=ops_ledger, now=current)
    return ProbeSummary(
        sent=int(sent or 0),
        engaged=int(engaged or 0),
        completed_spark=int(completed or 0),
        avg_quality=float(avg_quality) if avg_quality is not None else None,
        next_rate=decision.count,
        reason=decision.reason,
    )


def format_morning_digest_section(summary: ProbeSummary) -> str:
    quality = "n/a" if summary.avg_quality is None else f"{summary.avg_quality:.1f}"
    return (
        "Probe section\n"
        f"Probes sent yesterday: {summary.sent} | Engaged: {summary.engaged} | "
        f"Completed Spark: {summary.completed_spark} | Avg quality: {quality}\n"
        f"Rate next cycle: {summary.next_rate} ({summary.reason})"
    )


def horizon_probe_flags(conn: Any, *, now: datetime | None = None) -> list[str]:
    current = now or utc_now()
    since = current - timedelta(days=7)
    flags: list[str] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*)::int,
                   COUNT(*) FILTER (WHERE engaged IS TRUE)::int,
                   AVG(quality_score)
              FROM brain_index.probe_sessions
             WHERE initiated_at >= %s
            """,
            (since,),
        )
        total, engaged, avg_quality = cur.fetchone()
    total = int(total or 0)
    engaged = int(engaged or 0)
    if total >= 5 and engaged / max(total, 1) < 0.30:
        flags.append(f"Probe drop rate spiking: {engaged}/{total} engaged in 7d")
    if avg_quality is not None and float(avg_quality) < 0.50:
        flags.append(f"Probe quality declining: avg {float(avg_quality):.2f}")
    return flags
