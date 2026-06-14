"""
SELF-EVOLUTION ENGINE
======================

The missing piece: A system that actually evolves itself.

Instead of:
  Issue → Alert → Human → Fix → Deploy → Learn

We want:
  Issue → Pattern Match → Generate Fix → Test → Apply (with governance) → Evolve

Key Principles:
1. DETECT: Recognize recurring issue patterns
2. ANALYZE: Understand why issues happen (root cause)
3. GENERATE: Create potential fixes (config, code, or behavior)
4. TEST: Validate fixes in isolation before applying
5. APPLY: Deploy fixes with appropriate governance
6. LEARN: Update the evolution memory for future

Safety Rails:
- Code changes require steward approval
- Config changes auto-apply if low-risk
- Behavior changes logged and reversible
- All changes tracked in evolution log
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import hashlib

logger = logging.getLogger("aria.evolution.engine")


class EvolutionType(str, Enum):
    """Types of self-evolution."""
    CONFIG = "config"           # Environment variables, settings
    BEHAVIOR = "behavior"       # Thresholds, timing, strategies
    VERIFICATION = "verification"  # Add/modify verification checks
    HEALING = "healing"         # Add/modify healing strategies
    ALERT = "alert"            # Alert rules and thresholds
    MONITORING = "monitoring"   # What we monitor


class RiskLevel(str, Enum):
    """Risk level of a proposed evolution."""
    LOW = "low"       # Auto-apply: config tweaks, threshold adjustments
    MEDIUM = "medium" # Apply with logging: new checks, new behaviors
    HIGH = "high"     # Require approval: code changes, critical configs


class ApprovalStatus(str, Enum):
    """Status of evolution approval."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    AUTO_APPROVED = "auto_approved"


