#!/usr/bin/env python3
"""
ARIA SELF-HEALING DAEMON
=========================

Continuously monitors Aria and automatically heals detected issues.

Features:
- Scans error logs every minute
- Matches against known patterns
- Executes healing actions with safety limits
- Tracks healing history
- Escalates to human when needed
"""

import os
import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from collections import defaultdict
import httpx

logger = logging.getLogger("aria.healing.daemon")

# ============================================================================
# CONFIGURATION
# ============================================================================

CHECK_INTERVAL_SECONDS = int(os.getenv("HEALING_CHECK_INTERVAL", "60"))
MAX_HEALS_PER_HOUR = int(os.getenv("HEALING_MAX_PER_HOUR", "5"))
ESCALATION_THRESHOLD = int(os.getenv("HEALING_ESCALATION_THRESHOLD", "2"))

WORKSPACE_ROOT = Path(os.getenv("WORKSPACE_ROOT", "/opt/fpai/aria-command"))


@dataclass
class HealingEvent:
    """A healing event that occurred."""
    timestamp: datetime
    pattern_id: str
    action_name: str
    success: bool
    message: str


class SelfHealingDaemon:
    """
    Continuously monitors and heals Aria.
    
    Process:
    1. Scan recent error logs
    2. Match against known patterns
    3. Execute healing actions (with safety limits)
    4. Track results and escalate if needed
    """
    
    def __init__(self):
        self.running = False
        self.heal_count_this_hour = 0
        self.hour_start = datetime.now().replace(minute=0, second=0, microsecond=0)
        self.healing_history: List[HealingEvent] = []
        self.consecutive_failures: Dict[str, int] = defaultdict(int)
        self.last_check: Optional[datetime] = None
        
    async def start(self):
        """Start the healing daemon."""
        self.running = True
        logger.info(f"Self-healing daemon started (check every {CHECK_INTERVAL_SECONDS}s)")
        
        while self.running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error(f"Healing cycle error: {e}")
            
            await asyncio.sleep(CHECK_INTERVAL_SECONDS)
    
    def stop(self):
        """Stop the daemon."""
        self.running = False
        logger.info("Self-healing daemon stopped")
    
    async def _run_cycle(self):
        """Run one healing cycle."""
        now = datetime.now()
        
        # Reset hourly counter if needed
        if now.hour != self.hour_start.hour:
            self.heal_count_this_hour = 0
            self.hour_start = now.replace(minute=0, second=0, microsecond=0)
        
        # Check if we've hit the hourly limit
        if self.heal_count_this_hour >= MAX_HEALS_PER_HOUR:
            logger.debug(f"Hourly heal limit reached ({MAX_HEALS_PER_HOUR})")
            return
        
        # Scan for errors
        errors = await self._scan_error_logs()
        
        if not errors:
            return
        
        # Import pattern matching
        try:
            from .patterns import match_error_pattern, HEALING_PATTERNS
            from .actions import execute_healing_action, ActionResult
        except ImportError:
            from sovereign.healing.patterns import match_error_pattern, HEALING_PATTERNS
            from sovereign.healing.actions import execute_healing_action, ActionResult
        
        # Process each error
        for error in errors:
            pattern = match_error_pattern(error)
            
            if not pattern:
                continue
            
            # Check if pattern can be healed
            if not pattern.can_heal():
                logger.debug(f"Pattern {pattern.id} cannot heal right now")
                continue
            
            # Check if requires approval
            if pattern.requires_approval:
                await self._request_approval(pattern, error)
                continue
            
            # Execute healing
            logger.info(f"Healing: {pattern.name} -> {pattern.fix_action}")
            
            result = await execute_healing_action(pattern.fix_action)
            
            success = result.result == ActionResult.SUCCESS
            pattern.record_heal(success)
            
            # Track the event
            event = HealingEvent(
                timestamp=now,
                pattern_id=pattern.id,
                action_name=pattern.fix_action,
                success=success,
                message=result.message
            )
            self.healing_history.append(event)
            self.heal_count_this_hour += 1
            
            if success:
                self.consecutive_failures[pattern.id] = 0
                logger.info(f"Healed: {pattern.name}")
            else:
                self.consecutive_failures[pattern.id] += 1
                logger.warning(f"Healing failed: {pattern.name} - {result.message}")
                
                # Check for escalation
                if self.consecutive_failures[pattern.id] >= ESCALATION_THRESHOLD:
                    await self._escalate(pattern, error)
        
        self.last_check = now
    
    async def _scan_error_logs(self) -> List[str]:
        """
        Scan recent logs for errors.
        
        Returns list of error messages from the last check interval.
        """
        try:
            # Use journalctl to get recent aria-command errors
            since = self.last_check or (datetime.now() - timedelta(minutes=5))
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")
            
            result = subprocess.run(
                ["journalctl", "-u", "aria-command", "--no-pager",
                 "--since", since_str, "-p", "err"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout:
                # Split into individual log entries
                lines = result.stdout.strip().split("\n")
                # Filter out empty lines
                errors = [line for line in lines if line.strip()]
                return errors
            
            return []
            
        except subprocess.TimeoutExpired:
            logger.warning("Log scan timed out")
            return []
        except Exception as e:
            logger.error(f"Log scan failed: {e}")
            return []
    
    async def _request_approval(self, pattern, error: str):
        """Request human approval for a healing action."""
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.getenv("SUNHEART_CHAT_ID", "")
            
            if not token or not chat_id:
                return
            
            message = (
                f"🔧 **Healing Approval Needed**\n\n"
                f"**Issue:** {pattern.name}\n"
                f"**Severity:** {pattern.severity.value}\n"
                f"**Proposed Fix:** {pattern.fix_action}\n\n"
                f"**Error:**\n```\n{error[:500]}\n```\n\n"
                f"Reply `/approve_heal {pattern.id}` to proceed."
            )
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                )
                
        except Exception as e:
            logger.error(f"Failed to request approval: {e}")
    
    async def _escalate(self, pattern, error: str):
        """Escalate to human after repeated failures."""
        try:
            token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.getenv("SUNHEART_CHAT_ID", "")
            
            if not token or not chat_id:
                return
            
            message = (
                f"🚨 **Healing Escalation**\n\n"
                f"Failed to heal **{pattern.name}** after {ESCALATION_THRESHOLD} attempts.\n\n"
                f"**Error:**\n```\n{error[:500]}\n```\n\n"
                f"Manual intervention required."
            )
            
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                )
                
            # Reset counter to avoid spam
            self.consecutive_failures[pattern.id] = 0
            
        except Exception as e:
            logger.error(f"Failed to escalate: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current daemon status."""
        return {
            "running": self.running,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "heals_this_hour": self.heal_count_this_hour,
            "max_heals_per_hour": MAX_HEALS_PER_HOUR,
            "history_count": len(self.healing_history),
            "consecutive_failures": dict(self.consecutive_failures)
        }
    
    def get_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent healing events."""
        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "pattern": e.pattern_id,
                "action": e.action_name,
                "success": e.success,
                "message": e.message
            }
            for e in self.healing_history[-limit:]
        ]


# ============================================================================
# SINGLETON
# ============================================================================

_daemon: Optional[SelfHealingDaemon] = None
_daemon_task: Optional[asyncio.Task] = None


def get_healing_daemon() -> SelfHealingDaemon:
    """Get or create the global healing daemon."""
    global _daemon
    if _daemon is None:
        _daemon = SelfHealingDaemon()
    return _daemon


async def start_healing_daemon():
    """Start the healing daemon as a background task."""
    global _daemon_task
    
    daemon = get_healing_daemon()
    
    if _daemon_task is not None and not _daemon_task.done():
        logger.warning("Healing daemon already running")
        return
    
    _daemon_task = asyncio.create_task(daemon.start())
    logger.info("Started healing daemon background task")


async def stop_healing_daemon():
    """Stop the healing daemon."""
    global _daemon_task
    
    daemon = get_healing_daemon()
    daemon.stop()
    
    if _daemon_task:
        _daemon_task.cancel()
        try:
            await _daemon_task
        except asyncio.CancelledError:
            pass
        _daemon_task = None


