"""Time-bucket rollups (daily / weekly / monthly) + reconciliation vs ``cost_actuals``."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from ..budget import BudgetLedgerRow, list_cost_actuals
from ..metering import METERING_VERSION
from ..models.database import async_session

_ROLLUP_VERSION = "1.0.0"
_GRANULARITIES = frozenset({"daily", "weekly", "monthly"})


def _iso_week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _period_key(d: date, granularity: str) -> str:
    if granularity == "daily":
        return d.isoformat()
    if granularity == "monthly":
        return d.strftime("%Y-%m")
    return _iso_week_key(d)


async def _daily_metrics(since: datetime, until: datetime) -> list[dict[str, Any]]:
    """Per-calendar-day (UTC) aggregates from ``budget_ledger``."""
    async with async_session() as session:
        origin_rows = (
            await session.execute(
                select(
                    func.date(BudgetLedgerRow.timestamp).label("d"),
                    func.coalesce(BudgetLedgerRow.origin, ""),
                    func.sum(BudgetLedgerRow.estimated_cost_usd),
                    func.count(),
                )
                .where(BudgetLedgerRow.timestamp >= since)
                .where(BudgetLedgerRow.timestamp < until)
                .group_by(func.date(BudgetLedgerRow.timestamp), func.coalesce(BudgetLedgerRow.origin, ""))
                .order_by(func.date(BudgetLedgerRow.timestamp))
            )
        ).all()

        anth_rows = (
            await session.execute(
                select(
                    func.date(BudgetLedgerRow.timestamp).label("d"),
                    func.sum(BudgetLedgerRow.estimated_cost_usd),
                    func.coalesce(func.sum(BudgetLedgerRow.tokens_in), 0),
                    func.coalesce(func.sum(BudgetLedgerRow.tokens_out), 0),
                )
                .where(BudgetLedgerRow.timestamp >= since)
                .where(BudgetLedgerRow.timestamp < until)
                .where(BudgetLedgerRow.provider == "anthropic")
                .group_by(func.date(BudgetLedgerRow.timestamp))
                .order_by(func.date(BudgetLedgerRow.timestamp))
            )
        ).all()

    by_day: dict[str, dict[str, Any]] = {}
    for d, origin, usd, n in origin_rows:
        ds = str(d)
        if ds not in by_day:
            by_day[ds] = {
                "date": ds,
                "usd": 0.0,
                "calls": 0,
                "by_origin": defaultdict(float),
                "anthropic_usd": 0.0,
                "tokens_in_anthropic": 0,
                "tokens_out_anthropic": 0,
            }
        by_day[ds]["usd"] += float(usd or 0)
        by_day[ds]["calls"] += int(n or 0)
        by_day[ds]["by_origin"][origin or ""] += float(usd or 0)

    for d, ausd, tin, tout in anth_rows:
        ds = str(d)
        if ds not in by_day:
            by_day[ds] = {
                "date": ds,
                "usd": 0.0,
                "calls": 0,
                "by_origin": defaultdict(float),
                "anthropic_usd": 0.0,
                "tokens_in_anthropic": 0,
                "tokens_out_anthropic": 0,
            }
        by_day[ds]["anthropic_usd"] = float(ausd or 0)
        by_day[ds]["tokens_in_anthropic"] = int(tin or 0)
        by_day[ds]["tokens_out_anthropic"] = int(tout or 0)

    return [by_day[k] for k in sorted(by_day.keys())]


def _fold_buckets(daily: list[dict[str, Any]], granularity: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in daily:
        d = date.fromisoformat(row["date"])
        key = _period_key(d, granularity)
        if key not in buckets:
            buckets[key] = {
                "period_key": key,
                "computed_usd": 0.0,
                "computed_anthropic_usd": 0.0,
                "calls": 0,
                "tokens_in_anthropic": 0,
                "tokens_out_anthropic": 0,
                "by_origin": defaultdict(float),
            }
        b = buckets[key]
        b["computed_usd"] += float(row["usd"])
        b["computed_anthropic_usd"] += float(row.get("anthropic_usd", 0))
        b["calls"] += int(row["calls"])
        b["tokens_in_anthropic"] += int(row.get("tokens_in_anthropic", 0))
        b["tokens_out_anthropic"] += int(row.get("tokens_out_anthropic", 0))
        for o, v in row.get("by_origin", {}).items():
            b["by_origin"][o] += float(v)

    out = []
    for key in sorted(buckets.keys()):
        b = buckets[key]
        bo = {k: round(v, 5) for k, v in sorted(b["by_origin"].items()) if v > 0 or k == ""}
        out.append(
            {
                "period_key": key,
                "computed_usd": round(b["computed_usd"], 5),
                "computed_anthropic_usd": round(b["computed_anthropic_usd"], 5),
                "calls": b["calls"],
                "tokens_in_anthropic": b["tokens_in_anthropic"],
                "tokens_out_anthropic": b["tokens_out_anthropic"],
                "by_origin": bo,
            }
        )
    return out


async def cost_rollup_report(granularity: str = "daily", days: int = 30) -> dict[str, Any]:
    """Roll ledger spend into daily / weekly / monthly buckets (UTC)."""
    g = (granularity or "daily").strip().lower()
    if g not in _GRANULARITIES:
        raise ValueError(f"granularity must be one of {sorted(_GRANULARITIES)}")
    days = max(1, min(int(days), 366))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    daily = await _daily_metrics(since, now + timedelta(seconds=1))
    if g == "daily":
        buckets = [
            {
                "period_key": r["date"],
                "computed_usd": round(float(r["usd"]), 5),
                "computed_anthropic_usd": round(float(r.get("anthropic_usd", 0)), 5),
                "calls": int(r["calls"]),
                "tokens_in_anthropic": int(r.get("tokens_in_anthropic", 0)),
                "tokens_out_anthropic": int(r.get("tokens_out_anthropic", 0)),
                "by_origin": {k: round(v, 5) for k, v in sorted(r.get("by_origin", {}).items()) if v > 0},
            }
            for r in daily
        ]
    else:
        buckets = _fold_buckets(daily, g)

    total = sum(b["computed_usd"] for b in buckets)
    return {
        "version": _ROLLUP_VERSION,
        "granularity": g,
        "days": days,
        "generated_at": now.isoformat(),
        "metering_version": METERING_VERSION,
        "bucket_count": len(buckets),
        "computed_usd_total": round(total, 5),
        "buckets": buckets,
        "period_key_formats": {
            "daily": "YYYY-MM-DD (UTC)",
            "weekly": "YYYY-Www (ISO week, UTC date assignment)",
            "monthly": "YYYY-MM",
        },
    }


async def cost_reconciliation_report(granularity: str = "monthly", days: int = 120) -> dict[str, Any]:
    """Join rolled-up ledger estimates to ``cost_actuals`` rows (same ``period_key`` + ``granularity``)."""
    rollup = await cost_rollup_report(granularity=granularity, days=days)
    actuals = await list_cost_actuals(limit=2000)
    g = rollup["granularity"]
    act_for_g = [a for a in actuals if a["granularity"] == g]
    by_key_prov: dict[tuple[str, str], dict[str, Any]] = {}
    for a in act_for_g:
        by_key_prov[(a["period_key"], a["provider"])] = a

    rows_out: list[dict[str, Any]] = []
    for b in rollup["buckets"]:
        pk = b["period_key"]
        computed_all = b["computed_usd"]
        computed_ant = b["computed_anthropic_usd"]
        ant_actual = by_key_prov.get((pk, "anthropic"))
        all_actual = by_key_prov.get((pk, "all"))
        row: dict[str, Any] = {
            "period_key": pk,
            "computed_usd_all_providers": computed_all,
            "computed_usd_anthropic": computed_ant,
            "calls": b["calls"],
            "tokens_in_anthropic": b["tokens_in_anthropic"],
            "tokens_out_anthropic": b["tokens_out_anthropic"],
            "by_origin": b.get("by_origin", {}),
            "actual_usd_anthropic": ant_actual["amount_usd"] if ant_actual else None,
            "actual_usd_all": all_actual["amount_usd"] if all_actual else None,
            "delta_vs_anthropic_actual_usd": None,
            "delta_vs_all_actual_usd": None,
            "actual_source_anthropic": ant_actual["source"] if ant_actual else None,
            "actual_source_all": all_actual["source"] if all_actual else None,
        }
        if ant_actual is not None:
            row["delta_vs_anthropic_actual_usd"] = round(computed_ant - float(ant_actual["amount_usd"]), 5)
        if all_actual is not None:
            row["delta_vs_all_actual_usd"] = round(computed_all - float(all_actual["amount_usd"]), 5)
        rows_out.append(row)

    unmatched_actuals = [
        a for a in act_for_g if not any(a["period_key"] == b["period_key"] for b in rollup["buckets"])
    ]

    return {
        "version": _ROLLUP_VERSION,
        "granularity": g,
        "days": days,
        "generated_at": rollup["generated_at"],
        "metering_version": METERING_VERSION,
        "reconciliation_rows": rows_out,
        "actuals_stored": len(act_for_g),
        "actuals_outside_rollup_window": unmatched_actuals[:50],
        "how_to_use": [
            "POST /api/v1/costs/actual (admin) with body matching rollup keys, e.g. "
            '{"granularity":"monthly","period_key":"2026-04","provider":"anthropic","amount_usd":123.45,"source":"anthropic_console"}.',
            "Use provider=all for a total invoice line that includes every provider in the ledger for that bucket.",
            "Ledger only includes spend recorded on this fp-index host unless other surfaces push data — "
            "large deltas usually mean off-ledger usage (other servers, Cursor, shared API keys).",
        ],
    }
