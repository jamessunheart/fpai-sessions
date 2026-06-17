from __future__ import annotations

import datetime as dt
from typing import Any

from tools.benchmarks import grouped_rates, per_day, rate, rows_for, score_result

AGENT = "beacon"


def score(data: dict[str, Any] | None = None, *, now: dt.datetime | None = None) -> dict[str, Any]:
    pool = rows_for(data, "probe_pool")
    sessions = rows_for(data, "probe_sessions")
    pool_by_source = {str(row.get("source") or "unknown"): 0 for row in pool}
    for row in pool:
        pool_by_source[str(row.get("source") or "unknown")] = pool_by_source.get(str(row.get("source") or "unknown"), 0) + 1

    engaged_by_source: dict[str, int] = {source: 0 for source in pool_by_source}
    for row in sessions:
        source = str(row.get("source") or "unknown")
        if bool(row.get("engaged")):
            engaged_by_source[source] = engaged_by_source.get(source, 0) + 1

    source_quality = {
        source: {
            "contacts": count,
            "engaged": engaged_by_source.get(source, 0),
            "rate": rate(engaged_by_source.get(source, 0), count),
        }
        for source, count in sorted(pool_by_source.items())
    }
    primary = rate(sum(engaged_by_source.values()), len(pool))
    precision = rate(sum(1 for row in pool if float(row.get("discovery_score") or 0) >= 0.7), len(pool))
    triggered_sources = [source for source, row in source_quality.items() if row["contacts"] >= 10 and row["rate"] < 0.4]
    metrics = {
        "discovery_rate": per_day(pool, "created_at", now=now),
        "source_quality": source_quality,
        "signal_precision": precision,
    }
    return score_result(
        AGENT,
        primary_metric=primary,
        metrics=metrics,
        trigger_fired=bool(triggered_sources),
        trigger_metric="source_quality" if triggered_sources else None,
        trigger_reason=f"source_quality below 0.4 for {', '.join(triggered_sources)}" if triggered_sources else None,
    )
