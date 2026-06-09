#!/usr/bin/env python3
"""
ARIA ULTRA POWER - EVOLUTION LOOP
===================================

24-hour evolution cycle:
1. Analyze: Review all interactions, errors, performance
2. Identify: Find top improvement opportunities
3. Design: Create specific code changes
4. Validate: Test in sandbox
5. Propose: Send for approval (or auto-apply if safe)
6. Learn: Track results, update models
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import httpx

logger = logging.getLogger("aria.evolution.loop")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")


@dataclass
class EvolutionCycle:
    """Record of an evolution cycle."""
    cycle_id: str
    started_at: float
    completed_at: Optional[float]
    analysis_result: Optional[Dict]
    improvements_identified: int
    changes_proposed: int
    changes_applied: int
    changes_rejected: int
    status: str  # "running", "completed", "failed"


@dataclass 
class EvolutionState:
    """Current evolution system state."""
    enabled: bool
    auto_apply_safe: bool  # Auto-apply safe changes
    cycle_interval_hours: int
    last_cycle: Optional[float]
    total_cycles: int
    total_improvements: int
    pending_proposals: int


class EvolutionLoop:
    """
    Main evolution loop for Aria self-improvement.
    
    Features:
    - Scheduled analysis cycles
    - Improvement identification
    - Safe code generation
    - Approval workflow
    - Learning from results
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        self._state = EvolutionState(
            enabled=False,
            auto_apply_safe=True,
            cycle_interval_hours=24,
            last_cycle=None,
            total_cycles=0,
            total_improvements=0,
            pending_proposals=0,
        )
        
        self._current_cycle: Optional[EvolutionCycle] = None
        self._cycle_history: List[EvolutionCycle] = []
        
        logger.info("EvolutionLoop initialized")
    
    async def start(self, auto_apply_safe: bool = True):
        """Start the evolution loop."""
        if self._running:
            return
        
        self._running = True
        self._state.enabled = True
        self._state.auto_apply_safe = auto_apply_safe
        
        self._task = asyncio.create_task(self._run_loop())
        
        await self._notify("🧬 **Evolution System Started**\n\nAria will now continuously improve herself.")
        logger.info("Evolution loop started")
    
    async def stop(self):
        """Stop the evolution loop."""
        self._running = False
        self._state.enabled = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self._notify("⏹️ **Evolution System Stopped**")
        logger.info("Evolution loop stopped")
    
    async def _run_loop(self):
        """Main evolution loop."""
        while self._running:
            try:
                # Check if it's time for a cycle
                now = time.time()
                interval_seconds = self._state.cycle_interval_hours * 3600
                
                if self._state.last_cycle is None or (now - self._state.last_cycle) >= interval_seconds:
                    await self._run_cycle()
                    self._state.last_cycle = now
            
            except Exception as e:
                logger.error(f"Evolution loop error: {e}")
            
            # Check every hour
            await asyncio.sleep(3600)
    
    async def _run_cycle(self):
        """Run a single evolution cycle."""
        from .self_analyze import get_self_analyzer
        from .codegen import get_code_generator
        from .validate import get_validator
        
        cycle_id = f"evo_{int(time.time())}"
        
        self._current_cycle = EvolutionCycle(
            cycle_id=cycle_id,
            started_at=time.time(),
            completed_at=None,
            analysis_result=None,
            improvements_identified=0,
            changes_proposed=0,
            changes_applied=0,
            changes_rejected=0,
            status="running",
        )
        
        logger.info(f"Starting evolution cycle: {cycle_id}")
        await self._notify(f"🔄 **Evolution Cycle Started**\nID: `{cycle_id}`")
        
        try:
            # Step 1: Analyze
            analyzer = get_self_analyzer()
            report = analyzer.analyze(hours=24)
            
            self._current_cycle.analysis_result = {
                "score": report.overall_score,
                "issues": len(report.issues),
                "suggestions": len(report.improvement_suggestions),
            }
            
            # Step 2: Identify improvements
            improvements = self._identify_improvements(report)
            self._current_cycle.improvements_identified = len(improvements)
            
            if not improvements:
                self._current_cycle.status = "completed"
                self._current_cycle.completed_at = time.time()
                await self._notify(f"✅ **Evolution Cycle Complete**\n\nScore: {report.overall_score:.0f}/100\nNo improvements needed!")
                return
            
            # Step 3: Design changes
            generator = get_code_generator()
            
            for imp in improvements[:3]:  # Max 3 changes per cycle
                change = await generator.generate_change(
                    description=imp["description"],
                    target_file=imp["target_file"],
                    context=imp.get("context", ""),
                )
                
                if change:
                    self._current_cycle.changes_proposed += 1
                    
                    # Step 4: Validate or propose
                    if change.risk_level == "safe" and self._state.auto_apply_safe:
                        # Auto-apply safe changes
                        validator = get_validator()
                        await validator.capture_baseline(change.change_id)
                        
                        result = await generator.apply_change(change.change_id, force=True)
                        
                        if result.success:
                            self._current_cycle.changes_applied += 1
                            self._state.total_improvements += 1
                            
                            await self._notify(
                                f"✅ **Auto-Applied Improvement**\n\n"
                                f"File: `{change.file_path}`\n"
                                f"Change: {change.description[:100]}"
                            )
                            
                            # Validate the change
                            validation = await validator.validate_change(change.change_id, wait_minutes=1)
                            if validation.should_rollback:
                                generator.rollback_last()
                                self._current_cycle.changes_applied -= 1
                                await self._notify(f"⚠️ **Change Rolled Back**\n\nReason: {validation.reason}")
                    else:
                        # Propose for approval
                        self._state.pending_proposals += 1
                        await self._notify(
                            f"📝 **Improvement Proposal**\n\n"
                            f"{generator.format_change(change)}\n\n"
                            f"Reply `/approve {change.change_id}` or `/reject {change.change_id}`"
                        )
            
            self._current_cycle.status = "completed"
            self._current_cycle.completed_at = time.time()
            
            # Summary
            summary = (
                f"📊 **Evolution Cycle Complete**\n\n"
                f"ID: `{cycle_id}`\n"
                f"Score: {report.overall_score:.0f}/100\n"
                f"Improvements identified: {self._current_cycle.improvements_identified}\n"
                f"Changes proposed: {self._current_cycle.changes_proposed}\n"
                f"Auto-applied: {self._current_cycle.changes_applied}\n"
                f"Pending approval: {self._state.pending_proposals}"
            )
            
            await self._notify(summary)
            
        except Exception as e:
            self._current_cycle.status = "failed"
            self._current_cycle.completed_at = time.time()
            logger.error(f"Evolution cycle failed: {e}")
            await self._notify(f"❌ **Evolution Cycle Failed**\n\nError: {str(e)}")
        
        finally:
            self._cycle_history.append(self._current_cycle)
            self._state.total_cycles += 1
    
    def _identify_improvements(self, report) -> List[Dict]:
        """Identify specific improvements from analysis report."""
        improvements = []
        
        # From issues
        for issue in report.issues:
            if issue.auto_fixable:
                improvements.append({
                    "type": "fix_issue",
                    "description": f"Fix: {issue.description}",
                    "target_file": self._guess_file_for_issue(issue),
                    "context": issue.suggested_fix or "",
                    "priority": 10 if issue.severity == "high" else 5,
                })
        
        # From capability gaps
        for gap in report.capability_gaps:
            if gap.implementation_effort in ["trivial", "small"]:
                improvements.append({
                    "type": "add_capability",
                    "description": f"Add capability: {gap.capability}",
                    "target_file": self._guess_file_for_capability(gap),
                    "context": gap.description,
                    "priority": gap.priority,
                })
        
        # From suggestions
        for suggestion in report.improvement_suggestions[:5]:
            if "response time" in suggestion.lower():
                improvements.append({
                    "type": "optimize",
                    "description": suggestion,
                    "target_file": "/opt/fpai/aria-command/brain/opus_handler.py",
                    "context": "Optimize response time",
                    "priority": 7,
                })
        
        # Sort by priority
        return sorted(improvements, key=lambda x: x.get("priority", 0), reverse=True)
    
    def _guess_file_for_issue(self, issue) -> str:
        """Guess which file to modify for an issue."""
        desc_lower = issue.description.lower()
        
        if "approval" in desc_lower or "permission" in desc_lower:
            return "/opt/fpai/aria-command/access/terminal.py"
        if "response" in desc_lower or "slow" in desc_lower:
            return "/opt/fpai/aria-command/brain/opus_handler.py"
        if "trading" in desc_lower:
            return "/opt/fpai/aria-command/trading/awareness.py"
        
        return "/opt/fpai/aria-command/brain/opus_handler.py"
    
    def _guess_file_for_capability(self, gap) -> str:
        """Guess which file to modify for a capability."""
        cap_lower = gap.capability.lower()
        
        if "trading" in cap_lower:
            return "/opt/fpai/aria-command/trading/awareness.py"
        if "server" in cap_lower:
            return "/opt/fpai/aria-command/access/terminal.py"
        
        return "/opt/fpai/aria-command/telegram/bot.py"
    
    async def _notify(self, message: str):
        """Send notification via Telegram."""
        if not SUNHEART_CHAT_ID:
            return
        
        try:
            await self.http.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": SUNHEART_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
        except Exception as e:
            logger.error(f"Notification error: {e}")
    
    async def run_manual_cycle(self):
        """Trigger a manual evolution cycle."""
        await self._run_cycle()
    
    def get_state(self) -> EvolutionState:
        """Get current state."""
        return self._state
    
    def get_history(self, limit: int = 10) -> List[EvolutionCycle]:
        """Get cycle history."""
        return self._cycle_history[-limit:]
    
    def format_status(self) -> str:
        """Format status for display."""
        state = self._state
        
        lines = [
            "🧬 **Evolution System Status**",
            "",
            f"Enabled: {'Yes' if state.enabled else 'No'}",
            f"Auto-apply safe: {'Yes' if state.auto_apply_safe else 'No'}",
            f"Cycle interval: {state.cycle_interval_hours} hours",
            f"Total cycles: {state.total_cycles}",
            f"Total improvements: {state.total_improvements}",
            f"Pending proposals: {state.pending_proposals}",
        ]
        
        if state.last_cycle:
            hours_ago = (time.time() - state.last_cycle) / 3600
            lines.append(f"Last cycle: {hours_ago:.1f} hours ago")
        
        if self._current_cycle and self._current_cycle.status == "running":
            lines.append("")
            lines.append("**Current Cycle:**")
            lines.append(f"ID: `{self._current_cycle.cycle_id}`")
            lines.append(f"Improvements: {self._current_cycle.improvements_identified}")
        
        return "\n".join(lines)


# Singleton
_loop: Optional[EvolutionLoop] = None


def get_evolution_loop() -> EvolutionLoop:
    """Get global EvolutionLoop instance."""
    global _loop
    if _loop is None:
        _loop = EvolutionLoop()
    return _loop


