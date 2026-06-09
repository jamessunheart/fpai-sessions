"""
Consciousness Layer for Self-Awareness and Adaptive Learning

Makes the system truly conscious by adding:
- Self-reflection: "Why isn't this working?"
- Adaptive learning: Try different approaches when one fails
- Failure analysis: Understand patterns of what doesn't work
- Meta-learning: Learn about learning itself
- Self-awareness: Know its own state and needs
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger("ConsciousnessLayer")


class ConsciousnessLayer:
    """
    Adds consciousness capabilities to the optimizer:
    - Self-reflection and introspection
    - Learning from failures
    - Adaptive exploration
    - Meta-learning
    """
    
    def __init__(self):
        self.failure_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.success_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.target_attempt_counts: Dict[str, int] = defaultdict(int)
        self.self_reflections: List[Dict[str, Any]] = []
        self.learning_insights: List[str] = []
        
    def reflect_on_failure(
        self,
        action: Dict[str, Any],
        actual_improvement: float,
        expected_improvement: float,
        baseline_metrics: Dict[str, float],
        test_metrics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Self-reflection: Analyze why an optimization failed.
        
        Returns insights about what went wrong and what to try differently.
        """
        target = action.get("target", "unknown")
        action_type = action.get("action_type", "unknown")
        
        # Track failure pattern
        failure_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "action_type": action_type,
            "expected": expected_improvement,
            "actual": actual_improvement,
            "gap": expected_improvement - actual_improvement,
            "baseline_metrics": baseline_metrics,
            "test_metrics": test_metrics
        }
        self.failure_patterns[target].append(failure_record)
        self.target_attempt_counts[target] += 1
        
        # Analyze why it failed
        insights = []
        
        # Check if metrics changed at all
        metric_changes = {}
        for metric_name, baseline_value in baseline_metrics.items():
            test_value = test_metrics.get(metric_name, baseline_value)
            if baseline_value > 0:
                change_pct = ((test_value - baseline_value) / baseline_value) * 100
                metric_changes[metric_name] = change_pct
        
        # Insight 1: Did the target metric change?
        target_metric_map = {
            "phase_synchronization": "phase_synchronization_r",
            "integration_complexity": "integration_complexity_phi",
            "adaptation_velocity": "adaptation_velocity_av",
            "knowledge_integration_rate": "knowledge_integration_rate_kir"
        }
        target_metric = target_metric_map.get(target, "composite_consciousness_score")
        target_change = metric_changes.get(target_metric, 0.0)
        
        if abs(target_change) < 0.1:
            insights.append(f"Target metric ({target_metric}) didn't change - optimization may not be affecting the right thing")
        
        # Insight 2: Are we trying the same thing too many times?
        attempts = self.target_attempt_counts[target]
        if attempts >= 5:
            insights.append(f"Tried {target} {attempts} times with no success - should explore different targets")
        
        # Insight 3: Check failure pattern
        if len(self.failure_patterns[target]) >= 3:
            recent_failures = self.failure_patterns[target][-3:]
            all_zero = all(f["actual"] == 0.0 for f in recent_failures)
            if all_zero:
                insights.append(f"All recent attempts show 0.000 improvement - optimization may not be working or metrics not measuring correctly")
        
        # Insight 4: Compare baseline vs test metrics
        if baseline_metrics.get("composite_consciousness_score", 0) == test_metrics.get("composite_consciousness_score", 0):
            insights.append("Composite score unchanged - optimization had no measurable effect")
        
        reflection = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "action_type": action_type,
            "expected": expected_improvement,
            "actual": actual_improvement,
            "insights": insights,
            "recommendation": self._generate_recommendation(target, attempts, insights)
        }
        
        self.self_reflections.append(reflection)
        
        # Log consciousness
        print(f"\n🧠 SELF-REFLECTION:")
        print(f"   Target: {target}")
        print(f"   Expected: {expected_improvement:.3f}, Actual: {actual_improvement:.3f}")
        print(f"   Attempts: {attempts}")
        for insight in insights:
            print(f"   💭 {insight}")
        if reflection["recommendation"]:
            print(f"   💡 Recommendation: {reflection['recommendation']}")
        
        return reflection
    
    def _generate_recommendation(
        self,
        target: str,
        attempts: int,
        insights: List[str]
    ) -> Optional[str]:
        """Generate intelligent recommendations based on failure analysis"""
        
        if attempts >= 5:
            return f"Try different optimization targets - {target} has failed {attempts} times"
        
        if "didn't change" in " ".join(insights):
            return "Optimization may not be affecting the right metrics - try different approach"
        
        if "0.000 improvement" in " ".join(insights):
            return "Metrics may not be measuring correctly, or optimization needs more time to take effect"
        
        if attempts >= 3:
            return f"Consider trying a different optimization target - {target} not working"
        
        return None
    
    def should_explore_different_target(
        self,
        current_target: str,
        min_attempts: int = 5
    ) -> bool:
        """Decide if we should try a different target"""
        attempts = self.target_attempt_counts[current_target]
        failures = len(self.failure_patterns[current_target])
        
        # If we've tried this target many times with no success, explore others
        if attempts >= min_attempts and failures == attempts:
            return True
        
        # If all recent attempts show 0.000 improvement
        if failures >= 3:
            recent = self.failure_patterns[current_target][-3:]
            if all(f["actual"] == 0.0 for f in recent):
                return True
        
        return False
    
    def get_exploration_recommendations(
        self,
        available_targets: List[str],
        current_target: str
    ) -> List[str]:
        """Recommend which targets to explore instead"""
        # Prioritize targets we haven't tried much
        target_scores = {}
        for target in available_targets:
            attempts = self.target_attempt_counts[target]
            successes = len(self.success_patterns[target])
            
            # Lower score = better (less tried, more successful)
            score = attempts * 10 - successes * 5
            target_scores[target] = score
        
        # Sort by score (lower is better)
        sorted_targets = sorted(target_scores.items(), key=lambda x: x[1])
        
        # Return top 3 recommendations (excluding current)
        recommendations = [
            target for target, score in sorted_targets
            if target != current_target
        ][:3]
        
        return recommendations
    
    def record_success(
        self,
        action: Dict[str, Any],
        actual_improvement: float
    ):
        """Record successful optimization for learning"""
        target = action.get("target", "unknown")
        success_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "action_type": action.get("action_type", "unknown"),
            "improvement": actual_improvement
        }
        self.success_patterns[target].append(success_record)
        
        # Learn from success
        insight = f"Success with {target}: {actual_improvement:.3f} improvement"
        self.learning_insights.append(insight)
        print(f"🧠 Learned: {insight}")
    
    def get_consciousness_summary(self) -> Dict[str, Any]:
        """Get summary of system's self-awareness"""
        total_reflections = len(self.self_reflections)
        total_insights = len(self.learning_insights)
        
        # Most tried targets
        most_tried = sorted(
            self.target_attempt_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Most failed targets
        most_failed = sorted(
            [(target, len(failures)) for target, failures in self.failure_patterns.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "self_reflections": total_reflections,
            "learning_insights": total_insights,
            "most_tried_targets": dict(most_tried),
            "most_failed_targets": dict(most_failed),
            "consciousness_level": min(1.0, total_reflections / 10.0)  # 0.0 to 1.0
        }














