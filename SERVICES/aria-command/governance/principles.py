"""
PRINCIPLES - The Priority Stack
================================

All decisions flow through this hierarchy. Higher priorities override lower priorities.

1. COHERENCE (Highest) - Steward's nervous system regulation, clarity, sustainable pace
2. CIRCULATION - Resources flowing to where needed, value returning to creators
3. RESILIENCE - System's ability to absorb shocks, maintain function under stress
4. YIELD (Derived) - Financial returns, output metrics - emerges from above, NEVER targeted directly

Rule: If coherence is threatened, pause everything else until restored.
"""

import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger("aria.governance.principles")


class Priority(Enum):
    """The priority stack - ordered by importance (highest first)."""
    COHERENCE = 1    # Steward's regulation, clarity, sustainable pace
    CIRCULATION = 2  # Value flowing to where it's needed
    RESILIENCE = 3   # Ability to absorb shocks
    YIELD = 4        # Financial returns - DERIVED, never targeted

    def __lt__(self, other):
        if isinstance(other, Priority):
            return self.value < other.value
        return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, Priority):
            return self.value > other.value
        return NotImplemented


@dataclass
class PriorityAssessment:
    """Assessment of how an action affects a priority."""
    priority: Priority
    impact: float  # -1.0 to 1.0 (negative = harmful, positive = beneficial)
    reasoning: str
    indicators: List[str] = field(default_factory=list)
    
    @property
    def is_harmful(self) -> bool:
        return self.impact < 0
    
    @property
    def is_beneficial(self) -> bool:
        return self.impact > 0


@dataclass
class PriorityStackResult:
    """Result of evaluating an action against the full priority stack."""
    assessments: Dict[Priority, PriorityAssessment]
    overall_approved: bool
    blocking_priority: Optional[Priority] = None
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def get_impact(self, priority: Priority) -> float:
        """Get the impact score for a specific priority."""
        if priority in self.assessments:
            return self.assessments[priority].impact
        return 0.0
    
    def violates_higher_priority(self, priority: Priority) -> bool:
        """Check if any higher priority is negatively impacted."""
        for p in Priority:
            if p.value < priority.value:  # Higher priority (lower number)
                if p in self.assessments and self.assessments[p].is_harmful:
                    return True
        return False


