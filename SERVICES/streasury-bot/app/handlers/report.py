"""/report week|month|ytd|30d|90d."""
from __future__ import annotations

from ..reports.builders import build_report
from ..reports.formatters import render_report


async def cmd_report(_chat_id: int, args: str) -> str:
    period = (args or "month").strip().lower().split()[0] if args.strip() else "month"
    if period not in ("week", "month", "ytd", "30d", "90d"):
        return "Usage: <code>/report week | month | ytd | 30d | 90d</code>"
    try:
        report = await build_report(period)
    except Exception as e:
        return f"⚠️ report failed: {e}"
    return render_report(report)
