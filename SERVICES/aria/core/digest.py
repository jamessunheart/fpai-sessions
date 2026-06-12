"""
ARIA DAILY DIGEST
=================

Generates the morning briefing with:
- Overnight actions taken
- Trading overview
- Infrastructure status
- Builder progress
- Revenue metrics
- Curiosity insights
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import httpx

logger = logging.getLogger("aria.digest")


async def generate_digest(
    actions: List[Any],
    stats: Dict,
    sensors: Dict
) -> str:
    """
    Generate the morning briefing.
    
    Args:
        actions: List of ProactiveAction objects from today
        stats: Daemon stats
        sensors: Sensor instances for querying current state
        
    Returns:
        Formatted digest string
    """
    now = datetime.now()
    greeting = _get_greeting(now)
    
    sections = [
        f"{greeting}\n",
        "=" * 30,
        ""
    ]
    
    # Overnight Summary
    overnight_summary = _summarize_actions(actions)
    if overnight_summary:
        sections.append("**🌙 Overnight Activity**")
        sections.append(overnight_summary)
        sections.append("")
    
    # Trading Overview
    trading_section = await _get_trading_overview(sensors.get("trading"))
    if trading_section:
        sections.append("**📈 Trading**")
        sections.append(trading_section)
        sections.append("")
    
    # Infrastructure Status
    infra_section = await _get_infra_status(sensors.get("infrastructure"))
    if infra_section:
        sections.append("**🖥️ Infrastructure**")
        sections.append(infra_section)
        sections.append("")
    
    # Builder Progress
    builder_section = await _get_builder_status(sensors.get("builder"))
    if builder_section:
        sections.append("**🔧 Builder**")
        sections.append(builder_section)
        sections.append("")
    
    # Cost Summary
    cost_section = _get_cost_summary(stats)
    if cost_section:
        sections.append("**💰 Costs**")
        sections.append(cost_section)
        sections.append("")
    
    # Opportunities / Today's Focus
    focus_section = await _get_todays_focus(sensors)
    if focus_section:
        sections.append("**🎯 Today's Focus**")
        sections.append(focus_section)
        sections.append("")
    
    sections.append("=" * 30)
    sections.append("_Reply anytime to chat with me!_")
    
    return "\n".join(sections)


def _get_greeting(now: datetime) -> str:
    """Get time-appropriate greeting."""
    hour = now.hour
    
    greetings = [
        "Good morning! ☀️",
        "Rise and shine! 🌅",
        "Morning! ☕",
        "Hey there! 👋",
    ]
    
    if hour < 6:
        return "You're up early! 🌙"
    elif hour < 12:
        import random
        return random.choice(greetings)
    elif hour < 17:
        return "Good afternoon! 🌤️"
    else:
        return "Good evening! 🌆"


def _summarize_actions(actions: List[Any]) -> str:
    """Summarize overnight actions."""
    if not actions:
        return "No automated actions overnight."
    
    lines = []
    
    # Group by type
    auto_actions = [a for a in actions if a.approved_by == "auto"]
    proposed = [a for a in actions if a.approved_by != "auto"]
    
    if auto_actions:
        lines.append(f"• ⚡ {len(auto_actions)} auto-action(s)")
        for action in auto_actions[:3]:
            lines.append(f"  - {action.action_taken}")
        if len(auto_actions) > 3:
            lines.append(f"  - ... and {len(auto_actions) - 3} more")
    
    if proposed:
        lines.append(f"• 📋 {len(proposed)} proposed action(s)")
    
    return "\n".join(lines) if lines else "Quiet night! No actions needed."


async def _get_trading_overview(sensor) -> str:
    """Get trading overview."""
    if not sensor:
        return ""
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Get current signal
            r = await client.get("http://198.54.123.234:8601/api/signal/current")
            
            if r.status_code != 200:
                return "Unable to fetch trading data"
            
            data = r.json()
            
            lines = []
            
            # Current signal
            direction = data.get("direction", "NEUTRAL")
            confidence = data.get("confidence", 0)
            symbol = data.get("symbol", "SOL")
            
            emoji = {"LONG": "🟢", "SHORT": "🔴", "NEUTRAL": "⚪"}.get(direction, "⚪")
            lines.append(f"{emoji} {symbol}: {direction} ({confidence}% confidence)")
            
            # Market regime
            regime = data.get("regime", "unknown")
            regime_emoji = {"trending": "📈", "ranging": "↔️", "volatile": "🌊"}.get(regime, "❓")
            lines.append(f"{regime_emoji} Market: {regime}")
            
            # Positions
            r = await client.get("http://198.54.123.234:8600/api/live/positions")
            if r.status_code == 200:
                positions = r.json().get("positions", [])
                if positions:
                    total_pnl = sum(p.get("pnl_usd", 0) for p in positions)
                    pnl_emoji = "📈" if total_pnl >= 0 else "📉"
                    lines.append(f"{pnl_emoji} Open P&L: ${total_pnl:+,.2f}")
                else:
                    lines.append("📊 No open positions")
            
            return "\n".join(lines)
    
    except Exception as e:
        logger.warning(f"Trading overview error: {e}")
        return "Trading data unavailable"


async def _get_infra_status(sensor) -> str:
    """Get infrastructure status."""
    if not sensor:
        return ""
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # GPU status
            r = await client.get("http://162.0.208.88:8450/status")
            
            lines = []
            
            if r.status_code == 200:
                data = r.json()
                gpus = data.get("gpus", 0)
                cost = data.get("hourly_cost", 0)
                queue = data.get("queue_depth", 0)
                
                lines.append(f"🖥️ GPUs: {gpus} running (${cost:.2f}/hr)")
                lines.append(f"📋 Queue: {queue} tasks pending")
            
            # Check key services (quick)
            services_ok = 0
            services_total = 0
            
            for name, url in [
                ("Ollama", "http://162.0.208.88:11434/api/tags"),
                ("WhaleTrack", "http://198.54.123.234:8601/health"),
            ]:
                services_total += 1
                try:
                    r = await client.get(url, timeout=3)
                    if r.status_code == 200:
                        services_ok += 1
                except:
                    pass
            
            status_emoji = "✅" if services_ok == services_total else "⚠️"
            lines.append(f"{status_emoji} Services: {services_ok}/{services_total} healthy")
            
            return "\n".join(lines)
    
    except Exception as e:
        logger.warning(f"Infra status error: {e}")
        return "Infrastructure data unavailable"


async def _get_builder_status(sensor) -> str:
    """Get builder status."""
    if not sensor:
        return ""
    
    try:
        status = await sensor.get_status()
        queue_depth = status.get("last_queue_depth", 0)
        escalations = status.get("seen_escalations", 0)
        
        lines = []
        
        if queue_depth > 0:
            lines.append(f"📋 {queue_depth} task(s) in queue")
        else:
            lines.append("✅ Queue clear")
        
        if escalations > 0:
            lines.append(f"⚠️ {escalations} escalation(s) need review")
        
        return "\n".join(lines) if lines else "Builder idle"
    
    except Exception as e:
        logger.warning(f"Builder status error: {e}")
        return ""


def _get_cost_summary(stats: Dict) -> str:
    """Get cost summary."""
    savings = stats.get("cost_savings", 0)
    
    if savings > 0:
        return f"💚 Saved ${savings:.2f} via auto-scaling"
    
    return "No cost optimizations overnight"


async def _get_todays_focus(sensors: Dict) -> str:
    """Suggest today's focus areas."""
    focus_items = []
    
    # Check for strong trading signal
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://198.54.123.234:8601/api/signal/current")
            if r.status_code == 200:
                data = r.json()
                if data.get("confidence", 0) >= 70:
                    direction = data.get("direction", "")
                    symbol = data.get("symbol", "SOL")
                    focus_items.append(f"Strong {direction} signal on {symbol} - consider action")
    except:
        pass
    
    # Check pending approvals
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("http://162.0.208.88:8180/aria/pending")
            if r.status_code == 200:
                pending = r.json().get("pending", [])
                if pending:
                    focus_items.append(f"{len(pending)} approval(s) waiting for your decision")
    except:
        pass
    
    # Default focus
    if not focus_items:
        focus_items.append("All systems nominal. Check back anytime!")
    
    return "\n".join(f"• {item}" for item in focus_items)


async def generate_quick_status() -> str:
    """Generate a quick status check (not full digest)."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            lines = ["**Quick Status Check**", ""]
            
            # Trading
            try:
                r = await client.get("http://198.54.123.234:8601/api/signal/current", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    lines.append(f"📊 {data.get('symbol', 'SOL')}: {data.get('direction', '?')} ({data.get('confidence', 0)}%)")
            except:
                lines.append("📊 Trading: unavailable")
            
            # GPUs
            try:
                r = await client.get("http://162.0.208.88:8450/status", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    lines.append(f"🖥️ GPUs: {data.get('gpus', 0)} (${data.get('hourly_cost', 0):.2f}/hr)")
            except:
                lines.append("🖥️ GPUs: unavailable")
            
            # Services
            try:
                r = await client.get("http://162.0.208.88:8180/health", timeout=3)
                if r.status_code == 200:
                    lines.append("✅ Aria Core: healthy")
                else:
                    lines.append("⚠️ Aria Core: degraded")
            except:
                lines.append("❌ Aria Core: unreachable")
            
            return "\n".join(lines)
    
    except Exception as e:
        return f"Status check failed: {e}"


