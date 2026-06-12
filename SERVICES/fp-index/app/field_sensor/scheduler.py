"""Event-driven scheduler.

Sensing runs hourly (cheap, no LLM). Reflection runs only on events
that pass the significance gate — so reflection cadence is determined
by the field itself, not a cron.

Budget safety: hard cap of N reflections per day to prevent runaway
spend if the field explodes (e.g. a major conference week).
"""
from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone

from .gate import passes_gate, GATE_VERSION
from .reflect import reflect_on_event
from .registry import EVENTS_DB, ensure_brain_dir, registry_stats
from .sensors import sense_once, get_unreflected_events, mark_reflected

logger = logging.getLogger(__name__)

MAX_REFLECTIONS_PER_CYCLE = int(os.getenv("FPI_FIELD_MAX_REFLECTIONS", "2"))
MAX_REFLECTIONS_PER_DAY = int(os.getenv("FPI_FIELD_MAX_DAILY", "6"))


def _reflections_today() -> int:
    ensure_brain_dir()
    with sqlite3.connect(EVENTS_DB) as conn:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = conn.execute(
            "SELECT COUNT(*) FROM events WHERE reflected = 1 AND gated_passed = 1 "
            "AND reflected_at LIKE ?",
            (f"{today}%",),
        ).fetchone()
        return row[0] if row else 0


async def run_field_sensor_cycle() -> dict:
    """One full cycle: sense → gate → reflect (bounded) → log.

    Safe to call repeatedly; dedups via event_id. Idempotent.
    """
    cycle_start = datetime.now(timezone.utc)
    stats = {
        "cycle_start": cycle_start.isoformat(),
        "sensed": 0,
        "gated_passed": 0,
        "reflected": 0,
        "skipped_daily_cap": 0,
        "errors": 0,
        "gate_version": GATE_VERSION,
    }

    try:
        await sense_once()
    except Exception as e:
        logger.exception(f"[FIELD] sense_once failed: {e}")
        stats["errors"] += 1

    unreflected = get_unreflected_events(limit=200)
    stats["sensed"] = len(unreflected)

    scored = []
    for ev in unreflected:
        passed, score = passes_gate(ev)
        scored.append((ev, passed, score))
        if not passed:
            mark_reflected(ev["event_id"], score, gated=False)
    passed_events = [(ev, s) for (ev, p, s) in scored if p]
    passed_events.sort(key=lambda x: x[1], reverse=True)
    stats["gated_passed"] = len(passed_events)

    daily_used = _reflections_today()
    remaining_daily = max(0, MAX_REFLECTIONS_PER_DAY - daily_used)
    budget = min(MAX_REFLECTIONS_PER_CYCLE, remaining_daily)

    for ev, score in passed_events[:budget]:
        try:
            result = await asyncio.to_thread(reflect_on_event, ev, score)
            if result:
                stats["reflected"] += 1
            mark_reflected(ev["event_id"], score, gated=True)
        except Exception as e:
            logger.exception(f"[FIELD] reflect failed for {ev.get('event_id')}: {e}")
            stats["errors"] += 1

    stats["skipped_daily_cap"] = max(0, len(passed_events) - budget)
    stats["cycle_end"] = datetime.now(timezone.utc).isoformat()
    stats["registry"] = registry_stats()

    logger.info(
        f"[FIELD] cycle: sensed={stats['sensed']} gated={stats['gated_passed']} "
        f"reflected={stats['reflected']} skipped_cap={stats['skipped_daily_cap']} "
        f"errors={stats['errors']}"
    )
    return stats
