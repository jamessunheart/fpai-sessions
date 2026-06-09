#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - DAILY DIGEST
====================================

Generate and deliver daily briefings.

Includes:
- System health summary
- Trading activity
- Builder progress
- Cost report
- Top priorities
"""

import os
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger("aria.digest")

# ============================================================================
# CONFIGURATION
# ============================================================================

SERVERS = {
    "primary": "198.54.123.234",
    "secondary": "162.0.208.88"
}

WHALETRACK_URL = f"http://{SERVERS['primary']}:8600"
BUILDER_URL = f"http://{SERVERS['secondary']}:8720"


@dataclass
class DigestSection:
    """A section of the daily digest."""
    title: str
    emoji: str
    content: str
    priority: int = 0  # Higher = more important


@dataclass
class DailyDigest:
    """Complete daily digest."""
    date: datetime
    sections: List[DigestSection] = field(default_factory=list)
    top_priority: Optional[str] = None
    
    def format_text(self) -> str:
        """Format as text for Telegram."""
        msg = f"☀️ **Good morning! Here's your brief for {self.date.strftime('%A, %B %d')}**\n\n"
        
        # Sort by priority
        sorted_sections = sorted(self.sections, key=lambda s: -s.priority)
        
        for section in sorted_sections:
            msg += f"{section.emoji} **{section.title}**\n"
            msg += f"{section.content}\n\n"
        
        if self.top_priority:
            msg += f"📌 **Top Priority Today:** {self.top_priority}\n"
        
        msg += "\nWhat would you like to focus on?"
        return msg
    
    def format_voice(self) -> str:
        """Format for voice delivery."""
        msg = f"Good morning. Here's your brief for {self.date.strftime('%A, %B %d')}. "
        
        sorted_sections = sorted(self.sections, key=lambda s: -s.priority)
        
        for section in sorted_sections:
            msg += f"{section.title}. {section.content}. "
        
        if self.top_priority:
            msg += f"Your top priority today is: {self.top_priority}. "
        
        msg += "What would you like to focus on?"
        return msg


class DigestGenerator:
    """
    Generate daily briefings.
    
    Collects data from all systems and compiles into a digest.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def generate(self) -> DailyDigest:
        """Generate complete daily digest."""
        digest = DailyDigest(date=datetime.now())
        
        # Gather all sections
        sections = []
        
        # System health
        health_section = await self._get_health_section()
        if health_section:
            sections.append(health_section)
        
        # Trading activity
        trading_section = await self._get_trading_section()
        if trading_section:
            sections.append(trading_section)
        
        # Builder progress
        builder_section = await self._get_builder_section()
        if builder_section:
            sections.append(builder_section)
        
        # Cost report
        cost_section = await self._get_cost_section()
        if cost_section:
            sections.append(cost_section)
        
        # Overnight activity
        overnight_section = await self._get_overnight_section()
        if overnight_section:
            sections.append(overnight_section)
        
        digest.sections = sections
        
        # Determine top priority
        digest.top_priority = await self._determine_priority(sections)
        
        return digest
    
    async def _get_health_section(self) -> Optional[DigestSection]:
        """Get system health summary."""
        try:
            from .monitors import get_monitor
            monitor = get_monitor()
            
            # Check services
            result = await monitor.check_services()
            healthy_count = sum(1 for v in result.metrics.values() if v.get("healthy"))
            total_count = len(result.metrics)
            
            # Check for recent alerts
            recent_alerts = monitor.get_recent_alerts(minutes=480)  # Last 8 hours
            critical_alerts = [a for a in recent_alerts if a.level.value == "critical"]
            
            if critical_alerts:
                content = f"{len(critical_alerts)} critical issues overnight. "
                content += f"{healthy_count}/{total_count} services healthy."
                priority = 10
            elif healthy_count == total_count:
                content = f"All {total_count} services running smoothly. No issues overnight."
                priority = 2
            else:
                unhealthy = total_count - healthy_count
                content = f"{unhealthy} service(s) need attention. {healthy_count}/{total_count} healthy."
                priority = 7
            
            return DigestSection(
                title="System Health",
                emoji="🖥️",
                content=content,
                priority=priority
            )
        except Exception as e:
            logger.error(f"Health section failed: {e}")
            return DigestSection(
                title="System Health",
                emoji="🖥️",
                content="Unable to check system health.",
                priority=5
            )
    
    async def _get_trading_section(self) -> Optional[DigestSection]:
        """Get trading activity summary."""
        try:
            response = await self.http.get(f"{WHALETRACK_URL}/api/summary")
            
            if response.status_code == 200:
                data = response.json()
                
                signals = data.get("signals_24h", 0)
                profitable = data.get("profitable_signals", 0)
                positions = data.get("open_positions", 0)
                pnl = data.get("daily_pnl", 0)
                
                content = f"{signals} signals generated, {profitable} profitable. "
                if positions > 0:
                    content += f"{positions} open position(s). "
                if pnl != 0:
                    sign = "+" if pnl > 0 else ""
                    content += f"Daily P&L: {sign}${pnl:.2f}"
                else:
                    content += "No active trades."
                
                priority = 6 if positions > 0 else 3
                
                return DigestSection(
                    title="Trading Activity",
                    emoji="📈",
                    content=content,
                    priority=priority
                )
        except Exception as e:
            logger.debug(f"Trading section failed: {e}")
        
        return DigestSection(
            title="Trading Activity",
            emoji="📈",
            content="WhaleTrack data unavailable.",
            priority=2
        )
    
    async def _get_builder_section(self) -> Optional[DigestSection]:
        """Get builder progress summary."""
        try:
            response = await self.http.get(f"{BUILDER_URL}/builder/status")
            
            if response.status_code == 200:
                data = response.json()
                
                pending = data.get("pending_changes", 0)
                
                # Try to get build history
                history_response = await self.http.get(f"{BUILDER_URL}/builder/history")
                completed_24h = 0
                if history_response.status_code == 200:
                    history = history_response.json().get("data", [])
                    yesterday = datetime.now() - timedelta(hours=24)
                    completed_24h = len([b for b in history if b.get("completed")])
                
                if pending > 0:
                    content = f"{pending} changes awaiting review. {completed_24h} builds completed."
                    priority = 5
                else:
                    content = f"{completed_24h} builds completed. No pending reviews."
                    priority = 2
                
                return DigestSection(
                    title="Builder Progress",
                    emoji="🔨",
                    content=content,
                    priority=priority
                )
        except Exception as e:
            logger.debug(f"Builder section failed: {e}")
        
        return None
    
    async def _get_cost_section(self) -> Optional[DigestSection]:
        """Get cost summary."""
        try:
            # Check for GPU costs
            import asyncssh
            
            costs = {"server": 0, "gpu": 0}
            
            # Estimate server costs (fixed)
            costs["server"] = 2.0  # ~$60/month for servers
            
            # Check Vast.ai
            async with asyncssh.connect(SERVERS["secondary"], username="root", known_hosts=None) as conn:
                result = await conn.run("vastai show instances --raw 2>/dev/null || echo '{}'")
                if "dph_total" in result.stdout:
                    import json
                    instances = json.loads(result.stdout)
                    daily_gpu = sum(i.get("dph_total", 0) * 24 for i in instances if isinstance(i, dict))
                    costs["gpu"] = daily_gpu
            
            total_daily = costs["server"] + costs["gpu"]
            
            if costs["gpu"] > 10:
                content = f"Daily run rate: ${total_daily:.2f} (⚠️ GPU: ${costs['gpu']:.2f})"
                priority = 6
            else:
                content = f"Daily run rate: ${total_daily:.2f}. Within budget."
                priority = 1
            
            return DigestSection(
                title="Costs",
                emoji="💰",
                content=content,
                priority=priority
            )
        except Exception as e:
            logger.debug(f"Cost section failed: {e}")
        
        return None
    
    async def _get_overnight_section(self) -> Optional[DigestSection]:
        """Get overnight activity summary."""
        try:
            import asyncssh
            
            events = []
            
            # Check for service restarts
            async with asyncssh.connect(SERVERS["secondary"], username="root", known_hosts=None) as conn:
                result = await conn.run(
                    "journalctl --since '8 hours ago' -u 'fpai-*' | grep -i 'started\\|stopped\\|failed' | wc -l"
                )
                restart_count = int(result.stdout.strip() or 0)
                if restart_count > 0:
                    events.append(f"{restart_count} service events")
            
            if events:
                content = "Overnight: " + ", ".join(events)
            else:
                content = "Quiet night. No significant events."
            
            return DigestSection(
                title="Overnight Activity",
                emoji="🌙",
                content=content,
                priority=1
            )
        except Exception as e:
            logger.debug(f"Overnight section failed: {e}")
        
        return None
    
    async def _determine_priority(self, sections: List[DigestSection]) -> str:
        """Determine top priority for the day."""
        # Sort by priority
        sorted_sections = sorted(sections, key=lambda s: -s.priority)
        
        if sorted_sections and sorted_sections[0].priority >= 7:
            # High priority item
            section = sorted_sections[0]
            return f"{section.title}: {section.content[:50]}..."
        
        # Default priorities
        defaults = [
            "Review trading signals",
            "Check builder queue",
            "Optimize costs",
            "Ship new features",
        ]
        
        # Pick based on day of week
        day = datetime.now().weekday()
        return defaults[day % len(defaults)]


# ============================================================================
# SCHEDULED DELIVERY
# ============================================================================

async def generate_and_send_digest(chat_id: int, voice: bool = True):
    """Generate and send daily digest."""
    generator = DigestGenerator()
    
    try:
        digest = await generator.generate()
        
        if voice:
            from ..voice.speak import send_brief
            voice_text = digest.format_voice()
            await send_brief(chat_id, voice_text)
        else:
            # Send as text
            from ..telegram.bot import send_message
            text = digest.format_text()
            await send_message(chat_id, text)
        
        logger.info(f"Daily digest sent to {chat_id}")
        
    finally:
        await generator.close()


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_generator: Optional[DigestGenerator] = None


def get_generator() -> DigestGenerator:
    """Get or create global generator."""
    global _generator
    if _generator is None:
        _generator = DigestGenerator()
    return _generator


async def generate_digest() -> DailyDigest:
    """Generate daily digest."""
    return await get_generator().generate()


async def get_quick_brief() -> str:
    """Get a quick status brief."""
    try:
        digest = await generate_digest()
        return digest.format_text()
    except Exception as e:
        logger.error(f"Brief generation failed: {e}")
        return "Unable to generate brief. Check system status manually."