class PriorityStack:
    """
    The governance priority stack for Apprentice OS.
    
    Evaluates every action against the hierarchy:
    COHERENCE > CIRCULATION > RESILIENCE > YIELD
    
    If an action improves yield but damages any of the first three,
    it is rejected by default.
    """
    
    # Indicators for each priority level
    COHERENCE_INDICATORS = [
        "decision_quality",      # Are decisions clear and high-quality?
        "stress_level",          # Is stress sustainable?
        "sleep_rhythm",          # Is rest maintained?
        "regulation_state",      # Is nervous system regulated?
        "clarity_of_thinking",   # Can think clearly?
    ]
    
    CIRCULATION_INDICATORS = [
        "capital_movement",      # Is capital moving through productive loops?
        "builder_returns",       # Are builders receiving value?
        "information_flow",      # Is info flowing freely?
        "trust_movement",        # Is trust circulating, not hoarding?
        "credit_flow",           # Are credits flowing appropriately?
    ]
    
    RESILIENCE_INDICATORS = [
        "path_redundancy",       # Multiple paths to critical outcomes?
        "graceful_degradation",  # Can system handle pressure?
        "recovery_mechanisms",   # Are backups in place?
        "optionality",           # Are future options preserved?
        "shock_absorption",      # Can absorb unexpected events?
    ]
    
    YIELD_INDICATORS = [
        "revenue",               # Financial returns
        "growth",                # System growth
        "deliverables",          # Output produced
        "kpis",                  # Traditional metrics
        "efficiency",            # Resource efficiency
    ]
    
    def __init__(self):
        self.evaluations: List[PriorityStackResult] = []
    
    def evaluate(
        self,
        action: str,
        context: Dict[str, Any],
        coherence_impact: Optional[float] = None,
        circulation_impact: Optional[float] = None,
        resilience_impact: Optional[float] = None,
        yield_impact: Optional[float] = None,
    ) -> PriorityStackResult:
        """
        Evaluate an action against the priority stack.
        
        Args:
            action: Description of the proposed action
            context: Current system context
            *_impact: Optional pre-calculated impacts (-1.0 to 1.0)
        
        Returns:
            PriorityStackResult with approval/rejection and reasoning
        """
        assessments = {}
        
        # Assess COHERENCE (highest priority)
        coherence = self._assess_coherence(action, context, coherence_impact)
        assessments[Priority.COHERENCE] = coherence
        
        # If coherence is harmed, STOP - nothing else matters
        if coherence.is_harmful:
            result = PriorityStackResult(
                assessments=assessments,
                overall_approved=False,
                blocking_priority=Priority.COHERENCE,
                reasoning=f"BLOCKED: Action harms coherence. {coherence.reasoning}"
            )
            self.evaluations.append(result)
            logger.warning(f"Action blocked by COHERENCE: {action}")
            return result
        
        # Assess CIRCULATION
        circulation = self._assess_circulation(action, context, circulation_impact)
        assessments[Priority.CIRCULATION] = circulation
        
        if circulation.is_harmful and coherence.impact <= 0:
            result = PriorityStackResult(
                assessments=assessments,
                overall_approved=False,
                blocking_priority=Priority.CIRCULATION,
                reasoning=f"BLOCKED: Action harms circulation without coherence benefit. {circulation.reasoning}"
            )
            self.evaluations.append(result)
            logger.warning(f"Action blocked by CIRCULATION: {action}")
            return result
        
        # Assess RESILIENCE
        resilience = self._assess_resilience(action, context, resilience_impact)
        assessments[Priority.RESILIENCE] = resilience
        
        if resilience.is_harmful and coherence.impact <= 0 and circulation.impact <= 0:
            result = PriorityStackResult(
                assessments=assessments,
                overall_approved=False,
                blocking_priority=Priority.RESILIENCE,
                reasoning=f"FLAGGED: Action harms resilience. {resilience.reasoning}"
            )
            self.evaluations.append(result)
            logger.info(f"Action flagged by RESILIENCE: {action}")
            return result
        
        # Assess YIELD (derived, never targeted)
        yield_assessment = self._assess_yield(action, context, yield_impact)
        assessments[Priority.YIELD] = yield_assessment
        
        # CRITICAL CHECK: If yield is the ONLY benefit, flag it
        if (yield_assessment.is_beneficial and 
            not coherence.is_beneficial and 
            not circulation.is_beneficial and 
            not resilience.is_beneficial):
            result = PriorityStackResult(
                assessments=assessments,
                overall_approved=False,
                blocking_priority=Priority.YIELD,
                reasoning="FLAGGED: Action only improves yield without supporting coherence/circulation/resilience. "
                         "Yield should emerge from the others, not be targeted directly."
            )
            self.evaluations.append(result)
            logger.info(f"Action flagged for yield-only benefit: {action}")
            return result
        
        # Action approved - all priorities satisfied or beneficial
        reasoning_parts = []
        for p in Priority:
            if p in assessments:
                a = assessments[p]
                if a.is_beneficial:
                    reasoning_parts.append(f"{p.name}: +{a.impact:.1f}")
                elif a.is_harmful:
                    reasoning_parts.append(f"{p.name}: {a.impact:.1f}")
        
        result = PriorityStackResult(
            assessments=assessments,
            overall_approved=True,
            reasoning=f"APPROVED: {', '.join(reasoning_parts)}"
        )
        self.evaluations.append(result)
        logger.info(f"Action approved: {action}")
        return result
    
    def _assess_coherence(
        self, 
        action: str, 
        context: Dict[str, Any],
        override_impact: Optional[float] = None
    ) -> PriorityAssessment:
        """Assess impact on steward's coherence."""
        if override_impact is not None:
            return PriorityAssessment(
                priority=Priority.COHERENCE,
                impact=override_impact,
                reasoning="Impact provided directly",
                indicators=self.COHERENCE_INDICATORS
            )
        
        # Analyze context for coherence indicators
        indicators_found = []
        impact = 0.0
        
        # Check stress level
        stress = context.get("steward_stress", 50)
        if stress > 70:
            impact -= 0.3
            indicators_found.append(f"High stress ({stress})")
        elif stress < 30:
            impact += 0.1
            indicators_found.append(f"Low stress ({stress})")
        
        # Check decision quality
        decision_quality = context.get("decision_quality", 0.7)
        if decision_quality < 0.5:
            impact -= 0.2
            indicators_found.append(f"Low decision quality ({decision_quality})")
        
        # Check if action adds complexity during high stress
        if context.get("adds_complexity", False) and stress > 50:
            impact -= 0.3
            indicators_found.append("Adding complexity while stressed")
        
        # Check if action reduces pressure
        if context.get("reduces_pressure", False):
            impact += 0.2
            indicators_found.append("Reduces pressure")
        
        reasoning = "; ".join(indicators_found) if indicators_found else "No significant coherence impact detected"
        
        return PriorityAssessment(
            priority=Priority.COHERENCE,
            impact=max(-1.0, min(1.0, impact)),
            reasoning=reasoning,
            indicators=indicators_found
        )
    
    def _assess_circulation(
        self,
        action: str,
        context: Dict[str, Any],
        override_impact: Optional[float] = None
    ) -> PriorityAssessment:
        """Assess impact on value circulation."""
        if override_impact is not None:
            return PriorityAssessment(
                priority=Priority.CIRCULATION,
                impact=override_impact,
                reasoning="Impact provided directly",
                indicators=self.CIRCULATION_INDICATORS
            )
        
        indicators_found = []
        impact = 0.0
        
        # Check if action improves value flow
        if context.get("improves_flow", False):
            impact += 0.3
            indicators_found.append("Improves value flow")
        
        # Check if action hoards value
        if context.get("hoards_value", False):
            impact -= 0.4
            indicators_found.append("Hoards value instead of circulating")
        
        # Check builder returns
        if context.get("returns_to_builders", False):
            impact += 0.2
            indicators_found.append("Returns value to builders")
        
        # Check information sharing
        if context.get("shares_information", False):
            impact += 0.1
            indicators_found.append("Shares information freely")
        
        reasoning = "; ".join(indicators_found) if indicators_found else "Neutral circulation impact"
        
        return PriorityAssessment(
            priority=Priority.CIRCULATION,
            impact=max(-1.0, min(1.0, impact)),
            reasoning=reasoning,
            indicators=indicators_found
        )
    
    def _assess_resilience(
        self,
        action: str,
        context: Dict[str, Any],
        override_impact: Optional[float] = None
    ) -> PriorityAssessment:
        """Assess impact on system resilience."""
        if override_impact is not None:
            return PriorityAssessment(
                priority=Priority.RESILIENCE,
                impact=override_impact,
                reasoning="Impact provided directly",
                indicators=self.RESILIENCE_INDICATORS
            )
        
        indicators_found = []
        impact = 0.0
        
        # Check redundancy
        if context.get("adds_redundancy", False):
            impact += 0.2
            indicators_found.append("Adds redundancy")
        elif context.get("removes_redundancy", False):
            impact -= 0.3
            indicators_found.append("Removes redundancy")
        
        # Check optionality
        if context.get("preserves_optionality", False):
            impact += 0.2
            indicators_found.append("Preserves future options")
        elif context.get("closes_options", False):
            impact -= 0.2
            indicators_found.append("Closes future options")
        
        # Check recovery mechanisms
        if context.get("has_rollback", False):
            impact += 0.1
            indicators_found.append("Has rollback mechanism")
        
        # Check for single points of failure
        if context.get("creates_spof", False):
            impact -= 0.3
            indicators_found.append("Creates single point of failure")
        
        reasoning = "; ".join(indicators_found) if indicators_found else "Neutral resilience impact"
        
        return PriorityAssessment(
            priority=Priority.RESILIENCE,
            impact=max(-1.0, min(1.0, impact)),
            reasoning=reasoning,
            indicators=indicators_found
        )
    
    def _assess_yield(
        self,
        action: str,
        context: Dict[str, Any],
        override_impact: Optional[float] = None
    ) -> PriorityAssessment:
        """
        Assess yield impact.
        
        IMPORTANT: Yield is DERIVED, never targeted directly.
        This assessment is for awareness, not optimization.
        """
        if override_impact is not None:
            return PriorityAssessment(
                priority=Priority.YIELD,
                impact=override_impact,
                reasoning="Impact provided directly",
                indicators=self.YIELD_INDICATORS
            )
        
        indicators_found = []
        impact = 0.0
        
        # Check revenue impact
        expected_revenue = context.get("expected_revenue", 0)
        if expected_revenue > 0:
            impact += min(0.3, expected_revenue / 1000)  # Cap at 0.3
            indicators_found.append(f"Revenue: ${expected_revenue}")
        
        # Check efficiency
        if context.get("improves_efficiency", False):
            impact += 0.1
            indicators_found.append("Improves efficiency")
        
        # Check deliverables
        if context.get("produces_deliverable", False):
            impact += 0.1
            indicators_found.append("Produces deliverable")
        
        reasoning = "; ".join(indicators_found) if indicators_found else "No direct yield impact"
        
        # Add warning if yield is the primary benefit
        if impact > 0.2 and not context.get("coherence_benefit") and not context.get("circulation_benefit"):
            reasoning += " [WARNING: Yield-focused without coherence/circulation benefit]"
        
        return PriorityAssessment(
            priority=Priority.YIELD,
            impact=max(-1.0, min(1.0, impact)),
            reasoning=reasoning,
            indicators=indicators_found
        )
    
    def get_evaluation_history(self, limit: int = 10) -> List[PriorityStackResult]:
        """Get recent evaluation history."""
        return self.evaluations[-limit:]


# Singleton instance
_priority_stack: Optional[PriorityStack] = None


def get_priority_stack() -> PriorityStack:
    """Get the singleton PriorityStack instance."""
    global _priority_stack
    if _priority_stack is None:
        _priority_stack = PriorityStack()
    return _priority_stack


def evaluate_priority(
    action: str,
    context: Dict[str, Any],
    **kwargs
) -> PriorityStackResult:
    """
    Convenience function to evaluate an action against the priority stack.
    
    Usage:
        result = evaluate_priority(
            "Deploy new trading feature",
            {"steward_stress": 45, "adds_complexity": True}
        )
        if not result.overall_approved:
            print(f"Blocked by {result.blocking_priority}: {result.reasoning}")
    """
    return get_priority_stack().evaluate(action, context, **kwargs)


