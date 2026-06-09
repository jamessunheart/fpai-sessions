"""
Money ledger — Money view.

Reads core/STATE/ledger.json (costs + revenue), aggregates totals, identifies
the biggest cost leak. Revenue is a v0 placeholder (last-known); future versions
will pull live counters from booking + concierge services.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from app.config import settings
from app.models import CostItem, EngineRole, MoneyView, RevenueItem

logger = logging.getLogger(__name__)


def _ledger_path() -> Path:
    return Path(settings.COCKPIT_ROOT) / settings.STATE_SUBDIR / "ledger.json"


def _parse_dt(raw) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except Exception:
        return None


def _load_raw() -> Dict:
    path = _ledger_path()
    if not path.exists():
        logger.error("ledger.json not found at %s", path)
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logger.error("Failed to read %s: %s", path, e)
        return {}


def build_money_view() -> MoneyView:
    raw = _load_raw()

    costs: list[CostItem] = []
    for item in raw.get("costs_monthly_usd", []):
        try:
            role = EngineRole(item.get("engine_role", "unknown"))
        except ValueError:
            role = EngineRole.UNKNOWN
        costs.append(
            CostItem(
                name=item["name"],
                id=item.get("id", item["name"]),
                category=item.get("category", "other"),
                engine_role=role,
                monthly_usd=float(item.get("monthly_usd", 0)),
                purpose=item.get("purpose", ""),
                kill_candidate=bool(item.get("kill_candidate", False)),
            )
        )

    revenue: list[RevenueItem] = []
    rev_raw = raw.get("revenue_monthly", {})
    for stream, payload in rev_raw.items():
        if not isinstance(payload, dict):
            continue
        revenue.append(
            RevenueItem(
                stream=stream,
                revenue_usd=float(payload.get("revenue_usd", 0)),
                inquiries=payload.get("inquiries"),
                bookings_confirmed=payload.get("bookings_confirmed"),
                active_tenants=payload.get("active_tenants"),
                last30d_revenue_usd=payload.get("last30d_revenue_usd"),
                last30d_txns=payload.get("last30d_txns"),
                lifetime_txns=payload.get("lifetime_txns"),
                lifetime_revenue_usd=payload.get("lifetime_revenue_usd"),
                activity_summary=payload.get("activity_summary"),
                as_of=_parse_dt(payload.get("as_of")),
                note=payload.get("_note"),
            )
        )

    total_cost = sum(c.monthly_usd for c in costs)
    total_revenue = sum(r.revenue_usd for r in revenue)
    biggest = max(costs, key=lambda c: c.monthly_usd) if costs else None

    by_role: Dict[str, float] = {}
    for c in costs:
        by_role[c.engine_role.value] = round(by_role.get(c.engine_role.value, 0) + c.monthly_usd, 2)

    return MoneyView(
        costs=sorted(costs, key=lambda c: -c.monthly_usd),
        revenue=revenue,
        total_cost_monthly_usd=round(total_cost, 2),
        total_revenue_monthly_usd=round(total_revenue, 2),
        net_monthly_usd=round(total_revenue - total_cost, 2),
        biggest_leak=biggest,
        cost_by_engine_role=by_role,
    )
