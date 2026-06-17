from __future__ import annotations

import datetime as dt
from typing import Any

from tools.benchmarks import grouped_rates, rate, rows_for, score_result

AGENT = "hermes"


def score(data: dict[str, Any] | None = None, *, now: dt.datetime | None = None) -> dict[str, Any]:
    pool = rows_for(data, "probe_pool")
    sessions = rows_for(data, "probe_sessions")
    sent_sessions = [row for row in sessions if row.get("sent_at") or bool(row.get("sent"))]
    contacted = sum(1 for row in pool if row.get("contacted_at") or bool(row.get("contacted")))
    response_by_channel = grouped_rates(
        sent_sessions,
        group_key="platform",
        numerator_predicate=lambda row: bool(row.get("engaged")),
    )
    costs = (data or {}).get("estimated_cost_per_send") or {}
    channel_efficiency = {
        channel: round(values["rate"] / max(float(costs.get(channel, 1.0) or 1.0), 0.0001), 4)
        for channel, values in response_by_channel.items()
    }
    triggered = [
        channel
        for channel, values in response_by_channel.items()
        if values["denominator"] >= 20 and values["rate"] < 0.2
    ]
    metrics = {
        "delivery_rate": rate(len(sent_sessions), contacted),
        "response_rate": response_by_channel,
        "channel_efficiency": channel_efficiency,
    }
    primary = {channel: values["rate"] for channel, values in response_by_channel.items()}
    return score_result(
        AGENT,
        primary_metric=primary,
        metrics=metrics,
        trigger_fired=bool(triggered),
        trigger_metric="response_rate" if triggered else None,
        trigger_reason=f"response_rate below 0.2 for {', '.join(triggered)}" if triggered else None,
    )

