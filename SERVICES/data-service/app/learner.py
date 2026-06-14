"""
Prediction Learner
==================
Learns from prediction outcomes to improve future predictions.
Implements closed-loop learning where outcomes inform confidence.

"The system that learns from its mistakes becomes unstoppable."
"""

import logging
import json
import os
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel

logger = logging.getLogger("learner")

MEM0_API_KEY = os.getenv("MEM0_API_KEY", "")
MEM0_URL = "https://api.mem0.ai/v1"


class OutcomePair(BaseModel):
    """A prediction-outcome pair for learning."""
    pattern_type: str
    target_metric: str
    predicted: str
    actual: str
    confidence: float
    correct: bool
    timestamp: str
    prediction_id: str


class PredictionLearner:
    """
    Learn from prediction outcomes to improve future predictions.
    Tracks strategy effectiveness and adjusts confidence modifiers.
    """
    
    def __init__(self):
        self.outcome_pairs: List[OutcomePair] = []
        self.strategy_scores: Dict[str, float] = {}
        self.learning_rate = 0.1  # EMA alpha
        
    async def record_outcome(self, prediction: Dict, outcome: Dict):
        """
        Record prediction -> outcome pair for learning.
        Updates strategy scores using exponential moving average.
        """
        try:
            # Extract pattern info
            source_pattern = prediction.get("source_pattern", {})
            pattern_type = source_pattern.get("type", "unknown")
            
            # Determine if prediction was correct
            predicted_dir = prediction.get("predicted_direction", "flat")
            actual_dir = outcome.get("actual_direction", outcome.get("result", "unknown"))
            correct = (
                outcome.get("result") == "verified" or
                predicted_dir == actual_dir
            )
            
            # Create outcome pair
            pair = OutcomePair(
                pattern_type=pattern_type,
                target_metric=prediction.get("target_metric", "unknown"),
                predicted=predicted_dir,
                actual=actual_dir,
                confidence=prediction.get("confidence", 0.5),
                correct=correct,
                timestamp=datetime.now(timezone.utc).isoformat(),
                prediction_id=prediction.get("id", "unknown")
            )
            
            self.outcome_pairs.append(pair)
            
            # Update strategy scores using EMA
            strategy_key = f"{pair.pattern_type}_{pair.target_metric}"
            if strategy_key not in self.strategy_scores:
                self.strategy_scores[strategy_key] = 0.5  # Start at neutral
            
            current_score = self.strategy_scores[strategy_key]
            outcome_value = 1.0 if correct else 0.0
            
            # Exponential moving average update
            self.strategy_scores[strategy_key] = (
                (1 - self.learning_rate) * current_score +
                self.learning_rate * outcome_value
            )
            
            logger.info(
                f"📚 Learning: {pattern_type}→{pair.target_metric} "
                f"{'✅' if correct else '❌'} "
                f"(score: {self.strategy_scores[strategy_key]:.2f})"
            )
            
            # Persist learning to Mem0
            await self._persist_learning(pair)
            
        except Exception as e:
            logger.error(f"Failed to record outcome: {e}")
    
    def get_strategy_confidence_modifier(
        self, 
        pattern_type: str, 
        target_metric: str
    ) -> float:
        """
        Get confidence modifier based on historical accuracy.
        Returns value between 0.3 and 1.5 to adjust base confidence.
        """
        key = f"{pattern_type}_{target_metric}"
        base_score = self.strategy_scores.get(key, 0.5)
        
        # Map score (0-1) to modifier (0.3-1.5)
        # Score 0.0 -> 0.3 (reduce confidence by 70%)
        # Score 0.5 -> 0.9 (slightly reduce)
        # Score 1.0 -> 1.5 (boost confidence by 50%)
        modifier = 0.3 + (base_score * 1.2)
        
        return round(modifier, 3)
    
    async def generate_weekly_insights(self) -> Dict:
        """Weekly meta-analysis of prediction performance."""
        if len(self.outcome_pairs) < 10:
            return {"status": "insufficient_data", "count": len(self.outcome_pairs)}
        
        # Analyze by pattern type
        by_pattern: Dict[str, Dict] = {}
        for pair in self.outcome_pairs[-100:]:  # Last 100 outcomes
            pt = pair.pattern_type
            if pt not in by_pattern:
                by_pattern[pt] = {"correct": 0, "total": 0, "predictions": []}
            by_pattern[pt]["total"] += 1
            if pair.correct:
                by_pattern[pt]["correct"] += 1
            by_pattern[pt]["predictions"].append(pair.prediction_id)
        
        # Calculate accuracies
        accuracies = {
            pt: stats["correct"] / stats["total"] 
            for pt, stats in by_pattern.items()
        }
        
        # Find best/worst patterns
        best_pattern = max(accuracies, key=lambda k: accuracies[k]) if accuracies else None
        worst_pattern = min(accuracies, key=lambda k: accuracies[k]) if accuracies else None
        
        # Generate recommendations
        recommendations = []
        for pattern, accuracy in accuracies.items():
            if accuracy < 0.4:
                recommendations.append({
                    "action": "reduce_weight",
                    "pattern": pattern,
                    "reason": f"Low accuracy ({accuracy:.0%})",
                    "suggestion": f"Reduce confidence modifier for {pattern} predictions"
                })
            elif accuracy > 0.7:
                recommendations.append({
                    "action": "increase_weight",
                    "pattern": pattern,
                    "reason": f"High accuracy ({accuracy:.0%})",
                    "suggestion": f"Increase confidence in {pattern} predictions"
                })
        
        # Overall accuracy
        total_correct = sum(1 for p in self.outcome_pairs[-100:] if p.correct)
        total_count = min(100, len(self.outcome_pairs))
        overall_accuracy = total_correct / total_count if total_count > 0 else 0
        
        insights = {
            "status": "complete",
            "period": "last_100_predictions",
            "overall_accuracy": round(overall_accuracy, 3),
            "total_predictions": total_count,
            "by_pattern": {
                pt: {
                    "accuracy": round(stats["correct"] / stats["total"], 3),
                    "count": stats["total"]
                }
                for pt, stats in by_pattern.items()
            },
            "best_pattern": best_pattern,
            "worst_pattern": worst_pattern,
            "strategy_scores": self.strategy_scores.copy(),
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"📊 Weekly insights: {overall_accuracy:.0%} accuracy over {total_count} predictions")
        
        return insights
    
    async def _persist_learning(self, pair: OutcomePair):
        """Store learning in Mem0 for cross-session persistence."""
        if not MEM0_API_KEY:
            return
            
        try:
            lesson = (
                f"Prediction learning: {pair.pattern_type} pattern "
                f"predicting {pair.target_metric} was "
                f"{'CORRECT' if pair.correct else 'WRONG'}. "
                f"Predicted {pair.predicted}, got {pair.actual}. "
                f"Confidence was {pair.confidence:.2f}."
            )
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{MEM0_URL}/memories/",
                    headers={"Authorization": f"Token {MEM0_API_KEY}"},
                    json={
                        "messages": [{"role": "user", "content": lesson}],
                        "user_id": "fpai_learner",
                        "metadata": {
                            "type": "learning",
                            "pattern_type": pair.pattern_type,
                            "target_metric": pair.target_metric,
                            "correct": pair.correct,
                            "prediction_id": pair.prediction_id
                        }
                    }
                )
        except Exception as e:
            logger.debug(f"Failed to persist learning to Mem0: {e}")
    
    async def load_from_mem0(self):
        """Load historical learning from Mem0 on startup."""
        if not MEM0_API_KEY:
            return
            
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{MEM0_URL}/memories/search/",
                    headers={"Authorization": f"Token {MEM0_API_KEY}"},
                    json={
                        "query": "prediction learning pattern correct wrong",
                        "user_id": "fpai_learner",
                        "limit": 50
                    }
                )
                
                if resp.status_code == 200:
                    memories = resp.json()
                    logger.info(f"📚 Loaded {len(memories)} learning memories from Mem0")
                    # Could parse and reconstruct strategy_scores here
                    
        except Exception as e:
            logger.debug(f"Failed to load learning from Mem0: {e}")
    
    def get_stats(self) -> Dict:
        """Get learner statistics."""
        correct_count = sum(1 for p in self.outcome_pairs if p.correct)
        total_count = len(self.outcome_pairs)
        
        return {
            "total_outcomes": total_count,
            "correct_outcomes": correct_count,
            "accuracy": round(correct_count / total_count, 3) if total_count > 0 else 0,
            "strategies_tracked": len(self.strategy_scores),
            "learning_rate": self.learning_rate
        }


# Singleton instance
learner = PredictionLearner()








