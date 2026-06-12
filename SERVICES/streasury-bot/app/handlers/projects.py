"""/projects — show all active Claude session states.

Queries the Sessions API and formats the result for Telegram.
The bot answers "what am I in the middle of?" without James querying me.

Companion to The Practice of Signaling §1 (Founder ← Field rhythm).
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx

from .. import telegram
from ..config import settings

log = logging.getLogger("streasury.handlers.projects")

_TIMEOUT = httpx.Timeout(6.0, connect=3.0)


def _esc(s) -> str:
    return telegram.esc(str(s) if s is not None else "")


def _rel_time(iso: str) -> str:
    if not iso:
        return ""
    try:
        d = datetime.fromisoformat(iso)
        diff = (datetime.now() - d).total_seconds()
        if diff < 60:
            return f"{int(diff)}s ago"
        if diff < 3600:
            return f"{int(diff // 60)}m ago"
        if diff < 86400:
            return f"{int(diff // 3600)}h ago"
        return f"{int(diff // 86400)}d ago"
    except Exception:
        return ""


def _status_glyph(status: str) -> str:
    return {
        "active": "🟢",
        "paused": "⏸",
        "blocked": "🛑",
        "complete": "✓",
    }.get((status or "").lower(), "•")


async def cmd_projects(chat_id: int, args: str) -> str:
    """Return formatted project state across all known Claude sessions."""
    headers = {}
    if settings.sessions_api_token:
        headers["X-Sessions-Token"] = settings.sessions_api_token
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{settings.sessions_api_url.rstrip('/')}/list", headers=headers)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        log.warning("sessions api unreachable: %s", e)
        return "📡 <b>Projects</b>\n\nCould not reach the sessions API. Try again, or check service status."

    sessions = data.get("sessions", [])
    if not sessions:
        return (
            "📡 <b>Projects</b>\n\n"
            "<i>No active sessions tracked yet.</i>\n\n"
            "Push state from any Claude session:\n"
            "<code>python3 tools/session_state.py update --quest 'X' --next-move 'Y'</code>"
        )

    lines = ["📡 <b>Projects — what you're in the middle of</b>\n"]
    for s in sessions[:10]:  # cap at 10 to avoid Telegram message length issues
        glyph = _status_glyph(s.get("status", "active"))
        project = _esc(s.get("project", "?"))
        loop = s.get("loop_number")
        loop_str = f" · Loop {loop}" if loop is not None else ""
        last = _rel_time(s.get("last_activity", ""))
        lines.append(f"\n{glyph} <b>{project}</b>{loop_str} <i>· {_esc(last)}</i>")
        if s.get("quest"):
            lines.append(f"  Quest: {_esc(s['quest'])}")
        if s.get("next_move"):
            lines.append(f"  Next: <i>{_esc(s['next_move'])}</i>")
        if s.get("branch"):
            lines.append(f"  Branch: <code>{_esc(s['branch'])}</code>")

    if len(sessions) > 10:
        lines.append(f"\n<i>... and {len(sessions) - 10} more.</i>")

    return "\n".join(lines)
