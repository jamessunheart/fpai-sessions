#!/usr/bin/env python3
"""Conversation OS — concise Telegram views (no dashboard).

Pure formatters (no send). Render a Room and a digest as short Telegram-friendly
text. Sending is done by the existing send_tg_digest.py when James is in the loop.
"""
from __future__ import annotations

from typing import Any

_ROOM_LINE = {
    "proposed": "🟡 proposed", "awaiting_approval": "🟡 needs your approval",
    "active": "🟢 active", "blocked": "🔴 blocked",
    "completion_proposed": "🟡 completion claimed (needs proof)",
    "completed": "🟢 completed", "closed": "⚪ closed", "rejected": "⚪ rejected",
}


def room_view(room: dict[str, Any]) -> str:
    nxt = (room["actions"][-1]["action"] if room["actions"] else
           ("your approval" if room["state"] == "awaiting_approval" else "—"))
    blk = room["blockers"][-1]["blocker"] if room["blockers"] else "—"
    lines = [
        f"🗂 {room['objective']}",
        f"state · {_ROOM_LINE.get(room['state'], room['state'])}",
        f"owner · {', '.join(room['owner_candidates']) or '—'}",
        f"next · {nxt}",
        f"blocker · {blk}",
    ]
    if room["state"] == "awaiting_approval":
        lines.append("→ reply *approve* or *reject*")
    if room["submitted_proof"]:
        lines.append(f"proof · {room['submitted_proof']['proof'][:80]}")
    if room["state"] == "closed":
        lines.append(f"✅ outcome · {room.get('verified_outcome') or '—'}")
    return "\n".join(lines)


def digest(rooms: list[dict[str, Any]]) -> str:
    """Answers: what's active / needs me / moved / blocked / completed."""
    def has(s): return [r for r in rooms if r["state"] == s]
    active = has("active") + has("blocked")
    needs = has("awaiting_approval") + has("completion_proposed")
    done = has("completed") + has("closed")
    blocked = has("blocked")
    out = ["📋 *Conversation OS digest*"]
    out.append(f"active · {len(active)}   needs you · {len(needs)}   blocked · {len(blocked)}   done · {len(done)}")
    for r in needs:
        out.append(f"❗ needs you → {r['objective'][:60]}")
    for r in blocked:
        out.append(f"🔴 blocked → {r['objective'][:60]}")
    if not needs and not blocked:
        out.append("✅ nothing needs you right now")
    return "\n".join(out)
