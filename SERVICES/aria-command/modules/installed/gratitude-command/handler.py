#!/usr/bin/env python3
"""
Gratitude Module
================

Log daily gratitudes and build a practice of appreciation.
Stores entries per user with timestamps.
"""

import json
from datetime import datetime
from pathlib import Path

# Store gratitudes in a JSON file per user
DATA_DIR = Path("/opt/fpai/data/gratitude")


def _get_user_file(user_id: int) -> Path:
    """Get the gratitude file for a user."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / f"user_{user_id}.json"


def _load_entries(user_id: int) -> list:
    """Load gratitude entries for a user."""
    user_file = _get_user_file(user_id)
    if user_file.exists():
        try:
            return json.loads(user_file.read_text())
        except:
            return []
    return []


def _save_entries(user_id: int, entries: list):
    """Save gratitude entries for a user."""
    user_file = _get_user_file(user_id)
    user_file.write_text(json.dumps(entries, indent=2))


def handle(args: str, context: dict) -> str:
    """
    Handle the /gratitude command.
    
    Args:
        args: Gratitude text or empty to view history
        context: Command context with user_id
    
    Returns:
        Confirmation or gratitude history
    """
    user_id = context.get("user_id", 0)
    entries = _load_entries(user_id)
    
    # No args - show recent gratitudes
    if not args.strip():
        if not entries:
            return (
                "🙏 **Gratitude Journal**\n\n"
                "You haven't logged any gratitudes yet.\n\n"
                "Start now:\n"
                "`/gratitude I'm grateful for...`\n\n"
                "_\"Gratitude turns what we have into enough.\"_"
            )
        
        # Show last 7 entries
        recent = entries[-7:]
        lines = []
        for entry in reversed(recent):
            date = entry.get("date", "Unknown")
            text = entry.get("text", "")
            lines.append(f"• {text}\n  _{date}_")
        
        total = len(entries)
        streak_msg = f"\n\n🔥 Total entries: **{total}**" if total > 0 else ""
        
        return (
            "🙏 **Your Gratitudes**\n\n"
            + "\n\n".join(lines)
            + streak_msg
            + "\n\n_Add more with `/gratitude <text>`_"
        )
    
    # Add new gratitude
    gratitude_text = args.strip()
    
    # Limit length
    if len(gratitude_text) > 500:
        gratitude_text = gratitude_text[:500] + "..."
    
    new_entry = {
        "text": gratitude_text,
        "date": datetime.now().strftime("%b %d, %Y %I:%M %p"),
        "timestamp": datetime.now().isoformat()
    }
    
    entries.append(new_entry)
    _save_entries(user_id, entries)
    
    # Encouraging response
    count = len(entries)
    encouragement = ""
    if count == 1:
        encouragement = "\n\n🌱 First gratitude! Great start."
    elif count == 7:
        encouragement = "\n\n🎯 One week of gratitude! Keep going!"
    elif count == 30:
        encouragement = "\n\n🏆 30 gratitudes! You're building a beautiful practice."
    elif count == 100:
        encouragement = "\n\n✨ 100 gratitudes! You're a gratitude master!"
    elif count % 10 == 0:
        encouragement = f"\n\n🌟 {count} gratitudes logged!"
    
    return (
        f"🙏 **Logged**\n\n"
        f"_{gratitude_text}_"
        f"{encouragement}\n\n"
        f"View all: `/gratitude`"
    )


