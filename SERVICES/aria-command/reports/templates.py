#!/usr/bin/env python3
"""
Report Templates
================
Templates for different report types.

Report Types:
- Morning Brief: Start of day summary
- Progress: Task completed notification
- Status: Periodic check-in
- Heads Up: Upcoming event reminder
- Decision: Needs human input
- Digest: End of day summary
"""
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ReportData:
    """Data for generating reports."""
    # Trading
    treasury_value: Optional[float] = None
    treasury_change: Optional[float] = None
    open_positions: Optional[List[Dict]] = None
    
    # Messages
    messages_overnight: int = 0
    messages_handled: int = 0
    messages_pending: int = 0
    
    # Activities
    activities_today: int = 0
    activities_list: Optional[List[Dict]] = None
    
    # Queue
    queued_items: int = 0
    priority_items: Optional[List[Dict]] = None
    
    # Focus
    today_focus: Optional[str] = None
    priorities: Optional[List[str]] = None
    
    # Events
    upcoming_events: Optional[List[Dict]] = None
    
    # Custom
    custom_items: Optional[List[str]] = None


def format_morning_brief(data: ReportData) -> str:
    """
    Morning Brief - Start of day
    
    Format:
    ☀️ Morning Brief · 8:12am
    ───────────────────────
    Treasury: $543 (+2.1%)
    Overnight: 2 messages (handled)
    Today's focus: CIS implementation
    One priority: Review module submission
    """
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    
    lines = [f"☀️ Morning Brief · {time_str}"]
    lines.append("───────────────────────")
    
    # Treasury
    if data.treasury_value is not None:
        change_str = ""
        if data.treasury_change is not None:
            sign = "+" if data.treasury_change >= 0 else ""
            change_str = f" ({sign}{data.treasury_change:.1f}%)"
        lines.append(f"Treasury: ${data.treasury_value:,.0f}{change_str}")
    
    # Overnight messages
    if data.messages_overnight > 0:
        handled = "handled" if data.messages_handled >= data.messages_overnight else f"{data.messages_handled} handled"
        lines.append(f"Overnight: {data.messages_overnight} messages ({handled})")
    else:
        lines.append("Overnight: Quiet")
    
    # Today's focus
    if data.today_focus:
        lines.append(f"Today's focus: {data.today_focus}")
    
    # Priority items
    if data.priority_items and len(data.priority_items) > 0:
        item = data.priority_items[0]
        lines.append(f"One priority: {item.get('description', 'Review pending items')}")
    
    return "\n".join(lines)


def format_progress_report(task: str, outcome: str = "completed", details: str = "") -> str:
    """
    Progress Report - Task completed
    
    Format:
    ✅ Progress · 11:30am
    ───────────────────────
    Ashutosh submitted auth module.
    Tests passing. No action needed.
    """
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    
    lines = [f"✅ Progress · {time_str}"]
    lines.append("───────────────────────")
    lines.append(f"{task}.")
    
    if details:
        lines.append(details)
    else:
        if outcome == "completed":
            lines.append("No action needed.")
        elif outcome == "queued":
            lines.append("Queued for your review.")
    
    return "\n".join(lines)


def format_status_report(data: ReportData) -> str:
    """
    Status Report - Periodic check-in
    
    Format:
    📊 Status · 2:15pm
    ───────────────────────
    Running quiet. 3 things handled.
    Nothing needs you right now.
    """
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    
    lines = [f"📊 Status · {time_str}"]
    lines.append("───────────────────────")
    
    if data.activities_today > 0:
        lines.append(f"Running quiet. {data.activities_today} things handled.")
    else:
        lines.append("Running quiet. All clear.")
    
    if data.queued_items > 0:
        lines.append(f"{data.queued_items} items queued for later.")
    else:
        lines.append("Nothing needs you right now.")
    
    return "\n".join(lines)


def format_heads_up(event: Dict) -> str:
    """
    Heads Up - Upcoming event
    
    Format:
    ⏰ Heads Up · 1:30pm
    ───────────────────────
    Meeting in 30min with Alice
    Context: Q1 planning discussion
    """
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    
    lines = [f"⏰ Heads Up · {time_str}"]
    lines.append("───────────────────────")
    
    event_name = event.get("name", "Event")
    time_until = event.get("time_until", "soon")
    context = event.get("context", "")
    
    lines.append(f"{event_name} in {time_until}")
    
    if context:
        lines.append(f"Context: {context}")
    
    return "\n".join(lines)


def format_decision_request(question: str, options: List[str] = None, context: str = "") -> str:
    """
    Decision Request - Needs human input
    
    Format:
    ❓ Decision Needed
    ───────────────────────
    Alice wants to reschedule to Thursday.
    
    [Confirm] [Suggest alternative] [I'll handle]
    """
    lines = ["❓ Decision Needed"]
    lines.append("───────────────────────")
    lines.append(question)
    
    if context:
        lines.append("")
        lines.append(context)
    
    if options:
        lines.append("")
        options_str = " ".join([f"[{opt}]" for opt in options])
        lines.append(options_str)
    
    return "\n".join(lines)


def format_digest(data: ReportData) -> str:
    """
    Digest - End of day summary
    
    Format:
    🌙 Daily Digest · 8:45pm
    ───────────────────────
    Today: 7 things handled
    Treasury: $548 (+0.9%)
    
    Tomorrow's focus: Launch preparation
    
    Pending: 1 item needs review
    """
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    
    lines = [f"🌙 Daily Digest · {time_str}"]
    lines.append("───────────────────────")
    
    # Today summary
    lines.append(f"Today: {data.activities_today} things handled")
    
    # Treasury
    if data.treasury_value is not None:
        change_str = ""
        if data.treasury_change is not None:
            sign = "+" if data.treasury_change >= 0 else ""
            change_str = f" ({sign}{data.treasury_change:.1f}%)"
        lines.append(f"Treasury: ${data.treasury_value:,.0f}{change_str}")
    
    # Tomorrow focus
    if data.today_focus:
        lines.append("")
        lines.append(f"Tomorrow's focus: {data.today_focus}")
    
    # Pending
    if data.queued_items > 0:
        lines.append("")
        lines.append(f"Pending: {data.queued_items} items need review")
    
    return "\n".join(lines)


# Quick formatters for common cases

def quick_status(message: str) -> str:
    """Quick status message."""
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    return f"📊 {time_str} · {message}"


def quick_progress(message: str) -> str:
    """Quick progress message."""
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    return f"✅ {time_str} · {message}"


def quick_alert(message: str) -> str:
    """Quick alert message."""
    now = datetime.now()
    time_str = now.strftime("%-I:%M%p").lower()
    return f"⚠️ {time_str} · {message}"








