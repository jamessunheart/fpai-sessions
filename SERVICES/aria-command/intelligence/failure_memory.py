"""
FAILURE MEMORY
===============

Remember failures and what fixed them.

The key insight: If we've seen a failure before and know what fixed it,
we should apply that fix immediately instead of guessing.

Features:
1. Record all failures with symptoms, causes, and fixes
2. Find similar failures using keyword matching
3. Track fix success rates
4. Learn which fixes work best for which symptoms
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

from .intelligence_db import (
    IntelligenceDB, get_intelligence_db,
    FailureRecord, FixRecord
)

logger = logging.getLogger("aria.intelligence.memory")


@dataclass
class HistoricalFailure:
    """A failure from history with context."""
    id: int
    timestamp: str
    service: str
    symptom: str
    root_cause: str
    fix_applied: str
    fix_worked: bool
    time_to_fix_seconds: int
    similarity_score: float = 0.0  # How similar to current symptom
    
    @classmethod
    def from_record(cls, record: FailureRecord, similarity: float = 0.0) -> "HistoricalFailure":
        return cls(
            id=record.id,
            timestamp=record.timestamp,
            service=record.service,
            symptom=record.symptom,
            root_cause=record.root_cause,
            fix_applied=record.fix_applied,
            fix_worked=record.fix_worked,
            time_to_fix_seconds=record.time_to_fix_seconds,
            similarity_score=similarity
        )


@dataclass
class Fix:
    """A fix pattern with success tracking."""
    pattern: str
    fix_type: str
    fix_details: str
    success_count: int
    failure_count: int
    avg_time_seconds: float
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def is_reliable(self) -> bool:
        """A fix is reliable if it has >80% success rate with 3+ attempts."""
        return self.success_rate > 0.8 and (self.success_count + self.failure_count) >= 3
    
    @classmethod
    def from_record(cls, record: FixRecord) -> "Fix":
        return cls(
            pattern=record.pattern,
            fix_type=record.fix_type,
            fix_details=record.fix_details,
            success_count=record.success_count,
            failure_count=record.failure_count,
            avg_time_seconds=record.avg_time_seconds
        )


class FailureMemory:
    """
    Long-term memory for failures and fixes.
    
    Enables learning from past failures to fix new ones faster.
    """
    
    def __init__(self, db: IntelligenceDB = None):
        self.db = db or get_intelligence_db()
        logger.info("FailureMemory initialized")
    
    def record_failure(
        self,
        service: str,
        symptom: str,
        root_cause: str,
        root_cause_confidence: float,
        fix_applied: str,
        fix_worked: bool,
        time_to_fix: int = 0,
        category: str = "unknown",
        fix_type: str = "unknown"
    ) -> int:
        """
        Record a failure and its resolution.
        
        Returns the failure ID.
        """
        # Find if this is similar to a known failure
        similar = self.find_similar_failures(symptom, limit=1)
        similar_id = similar[0].id if similar else None
        
        # Create failure record
        record = FailureRecord(
            timestamp=datetime.now().isoformat(),
            service=service,
            symptom=symptom,
            root_cause=root_cause,
            root_cause_confidence=root_cause_confidence,
            fix_applied=fix_applied,
            fix_worked=fix_worked,
            time_to_fix_seconds=time_to_fix,
            similar_failure_id=similar_id,
            metadata={"category": category, "fix_type": fix_type}
        )
        
        failure_id = self.db.record_failure(record)
        
        # Update fix pattern
        if fix_applied:
            self._update_fix_pattern(
                pattern=f"{service}:{root_cause}",
                fix_type=fix_type,
                fix_details=fix_applied,
                success=fix_worked,
                time_seconds=time_to_fix
            )
        
        logger.info(f"Recorded failure #{failure_id}: {service} - {symptom[:50]}")
        return failure_id
    
    def find_similar_failures(
        self,
        symptom: str,
        service: str = None,
        limit: int = 5
    ) -> List[HistoricalFailure]:
        """
        Find similar failures from history.
        
        Uses keyword matching to find relevant past failures.
        """
        all_failures = self.db.find_similar_failures(symptom, limit=limit * 2)
        
        # Filter by service if specified
        if service:
            all_failures = [f for f in all_failures if f.service == service]
        
        # Calculate similarity scores
        symptom_words = set(symptom.lower().split())
        
        scored = []
        for failure in all_failures:
            failure_words = set(failure.symptom.lower().split())
            
            # Jaccard similarity
            intersection = len(symptom_words & failure_words)
            union = len(symptom_words | failure_words)
            similarity = intersection / union if union > 0 else 0
            
            scored.append(HistoricalFailure.from_record(failure, similarity))
        
        # Sort by similarity
        scored.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return scored[:limit]
    
    def get_best_fix(self, pattern: str) -> Optional[Fix]:
        """
        Get the best fix for a failure pattern.
        
        Returns the fix with the highest success rate.
        """
        fix_record = self.db.get_best_fix(pattern)
        
        if fix_record:
            fix = Fix.from_record(fix_record)
            if fix.is_reliable:
                logger.info(f"Found reliable fix for {pattern}: {fix.fix_details[:50]}")
                return fix
            else:
                logger.debug(f"Found fix for {pattern} but not reliable enough: {fix.success_rate:.0%}")
        
        return None
    
    def get_best_fix_for_symptom(self, service: str, symptom: str) -> Optional[Fix]:
        """
        Get the best fix based on symptom similarity.
        
        Looks at similar failures and returns the most successful fix.
        """
        similar = self.find_similar_failures(symptom, service=service, limit=10)
        
        # Count fix success rates
        fix_stats: Dict[str, Dict[str, int]] = {}
        
        for failure in similar:
            if failure.fix_applied and failure.fix_worked:
                fix = failure.fix_applied
                if fix not in fix_stats:
                    fix_stats[fix] = {"success": 0, "failure": 0, "details": failure.root_cause}
                fix_stats[fix]["success"] += 1
            elif failure.fix_applied:
                fix = failure.fix_applied
                if fix not in fix_stats:
                    fix_stats[fix] = {"success": 0, "failure": 0, "details": failure.root_cause}
                fix_stats[fix]["failure"] += 1
        
        # Find best fix
        best_fix = None
        best_rate = 0.0
        
        for fix, stats in fix_stats.items():
            total = stats["success"] + stats["failure"]
            rate = stats["success"] / total if total > 0 else 0
            
            if rate > best_rate and rate > 0.5:  # At least 50% success
                best_rate = rate
                best_fix = Fix(
                    pattern=f"{service}:symptom_match",
                    fix_type="learned",
                    fix_details=fix,
                    success_count=stats["success"],
                    failure_count=stats["failure"],
                    avg_time_seconds=0
                )
        
        return best_fix
    
    def _update_fix_pattern(
        self,
        pattern: str,
        fix_type: str,
        fix_details: str,
        success: bool,
        time_seconds: int
    ):
        """Update or create a fix pattern record."""
        fix_record = FixRecord(
            pattern=pattern,
            fix_type=fix_type,
            fix_details=fix_details,
            success_count=1 if success else 0,
            failure_count=0 if success else 1,
            avg_time_seconds=float(time_seconds)
        )
        
        self.db.record_fix(fix_record)
    
    def get_failure_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get failure statistics."""
        failures = self.db.get_recent_failures(days=days)
        
        by_service: Dict[str, int] = {}
        by_category: Dict[str, int] = {}
        fixed_count = 0
        total_fix_time = 0
        
        for failure in failures:
            # By service
            by_service[failure.service] = by_service.get(failure.service, 0) + 1
            
            # By category
            category = failure.metadata.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1
            
            # Fixed count
            if failure.fix_worked:
                fixed_count += 1
                total_fix_time += failure.time_to_fix_seconds
        
        return {
            "period_days": days,
            "total_failures": len(failures),
            "fixed_count": fixed_count,
            "fix_rate": fixed_count / len(failures) if failures else 0,
            "avg_fix_time_seconds": total_fix_time / fixed_count if fixed_count else 0,
            "by_service": by_service,
            "by_category": by_category,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_learning_effectiveness(self) -> Dict[str, Any]:
        """
        Measure how well we're learning from failures.
        
        Key metrics:
        - Repeat failure rate (should decrease over time)
        - Time to fix trend (should decrease)
        - Fix success rate (should increase)
        """
        stats = self.db.get_intelligence_stats()
        fix_success_rate = self.db.get_fix_success_rate()
        
        # Get recent failures to check for repeats
        recent = self.db.get_recent_failures(days=7)
        older = self.db.get_recent_failures(days=30)
        
        # Count unique symptom patterns
        recent_patterns = set(f"{f.service}:{f.symptom[:30]}" for f in recent)
        older_patterns = set(f"{f.service}:{f.symptom[:30]}" for f in older)
        
        # Repeat rate = patterns that appear in both periods
        repeats = recent_patterns & older_patterns
        repeat_rate = len(repeats) / len(recent_patterns) if recent_patterns else 0
        
        return {
            "fix_success_rate": fix_success_rate,
            "repeat_failure_rate": repeat_rate,
            "known_patterns": stats["fixes"]["patterns_known"],
            "total_fix_applications": stats["fixes"]["total_applications"],
            "learning_score": (fix_success_rate * 0.5 + (1 - repeat_rate) * 0.5),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_memory: Optional[FailureMemory] = None


def get_failure_memory() -> FailureMemory:
    """Get or create the failure memory instance."""
    global _memory
    if _memory is None:
        _memory = FailureMemory()
    return _memory


def record_failure(
    service: str,
    symptom: str,
    root_cause: str,
    fix_applied: str,
    fix_worked: bool,
    **kwargs
) -> int:
    """Convenience function to record a failure."""
    return get_failure_memory().record_failure(
        service=service,
        symptom=symptom,
        root_cause=root_cause,
        root_cause_confidence=kwargs.get("root_cause_confidence", 0.0),
        fix_applied=fix_applied,
        fix_worked=fix_worked,
        time_to_fix=kwargs.get("time_to_fix", 0),
        category=kwargs.get("category", "unknown"),
        fix_type=kwargs.get("fix_type", "unknown")
    )