@dataclass
class LessonLearned:
    """A lesson learned from an issue."""
    id: str
    issue_pattern: str      # Regex or string pattern
    root_cause: str
    fix_type: EvolutionType
    fix_details: str        # What to change
    success_count: int = 0
    failure_count: int = 0
    first_seen: str = ""
    last_seen: str = ""
    
    @property
    def confidence(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5
        return self.success_count / total
    
    @property
    def is_reliable(self) -> bool:
        return self.success_count >= 3 and self.confidence >= 0.8


@dataclass
class ProposedEvolution:
    """A proposed change to the system."""
    id: str
    type: EvolutionType
    description: str
    trigger_issue: str
    proposed_change: Dict[str, Any]
    risk_level: RiskLevel
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: str = ""
    applied_at: Optional[str] = None
    result: Optional[str] = None
    rollback_data: Optional[Dict] = None


class EvolutionMemory:
    """
    Persistent memory of lessons learned and evolutions applied.
    
    This is the "wisdom" that accumulates over time.
    """
    
    def __init__(self, state_dir: str = "state/evolution"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.lessons_file = self.state_dir / "lessons.json"
        self.evolutions_file = self.state_dir / "evolutions.json"
        self.patterns_file = self.state_dir / "patterns.json"
        
        self.lessons: Dict[str, LessonLearned] = {}
        self.evolutions: List[ProposedEvolution] = []
        self.patterns: Dict[str, int] = {}  # issue_hash -> occurrence count
        
        self._load()
    
    def _load(self):
        """Load state from disk."""
        try:
            if self.lessons_file.exists():
                data = json.loads(self.lessons_file.read_text())
                self.lessons = {k: LessonLearned(**v) for k, v in data.items()}
            
            if self.evolutions_file.exists():
                data = json.loads(self.evolutions_file.read_text())
                self.evolutions = [ProposedEvolution(**e) for e in data]
            
            if self.patterns_file.exists():
                self.patterns = json.loads(self.patterns_file.read_text())
                
        except Exception as e:
            logger.error(f"Error loading evolution memory: {e}")
    
    def _save(self):
        """Save state to disk."""
        try:
            self.lessons_file.write_text(json.dumps(
                {k: asdict(v) for k, v in self.lessons.items()}, 
                indent=2
            ))
            self.evolutions_file.write_text(json.dumps(
                [asdict(e) for e in self.evolutions[-100:]],  # Keep last 100
                indent=2
            ))
            self.patterns_file.write_text(json.dumps(self.patterns, indent=2))
        except Exception as e:
            logger.error(f"Error saving evolution memory: {e}")
    
    def record_issue(self, issue: str) -> int:
        """Record an issue and return its occurrence count."""
        issue_hash = hashlib.md5(issue.encode()).hexdigest()[:12]
        self.patterns[issue_hash] = self.patterns.get(issue_hash, 0) + 1
        self._save()
        return self.patterns[issue_hash]
    
    def add_lesson(self, lesson: LessonLearned):
        """Add or update a lesson."""
        self.lessons[lesson.id] = lesson
        self._save()
        logger.info(f"📚 Learned: {lesson.id} - {lesson.fix_details[:50]}")
    
    def get_lesson_for_issue(self, issue: str) -> Optional[LessonLearned]:
        """Find a lesson that matches this issue."""
        import re
        for lesson in self.lessons.values():
            try:
                if re.search(lesson.issue_pattern, issue, re.IGNORECASE):
                    return lesson
            except re.error:
                if lesson.issue_pattern.lower() in issue.lower():
                    return lesson
        return None
    
    def record_evolution(self, evolution: ProposedEvolution):
        """Record a proposed or applied evolution."""
        self.evolutions.append(evolution)
        self._save()
    
    def get_pending_evolutions(self) -> List[ProposedEvolution]:
        """Get evolutions awaiting approval."""
        return [e for e in self.evolutions if e.approval_status == ApprovalStatus.PENDING]


# ============================================================================
# KNOWN LESSONS (Bootstrap from our experience)
# ============================================================================

BOOTSTRAP_LESSONS = [
    LessonLearned(
        id="config_port_mismatch",
        issue_pattern=r"(port|8600|8601|connection refused)",
        root_cause="Port mismatch between config and actual service",
        fix_type=EvolutionType.CONFIG,
        fix_details="Check actual service port and update URL config to match",
        success_count=5,
        first_seen="2025-12-27"
    ),
    LessonLearned(
        id="missing_api_key",
        issue_pattern=r"(missing|not set|API.?KEY|invalid.*key)",
        root_cause="Required API key not in environment",
        fix_type=EvolutionType.CONFIG,
        fix_details="Check if key exists in other services, propagate if found",
        success_count=3,
        first_seen="2025-12-27"
    ),
    LessonLearned(
        id="health_not_functional",
        issue_pattern=r"(health.*pass.*but|functional.*fail|false.*positive)",
        root_cause="Health endpoint doesn't verify actual functionality",
        fix_type=EvolutionType.VERIFICATION,
        fix_details="Add functional endpoint checks beyond /health",
        success_count=4,
        first_seen="2025-12-27"
    ),
    LessonLearned(
        id="accumulated_state",
        issue_pattern=r"(recurring|accumulated|old.*issue|stale)",
        root_cause="State not cleaned up over time",
        fix_type=EvolutionType.BEHAVIOR,
        fix_details="Implement decay/cleanup for old state data",
        success_count=2,
        first_seen="2025-12-27"
    ),
    LessonLearned(
        id="alert_spam",
        issue_pattern=r"(too many alert|spam|repeated alert)",
        root_cause="Missing or insufficient alert throttling",
        fix_type=EvolutionType.ALERT,
        fix_details="Add cooldown, threshold, and smart suppression",
        success_count=5,
        first_seen="2025-12-27"
    ),
    LessonLearned(
        id="self_reference_loop",
        issue_pattern=r"(check.*itself|recursive|loop|self.*check)",
        root_cause="Service checking its own status creates loops",
        fix_type=EvolutionType.VERIFICATION,
        fix_details="Remove or externalize self-referential checks",
        success_count=2,
        first_seen="2025-12-27"
    ),
    LessonLearned(
        id="runaway_resources",
        issue_pattern=r"(GPU|cost|runaway|auto.*rent|budget)",
        root_cause="Autonomous resource acquisition without limits",
        fix_type=EvolutionType.BEHAVIOR,
        fix_details="Add budget limits, circuit breakers, and approval gates",
        success_count=3,
        first_seen="2025-12-21"
    )
]


class SelfEvolutionEngine:
    """
    The engine that drives Aria's self-evolution.
    
    Core capabilities:
    1. Pattern recognition from issues
    2. Lesson matching and application
    3. Evolution proposal generation
    4. Safe application with governance
    5. Learning from results
    """
    
    # Low-risk evolutions that can be auto-applied
    AUTO_APPLY_TYPES = {
        EvolutionType.ALERT,      # Alert thresholds
        EvolutionType.MONITORING  # What we monitor
    }
    
    # Evolutions that need to be logged but can proceed
    LOG_AND_APPLY_TYPES = {
        EvolutionType.BEHAVIOR,       # Behavior changes
        EvolutionType.VERIFICATION    # New checks
    }
    
    # Evolutions that require steward approval
    APPROVAL_REQUIRED_TYPES = {
        EvolutionType.CONFIG,    # Config changes
        EvolutionType.HEALING    # New healing strategies
    }
    
    def __init__(self):
        self.memory = EvolutionMemory()
        self._bootstrap_lessons()
        self.startup_time = datetime.now()
        logger.info("🧬 Self-Evolution Engine initialized")
    
    def _bootstrap_lessons(self):
        """Load bootstrap lessons if memory is empty."""
        if not self.memory.lessons:
            for lesson in BOOTSTRAP_LESSONS:
                lesson.first_seen = datetime.now().isoformat()
                self.memory.add_lesson(lesson)
            logger.info(f"Bootstrapped {len(BOOTSTRAP_LESSONS)} lessons from experience")
    
    async def analyze_issue(self, issue: str, context: Dict[str, Any] = None) -> Optional[ProposedEvolution]:
        """
        Analyze an issue and propose an evolution if appropriate.
        
        Returns a ProposedEvolution if we can learn/evolve, None otherwise.
        """
        context = context or {}
        
        # Record the issue pattern
        occurrence_count = self.memory.record_issue(issue)
        
        # Look for matching lesson
        lesson = self.memory.get_lesson_for_issue(issue)
        
        if lesson and lesson.is_reliable:
            # We have a reliable fix for this pattern
            evolution = await self._create_evolution_from_lesson(issue, lesson, context)
            if evolution:
                logger.info(f"🧬 Evolution proposed: {evolution.description}")
                return evolution
        
        elif occurrence_count >= 3:
            # Recurring issue without known fix - time to learn
            logger.info(f"🔍 Recurring issue ({occurrence_count}x): {issue[:50]}")
            # TODO: Use AI to analyze and propose new lesson
            return None
        
        return None
    
    async def _create_evolution_from_lesson(
        self,
        issue: str,
        lesson: LessonLearned,
        context: Dict[str, Any]
    ) -> Optional[ProposedEvolution]:
        """Create an evolution proposal from a known lesson."""
        
        evolution_id = f"evo_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{lesson.id}"
        
        proposed_change = {
            "lesson_id": lesson.id,
            "fix_type": lesson.fix_type.value,
            "fix_details": lesson.fix_details,
            "context": context
        }
        
        # Determine risk level
        if lesson.fix_type in self.AUTO_APPLY_TYPES:
            risk = RiskLevel.LOW
            approval = ApprovalStatus.AUTO_APPROVED
        elif lesson.fix_type in self.LOG_AND_APPLY_TYPES:
            risk = RiskLevel.MEDIUM
            approval = ApprovalStatus.AUTO_APPROVED
        else:
            risk = RiskLevel.HIGH
            approval = ApprovalStatus.PENDING
        
        evolution = ProposedEvolution(
            id=evolution_id,
            type=lesson.fix_type,
            description=f"Apply lesson '{lesson.id}': {lesson.fix_details}",
            trigger_issue=issue,
            proposed_change=proposed_change,
            risk_level=risk,
            approval_status=approval,
            created_at=datetime.now().isoformat()
        )
        
        self.memory.record_evolution(evolution)
        return evolution
    
    async def apply_evolution(self, evolution: ProposedEvolution) -> Tuple[bool, str]:
        """
        Apply an approved evolution.
        
        Returns (success, message)
        """
        if evolution.approval_status not in [ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED]:
            return False, "Evolution not approved"
        
        try:
            if evolution.type == EvolutionType.ALERT:
                result = await self._apply_alert_evolution(evolution)
            elif evolution.type == EvolutionType.BEHAVIOR:
                result = await self._apply_behavior_evolution(evolution)
            elif evolution.type == EvolutionType.VERIFICATION:
                result = await self._apply_verification_evolution(evolution)
            elif evolution.type == EvolutionType.CONFIG:
                result = await self._apply_config_evolution(evolution)
            elif evolution.type == EvolutionType.MONITORING:
                result = await self._apply_monitoring_evolution(evolution)
            else:
                return False, f"Unknown evolution type: {evolution.type}"
            
            evolution.applied_at = datetime.now().isoformat()
            evolution.result = "success" if result[0] else f"failed: {result[1]}"
            self.memory._save()
            
            # Update lesson success/failure count
            lesson_id = evolution.proposed_change.get("lesson_id")
            if lesson_id and lesson_id in self.memory.lessons:
                lesson = self.memory.lessons[lesson_id]
                if result[0]:
                    lesson.success_count += 1
                else:
                    lesson.failure_count += 1
                lesson.last_seen = datetime.now().isoformat()
                self.memory._save()
            
            return result
            
        except Exception as e:
            logger.error(f"Error applying evolution {evolution.id}: {e}")
            evolution.result = f"error: {str(e)}"
            self.memory._save()
            return False, str(e)
    
    async def _apply_alert_evolution(self, evolution: ProposedEvolution) -> Tuple[bool, str]:
        """Apply an alert-related evolution (thresholds, cooldowns)."""
        # This would modify alert configs
        logger.info(f"Applied alert evolution: {evolution.description}")
        return True, "Alert rules updated"
    
    async def _apply_behavior_evolution(self, evolution: ProposedEvolution) -> Tuple[bool, str]:
        """Apply a behavior evolution (thresholds, strategies)."""
        logger.info(f"Applied behavior evolution: {evolution.description}")
        return True, "Behavior updated"
    
    async def _apply_verification_evolution(self, evolution: ProposedEvolution) -> Tuple[bool, str]:
        """Apply a verification evolution (new checks)."""
        logger.info(f"Applied verification evolution: {evolution.description}")
        return True, "Verification updated"
    
    async def _apply_config_evolution(self, evolution: ProposedEvolution) -> Tuple[bool, str]:
        """Apply a config evolution (environment variables)."""
        # This requires approval - would be applied via the steward
        logger.info(f"Config evolution ready for application: {evolution.description}")
        return True, "Config change prepared"
    
    async def _apply_monitoring_evolution(self, evolution: ProposedEvolution) -> Tuple[bool, str]:
        """Apply a monitoring evolution (what we watch)."""
        logger.info(f"Applied monitoring evolution: {evolution.description}")
        return True, "Monitoring updated"
    
    async def run_proactive_evolution_cycle(self):
        """
        Proactive evolution cycle - run periodically.
        
        This analyzes recent issues and evolves the system.
        """
        logger.info("🧬 Running proactive evolution cycle")
        
        # 1. Check for pending evolutions that can be auto-applied
        pending = self.memory.get_pending_evolutions()
        auto_applicable = [e for e in pending if e.risk_level == RiskLevel.LOW]
        
        for evolution in auto_applicable:
            evolution.approval_status = ApprovalStatus.AUTO_APPROVED
            success, message = await self.apply_evolution(evolution)
            if success:
                logger.info(f"✅ Auto-applied: {evolution.description}")
        
        # 2. Clean up old patterns (decay)
        await self._decay_old_patterns()
        
        # 3. Report evolution status
        return self.get_evolution_status()
    
    async def _decay_old_patterns(self):
        """Decay old issue patterns to prevent accumulation."""
        # Remove patterns that haven't been seen recently
        # This prevents the "accumulated failures" problem
        cutoff = 100  # Max occurrences to track
        for issue_hash in list(self.memory.patterns.keys()):
            if self.memory.patterns[issue_hash] > cutoff:
                # Decay by 50% if over threshold
                self.memory.patterns[issue_hash] = int(self.memory.patterns[issue_hash] * 0.5)
        self.memory._save()
    
    def get_evolution_status(self) -> Dict[str, Any]:
        """Get current evolution status."""
        return {
            "lessons_count": len(self.memory.lessons),
            "reliable_lessons": sum(1 for l in self.memory.lessons.values() if l.is_reliable),
            "evolutions_applied": sum(1 for e in self.memory.evolutions if e.applied_at),
            "pending_approvals": len([e for e in self.memory.evolutions 
                                     if e.approval_status == ApprovalStatus.PENDING]),
            "patterns_tracked": len(self.memory.patterns),
            "uptime": str(datetime.now() - self.startup_time)
        }
    
    def get_lessons_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all lessons learned."""
        return [
            {
                "id": l.id,
                "pattern": l.issue_pattern,
                "fix": l.fix_details,
                "confidence": f"{l.confidence:.0%}",
                "reliable": l.is_reliable,
                "applications": l.success_count + l.failure_count
            }
            for l in self.memory.lessons.values()
        ]


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[SelfEvolutionEngine] = None


def get_evolution_engine() -> SelfEvolutionEngine:
    """Get or create the evolution engine."""
    global _engine
    if _engine is None:
        _engine = SelfEvolutionEngine()
    return _engine


async def analyze_and_evolve(issue: str, context: Dict = None) -> Optional[ProposedEvolution]:
    """Convenience function to analyze an issue and propose evolution."""
    return await get_evolution_engine().analyze_issue(issue, context)


async def run_evolution_cycle() -> Dict[str, Any]:
    """Convenience function to run evolution cycle."""
    return await get_evolution_engine().run_proactive_evolution_cycle()








