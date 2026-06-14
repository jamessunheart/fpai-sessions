#!/usr/bin/env python3
"""
Presence Status Display
=======================
Formats presence status for display in various contexts.

Outputs:
- Text summary for Telegram
- JSON for API
- Rich display for dashboard
"""
from datetime import datetime
from typing import Dict, Optional
from .engine import get_presence_engine, PresenceStatus, PresenceState


def get_state_emoji(state: PresenceState) -> str:
    """Get emoji for state."""
    return {
        PresenceState.ONLINE: "🟢",
        PresenceState.FOCUSING: "🟡",
        PresenceState.AWAY: "🔴",
        PresenceState.OFFLINE: "⚪"
    }.get(state, "⚪")


def get_state_label(state: PresenceState) -> str:
    """Get human label for state."""
    return {
        PresenceState.ONLINE: "Online",
        PresenceState.FOCUSING: "Focusing",
        PresenceState.AWAY: "Away",
        PresenceState.OFFLINE: "Offline"
    }.get(state, "Unknown")


def format_status_text(status: PresenceStatus) -> str:
    """Format status as plain text for Telegram."""
    emoji = get_state_emoji(status.state)
    label = get_state_label(status.state)
    
    lines = [f"{emoji} JAI is {label.lower()}"]
    lines.append("")
    
    lines.append("Currently:")
    
    if status.channels_monitoring:
        channels = ", ".join(status.channels_monitoring)
        lines.append(f"• Monitoring {channels}")
    
    if status.activities_today > 0:
        lines.append(f"• {status.activities_today} activities today")
    
    if status.queued_items > 0:
        lines.append(f"• {status.queued_items} items queued for review")
    else:
        lines.append("• No items pending")
    
    if status.current_activity:
        lines.append(f"• Active: {status.current_activity}")
    
    if status.next_update:
        lines.append(f"• Next update: {status.next_update}")
    
    return "\n".join(lines)


def format_status_short(status: PresenceStatus) -> str:
    """Format as a short one-liner."""
    emoji = get_state_emoji(status.state)
    label = get_state_label(status.state)
    
    if status.current_activity:
        return f"{emoji} {label} — {status.current_activity}"
    
    if status.queued_items > 0:
        return f"{emoji} {label} — {status.queued_items} items queued"
    
    return f"{emoji} {label} — Running quiet"


def format_status_json(status: PresenceStatus) -> Dict:
    """Format status as JSON for API."""
    return {
        "state": status.state.value,
        "state_emoji": get_state_emoji(status.state),
        "state_label": get_state_label(status.state),
        "since": status.since,
        "current_activity": status.current_activity,
        "activities_today": status.activities_today,
        "queued_items": status.queued_items,
        "next_update": status.next_update,
        "channels_monitoring": status.channels_monitoring,
        "is_available": status.state == PresenceState.ONLINE
    }


def format_status_card(status: PresenceStatus) -> str:
    """Format as a nice card for dashboard/display."""
    emoji = get_state_emoji(status.state)
    label = get_state_label(status.state)
    
    card = f"""
┌─────────────────────────────────────┐
│ {emoji} JAI is {label.lower():26}│
│                                     │
│ Currently:                          │
"""
    
    if status.channels_monitoring:
        channels = ", ".join(status.channels_monitoring[:3])
        card += f"│ • Monitoring {channels:21}│\n"
    
    card += f"│ • {status.activities_today} activities today{' ' * (15 - len(str(status.activities_today)))}│\n"
    
    if status.queued_items > 0:
        card += f"│ • {status.queued_items} items queued{' ' * (18 - len(str(status.queued_items)))}│\n"
    
    if status.next_update:
        card += f"│ • Next update: {status.next_update:17}│\n"
    
    card += "└─────────────────────────────────────┘"
    
    return card


def get_status_for_telegram() -> str:
    """Get status formatted for Telegram."""
    engine = get_presence_engine()
    status = engine.get_status()
    return format_status_text(status)


def get_status_for_api() -> Dict:
    """Get status formatted for API."""
    engine = get_presence_engine()
    status = engine.get_status()
    return format_status_json(status)


def get_status_short() -> str:
    """Get short status."""
    engine = get_presence_engine()
    status = engine.get_status()
    return format_status_short(status)








