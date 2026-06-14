"""
ARIA MEMORY LEARNING
====================

Learning from outcomes system.

When actions happen and results come back, Aria learns:
- What worked
- What didn't
- What patterns emerge
- What preferences are discovered
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .store import (
    get_memory_store, Memory, MemoryStore,
    MemoryCategory, MemoryImportance
)

logger = logging.getLogger("aria.memory.learn")


class OutcomeType(str, Enum):
    """Types of outcomes."""
    POSITIVE = "positive"     # Worked as expected or better
    NEUTRAL = "neutral"       # Neither good nor bad
    NEGATIVE = "negative"     # Didn't work as expected
    PARTIAL = "partial"       # Partially worked
    UNEXPECTED = "unexpected" # Surprise outcome (could be good or bad)


@dataclass
class LearningEntry:
    """A learning entry."""
    action: str
    outcome: str
    outcome_type: OutcomeType
    insight: str
    context: Optional[Dict] = None
    related_vision_id: Optional[str] = None


class MemoryLearning:
    """
    Learning from outcomes.
    
    Records what worked, what didn't, and extracts insights.
    """
    
    def __init__(self):
        self.store = get_memory_store()
        logger.info("MemoryLearning initialized")
    
    def learn(
        self,
        action: str,
        outcome: str,
        outcome_type: OutcomeType = OutcomeType.NEUTRAL,
        insight: str = None,
        context: Dict = None,
        related_vision_id: str = None
    ) -> Memory:
        """
        Learn from an action-outcome pair.
        
        Args:
            action: What was done
            outcome: What happened
            outcome_type: How it turned out
            insight: What we learned (optional - will be generated if not provided)
            context: Additional context
            related_vision_id: If this relates to a vision
        """
        # Generate insight if not provided
        if not insight:
            insight = self._generate_insight(action, outcome, outcome_type)
        
        # Determine importance based on outcome type
        importance = {
            OutcomeType.POSITIVE: MemoryImportance.HIGH,
            OutcomeType.NEGATIVE: MemoryImportance.HIGH,
            OutcomeType.UNEXPECTED: MemoryImportance.HIGH,
            OutcomeType.PARTIAL: MemoryImportance.MEDIUM,
            OutcomeType.NEUTRAL: MemoryImportance.LOW
        }.get(outcome_type, MemoryImportance.MEDIUM)
        
        # Create the learning memory
        content = f"Action: {action}\nOutcome: {outcome}\nInsight: {insight}"
        
        memory = self.store.store(
            content=content,
            category=MemoryCategory.LEARNING,
            importance=importance,
            action=action,
            outcome=outcome,
            insight=insight,
            source="learning",
            tags=[outcome_type.value]
        )
        
        # Also check if this reveals a preference
        preference = self._detect_preference(action, outcome, outcome_type)
        if preference:
            self.store.store(
                content=preference,
                category=MemoryCategory.PREFERENCE,
                importance=MemoryImportance.MEDIUM,
                source="learned_preference"
            )
        
        logger.info(f"Learned: {insight[:50]}... [{outcome_type.value}]")
        return memory
    
    def learn_from_feedback(
        self,
        aria_response: str,
        user_feedback: str,
        was_helpful: bool
    ) -> Memory:
        """
        Learn from direct user feedback on a response.
        """
        outcome_type = OutcomeType.POSITIVE if was_helpful else OutcomeType.NEGATIVE
        
        insight = (
            f"Response style {'worked well' if was_helpful else 'could improve'}: "
            f"User said '{user_feedback[:100]}'"
        )
        
        return self.learn(
            action=f"Responded: {aria_response[:100]}...",
            outcome=user_feedback,
            outcome_type=outcome_type,
            insight=insight
        )
    
    def learn_preference(
        self,
        preference: str,
        context: str = None,
        importance: MemoryImportance = MemoryImportance.MEDIUM
    ) -> Memory:
        """
        Directly record a discovered preference.
        """
        content = preference
        if context:
            content = f"{preference} (Context: {context})"
        
        return self.store.store(
            content=content,
            category=MemoryCategory.PREFERENCE,
            importance=importance,
            source="explicit_preference"
        )
    
    def learn_decision(
        self,
        decision: str,
        reasoning: str = None,
        outcome: str = None
    ) -> Memory:
        """
        Record a decision that was made.
        """
        content = f"Decision: {decision}"
        if reasoning:
            content += f"\nReasoning: {reasoning}"
        if outcome:
            content += f"\nOutcome: {outcome}"
        
        return self.store.store(
            content=content,
            category=MemoryCategory.DECISION,
            importance=MemoryImportance.HIGH,
            source="decision_record"
        )
    
    def learn_pattern(
        self,
        pattern: str,
        evidence: List[str] = None,
        confidence: float = 0.5
    ) -> Memory:
        """
        Record a detected pattern.
        """
        content = f"Pattern: {pattern}"
        if evidence:
            content += f"\nEvidence: {'; '.join(evidence[:5])}"
        content += f"\nConfidence: {confidence:.0%}"
        
        importance = (
            MemoryImportance.HIGH if confidence > 0.7
            else MemoryImportance.MEDIUM if confidence > 0.4
            else MemoryImportance.LOW
        )
        
        return self.store.store(
            content=content,
            category=MemoryCategory.PATTERN,
            importance=importance,
            source="pattern_detection",
            tags=[f"confidence_{int(confidence*100)}"]
        )
    
    def get_learnings(
        self,
        outcome_type: OutcomeType = None,
        limit: int = 20
    ) -> List[Memory]:
        """Get learning memories."""
        learnings = self.store.get_by_category(MemoryCategory.LEARNING, limit=limit)
        
        if outcome_type:
            learnings = [
                m for m in learnings 
                if outcome_type.value in (m.tags or [])
            ]
        
        return learnings
    
    def get_preferences(self, limit: int = 20) -> List[Memory]:
        """Get discovered preferences."""
        return self.store.get_by_category(MemoryCategory.PREFERENCE, limit=limit)
    
    def get_patterns(self, limit: int = 20) -> List[Memory]:
        """Get detected patterns."""
        return self.store.get_by_category(MemoryCategory.PATTERN, limit=limit)
    
    def get_learning_summary(self) -> Dict:
        """Get a summary of what has been learned."""
        learnings = self.get_learnings(limit=100)
        preferences = self.get_preferences(limit=50)
        patterns = self.get_patterns(limit=50)
        
        # Count by outcome type
        outcome_counts = {}
        for learning in learnings:
            for tag in (learning.tags or []):
                if tag in [t.value for t in OutcomeType]:
                    outcome_counts[tag] = outcome_counts.get(tag, 0) + 1
        
        # Extract recent insights
        recent_insights = [
            m.insight for m in learnings[:10]
            if m.insight
        ]
        
        return {
            "total_learnings": len(learnings),
            "total_preferences": len(preferences),
            "total_patterns": len(patterns),
            "outcome_distribution": outcome_counts,
            "recent_insights": recent_insights
        }
    
    # ==================== PRIVATE METHODS ====================
    
    def _generate_insight(
        self,
        action: str,
        outcome: str,
        outcome_type: OutcomeType
    ) -> str:
        """Generate an insight from action-outcome pair."""
        if outcome_type == OutcomeType.POSITIVE:
            return f"'{action[:50]}' worked well: {outcome[:100]}"
        elif outcome_type == OutcomeType.NEGATIVE:
            return f"'{action[:50]}' didn't work: {outcome[:100]}. Consider alternative approach."
        elif outcome_type == OutcomeType.PARTIAL:
            return f"'{action[:50]}' partially worked: {outcome[:100]}. Refinement needed."
        elif outcome_type == OutcomeType.UNEXPECTED:
            return f"Unexpected result from '{action[:50]}': {outcome[:100]}. Worth noting."
        else:
            return f"Neutral outcome from '{action[:50]}': {outcome[:100]}"
    
    def _detect_preference(
        self,
        action: str,
        outcome: str,
        outcome_type: OutcomeType
    ) -> Optional[str]:
        """Detect if this reveals a preference."""
        action_lower = action.lower()
        outcome_lower = outcome.lower()
        
        # Only detect preferences from positive or strong negative outcomes
        if outcome_type not in [OutcomeType.POSITIVE, OutcomeType.NEGATIVE]:
            return None
        
        # Time-related preferences
        time_words = ['morning', 'evening', 'night', 'afternoon', 'early', 'late']
        for word in time_words:
            if word in action_lower or word in outcome_lower:
                verb = "prefers" if outcome_type == OutcomeType.POSITIVE else "dislikes"
                return f"{verb.capitalize()} {word} for this type of activity"
        
        # Communication preferences
        comm_words = ['voice', 'text', 'brief', 'detailed', 'quick', 'thorough']
        for word in comm_words:
            if word in action_lower:
                if outcome_type == OutcomeType.POSITIVE:
                    return f"Prefers {word} communication style"
        
        return None


# Singleton
_learning: Optional[MemoryLearning] = None


def get_memory_learning() -> MemoryLearning:
    """Get or create memory learning instance."""
    global _learning
    if _learning is None:
        _learning = MemoryLearning()
    return _learning


