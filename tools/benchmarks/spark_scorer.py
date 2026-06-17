from __future__ import annotations

import datetime as dt
from typing import Any

from tools.benchmarks import rate, rows_for, safe_median, score_result

AGENT = "spark"


def _message_count(row: dict[str, Any]) -> int:
    for key in ("message_count", "messages", "last_message_number", "drop_off_message"):
        value = row.get(key)
        if isinstance(value, list):
            return len(value)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def score(data: dict[str, Any] | None = None, *, now: dt.datetime | None = None) -> dict[str, Any]:
    sessions = rows_for(data, "probe_sessions")
    completed = sum(1 for row in sessions if bool(row.get("completed_spark")))
    counts = [_message_count(row) for row in sessions]
    drop_off = safe_median([count for count in counts if count > 0])
    metrics = {
        "routing_completion": rate(completed, len(sessions)),
        "drop_off_message": drop_off,
        "conversation_continue_rate": rate(sum(1 for count in counts if count >= 3), len(sessions)),
    }
    return score_result(
        AGENT,
        primary_metric=metrics["routing_completion"],
        metrics=metrics,
        trigger_fired=bool(sessions) and drop_off < 3,
        trigger_metric="drop_off_message" if sessions and drop_off < 3 else None,
        trigger_reason=f"median drop-off message {drop_off} below 3" if sessions and drop_off < 3 else None,
    )

