"""Strategic decision engine with priority calculation algorithms"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from .config import settings
from .models import Decision, DecisionCriteria, Task, TaskPriority
from .memory_manager import MemoryManager


class DecisionEngine:
    """
    Makes strategic decisions using data-driven algorithms.

    Supports multiple decision algorithms:
    - weighted_multi_criteria: Weighted scoring across multiple criteria
    - simple: Basic priority-based decisions
    - ml_based: Machine learning from past decisions (future)
    """

    def __init__(self, memory_manager: MemoryManager):
        """Initialize decision engine with memory"""
        self.memory = memory_manager

        # Default weights for multi-criteria decision making
        self.criteria_weights = {
            "revenue_impact": 0.35,      # 35% weight - highest priority
            "risk_level": -0.20,         # 20% negative weight (lower risk is better)
            "time_to_value": -0.15,      # 15% negative weight (faster is better)
            "resource_requirement": -0.10,  # 10% negative weight (less resources is better)
            "strategic_alignment": 0.30   # 30% weight - second highest priority
        }

    def make_decision(
        self,
        title: str,
        description: str,
        options: List[str],
        criteria: DecisionCriteria
    ) -> Decision:
        """
        Make a strategic decision.

        Args:
            title: Decision title
            description: What needs to be decided
            options: List of possible options
            criteria: Evaluation criteria

        Returns:
            Decision with recommended option and reasoning
        """
        decision_id = f"decision-{uuid.uuid4().hex[:8]}"

        # Check for similar past decisions
        similar_decisions = self.memory.recall_similar_decisions(title, limit=3)

        # Calculate scores for each option
        option_scores = {}

        if settings.priority_algorithm == "weighted_multi_criteria":
            option_scores = self._weighted_multi_criteria(options, criteria, similar_decisions)
        elif settings.priority_algorithm == "simple":
            option_scores = self._simple_scoring(options, criteria)
        else:
            option_scores = self._weighted_multi_criteria(options, criteria, similar_decisions)

        # Select best option
        if option_scores:
            best_option = max(option_scores.items(), key=lambda x: x[1]["total_score"])
            recommended = best_option[0]
            confidence = best_option[1]["total_score"]
            reasoning = best_option[1]["reasoning"]
        else:
            recommended = options[0] if options else None
            confidence = 0.5
            reasoning = "No scoring algorithm available, selected first option"

        decision = Decision(
            decision_id=decision_id,
            title=title,
            description=description,
            options=options,
            criteria=criteria,
            recommended_option=recommended,
            confidence_score=confidence,
            reasoning=reasoning,
            created_at=datetime.now()
        )

        return decision

    def _weighted_multi_criteria(
        self,
        options: List[str],
        criteria: DecisionCriteria,
        past_decisions: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Weighted multi-criteria decision making.

        Formula:
        Score = (revenue_impact * 0.35) + (-risk * 0.20) + (-time_to_value * 0.15) +
                (-resource * 0.10) + (strategic_alignment * 0.30)

        Plus bonus from similar successful past decisions.
        """
        scores = {}

        for option in options:
            # Calculate base score from criteria
            base_score = (
                criteria.revenue_impact * self.criteria_weights["revenue_impact"] +
                criteria.risk_level * self.criteria_weights["risk_level"] +
                (criteria.time_to_value / 365) * self.criteria_weights["time_to_value"] +  # Normalize to 0-1
                criteria.resource_requirement * self.criteria_weights["resource_requirement"] +
                criteria.strategic_alignment * self.criteria_weights["strategic_alignment"]
            )

            # Bonus from past successful similar decisions
            past_success_bonus = 0.0
            if past_decisions:
                successful_similar = [
                    d for d in past_decisions
                    if d.get("success") and option.lower() in d.get("chosen_option", "").lower()
                ]
                past_success_bonus = len(successful_similar) * 0.05  # 5% bonus per similar success

            total_score = base_score + past_success_bonus

            # Build reasoning
            reasoning_parts = []
            reasoning_parts.append(f"Base score: {base_score:.2f}")

            if criteria.revenue_impact > 0.7:
                reasoning_parts.append(f"High revenue impact ({criteria.revenue_impact:.0%})")
            if criteria.risk_level < 0.3:
                reasoning_parts.append(f"Low risk ({criteria.risk_level:.0%})")
            if criteria.strategic_alignment > 0.7:
                reasoning_parts.append(f"Strong strategic fit ({criteria.strategic_alignment:.0%})")
            if past_success_bonus > 0:
                reasoning_parts.append(f"Proven success in {len(successful_similar)} similar cases")

            reasoning = "; ".join(reasoning_parts)

            scores[option] = {
                "total_score": total_score,
                "base_score": base_score,
                "past_success_bonus": past_success_bonus,
                "reasoning": reasoning
            }

        return scores

    def _simple_scoring(
        self,
        options: List[str],
        criteria: DecisionCriteria
    ) -> Dict[str, Dict[str, Any]]:
        """Simple scoring based on revenue impact and risk"""
        scores = {}

        for option in options:
            # Simple formula: revenue_impact - risk_level
            score = criteria.revenue_impact - criteria.risk_level

            scores[option] = {
                "total_score": score,
                "base_score": score,
                "past_success_bonus": 0,
                "reasoning": f"Revenue: {criteria.revenue_impact:.0%}, Risk: {criteria.risk_level:.0%}"
            }

        return scores

    def prioritize_tasks(self, tasks: List[Task]) -> List[Task]:
        """
        Prioritize a list of tasks based on multiple factors.

        Returns tasks sorted by priority (highest first).
        """
        def calculate_task_score(task: Task) -> float:
            """Calculate priority score for a task"""

            # Base score from priority level
            priority_scores = {
                TaskPriority.CRITICAL: 100,
                TaskPriority.HIGH: 75,
                TaskPriority.MEDIUM: 50,
                TaskPriority.LOW: 25
            }
            score = priority_scores.get(task.priority, 50)

            # Increase score for tasks with no dependencies (can start immediately)
            if not task.dependencies:
                score += 20

            # Decrease score based on estimated duration (prefer quick wins)
            if task.estimated_duration_minutes:
                if task.estimated_duration_minutes < 30:
                    score += 10  # Quick tasks
                elif task.estimated_duration_minutes > 240:
                    score -= 10  # Long tasks

            # Use memory to boost tasks similar to past successes
            suggestions = self.memory.suggest_optimal_execution(task)
            if suggestions["confidence"] > 0.5:
                score += suggestions["confidence"] * 15  # Up to +15 for high confidence

            return score

        # Calculate scores and sort
        task_scores = [(task, calculate_task_score(task)) for task in tasks]
        task_scores.sort(key=lambda x: x[1], reverse=True)

        return [task for task, score in task_scores]

    def should_deploy_treasury(
        self,
        available_capital_usd: float,
        current_revenue_monthly: float,
        cycle_position: str
    ) -> Dict[str, Any]:
        """
        Decide whether to deploy capital to treasury and how much.

        Args:
            available_capital_usd: Capital available to deploy
            current_revenue_monthly: Current monthly revenue
            cycle_position: "early", "mid", "peak", "correction"

        Returns:
            {
                "should_deploy": bool,
                "amount_to_deploy_usd": float,
                "allocation": {"stable": float, "tactical": float},
                "reasoning": str
            }
        """
        # Minimum threshold: $10K
        if available_capital_usd < 10000:
            return {
                "should_deploy": False,
                "amount_to_deploy_usd": 0,
                "allocation": {"stable": 0, "tactical": 0},
                "reasoning": f"Available capital ${available_capital_usd:,.0f} below $10K minimum threshold"
            }

        # Decision criteria based on cycle position
        allocations = {
            "early": {"stable": 0.50, "tactical": 0.50},     # More tactical in early cycle
            "mid": {"stable": 0.60, "tactical": 0.40},       # Balanced
            "peak": {"stable": 0.80, "tactical": 0.20},      # More conservative near peak
            "correction": {"stable": 0.70, "tactical": 0.30}  # Wait for better entries
        }

        allocation = allocations.get(cycle_position, {"stable": 0.60, "tactical": 0.40})

        # Deploy percentage based on revenue confidence
        # If monthly revenue > 2x capital, deploy 80%
        # If monthly revenue > capital, deploy 60%
        # Otherwise, deploy 40%

        if current_revenue_monthly > available_capital_usd * 2:
            deploy_percent = 0.80
            confidence = "high"
        elif current_revenue_monthly > available_capital_usd:
            deploy_percent = 0.60
            confidence = "medium"
        else:
            deploy_percent = 0.40
            confidence = "low"

        amount_to_deploy = available_capital_usd * deploy_percent

        reasoning = f"""Deploy {deploy_percent:.0%} (${amount_to_deploy:,.0f}) based on {confidence} revenue confidence.
Allocation: {allocation['stable']:.0%} stable yield, {allocation['tactical']:.0%} tactical.
Cycle position: {cycle_position} - {"favoring tactical entries" if cycle_position == "early" else "more conservative approach"}."""

        return {
            "should_deploy": True,
            "amount_to_deploy_usd": amount_to_deploy,
            "allocation": {
                "stable_usd": amount_to_deploy * allocation["stable"],
                "tactical_usd": amount_to_deploy * allocation["tactical"]
            },
            "reasoning": reasoning,
            "confidence": confidence
        }

    def evaluate_service_build(
        self,
        service_name: str,
        estimated_build_hours: float,
        estimated_monthly_revenue: float,
        resource_requirement: float = 0.5
    ) -> Dict[str, Any]:
        """
        Evaluate whether to build a new service.

        Returns ROI analysis and recommendation.
        """
        # Calculate ROI
        # Assume architect time worth $200/hour
        build_cost_usd = estimated_build_hours * 200

        # Time to ROI in months
        if estimated_monthly_revenue > 0:
            months_to_roi = build_cost_usd / estimated_monthly_revenue
            annual_roi = (estimated_monthly_revenue * 12 - build_cost_usd) / build_cost_usd
        else:
            months_to_roi = float('inf')
            annual_roi = -1.0

        # Recommendation
        if months_to_roi <= 1:
            recommendation = "HIGHLY RECOMMENDED"
            priority = "critical"
        elif months_to_roi <= 3:
            recommendation = "RECOMMENDED"
            priority = "high"
        elif months_to_roi <= 6:
            recommendation = "CONSIDER"
            priority = "medium"
        else:
            recommendation = "LOW PRIORITY"
            priority = "low"

        return {
            "service_name": service_name,
            "build_cost_usd": build_cost_usd,
            "estimated_monthly_revenue": estimated_monthly_revenue,
            "months_to_roi": months_to_roi if months_to_roi != float('inf') else None,
            "annual_roi_percent": annual_roi * 100 if annual_roi >= 0 else None,
            "recommendation": recommendation,
            "priority": priority,
            "reasoning": f"ROI in {months_to_roi:.1f} months" if months_to_roi != float('inf') else "No revenue projected"
        }
