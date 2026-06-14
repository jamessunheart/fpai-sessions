"""
Background Development Daemon - Works on improvements during idle time.

Scans for opportunities, executes low-risk improvements automatically,
and queues higher-risk items for human review.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .sensors import get_sensor_network, SensorFinding, SensorPriority
from .opportunity_queue import get_opportunity_queue, Opportunity, OpportunityType

logger = logging.getLogger("aria.proactive.background_dev")


@dataclass
class DailyReport:
    """Summary of background development activity."""
    date: datetime
    opportunities_found: int = 0
    auto_executed: int = 0
    queued_for_review: int = 0
    successful_fixes: List[str] = field(default_factory=list)
    failed_fixes: List[str] = field(default_factory=list)
    high_priority_items: List[str] = field(default_factory=list)
    
    def to_message(self) -> str:
        """Generate morning briefing message."""
        parts = [
            f"Good morning! Here's what I did overnight ({self.date.strftime('%B %d')}):",
            "",
        ]
        
        if self.successful_fixes:
            parts.append(f"✅ **Auto-fixed {len(self.successful_fixes)} issues:**")
            for fix in self.successful_fixes[:5]:
                parts.append(f"  • {fix}")
            if len(self.successful_fixes) > 5:
                parts.append(f"  ... and {len(self.successful_fixes) - 5} more")
            parts.append("")
        
        if self.high_priority_items:
            parts.append(f"⚠️ **{len(self.high_priority_items)} items need your attention:**")
            for item in self.high_priority_items[:3]:
                parts.append(f"  • {item}")
            parts.append("")
        
        if self.queued_for_review > 0:
            parts.append(f"📋 **{self.queued_for_review} opportunities queued** for your review")
            parts.append("Use `/opportunities` to see them")
        
        if not self.successful_fixes and not self.high_priority_items:
            parts.append("All systems healthy - nothing needed overnight!")
        
        return "\n".join(parts)


class BackgroundDevelopmentDaemon:
    """
    Background daemon that continuously improves the system.
    
    Operating modes:
    - Active: During configured hours, aggressive scanning and auto-fixing
    - Passive: Outside hours, only critical fixes and monitoring
    
    Safety:
    - Only auto-executes Tier 1 (high confidence, low risk) changes
    - Creates backups before any modification
    - Logs all actions for review
    """
    
    # Configuration
    ACTIVE_HOURS = (9, 22)  # 9 AM to 10 PM
    SCAN_INTERVAL = 3600   # 1 hour between full scans
    MINI_SCAN_INTERVAL = 300  # 5 minutes for quick checks
    
    # Safety
    MAX_AUTO_FIXES_PER_HOUR = 5
    MIN_CONFIDENCE_FOR_AUTO = 0.90
    
    def __init__(self):
        self.is_running = False
        self.last_scan: Optional[datetime] = None
        self.daily_report: Optional[DailyReport] = None
        self.auto_fixes_this_hour = 0
        self.last_hour_reset = datetime.now()
        
        self.sensor_network = get_sensor_network()
        self.opportunity_queue = get_opportunity_queue()
    
    async def start(self):
        """Start the background development daemon."""
        self.is_running = True
        logger.info("Background Development Daemon started")
        
        while self.is_running:
            try:
                # Reset hourly counter if needed
                if datetime.now().hour != self.last_hour_reset.hour:
                    self.auto_fixes_this_hour = 0
                    self.last_hour_reset = datetime.now()
                
                # Check if we should do a full scan
                if self._should_full_scan():
                    await self._full_scan_cycle()
                else:
                    await self._mini_scan_cycle()
                
                # Generate morning report if it's a new day
                await self._check_morning_report()
                
                # Wait before next iteration
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Background dev error: {e}")
                await asyncio.sleep(300)  # Wait longer on error
    
    def stop(self):
        """Stop the daemon."""
        self.is_running = False
        logger.info("Background Development Daemon stopped")
    
    async def _full_scan_cycle(self):
        """Run a full sensor scan and process findings."""
        logger.info("Starting full scan cycle")
        
        # Run all sensors
        findings = await self.sensor_network.scan_all()
        
        if not self.daily_report:
            self.daily_report = DailyReport(date=datetime.now())
        
        self.daily_report.opportunities_found += len(findings)
        
        # Process findings
        for finding in findings:
            await self._process_finding(finding)
        
        self.last_scan = datetime.now()
        logger.info(f"Full scan complete: {len(findings)} findings")
    
    async def _mini_scan_cycle(self):
        """Quick scan for critical issues only."""
        # Only scan infrastructure for critical issues
        from .sensors import SensorCategory
        findings = await self.sensor_network.scan_category(SensorCategory.INFRASTRUCTURE)
        
        # Only process critical findings
        critical = [f for f in findings if f.priority == SensorPriority.CRITICAL]
        
        for finding in critical:
            await self._process_finding(finding, urgent=True)
    
    async def _process_finding(self, finding: SensorFinding, urgent: bool = False):
        """Process a sensor finding."""
        # Create opportunity
        opportunity = self.opportunity_queue.add_from_finding(finding)
        
        if not opportunity:
            return  # Duplicate or invalid
        
        # Check if we should auto-fix
        should_auto = (
            opportunity.auto_executable and
            opportunity.confidence >= self.MIN_CONFIDENCE_FOR_AUTO and
            self.auto_fixes_this_hour < self.MAX_AUTO_FIXES_PER_HOUR and
            self._is_active_hours()
        )
        
        # Critical issues in passive mode still get auto-fixed
        if urgent and opportunity.auto_executable:
            should_auto = True
        
        if should_auto:
            success = await self._auto_fix(opportunity)
            
            if success:
                self.auto_fixes_this_hour += 1
                if self.daily_report:
                    self.daily_report.auto_executed += 1
                    self.daily_report.successful_fixes.append(opportunity.title)
            else:
                if self.daily_report:
                    self.daily_report.failed_fixes.append(opportunity.title)
        else:
            # Queue for review
            if self.daily_report:
                self.daily_report.queued_for_review += 1
                
                if finding.priority in [SensorPriority.HIGH, SensorPriority.CRITICAL]:
                    self.daily_report.high_priority_items.append(opportunity.title)
    
    async def _auto_fix(self, opportunity: Opportunity) -> bool:
        """Attempt to auto-fix an opportunity."""
        logger.info(f"Auto-fixing: {opportunity.title}")
        
        try:
            self.opportunity_queue.start(opportunity.id)
            
            # Get the appropriate agent
            from agents.orchestrator import get_orchestrator
            orchestrator = get_orchestrator()
            
            result = await orchestrator.process_task(
                task=f"Fix: {opportunity.title}\n{opportunity.description}",
                context={
                    "file_path": opportunity.file_path,
                    "execution_plan": opportunity.execution_plan
                },
                auto_execute=True  # Allow auto-execution for Tier 1
            )
            
            success = result.get("execution", {}).get("success", False)
            self.opportunity_queue.complete(opportunity.id, success)
            
            return success
            
        except Exception as e:
            logger.error(f"Auto-fix failed for {opportunity.title}: {e}")
            self.opportunity_queue.complete(opportunity.id, False)
            return False
    
    def _should_full_scan(self) -> bool:
        """Check if it's time for a full scan."""
        if self.last_scan is None:
            return True
        
        elapsed = (datetime.now() - self.last_scan).total_seconds()
        
        # More frequent scans during active hours
        interval = self.SCAN_INTERVAL if self._is_active_hours() else self.SCAN_INTERVAL * 2
        
        return elapsed >= interval
    
    def _is_active_hours(self) -> bool:
        """Check if we're in active development hours."""
        hour = datetime.now().hour
        return self.ACTIVE_HOURS[0] <= hour < self.ACTIVE_HOURS[1]
    
    async def _check_morning_report(self):
        """Check if we should generate and send morning report."""
        now = datetime.now()
        
        # Send report at 8 AM
        if now.hour == 8 and self.daily_report:
            await self._send_morning_report()
            
            # Reset for new day
            self.daily_report = DailyReport(date=now)
    
    async def _send_morning_report(self):
        """Send the morning briefing."""
        if not self.daily_report:
            return
        
        message = self.daily_report.to_message()
        
        # Send via Telegram
        try:
            from telegram.bot import send_to_sunheart
            await send_to_sunheart(message, voice=True)
            logger.info("Morning report sent")
        except Exception as e:
            logger.error(f"Failed to send morning report: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get daemon status."""
        return {
            "is_running": self.is_running,
            "mode": "active" if self._is_active_hours() else "passive",
            "last_scan": self.last_scan.isoformat() if self.last_scan else None,
            "auto_fixes_this_hour": self.auto_fixes_this_hour,
            "max_auto_fixes": self.MAX_AUTO_FIXES_PER_HOUR,
            "daily_report": {
                "opportunities_found": self.daily_report.opportunities_found if self.daily_report else 0,
                "auto_executed": self.daily_report.auto_executed if self.daily_report else 0,
                "queued_for_review": self.daily_report.queued_for_review if self.daily_report else 0
            }
        }


# Singleton instance
_daemon: Optional[BackgroundDevelopmentDaemon] = None

def get_background_daemon() -> BackgroundDevelopmentDaemon:
    """Get or create background daemon instance."""
    global _daemon
    if _daemon is None:
        _daemon = BackgroundDevelopmentDaemon()
    return _daemon

async def start_background_daemon():
    """Start the background development daemon."""
    daemon = get_background_daemon()
    await daemon.start()


