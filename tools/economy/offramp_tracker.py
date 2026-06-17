#!/usr/bin/env python3
"""Off-ramp minimization metrics for the internal economy."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any, Iterable


@dataclass(frozen=True)
class OfframpSummary:
    period_start: str
    period_end: str
    total_cora_equivalent: float
    internal_cora_equivalent: float
    external_cora_equivalent: float
    external_extraction: float
    internal_retention_rate: float
    external_extraction_rate: float
    previous_internal_retention_rate: float | None = None

    def row(self) -> dict[str, Any]:
        data = asdict(self)
        for key in (
            "total_cora_equivalent",
            "internal_cora_equivalent",
            "external_cora_equivalent",
            "external_extraction",
            "internal_retention_rate",
            "external_extraction_rate",
        ):
            data[key] = round(float(data[key]), 4)
        return data


def summarize_exchanges(
    ledger_rows: Iterable[dict[str, Any]],
    *,
    period_start: str | date | None = None,
    period_end: str | date | None = None,
    previous_summary: OfframpSummary | dict[str, Any] | None = None,
) -> OfframpSummary:
    rows = list(ledger_rows)
    total = sum(_cora_equivalent(row) for row in rows)
    internal = sum(_cora_equivalent(row) for row in rows if bool(row.get("internal_flag", True)))
    external = max(0.0, total - internal)
    extraction = sum(max(0.0, float(row.get("external_extraction") or 0.0)) for row in rows)
    previous_rate = None
    if previous_summary is not None:
        previous_rate = (
            previous_summary.internal_retention_rate
            if isinstance(previous_summary, OfframpSummary)
            else float(previous_summary.get("internal_retention_rate") or 0.0)
        )
    return OfframpSummary(
        period_start=_period(period_start, fallback="start"),
        period_end=_period(period_end, fallback="end"),
        total_cora_equivalent=total,
        internal_cora_equivalent=internal,
        external_cora_equivalent=external,
        external_extraction=extraction,
        internal_retention_rate=internal / total if total else 0.0,
        external_extraction_rate=extraction / total if total else 0.0,
        previous_internal_retention_rate=previous_rate,
    )


def retention_surface(summary: OfframpSummary | dict[str, Any]) -> str:
    row = summary.row() if isinstance(summary, OfframpSummary) else dict(summary)
    retained = round(float(row.get("internal_retention_rate") or 0.0) * 100)
    previous = row.get("previous_internal_retention_rate")
    if previous is None:
        return f"Network retained {retained}% of value internally this week."
    direction = "up" if float(row["internal_retention_rate"]) >= float(previous) else "down"
    prev_pct = round(float(previous) * 100)
    return f"Network retained {retained}% of value internally this week ({direction} from {prev_pct}% last week)."


def offramp_alternative_prompt(
    *,
    identifier: str,
    cora_balance: float,
    requested_need: str,
    internal_cost_cora: float,
) -> str | None:
    if float(cora_balance or 0.0) < float(internal_cost_cora or 0.0):
        return None
    return (
        f"{identifier} has {int(cora_balance)} CORA credits. "
        f"The {requested_need} can be met internally for {int(internal_cost_cora)} credits. "
        "Offer credits before any fiat off-ramp."
    )


def _cora_equivalent(row: dict[str, Any]) -> float:
    if "cora_equivalent" in row:
        return max(0.0, float(row.get("cora_equivalent") or 0.0))
    return max(0.0, float(row.get("amount") or 0.0) * float(row.get("exchange_rate_to_cora") or 0.0))


def _period(value: str | date | None, *, fallback: str) -> str:
    if value is not None:
        return value.isoformat() if isinstance(value, date) else str(value)
    now = datetime.now(timezone.utc).date()
    return now.isoformat() if fallback == "end" else now.replace(day=1).isoformat()

