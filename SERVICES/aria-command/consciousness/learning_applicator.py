"""
ARIA LEARNING APPLICATOR
=========================

Gap 5 Solution: This module actually APPLIES learned patterns.

The problem was:
- Evolution system detects patterns and stores them
- But those learnings were never injected back into behavior

This module:
1. Gets learned corrections before each query
2. Injects them into the system prompt
3. Records interaction outcomes
4. Builds a learning context that grows over time

Now Aria doesn't just STORE learnings - she USES them.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("aria.consciousness.learning")


class LearningApplicator:
    """
    Applies learned patterns to improve Aria's behavior.
    
    This bridges the gap between detection and application.
    """
    
    def __init__(self):
        self._realtime_learner = None
        self._initialized = False
        logger.info("Learning applicator initialized")
    
    def _ensure_learner(self):
        """Ensure the realtime learner is available."""
        if not self._initialized:
            try:
                from sovereign.evolution.realtime_learner import get_realtime_learner
                self._realtime_learner = get_realtime_learner()
                self._initialized = True
            except ImportError as e:
                logger.warning(f"Realtime learner not available: {e}")
    
    def get_learning_context(self, user_message: str) -> str:
        """
        Get learning context to inject into system prompt.
        
        This is where stored learnings become APPLIED learnings.
        
        Args:
            user_message: The current user message
        
        Returns:
            Formatted string to inject into system prompt
        """
        self._ensure_learner()
        
        if not self._realtime_learner:
            return ""
        
        try:
            from sovereign.evolution.realtime_learner import get_query_insights
            
            insights = get_query_insights(user_message)
            
            lines = []
            
            # If we have a correction for this type of query
            if insights.get("has_correction"):
                correction = insights["correction"]
                if correction and correction.get("confidence", 0) >= 0.5:
                    lines.append("\n## 📚 LEARNED CORRECTION")
                    lines.append(f"For queries like this, I previously learned:")
                    lines.append(f"→ **Better interpretation:** {correction['correct_interpretation']}")
                    lines.append(f"→ **Confidence:** {correction['confidence']:.0%}")
                    lines.append("*Apply this learning to avoid repeating the same mistake.*\n")
            
            # If we have a success pattern for this type of query
            if insights.get("has_success_pattern"):
                pattern = insights["success_pattern"]
                if pattern and pattern.get("reinforcement_count", 0) >= 2:
                    lines.append("\n## 🎯 PROVEN APPROACH")
                    lines.append(f"For queries like this, this approach worked well:")
                    lines.append(f"→ **Approach:** {pattern['approach']}")
                    lines.append(f"→ **Confirmed:** {pattern['reinforcement_count']} times")
                    lines.append("*Use this proven approach.*\n")
            
            if lines:
                return "\n".join(lines)
            
            return ""
            
        except Exception as e:
            logger.debug(f"Could not get learning context: {e}")
            return ""
    
    def record_interaction(
        self,
        user_id: str,
        user_message: str,
        aria_response: str,
        response_time_ms: float = 0,
        tools_used: List[str] = None,
        success: bool = True
    ) -> Dict[str, Any]:
        """
        Record an interaction for learning.
        
        This should be called after every response to enable learning.
        
        Returns:
            Dict with learning insights (what was learned)
        """
        self._ensure_learner()
        
        if not self._realtime_learner:
            return {"recorded": False, "reason": "learner not available"}
        
        try:
            from sovereign.evolution.realtime_learner import process_interaction
            
            insights = process_interaction(
                user_id=str(user_id),
                user_message=user_message,
                aria_response=aria_response,
                response_time_ms=response_time_ms,
                tools_used=tools_used or [],
                success=success
            )
            
            # Also update self-model if there was a correction
            if insights.get("correction_detected"):
                try:
                    from consciousness import get_self_model
                    model = get_self_model()
                    model.add_pattern(
                        f"Corrected: {insights['correction_applied'].get('original', '')[:30]}",
                        "weakness",
                        "User corrected this interpretation"
                    )
                except Exception:
                    pass
            
            # Update self-model on success
            if insights.get("success_reinforced"):
                try:
                    from consciousness import get_self_model
                    model = get_self_model()
                    model.record_interaction(success=True, response_time_ms=response_time_ms)
                except Exception:
                    pass
            
            return {
                "recorded": True,
                "insights": insights
            }
            
        except Exception as e:
            logger.warning(f"Could not record interaction: {e}")
            return {"recorded": False, "reason": str(e)}
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of all learnings."""
        self._ensure_learner()
        
        if not self._realtime_learner:
            return {"available": False}
        
        try:
            return {
                "available": True,
                **self._realtime_learner.get_learning_summary()
            }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def get_recent_corrections(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent corrections that were learned."""
        self._ensure_learner()
        
        if not self._realtime_learner:
            return []
        
        try:
            corrections = []
            for hash_key, correction in list(self._realtime_learner._correction_cache.items())[:limit]:
                corrections.append({
                    "query_pattern": correction.query_pattern[:100],
                    "correct_interpretation": correction.correct_interpretation[:100],
                    "confidence": correction.confidence,
                    "occurrence_count": correction.occurrence_count
                })
            return corrections
        except Exception:
            return []


# ============================================================================
# SINGLETON
# ============================================================================

_applicator: Optional[LearningApplicator] = None


def get_learning_applicator() -> LearningApplicator:
    """Get or create learning applicator."""
    global _applicator
    if _applicator is None:
        _applicator = LearningApplicator()
    return _applicator


def get_learning_context(user_message: str) -> str:
    """Get learning context for a message."""
    return get_learning_applicator().get_learning_context(user_message)


def record_learning(
    user_id: str,
    user_message: str,
    aria_response: str,
    response_time_ms: float = 0,
    tools_used: List[str] = None,
    success: bool = True
) -> Dict[str, Any]:
    """Record an interaction for learning."""
    return get_learning_applicator().record_interaction(
        user_id, user_message, aria_response,
        response_time_ms, tools_used, success
    )









