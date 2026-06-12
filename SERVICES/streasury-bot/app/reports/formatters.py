"""app/reports/formatters.py — render report dicts to Telegram-friendly HTML."""
from __future__ import annotations

from typing import Any

from ..telegram import esc


def _money(x: float, currency: str = "USD") -> str:
    sign = "-" if x < 0 else ""
    return f"{sign}{currency} {abs(x):,.2f}"


def render_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"<b>📊 Treasury report — {esc(report['label'])}</b>")
    lines.append(
        f"<b>Net:</b> {_money(report['net'])} "
        f"(in {_money(report['income'])} / out {_money(report['expense'])}, "
        f"{report['n']} txns)"
    )

    if report["balances"]:
        lines.append("")
        lines.append("<b>Balances now</b>")
        for b in report["balances"][:12]:
            lines.append(f"  • <code>{esc(b['slug'])}</code> — {_money(b['balance'], b['currency'])}")

    if report["by_category"]:
        lines.append("")
        lines.append("<b>By category (window)</b>")
        for c in report["by_category"][:10]:
            net = c["income"] - c["expense"]
            sign = "+" if net >= 0 else ""
            lines.append(
                f"  • {esc(c['category'])}: in {c['income']:,.0f} / out {c['expense']:,.0f} "
                f"<i>(net {sign}{net:,.0f})</i>"
            )

    if report["by_account"]:
        lines.append("")
        lines.append("<b>Account deltas (window)</b>")
        for a in report["by_account"][:12]:
            sign = "+" if a["delta"] >= 0 else ""
            lines.append(f"  • <code>{esc(a['slug'])}</code>: {sign}{a['delta']:,.2f}")

    if report["kpis"]:
        lines.append("")
        lines.append("<b>KPIs (latest)</b>")
        for k in report["kpis"][:10]:
            unit = f" {esc(k['unit'])}" if k["unit"] else ""
            lines.append(f"  • {esc(k['name'])}: <b>{k['value']:,.4g}</b>{unit}")

    return "\n".join(lines)


def render_balances(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No accounts yet. Try <code>/log 100 revenue stripe \"first dollar\"</code>."
    lines = ["<b>💰 Balances</b>"]
    total = 0.0
    for r in rows:
        if r["currency"] == "USD":
            total += r["balance"]
        lines.append(
            f"  • <code>{esc(r['slug'])}</code> — {_money(r['balance'], r['currency'])}"
            f" <i>({r['txn_count']} txns)</i>"
        )
    lines.append("")
    lines.append(f"<b>USD total:</b> {_money(total)}")
    return "\n".join(lines)


def render_kpi_history(name: str, history: list[dict[str, Any]]) -> str:
    if not history:
        return f"No history for <b>{esc(name)}</b>."
    blocks = "▁▂▃▄▅▆▇█"
    values = [h["value"] for h in history]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1
    sparkline = "".join(blocks[min(7, max(0, int((v - lo) / span * 7)))] for v in values)
    last = history[-1]
    first = history[0]
    delta = last["value"] - first["value"]
    sign = "+" if delta >= 0 else ""
    unit = f" {esc(last['unit'])}" if last["unit"] else ""
    return (
        f"<b>📈 {esc(name)}</b>\n"
        f"  <code>{sparkline}</code>\n"
        f"  Now: <b>{last['value']:,.4g}</b>{unit}\n"
        f"  {len(history)}-pt range: {lo:,.4g} → {hi:,.4g} "
        f"<i>(Δ {sign}{delta:,.4g})</i>"
    )
