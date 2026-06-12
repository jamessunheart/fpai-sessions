"""/money and /priority — Chief of Staff cross-system views.

Calls the Chief of Staff service (configured via cockpit_api_url) and formats
results for Telegram. Falls back gracefully when the service is unreachable.
"""
from __future__ import annotations

import logging

import httpx

from .. import telegram
from ..config import settings

log = logging.getLogger("streasury.handlers.cos")


def _esc(s: str) -> str:
    return telegram.esc(s)


_TIMEOUT = httpx.Timeout(8.0, connect=3.0)


async def _get(path: str) -> dict | None:
    url = f"{settings.cockpit_api_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        log.warning("Chief of Staff call failed (%s): %s", url, e)
        return None


def _service_unavailable(label: str) -> str:
    return (
        f"⚠️  Chief of Staff unreachable for {label}.\n"
        f"  • URL: <code>{_esc(settings.cockpit_api_url)}</code>\n"
        f"  • Make sure the service is running on port 8107."
    )


async def cmd_money(_chat_id: int, _args: str) -> str:
    data = await _get("/money")
    if not data:
        return _service_unavailable("/money")

    cost = data.get("total_cost_monthly_usd", 0)
    rev = data.get("total_revenue_monthly_usd", 0)
    net = data.get("net_monthly_usd", 0)
    leak = data.get("biggest_leak") or {}
    by_role = data.get("cost_by_engine_role", {})
    costs = data.get("costs", [])
    revenue_streams = data.get("revenue", [])

    lines = ["<b>💰 Money</b>"]
    lines.append(f"  Cost: <code>${cost:,.0f}/mo</code>")
    lines.append(f"  Revenue: <code>${rev:,.0f}/mo</code>")
    net_emoji = "🟢" if net >= 0 else "🔴"
    lines.append(f"  Net: {net_emoji} <code>${net:,.0f}/mo</code>")

    if by_role:
        lines.append("")
        lines.append("<b>By engine role</b>")
        role_order = ("P1", "P2", "infra", "unknown", "cruft")
        for role in role_order:
            if role in by_role:
                lines.append(f"  {role}: <code>${by_role[role]:,.0f}/mo</code>")

    if leak:
        kill = " · ⚠️ kill candidate" if leak.get("kill_candidate") else ""
        lines.append("")
        lines.append(
            f"<b>Biggest leak</b>: {_esc(leak.get('name', '?'))} · "
            f"<code>${leak.get('monthly_usd', 0):,.0f}/mo</code> · "
            f"<i>{_esc(leak.get('engine_role', '?'))}</i>{kill}"
        )

    if revenue_streams:
        lines.append("")
        lines.append("<b>Revenue activity</b>")
        for r in revenue_streams:
            stream = r.get("stream", "?")
            details = []
            if r.get("bookings_confirmed") is not None:
                details.append(f"{r['bookings_confirmed']} bookings")
            if r.get("inquiries") is not None:
                details.append(f"{r['inquiries']} inquiries")
            if r.get("active_tenants") is not None:
                details.append(f"{r['active_tenants']} tenants")
            if r.get("last30d_txns") is not None:
                details.append(f"{r['last30d_txns']} txns (30d)")
            rev_amt = r.get("revenue_usd", 0)
            amt_str = f"<code>${rev_amt:,.0f}/mo</code>" if rev_amt else "<i>$0/mo</i>"
            detail_str = " · ".join(details) if details else "—"
            lines.append(f"  • {_esc(stream)}: {detail_str} · {amt_str}")
            if r.get("lifetime_revenue_usd"):
                lines.append(f"    <i>lifetime: ${r['lifetime_revenue_usd']:,.0f} across {r.get('lifetime_txns', 0):,} txns</i>")

    if costs:
        lines.append("")
        lines.append("<b>Top costs</b>")
        for c in costs[:6]:
            role = c.get("engine_role", "?")
            lines.append(
                f"  • <code>${c.get('monthly_usd', 0):,.0f}</code> · "
                f"<i>{_esc(role)}</i> · {_esc(c.get('name', '?'))}"
            )

    return "\n".join(lines)


async def cmd_priority(_chat_id: int, _args: str) -> str:
    data = await _get("/priority")
    if not data:
        return _service_unavailable("/priority")

    total = data.get("total_services", 0)
    by_role = data.get("by_role", {})
    services = data.get("services", [])

    lines = ["<b>🎯 Priority</b>"]
    lines.append(f"  <i>Filter:</i> proof / revenue / clarity / ease in 30 days")
    lines.append("")
    lines.append(f"<b>{total} services</b>")
    role_order = ("P1", "P2", "infra", "unknown", "cruft")
    for role in role_order:
        n = by_role.get(role, 0)
        if n:
            emoji = {"P1": "🟢", "P2": "🔵", "infra": "⚙️", "unknown": "❓", "cruft": "🔴"}.get(role, "·")
            lines.append(f"  {emoji} {role}: <b>{n}</b>")

    p1 = [s for s in services if s.get("engine_role") == "P1"]
    p2 = [s for s in services if s.get("engine_role") == "P2"]
    if p1 or p2:
        lines.append("")
        lines.append("<b>Engine services</b>")
        for s in p1 + p2:
            role = s.get("engine_role", "?")
            lines.append(f"  • <i>{_esc(role)}</i> · {_esc(s.get('name', '?'))}")

    unknown_count = by_role.get("unknown", 0)
    if unknown_count:
        lines.append("")
        lines.append(
            f"<b>{unknown_count} unknown</b> services need a decision. "
            f"Tag them in <code>core/STATE/catalog.json</code>."
        )

    return "\n".join(lines)
