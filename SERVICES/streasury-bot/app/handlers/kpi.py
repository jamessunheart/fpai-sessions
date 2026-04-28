"""/kpi set | show | list — custom named metrics."""
from __future__ import annotations

import shlex

from .. import ledger, telegram
from ..reports.formatters import render_kpi_history


def _esc(s: str) -> str:
    return telegram.esc(s)


async def cmd_kpi(_chat_id: int, args: str) -> str:
    if not args.strip():
        return (
            "<b>KPI</b>\n"
            "  <code>/kpi set NAME VALUE [UNIT] [\"NOTE\"]</code>\n"
            "  <code>/kpi show NAME</code>\n"
            "  <code>/kpi list</code>"
        )
    try:
        parts = shlex.split(args)
    except ValueError:
        parts = args.split()
    sub = parts[0].lower()

    if sub == "set":
        if len(parts) < 3:
            return "Usage: <code>/kpi set NAME VALUE [UNIT] [\"NOTE\"]</code>"
        name = parts[1]
        try:
            value = float(parts[2].replace(",", "").replace("$", ""))
        except ValueError:
            return f"Couldn't parse value: <code>{_esc(parts[2])}</code>"
        unit = parts[3] if len(parts) > 3 else None
        note = " ".join(parts[4:]) if len(parts) > 4 else None
        await ledger.kpi_set(name, value, unit, note)
        return f"✅ <b>{_esc(name)}</b> = {value:,.4g}{(' ' + _esc(unit)) if unit else ''}"

    if sub == "show":
        if len(parts) < 2:
            return "Usage: <code>/kpi show NAME</code>"
        history = await ledger.kpi_history(parts[1], limit=30)
        return render_kpi_history(parts[1], history)

    if sub == "list":
        from ..ai.snapshot import build_snapshot
        snap = await build_snapshot(lookback_days=365)
        if not snap["kpis"]:
            return "No KPIs yet. Try <code>/kpi set MRR 4200 USD</code>."
        lines = ["<b>📈 KPIs</b>"]
        for k in snap["kpis"]:
            unit = f" {_esc(k['unit'])}" if k["unit"] else ""
            lines.append(f"  • <b>{_esc(k['name'])}</b>: {k['value']:,.4g}{unit}")
        return "\n".join(lines)

    return "Unknown subcommand. Try: <code>/kpi set | show | list</code>"
