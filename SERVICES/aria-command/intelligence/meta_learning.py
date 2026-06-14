"""
META-LEARNING
==============

Learn to learn better.

This module tracks how well the intelligence system is learning and
makes adjustments to improve over time.

Key metrics:
1. Fix success rate - Are our fixes working?
2. Diagnosis speed - Are we getting faster at finding root causes?
3. Repeat failure rate - Are we preventing the same failures?
4. Prediction accuracy - Are our predictions useful?
5. Novel failure rate - Are we seeing new types of problems?

The goal: The system should get smarter over time, not just stay the same.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .intelligence_db import IntelligenceDB, get_intelligence_db
from .failure_memory import FailureMemory, get_failure_memory
from .pattern_engine import PatternEngine, get_pattern_engine

logger = logging.getLogger("aria.intelligence.metalearning")


@dataclass
class LearningMetrics:
    """Metrics for learning effectiveness."""
    fix_success_rate: float = 0.0
    diagnosis_speed_trend: float = 0.0  # Positive = getting faster
    repeat_failure_rate: float = 0.0
    prediction_accuracy: float = 0.0
    novelty_rate: float = 0.0
    patterns_discovered: int = 0
    overall_intelligence_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "fix_success_rate": self.fix_success_rate,
            "diagnosis_speed_trend": self.diagnosis_speed_trend,
            "repeat_failure_rate": self.repeat_failure_rate,
            "prediction_accuracy": self.prediction_accuracy,
            "novelty_rate": self.novelty_rate,
            "patterns_discovered": self.patterns_discovered,
            "overall_intelligence_score": self.overall_intelligence_score,
            "timestamp": self.timestamp
        }


@dataclass
class LearningRecommendation:
    """A recommendation to improve learning."""
    area: str
    issue: str
    recommendation: str
    priority: str  # high, medium, low
    expected_improvement: str


class MetaLearner:
    """
    Meta-learning: Learning to learn better.
    
    Tracks learning effectiveness and makes recommendations
    for improving the intelligence system.
    """
    
    def __init__(self):
        self.db = get_intelligence_db()
        self.memory = get_failure_memory()
        self.patterns = get_pattern_engine()
        self.metrics_history: List[LearningMetrics] = []
        logger.info("MetaLearner initialized")
    
    def evaluate(self) -> LearningMetrics:
        """
        Evaluate current learning effectiveness.
        
        Returns comprehensive metrics on how well the system is learning.
        """
        metrics = LearningMetrics()
        
        # 1. Fix success rate
        metrics.fix_success_rate = self._calculate_fix_success_rate()
        
        # 2. Diagnosis speed trend
        metrics.diagnosis_speed_trend = self._calculate_diagnosis_speed_trend()
        
        # 3. Repeat failure rate
        metrics.repeat_failure_rate = self._calculate_repeat_rate()
        
        # 4. Prediction accuracy
        metrics.prediction_accuracy = self._calculate_prediction_accuracy()
        
        # 5. Novelty rate
        metrics.novelty_rate = self._calculate_novelty_rate()
        
        # 6. Patterns discovered
        metrics.patterns_discovered = len(self.patterns.patterns)
        
        # 7. Overall intelligence score
        metrics.overall_intelligence_score = self._calculate_intelligence_score(metrics)
        
        # Record metrics
        self.db.record_metric("fix_success_rate", metrics.fix_success_rate)
        self.db.record_metric("repeat_failure_rate", metrics.repeat_failure_rate)
        self.db.record_metric("intelligence_score", metrics.overall_intelligence_score)
        
        self.metrics_history.append(metrics)
        
        logger.info(f"Learning evaluation: Intelligence score = {metrics.overall_intelligence_score:.1f}/10")
        
        return metrics
    
    def _calculate_fix_success_rate(self) -> float:
        """Calculate rate of successful fixes."""
        return self.db.get_fix_success_rate()
    
    def _calculate_diagnosis_speed_trend(self) -> float:
        """
        Calculate if we're getting faster at diagnosis.
        
        Returns positive value if improving, negative if degrading.
        """
        # Get fix times from recent vs older failures
        recent = self.db.get_recent_failures(days=7)
        older = self.db.get_recent_failures(days=30)
        
        recent_times = [f.time_to_fix_seconds for f in recent if f.time_to_fix_seconds > 0]
        older_times = [f.time_to_fix_seconds for f in older if f.time_to_fix_seconds > 0]
        
        if not recent_times or not older_times:
            return 0.0
        
        recent_avg = sum(recent_times) / len(recent_times)
        older_avg = sum(older_times) / len(older_times)
        
        if older_avg == 0:
            return 0.0
        
        # Improvement ratio (positive = faster)
        improvement = (older_avg - recent_avg) / older_avg
        return max(-1.0, min(1.0, improvement))
    
    def _calculate_repeat_rate(self) -> float:
        """Calculate rate of repeat failures."""
        effectiveness = self.memory.get_learning_effectiveness()
        return effectiveness.get("repeat_failure_rate", 0.0)
    
    def _calculate_prediction_accuracy(self) -> float:
        """
        Calculate how accurate our predictions are.
        
        TODO: Implement proper prediction tracking.
        For now, use pattern confidence as a proxy.
        """
        high_confidence = self.patterns.get_high_confidence_patterns(0.7)
        if not self.patterns.patterns:
            return 0.0
        
        return len(high_confidence) / len(self.patterns.patterns)
    
    def _calculate_novelty_rate(self) -> float:
        """
        Calculate rate of novel (never-before-seen) failures.
        
        High novelty = we're encountering new problems
        Low novelty = we're mostly seeing known issues (good!)
        """
        recent = self.db.get_recent_failures(days=7)
        
        if not recent:
            return 0.0
        
        novel_count = sum(1 for f in recent if f.similar_failure_id is None)
        return novel_count / len(recent)
    
    def _calculate_intelligence_score(self, metrics: LearningMetrics) -> float:
        """
        Calculate overall intelligence score (0-10).
        
        Weights:
        - Fix success rate: 30%
        - Low repeat rate: 25%
        - Diagnosis speed: 15%
        - Prediction accuracy: 15%
        - Low novelty: 15% (we've seen most problems before)
        """
        score = 0.0
        
        # Fix success rate (higher = better)
        score += metrics.fix_success_rate * 3.0
        
        # Repeat rate (lower = better, so we invert)
        score += (1 - metrics.repeat_failure_rate) * 2.5
        
        # Diagnosis speed (positive trend = better)
        speed_score = (metrics.diagnosis_speed_trend + 1) / 2  # Normalize to 0-1
        score += speed_score * 1.5
        
        # Prediction accuracy (higher = better)
        score += metrics.prediction_accuracy * 1.5
        
        # Novelty rate (lower = better, we've seen issues before)
        score += (1 - metrics.novelty_rate) * 1.5
        
        return min(10.0, score)
    
    def get_recommendations(self) -> List[LearningRecommendation]:
        """
        Get recommendations for improving learning.
        
        Analyzes current metrics and suggests improvements.
        """
        metrics = self.evaluate()
        recommendations = []
        
        # Low fix success rate
        if metrics.fix_success_rate < 0.7:
            recommendations.append(LearningRecommendation(
                area="Fix Application",
                issue=f"Fix success rate is only {metrics.fix_success_rate:.0%}",
                recommendation="Review failed fixes and improve root cause analysis",
                priority="high",
                expected_improvement="Higher first-attempt fix rate"
            ))
        
        # High repeat rate
        if metrics.repeat_failure_rate > 0.3:
            recommendations.append(LearningRecommendation(
                area="Learning Memory",
                issue=f"Repeat failure rate is {metrics.repeat_failure_rate:.0%}",
                recommendation="Improve pattern matching for known issues",
                priority="high",
                expected_improvement="Fewer repeated failures"
            ))
        
        # Slow diagnosis
        if metrics.diagnosis_speed_trend < 0:
            recommendations.append(LearningRecommendation(
                area="Diagnosis",
                issue="Getting slower at diagnosis",
                recommendation="Review and optimize root cause analysis",
                priority="medium",
                expected_improvement="Faster time to fix"
            ))
        
        # Low prediction accuracy
        if metrics.prediction_accuracy < 0.5:
            recommendations.append(LearningRecommendation(
                area="Pattern Detection",
                issue=f"Pattern confidence is low ({metrics.prediction_accuracy:.0%})",
                recommendation="Gather more failure data and refine patterns",
                priority="medium",
                expected_improvement="Better failure prediction"
            ))
        
        # High novelty (many new types of failures)
        if metrics.novelty_rate > 0.5:
            recommendations.append(LearningRecommendation(
                area="Coverage",
                issue=f"Many novel failures ({metrics.novelty_rate:.0%})",
                recommendation="Expand monitoring and proactive checks",
                priority="medium",
                expected_improvement="Catch more failure types in advance"
            ))
        
        # Few patterns discovered
        if metrics.patterns_discovered < 5:
            recommendations.append(LearningRecommendation(
                area="Pattern Engine",
                issue=f"Only {metrics.patterns_discovered} patterns discovered",
                recommendation="Run pattern detection with more history",
                priority="low",
                expected_improvement="More predictive patterns"
            ))
        
        return recommendations
    
    def optimize(self):
        """
        Apply automatic optimizations based on metrics.
        
        This is the "learning to learn better" part.
        """
        metrics = self.evaluate()
        
        # If repeat rate is high, try to discover more patterns
        if metrics.repeat_failure_rate > 0.3:
            logger.info("High repeat rate - running extended pattern detection")
            self.patterns.detect_patterns(days=60)
        
        # If few patterns, also run detection
        if metrics.patterns_discovered < 3:
            logger.info("Few patterns - running pattern detection")
            self.patterns.detect_patterns(days=30)
        
        logger.info("Meta-learning optimization complete")
    
    def get_intelligence_trend(self, days: int = 7) -> Dict[str, Any]:
        """Get intelligence score trend over time."""
        trend = self.db.get_metric_trend("intelligence_score", days=days)
        
        if len(trend) < 2:
            return {
                "trend": "insufficient_data",
                "data_points": len(trend),
                "current_score": trend[-1][1] if trend else 0
            }
        
        first_score = trend[0][1]
        last_score = trend[-1][1]
        change = last_score - first_score
        
        return {
            "trend": "improving" if change > 0.1 else "declining" if change < -0.1 else "stable",
            "change": change,
            "first_score": first_score,
            "current_score": last_score,
            "data_points": len(trend)
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive learning summary."""
        metrics = self.evaluate()
        recommendations = self.get_recommendations()
        trend = self.get_intelligence_trend()
        
        return {
            "current_intelligence_score": metrics.overall_intelligence_score,
            "metrics": metrics.to_dict(),
            "trend": trend,
            "recommendations": [
                {
                    "area": r.area,
                    "issue": r.issue,
                    "recommendation": r.recommendation,
                    "priority": r.priority
                }
                for r in recommendations
            ],
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_learner: Optional[MetaLearner] = None


def get_meta_learner() -> MetaLearner:
    """Get or create the meta-learner instance."""
    global _learner
    if _learner is None:
        _learner = MetaLearner()
    return _learner


def evaluate_learning() -> LearningMetrics:
    """Convenience function to evaluate learning."""
    return get_meta_learner().evaluate()


def get_recommendations() -> List[LearningRecommendation]:
    """Convenience function to get recommendations."""
    return get_meta_learner().get_recommendations()









