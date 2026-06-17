from __future__ import annotations

import datetime as dt
from typing import Any

from tools.benchmarks import KNOWN_EVENT_TYPES, age_days, parse_time, rate, rows_for, safe_median, score_result

AGENT = "steward"


def score(data: dict[str, Any] | None = None, *, now: dt.datetime | None = None) -> dict[str, Any]:
    current = now or dt.datetime.now(dt.timezone.utc)
    ops_rows = rows_for(data, "ops_ledger")
    known = set((data or {}).get("known_event_types") or KNOWN_EVENT_TYPES)
    seen = {str(row.get("event")) for row in ops_rows if row.get("event")}
    last_ts = max((parse_time(row.get("ts") or row.get("created_at")) for row in ops_rows), default=None)
    correction_times = {
        str(row.get("correction_id") or row.get("id")): parse_time(row.get("ts") or row.get("created_at"))
        for row in ops_rows
        if row.get("event") == "correction"
    }
    lags = []
    for row in ops_rows:
        if row.get("event") != "spec_queued":
            continue
        key = str(row.get("correction_id") or row.get("source_id") or "")
        start = correction_times.get(key)
        end = parse_time(row.get("ts") or row.get("created_at"))
        if start and end and end >= start:
            lags.append((end - start).total_seconds() / 3600.0)
    metrics = {
        "measurement_coverage": rate(len(seen & known), len(known)),
        "ledger_freshness_hours": round(((current - last_ts).total_seconds() / 3600.0), 4) if last_ts else None,
        "correction_to_build_lag_hours": safe_median(lags),
    }
    return score_result(
        AGENT,
        primary_metric=metrics["measurement_coverage"],
        metrics=metrics,
        trigger_fired=metrics["measurement_coverage"] < 0.8,
        trigger_metric="measurement_coverage" if metrics["measurement_coverage"] < 0.8 else None,
        trigger_reason=f"measurement_coverage {metrics['measurement_coverage']} below 0.8" if metrics["measurement_coverage"] < 0.8 else None,
    )

