"""
PROACTIVE EVOLUTION DAEMON
===========================

Runs continuously to evolve the system proactively.

Instead of waiting for issues to happen and then fixing them,
this daemon:

1. PREDICTS: Analyzes patterns to predict likely issues
2. PREVENTS: Applies preventive evolutions before issues occur
3. OPTIMIZES: Continuously improves thresholds and behaviors
4. REPORTS: Keeps the steward informed of evolution activity

Runs every 30 minutes for proactive cycles.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .self_evolution_engine import (
    get_evolution_engine, 
    SelfEvolutionEngine,
    EvolutionType,
    RiskLevel,
    LessonLearned,
    ProposedEvolution,
    ApprovalStatus
)

logger = logging.getLogger("aria.evolution.daemon")


class ProactiveEvolutionDaemon:
    """
    The daemon that drives proactive system evolution.
    
    Key behaviors:
    1. Pattern monitoring - watch for recurring issues
    2. Threshold optimization - tune based on performance
    3. Predictive prevention - fix issues before they happen
    4. Learning consolidation - strengthen reliable lessons
    """
    
    # How often to run proactive cycles
    CYCLE_INTERVAL = timedelta(minutes=30)
    
    # Minimum issues to trigger pattern analysis
    PATTERN_THRESHOLD = 3
    
    # Confidence threshold for auto-application
    CONFIDENCE_THRESHOLD = 0.8
    
    def __init__(self):
        self.engine = get_evolution_engine()
        self.last_cycle = datetime.now()
        self.cycles_run = 0
        self.evolutions_applied = 0
        self.running = False
        logger.info("🧬 Proactive Evolution Daemon initialized")
    
    async def start(self):
        """Start the proactive evolution daemon."""
        self.running = True
        logger.info("🧬 Proactive Evolution Daemon started")
        
        while self.running:
            try:
                await self._run_cycle()
            except Exception as e:
                logger.error(f"Evolution cycle error: {e}")
            
            # Wait for next cycle
            await asyncio.sleep(self.CYCLE_INTERVAL.total_seconds())
    
    async def stop(self):
        """Stop the daemon."""
        self.running = False
        logger.info("🧬 Proactive Evolution Daemon stopped")
    
    async def _run_cycle(self):
        """Run a single proactive evolution cycle."""
        self.cycles_run += 1
        cycle_start = datetime.now()
        logger.info(f"🧬 Evolution cycle #{self.cycles_run} starting")
        
        # 1. Analyze recent issues for patterns
        patterns_found = await self._analyze_patterns()
        
        # 2. Check for optimization opportunities
        optimizations = await self._find_optimizations()
        
        # 3. Apply auto-approvable evolutions
        applied = await self._apply_safe_evolutions()
        
        # 4. Consolidate learning
        await self._consolidate_learning()
        
        # 5. Generate predictive warnings
        predictions = await self._predict_issues()
        
        # 6. Report status
        duration = (datetime.now() - cycle_start).total_seconds()
        self.last_cycle = datetime.now()
        
        logger.info(
            f"🧬 Evolution cycle #{self.cycles_run} complete: "
            f"{patterns_found} patterns, {len(optimizations)} optimizations, "
            f"{applied} applied, {len(predictions)} predictions "
            f"({duration:.1f}s)"
        )
        
        return {
            "cycle": self.cycles_run,
            "patterns_found": patterns_found,
            "optimizations": len(optimizations),
            "evolutions_applied": applied,
            "predictions": len(predictions),
            "duration_s": duration
        }
    
    async def _analyze_patterns(self) -> int:
        """Analyze issue patterns and create lessons."""
        patterns = self.engine.memory.patterns
        new_patterns = 0
        
        for issue_hash, count in patterns.items():
            if count >= self.PATTERN_THRESHOLD:
                # This pattern is recurring - worth analyzing
                # In a full implementation, we'd use AI to analyze the pattern
                new_patterns += 1
        
        return new_patterns
    
    async def _find_optimizations(self) -> List[Dict[str, Any]]:
        """Find opportunities to optimize system behavior."""
        optimizations = []
        
        # Check lessons for optimization opportunities
        for lesson in self.engine.memory.lessons.values():
            if lesson.is_reliable and lesson.success_count > 10:
                # This lesson is very reliable - could be promoted
                optimizations.append({
                    "type": "promote_lesson",
                    "lesson_id": lesson.id,
                    "reason": f"High reliability ({lesson.confidence:.0%}) with {lesson.success_count} successes"
                })
        
        return optimizations
    
    async def _apply_safe_evolutions(self) -> int:
        """Apply evolutions that are safe to auto-apply."""
        applied = 0
        
        pending = self.engine.memory.get_pending_evolutions()
        
        for evolution in pending:
            # Only auto-apply low-risk evolutions
            if evolution.risk_level == RiskLevel.LOW:
                evolution.approval_status = ApprovalStatus.AUTO_APPROVED
                success, message = await self.engine.apply_evolution(evolution)
                if success:
                    applied += 1
                    self.evolutions_applied += 1
                    logger.info(f"✅ Auto-evolved: {evolution.description}")
            
            # Medium risk with high confidence lesson
            elif evolution.risk_level == RiskLevel.MEDIUM:
                lesson_id = evolution.proposed_change.get("lesson_id")
                if lesson_id and lesson_id in self.engine.memory.lessons:
                    lesson = self.engine.memory.lessons[lesson_id]
                    if lesson.confidence >= self.CONFIDENCE_THRESHOLD:
                        evolution.approval_status = ApprovalStatus.AUTO_APPROVED
                        success, message = await self.engine.apply_evolution(evolution)
                        if success:
                            applied += 1
                            self.evolutions_applied += 1
                            logger.info(f"✅ Confidence-evolved: {evolution.description}")
        
        return applied
    
    async def _consolidate_learning(self):
        """Consolidate and strengthen lessons."""
        # Decay old, unreliable lessons
        for lesson_id, lesson in list(self.engine.memory.lessons.items()):
            total = lesson.success_count + lesson.failure_count
            
            # Remove lessons that have failed too much
            if total >= 10 and lesson.confidence < 0.3:
                logger.info(f"📚 Removing unreliable lesson: {lesson_id}")
                del self.engine.memory.lessons[lesson_id]
            
            # Strengthen reliable lessons
            elif lesson.is_reliable and total >= 20:
                # This is a very reliable lesson - it's becoming wisdom
                logger.debug(f"📚 Lesson {lesson_id} is becoming wisdom")
        
        self.engine.memory._save()
    
    async def _predict_issues(self) -> List[Dict[str, Any]]:
        """Predict likely future issues based on patterns."""
        predictions = []
        
        # Look for patterns that are building up
        for issue_hash, count in self.engine.memory.patterns.items():
            if 2 <= count < self.PATTERN_THRESHOLD:
                # This pattern is emerging but not yet critical
                predictions.append({
                    "pattern_hash": issue_hash,
                    "occurrences": count,
                    "threshold": self.PATTERN_THRESHOLD,
                    "prediction": "Pattern emerging - watch for recurrence"
                })
        
        return predictions
    
    def get_status(self) -> Dict[str, Any]:
        """Get daemon status."""
        return {
            "running": self.running,
            "cycles_run": self.cycles_run,
            "evolutions_applied": self.evolutions_applied,
            "last_cycle": self.last_cycle.isoformat(),
            "next_cycle": (self.last_cycle + self.CYCLE_INTERVAL).isoformat(),
            "engine_status": self.engine.get_evolution_status()
        }


# ============================================================================
# INTEGRATION WITH CONSCIOUSNESS LOOP
# ============================================================================

async def on_issue_detected(issue: str, context: Dict = None) -> Optional[ProposedEvolution]:
    """
    Called by the consciousness loop when an issue is detected.
    
    This is the integration point between detection and evolution.
    """
    engine = get_evolution_engine()
    return await engine.analyze_issue(issue, context)


async def get_evolution_recommendations() -> List[Dict[str, Any]]:
    """Get current evolution recommendations for the steward."""
    engine = get_evolution_engine()
    pending = engine.memory.get_pending_evolutions()
    
    return [
        {
            "id": e.id,
            "type": e.type.value,
            "description": e.description,
            "risk": e.risk_level.value,
            "trigger": e.trigger_issue[:100],
            "created": e.created_at
        }
        for e in pending
        if e.risk_level == RiskLevel.HIGH  # Only show high-risk for approval
    ]


# ============================================================================
# SINGLETON DAEMON
# ============================================================================

_daemon: Optional[ProactiveEvolutionDaemon] = None


def get_evolution_daemon() -> ProactiveEvolutionDaemon:
    """Get or create the evolution daemon."""
    global _daemon
    if _daemon is None:
        _daemon = ProactiveEvolutionDaemon()
    return _daemon


async def start_evolution_daemon():
    """Start the evolution daemon as a background task."""
    daemon = get_evolution_daemon()
    asyncio.create_task(daemon.start())
    return daemon








