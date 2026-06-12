#!/usr/bin/env python3
"""
ARIA SELF-IMPROVEMENT DAILY DIGEST
===================================

Generates and sends a daily summary of self-improvement activities:
- Auto-applied changes (low risk)
- Pending approvals (high risk)
- Cost report
- Performance improvements
- Error fixes

Sends via Telegram at a configured time (default: 8 AM).
"""

import os
import asyncio
import logging
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger("aria.sovereign.improvement_digest")

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")
DIGEST_HOUR = int(os.getenv("ARIA_DIGEST_HOUR", "8"))  # 8 AM


class ImprovementDigest:
    """
    Generates and sends self-improvement digests.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def generate_digest(self) -> str:
        """
        Generate the daily improvement digest.
        
        Returns formatted markdown message.
        """
        try:
            from .cost_tracker import get_cost_tracker
            from .auto_executor import get_executor
            from .opus_reviewer import get_reviewer
        except ImportError:
            from sovereign.cost_tracker import get_cost_tracker
            from sovereign.auto_executor import get_executor
            from sovereign.opus_reviewer import get_reviewer
        
        lines = [
            "**Aria Self-Improvement Report**",
            f"📅 {datetime.now().strftime('%B %d, %Y')}",
            ""
        ]
        
        # === Auto-Applied Changes ===
        executor = get_executor()
        changelog = executor.get_changelog(24)  # Last 24 entries
        
        # Filter to last 24 hours
        yesterday = datetime.now() - timedelta(hours=24)
        recent = [e for e in changelog if e.timestamp >= yesterday]
        
        auto_applied = [e for e in recent if e.success and not e.rolled_back]
        rolled_back = [e for e in recent if e.rolled_back]
        
        if auto_applied:
            lines.append("**✅ Auto-Applied (Low Risk):**")
            for entry in auto_applied[:5]:
                lines.append(f"• {entry.description[:50]}")
            if len(auto_applied) > 5:
                lines.append(f"  _...and {len(auto_applied) - 5} more_")
            lines.append("")
        
        if rolled_back:
            lines.append("**↩️ Rolled Back (Failed):**")
            for entry in rolled_back[:3]:
                lines.append(f"• {entry.description[:50]}")
            lines.append("")
        
        # === Pending Approvals ===
        reviewer = get_reviewer()
        pending = reviewer.get_pending_proposals()
        
        if pending:
            lines.append("**🔒 Pending Approval:**")
            for proposal in pending[:5]:
                risk_icon = ["", "🟢", "🟡", "🟠", "🔴", "⛔"][proposal.risk_level]
                lines.append(f"{risk_icon} `{proposal.id}`: {proposal.problem_description[:40]}...")
            if len(pending) > 5:
                lines.append(f"  _...and {len(pending) - 5} more_")
            lines.append("")
            lines.append("Use `/improvements` to review and `/approve <id>` to approve.")
            lines.append("")
        
        # === Cost Report ===
        cost_tracker = get_cost_tracker()
        cost_summary = cost_tracker.get_cost_summary(days=1)
        
        lines.append("**💰 Costs (24h):**")
        lines.append(f"• API Calls: ${cost_summary['total_cost_usd']:.2f}")
        lines.append(f"• Calls Made: {cost_summary['total_calls']}")
        lines.append(f"• Remaining Budget: ${cost_summary['remaining_budget']:.2f}")
        lines.append("")
        
        # === Performance Summary ===
        try:
            from ..aria_logging import get_logger as get_struct_logger
        except ImportError:
            try:
                from aria_logging.structured_logger import get_logger as get_struct_logger
            except ImportError:
                get_struct_logger = None
        
        if get_struct_logger:
            struct_logger = get_struct_logger()
            perf = struct_logger.get_performance_metrics(hours=24)
            errors = struct_logger.get_error_summary(hours=24)
            
            lines.append("**📊 Performance (24h):**")
            lines.append(f"• Success Rate: {perf['success_rate']:.1f}%")
            if perf['response_times']['avg_duration']:
                lines.append(f"• Avg Response: {perf['response_times']['avg_duration']:.0f}ms")
            lines.append(f"• Total Errors: {errors['total_errors']}")
            lines.append("")
            
            if errors['total_errors'] > 0:
                lines.append("**Top Error Types:**")
                for error_type, count in list(errors['by_type'].items())[:3]:
                    lines.append(f"• {error_type}: {count}")
                lines.append("")
        
        # === Summary ===
        total_changes = len(auto_applied) + len(rolled_back)
        pending_count = len(pending)
        
        if total_changes == 0 and pending_count == 0:
            lines.append("_No changes or proposals in the last 24 hours._")
        else:
            lines.append("---")
            lines.append(f"📈 **Summary:** {len(auto_applied)} applied, {len(rolled_back)} rolled back, {pending_count} pending")
        
        return "\n".join(lines)
    
    async def send_digest(self, chat_id: str = None) -> bool:
        """
        Send the digest to Telegram.
        
        Returns True if sent successfully.
        """
        target_chat = chat_id or SUNHEART_CHAT_ID
        
        if not TELEGRAM_BOT_TOKEN or not target_chat:
            logger.warning("Telegram credentials not configured for digest")
            return False
        
        try:
            message = await self.generate_digest()
            
            response = await self.http.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": target_chat,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
            
            if response.status_code == 200:
                logger.info("Daily digest sent successfully")
                return True
            else:
                logger.error(f"Failed to send digest: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending digest: {e}")
            return False


class DigestScheduler:
    """
    Schedules daily digest sending.
    """
    
    def __init__(self, digest_hour: int = DIGEST_HOUR):
        self.digest_hour = digest_hour
        self.digest = ImprovementDigest()
        self.running = False
        self._last_sent: Optional[datetime] = None
    
    async def start(self):
        """Start the digest scheduler."""
        self.running = True
        logger.info(f"Digest scheduler started (sends at {self.digest_hour}:00)")
        
        while self.running:
            try:
                now = datetime.now()
                
                # Check if it's time to send
                if self._should_send(now):
                    await self.digest.send_digest()
                    self._last_sent = now
                
                # Sleep until next check (every 30 minutes)
                await asyncio.sleep(1800)
                
            except Exception as e:
                logger.error(f"Digest scheduler error: {e}")
                await asyncio.sleep(300)
    
    def _should_send(self, now: datetime) -> bool:
        """Check if we should send the digest now."""
        # Only send at the configured hour
        if now.hour != self.digest_hour:
            return False
        
        # Only send if we haven't sent today
        if self._last_sent and self._last_sent.date() == now.date():
            return False
        
        return True
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_digest: Optional[ImprovementDigest] = None
_scheduler: Optional[DigestScheduler] = None


def get_digest() -> ImprovementDigest:
    """Get or create global digest."""
    global _digest
    if _digest is None:
        _digest = ImprovementDigest()
    return _digest


def get_scheduler() -> DigestScheduler:
    """Get or create global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = DigestScheduler()
    return _scheduler


async def send_digest_now(chat_id: str = None) -> bool:
    """Send the digest immediately."""
    return await get_digest().send_digest(chat_id)


async def generate_digest() -> str:
    """Generate digest content without sending."""
    return await get_digest().generate_digest()


