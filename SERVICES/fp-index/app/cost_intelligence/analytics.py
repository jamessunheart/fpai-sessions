"""Aggregate API spend from budget_ledger for self-optimization."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select

from ..budget import BudgetLedgerRow, get_budget_status
from ..metering import METERING_VERSION
from ..models.database import async_session

logger = logging.getLogger(__name__)


def _hints(by_action: dict[str, float], by_provider: dict[str, float]) -> list[str]:
    hints: list[str] = []
    if not by_action:
        hints.append("No ledger rows in this window — either idle period or spend not being logged.")
        return hints
    top_a = max(by_action.items(), key=lambda x: x[1])
    top_p = max(by_provider.items(), key=lambda x: x[1]) if by_provider else ("", 0.0)
    hints.append(f"Largest cost bucket by action_type: {top_a[0]} (~${top_a[1]:.3f}).")
    if top_p[0]:
        hints.append(f"Largest provider: {top_p[0]} (~${top_p[1]:.3f}).")
    if by_action.get("briefing_synthesis", 0) > 0.15:
        hints.append(
            "briefing_synthesis is material — ensure scans are not re-synthesizing the same day "
            "(default: one Claude pass per calendar day; set FPI_BRIEFING_RESYNTH_EVERY_SCAN=1 only if needed)."
        )
    if by_action.get("adoption_evaluation", 0) > 0.15:
        hints.append(
            "adoption_evaluation stacks with pending execution briefs — reduce scan frequency "
            "or clear stale pending briefs if costs run high."
        )
    return hints[:6]


async def cost_report(window_days: int = 7) -> dict[str, Any]:
    """Structured spend intelligence from budget_ledger + budget caps."""
    window_days = max(1, min(int(window_days), 90))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=window_days)

    status = await get_budget_status()

    async with async_session() as session:
        rows = (await session.execute(
            select(func.count(), func.coalesce(func.sum(BudgetLedgerRow.estimated_cost_usd), 0.0))
            .where(BudgetLedgerRow.timestamp >= since)
        )).one()
        n_calls = int(rows[0] or 0)
        total_usd = float(rows[1] or 0.0)

        by_provider = dict(
            (await session.execute(
                select(BudgetLedgerRow.provider, func.sum(BudgetLedgerRow.estimated_cost_usd))
                .where(BudgetLedgerRow.timestamp >= since)
                .group_by(BudgetLedgerRow.provider)
            )).all()
        )
        by_model = dict(
            (await session.execute(
                select(BudgetLedgerRow.model, func.sum(BudgetLedgerRow.estimated_cost_usd))
                .where(BudgetLedgerRow.timestamp >= since)
                .where(BudgetLedgerRow.model != "")
                .group_by(BudgetLedgerRow.model)
            )).all()
        )
        by_action = dict(
            (await session.execute(
                select(BudgetLedgerRow.action_type, func.sum(BudgetLedgerRow.estimated_cost_usd))
                .where(BudgetLedgerRow.timestamp >= since)
                .group_by(BudgetLedgerRow.action_type)
            )).all()
        )

        daily_rows = (
            await session.execute(
                select(
                    func.date(BudgetLedgerRow.timestamp).label("d"),
                    func.sum(BudgetLedgerRow.estimated_cost_usd),
                    func.count(),
                )
                .where(BudgetLedgerRow.timestamp >= since)
                .group_by(func.date(BudgetLedgerRow.timestamp))
                .order_by(func.date(BudgetLedgerRow.timestamp))
            )
        ).all()

        tok_row = (
            await session.execute(
                select(
                    func.coalesce(func.sum(BudgetLedgerRow.tokens_in), 0),
                    func.coalesce(func.sum(BudgetLedgerRow.tokens_out), 0),
                ).where(BudgetLedgerRow.timestamp >= since).where(BudgetLedgerRow.provider == "anthropic")
            )
        ).one()
        tokens_in_total = int(tok_row[0] or 0)
        tokens_out_total = int(tok_row[1] or 0)

        by_origin = dict(
            (await session.execute(
                select(
                    func.coalesce(BudgetLedgerRow.origin, ""),
                    func.sum(BudgetLedgerRow.estimated_cost_usd),
                )
                .where(BudgetLedgerRow.timestamp >= since)
                .group_by(func.coalesce(BudgetLedgerRow.origin, ""))
            )).all()
        )

    by_provider = {k: round(float(v), 5) for k, v in by_provider.items()}
    by_model = {k: round(float(v), 5) for k, v in by_model.items()}
    by_action = {k: round(float(v), 5) for k, v in by_action.items()}
    by_origin = {k: round(float(v), 5) for k, v in by_origin.items()}

    daily = [
        {"date": str(r[0]), "usd": round(float(r[1] or 0), 5), "calls": int(r[2] or 0)}
        for r in daily_rows
    ]

    return {
        "version": "1.2.0",
        "window_days": window_days,
        "generated_at": now.isoformat(),
        "ledger": {
            "call_count": n_calls,
            "estimated_usd_total": round(total_usd, 5),
            "tokens_in_total_anthropic": tokens_in_total,
            "tokens_out_total_anthropic": tokens_out_total,
            "by_provider": by_provider,
            "by_model": by_model,
            "by_action_type": by_action,
            "by_origin": by_origin,
            "daily": daily,
        },
        "budget_caps": {
            "daily_limit_usd": status["daily"]["limit"],
            "daily_spent_usd": status["daily"]["spent"],
            "daily_pct_used": status["daily"]["pct_used"],
            "monthly_limit_usd": status["monthly"]["limit"],
            "monthly_spent_usd": status["monthly"]["spent"],
            "monthly_pct_used": status["monthly"]["pct_used"],
            "per_action_limit_usd": status["per_action_limit"],
            "paused": status.get("paused", False),
        },
        "coverage_gaps": [
            "fp-index: engine/actuators/autonomous_actions use async record_spend; field_sensor, probes, proposer, conscience use sync metering (same table, token-derived USD).",
            "fp-index companion still uses raw httpx to Anthropic — usage not in this ledger until wired to metering or SDK.",
            "Outside fp-index (e.g. MetaClaw/OpenClaw on other hosts, Cursor, local dev) still bills the same Anthropic org but does not write this ledger — reconcile in Console by API key.",
            "Cross-host: set FPI_COST_ORIGIN per host and use GET /api/v1/costs/rollup + POST /api/v1/costs/actual for billed amounts; only this DB aggregates origins that wrote here.",
        ],
        "reconciliation": {
            "metering_version": METERING_VERSION,
            "pricing_basis": (
                "USD = sum(ledger.estimated_cost_usd); each row uses budget.estimate_cost(provider, model, tokens_in, tokens_out) "
                "from budget.COST_ESTIMATES (list prices / Mtok). Match Anthropic Console Usage for the same dates; "
                "credits, taxes, rounding, or non-fp-index keys explain deltas."
            ),
            "how_to_baseline": [
                "Anthropic Console → Usage → same calendar window as `window_days`.",
                "If totals diverge >5%, split API keys (fp-index vs MetaClaw vs dev) and compare per-key spend to `ledger.by_model` / `by_action_type`.",
                "Export Console CSV and compare summed cost to `ledger.estimated_usd_total` + token rows.",
                "Store invoice lines via POST /api/v1/costs/actual then GET /api/v1/costs/reconciliation for bucket deltas.",
            ],
        },
        "optimization_hints": _hints(by_action, by_provider),
    }


async def cost_context_block(window_days: int = 7) -> str:
    """Compact block injected into companion WIDE context."""
    try:
        r = await cost_report(window_days=window_days)
    except Exception as e:
        logger.debug(f"[COST_INTEL] report failed: {e}")
        return "API cost intelligence: unavailable (ledger read error)."

    L = r["ledger"]
    caps = r["budget_caps"]
    lines = [
        "--- API COST SELF-PULSE (token-metered where wired; reconcile vs Anthropic Console) ---",
        f"Last {r['window_days']}d: ~${L['estimated_usd_total']:.3f} across {L['call_count']} ledger rows; "
        f"Anthropic tokens in/out (window): {L.get('tokens_in_total_anthropic', 0)}/{L.get('tokens_out_total_anthropic', 0)}.",
        f"Budget: ${caps['daily_spent_usd']:.2f}/${caps['daily_limit_usd']:.2f} today ({caps['daily_pct_used']:.0f}% of daily), "
        f"${caps['monthly_spent_usd']:.2f}/${caps['monthly_limit_usd']:.2f} this month ({caps['monthly_pct_used']:.0f}% of monthly), "
        f"max ${caps['per_action_limit_usd']:.2f}/action.",
    ]
    if caps.get("paused"):
        lines.append("BUDGET PAUSED — autonomous API spend should be off.")
    if L["by_action_type"]:
        top3 = sorted(L["by_action_type"].items(), key=lambda x: -x[1])[:3]
        lines.append("Top action_types: " + ", ".join(f"{k}=${v:.3f}" for k, v in top3))
    if L["by_provider"]:
        lines.append("By provider: " + ", ".join(f"{k}=${v:.3f}" for k, v in sorted(L['by_provider'].items(), key=lambda x: -x[1])[:4]))
    if L["by_model"]:
        lines.append("By model: " + ", ".join(f"{k}=${v:.3f}" for k, v in sorted(L['by_model'].items(), key=lambda x: -x[1])[:4]))
    for h in r.get("optimization_hints", [])[:3]:
        lines.append(f"Hint: {h}")
    lines.append(f"Coverage: {r['coverage_gaps'][1][:200]}...")
    return "\n".join(lines)
