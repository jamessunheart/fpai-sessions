#!/usr/bin/env python3
"""
ARIA REFLECTION REPORTER
========================

Reports on reflection cycles:
- Telegram alerts after each cycle
- Dashboard updates
- Daily/weekly digests
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx

from .cost_tracker import CycleCost, get_cost_summary
from .dialogue import DialogueResult
from .summarizer import InteractionSummary
from .spec_generator import GeneratedSpec
from .builder_bridge import BuildJob, get_queue_status

logger = logging.getLogger("aria.reflection.reporter")

# ============================================================================
# CONFIGURATION
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DASHBOARD_API = os.getenv("DASHBOARD_API", "http://localhost:9090")


@dataclass
class CycleReport:
    """Complete report for a reflection cycle."""
    cycle_id: str
    timestamp: datetime
    
    # Summary
    interactions_reviewed: int = 0
    dialogue_rounds: int = 0
    consensus_reached: bool = False
    
    # Results
    proposals: int = 0
    specs_generated: int = 0
    builds_queued: int = 0
    builds_needing_approval: int = 0
    
    # Cost
    total_cost: float = 0.0
    
    # Details
    proposal_titles: List[str] = None
    
    def __post_init__(self):
        if self.proposal_titles is None:
            self.proposal_titles = []
    
    def to_telegram_message(self) -> str:
        """Format as Telegram message."""
        lines = [
            "🔄 *Reflection Cycle Complete*",
            "",
            f"📊 Reviewed: {self.interactions_reviewed} interactions",
            f"💬 Dialogue rounds: {self.dialogue_rounds}",
            f"✅ Consensus: {'Yes' if self.consensus_reached else 'No'}",
            "",
        ]
        
        if self.proposals > 0:
            lines.append(f"*Improvements identified: {self.proposals}*")
            for i, title in enumerate(self.proposal_titles, 1):
                status = "📝 QUEUED" if i <= self.builds_queued - self.builds_needing_approval else "⏳ NEEDS APPROVAL"
                lines.append(f"  {i}. {title} [{status}]")
            lines.append("")
        else:
            lines.append("No improvements identified this cycle.")
            lines.append("")
        
        lines.append(f"💰 Cost: ${self.total_cost:.2f}")
        
        # Estimate value
        if self.proposals > 0:
            value = "High" if self.proposals >= 2 else "Medium"
            lines.append(f"📈 Est. value: {value}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp.isoformat(),
            "interactions_reviewed": self.interactions_reviewed,
            "dialogue_rounds": self.dialogue_rounds,
            "consensus_reached": self.consensus_reached,
            "proposals": self.proposals,
            "specs_generated": self.specs_generated,
            "builds_queued": self.builds_queued,
            "builds_needing_approval": self.builds_needing_approval,
            "total_cost": self.total_cost,
            "proposal_titles": self.proposal_titles
        }


# ============================================================================
# REPORTER
# ============================================================================

class ReflectionReporter:
    """
    Reports on reflection cycles via Telegram and dashboard.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.http.aclose()
    
    # ========================================================================
    # TELEGRAM NOTIFICATIONS
    # ========================================================================
    
    async def send_telegram(self, message: str, parse_mode: str = "Markdown") -> bool:
        """Send message to Telegram."""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured")
            return False
        
        try:
            response = await self.http.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": parse_mode
                }
            )
            
            if response.status_code == 200:
                logger.info("Telegram notification sent")
                return True
            else:
                logger.error(f"Telegram error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    
    async def report_cycle_complete(
        self,
        cycle_id: str,
        summary: InteractionSummary,
        dialogue: DialogueResult,
        specs: List[GeneratedSpec],
        builds: List[BuildJob],
        cost: CycleCost
    ):
        """
        Send complete cycle report to Telegram.
        """
        report = CycleReport(
            cycle_id=cycle_id,
            timestamp=datetime.now(),
            interactions_reviewed=summary.interaction_count,
            dialogue_rounds=dialogue.rounds_completed,
            consensus_reached=dialogue.consensus_reached,
            proposals=len(dialogue.proposals),
            specs_generated=len(specs),
            builds_queued=len(builds),
            builds_needing_approval=sum(1 for b in builds if b.status == "needs_approval"),
            total_cost=cost.total_cost if cost else 0,
            proposal_titles=[p.title for p in dialogue.proposals]
        )
        
        message = report.to_telegram_message()
        await self.send_telegram(message)
        
        # Also update dashboard
        await self.update_dashboard(report)
        
        return report
    
    async def report_build_complete(self, build: BuildJob, success: bool):
        """Report when a build completes."""
        if success:
            emoji = "✅"
            status = "completed successfully"
        else:
            emoji = "❌"
            status = f"failed: {build.error_message}"
        
        message = f"{emoji} *Build Update*\n\n{build.spec_title} {status}"
        await self.send_telegram(message)
    
    async def report_approval_needed(self, builds: List[BuildJob]):
        """Alert about builds needing approval."""
        if not builds:
            return
        
        lines = [
            "⏳ *Approval Needed*",
            "",
            f"{len(builds)} improvement(s) need your approval:",
            ""
        ]
        
        for i, build in enumerate(builds, 1):
            lines.append(f"{i}. *{build.spec_title}*")
            lines.append(f"   Complexity: {build.complexity} | Risk: {build.risk}")
            lines.append(f"   `/approve {build.spec_id}`")
            lines.append("")
        
        lines.append("Reply with `/approve <id>` or `/reject <id>`")
        
        await self.send_telegram("\n".join(lines))
    
    # ========================================================================
    # DIGESTS
    # ========================================================================
    
    async def send_daily_digest(self):
        """Send daily cost and progress digest."""
        cost_summary = get_cost_summary()
        queue_status = get_queue_status()
        
        today = cost_summary.get("today", {})
        
        lines = [
            "📊 *Daily Reflection Digest*",
            "",
            f"*Today's Activity*",
            f"• Cycles run: {today.get('cycles', 0)}",
            f"• Cost: ${today.get('total_cost', 0):.2f}",
            f"• Improvements: {today.get('outcomes', {}).get('builds_completed', 0)} completed",
            "",
            f"*This Month*",
            f"• Total cost: ${cost_summary.get('this_month', {}).get('total_cost', 0):.2f}",
            f"• Total improvements: {cost_summary.get('this_month', {}).get('builds_completed', 0)}",
            "",
        ]
        
        # Queue status
        status_counts = queue_status.get("status_counts", {})
        queued = status_counts.get("queued", 0)
        pending = status_counts.get("needs_approval", 0)
        
        if queued + pending > 0:
            lines.append("*Build Queue*")
            if queued > 0:
                lines.append(f"• {queued} queued")
            if pending > 0:
                lines.append(f"• {pending} awaiting approval")
        
        await self.send_telegram("\n".join(lines))
    
    async def send_weekly_digest(self):
        """Send weekly summary digest."""
        cost_summary = get_cost_summary()
        
        week = cost_summary.get("this_week", {})
        roi = cost_summary.get("roi_metrics", {})
        
        lines = [
            "📈 *Weekly Reflection Summary*",
            "",
            f"*This Week*",
            f"• Reflection cycles: {week.get('cycles', 0)}",
            f"• Total cost: ${week.get('total_cost', 0):.2f}",
            f"• Improvements implemented: {week.get('builds_completed', 0)}",
            "",
            f"*ROI Metrics*",
            f"• Cost per improvement: ${roi.get('cost_per_improvement', 0):.2f}",
            f"• Est. monthly cost: ${roi.get('estimated_monthly', 0):.2f}",
        ]
        
        await self.send_telegram("\n".join(lines))
    
    # ========================================================================
    # DASHBOARD
    # ========================================================================
    
    async def update_dashboard(self, report: CycleReport):
        """Update dashboard with cycle report."""
        try:
            await self.http.post(
                f"{DASHBOARD_API}/api/reflection/cycle",
                json=report.to_dict()
            )
        except Exception as e:
            logger.debug(f"Dashboard update failed: {e}")
    
    # ========================================================================
    # STATUS REPORTS
    # ========================================================================
    
    def get_status_message(self) -> str:
        """Get current reflection system status."""
        cost_summary = get_cost_summary()
        queue_status = get_queue_status()
        
        today = cost_summary.get("today", {})
        
        lines = [
            "🔄 *Reflection System Status*",
            "",
            f"*Today*",
            f"• Cycles: {today.get('cycles', 0)}",
            f"• Cost: ${today.get('total_cost', 0):.2f}",
            f"• Proposals: {today.get('outcomes', {}).get('proposals', 0)}",
            f"• Completed: {today.get('outcomes', {}).get('builds_completed', 0)}",
            "",
        ]
        
        # Queue status
        status_counts = queue_status.get("status_counts", {})
        if status_counts:
            lines.append("*Build Queue*")
            for status, count in status_counts.items():
                lines.append(f"• {status}: {count}")
        
        return "\n".join(lines)


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_reporter: Optional[ReflectionReporter] = None


def get_reporter() -> ReflectionReporter:
    """Get global reporter instance."""
    global _reporter
    if _reporter is None:
        _reporter = ReflectionReporter()
    return _reporter


async def report_cycle(
    cycle_id: str,
    summary: InteractionSummary,
    dialogue: DialogueResult,
    specs: List[GeneratedSpec],
    builds: List[BuildJob],
    cost: CycleCost
) -> CycleReport:
    """Report cycle completion."""
    return await get_reporter().report_cycle_complete(
        cycle_id, summary, dialogue, specs, builds, cost
    )


async def send_telegram(message: str) -> bool:
    """Send Telegram message."""
    return await get_reporter().send_telegram(message)


async def send_daily_digest():
    """Send daily digest."""
    await get_reporter().send_daily_digest()


async def send_weekly_digest():
    """Send weekly digest."""
    await get_reporter().send_weekly_digest()


def get_status_message() -> str:
    """Get status message."""
    return get_reporter().get_status_message()


