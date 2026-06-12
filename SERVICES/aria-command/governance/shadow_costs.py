"""
SHADOW COSTS - Hidden Cost Tracking
===================================

Shadow costs are the invisible costs that extraction economics ignores:
- Stress accumulation
- Trust decay
- Optionality loss
- Complexity creep

Every significant action has shadow costs. This module makes them visible.

When shadow costs exceed benefits, the action should be flagged or blocked.
"""

import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger("aria.governance.shadow_costs")


class ShadowCostType(Enum):
    """Types of shadow costs tracked by the system."""
    STRESS_ACCUMULATION = auto()   # Compound pressure on steward's nervous system
    TRUST_DECAY = auto()           # Erosion of relational capital
    OPTIONALITY_LOSS = auto()      # Closing future paths through commitments
    COMPLEXITY_CREEP = auto()      # Incremental additions exceeding coherence capacity


@dataclass
class ShadowCostDefinition:
    """Definition of a shadow cost type."""
    cost_type: ShadowCostType
    description: str
    measurement: str
    sources: List[str]
    threshold_warning: float
    threshold_critical: float


# Shadow cost definitions from Apprentice OS spec
SHADOW_COST_DEFINITIONS: Dict[ShadowCostType, ShadowCostDefinition] = {
    ShadowCostType.STRESS_ACCUMULATION: ShadowCostDefinition(
        cost_type=ShadowCostType.STRESS_ACCUMULATION,
        description="Compound pressure on steward's nervous system",
        measurement="self_report + interaction_pattern_analysis + decision_quality_delta",
        sources=[
            "steward_metrics.stress_level (self-report)",
            "events table (response gaps, tone shifts)",
            "override_count / decision_count ratio"
        ],
        threshold_warning=60,
        threshold_critical=80
    ),
    ShadowCostType.TRUST_DECAY: ShadowCostDefinition(
        cost_type=ShadowCostType.TRUST_DECAY,
        description="Erosion of relational capital through misalignment",
        measurement="response_latency + collaboration_friction + explicit_feedback",
        sources=[
            "events table (time between request and action)",
            "clarification loop count in conversations",
            "explicit trust feedback"
        ],
        threshold_warning=-10,  # Negative because decay is measured as loss
        threshold_critical=-25
    ),
    ShadowCostType.OPTIONALITY_LOSS: ShadowCostDefinition(
        cost_type=ShadowCostType.OPTIONALITY_LOSS,
        description="Closing future paths through commitments",
        measurement="reversibility_score + lock_in_count",
        sources=[
            "commitment reversibility assessment (1-5 scale)",
            "count of irreversible decisions in last 30 days"
        ],
        threshold_warning=3,
        threshold_critical=5
    ),
    ShadowCostType.COMPLEXITY_CREEP: ShadowCostDefinition(
        cost_type=ShadowCostType.COMPLEXITY_CREEP,
        description="Incremental additions exceeding coherence capacity",
        measurement="entity_count + connection_density + rule_count",
        sources=[
            "COUNT(*) from apprentices + assistants + modules",
            "relationships / entity_count",
            "COUNT of rules in rules.yaml"
        ],
        threshold_warning=1.2,  # Ratio of complexity to capacity
        threshold_critical=1.5
    )
}


@dataclass
class ShadowCost:
    """A calculated shadow cost for a specific action."""
    cost_type: ShadowCostType
    value: float                # The calculated cost value
    threshold_warning: float    # Warning threshold from definition
    threshold_critical: float   # Critical threshold from definition
    sources_used: List[str]     # Which data sources were used
    calculation_notes: str      # How the cost was calculated
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def status(self) -> str:
        """Get status: ok, warning, or critical."""
        # For trust decay, the thresholds are negative
        if self.cost_type == ShadowCostType.TRUST_DECAY:
            if self.value <= self.threshold_critical:
                return "critical"
            elif self.value <= self.threshold_warning:
                return "warning"
            return "ok"
        else:
            if self.value >= self.threshold_critical:
                return "critical"
            elif self.value >= self.threshold_warning:
                return "warning"
            return "ok"
    
    @property
    def is_critical(self) -> bool:
        return self.status == "critical"
    
    @property
    def is_warning(self) -> bool:
        return self.status == "warning"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cost_type": self.cost_type.name,
            "value": self.value,
            "status": self.status,
            "threshold_warning": self.threshold_warning,
            "threshold_critical": self.threshold_critical,
            "sources_used": self.sources_used,
            "calculation_notes": self.calculation_notes,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ShadowCostResult:
    """Result of shadow cost calculation for an action."""
    action: str
    costs: Dict[ShadowCostType, ShadowCost]
    total_shadow_cost: float    # Weighted sum of all costs
    total_benefit: float        # Expected benefit of the action
    shadow_cost_ratio: float    # total_shadow_cost / total_benefit
    recommendation: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def exceeds_benefit(self) -> bool:
        """Do shadow costs exceed the benefits?"""
        return self.shadow_cost_ratio > 1.0
    
    @property
    def has_critical_costs(self) -> bool:
        """Are any costs at critical level?"""
        return any(c.is_critical for c in self.costs.values())
    
    @property
    def has_warnings(self) -> bool:
        """Are any costs at warning level?"""
        return any(c.is_warning for c in self.costs.values())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "costs": {k.name: v.to_dict() for k, v in self.costs.items()},
            "total_shadow_cost": self.total_shadow_cost,
            "total_benefit": self.total_benefit,
            "shadow_cost_ratio": self.shadow_cost_ratio,
            "exceeds_benefit": self.exceeds_benefit,
            "has_critical_costs": self.has_critical_costs,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp.isoformat()
        }


class ShadowCostTracker:
    """
    Tracks and calculates shadow costs for actions.
    
    Makes the invisible visible. Every action has costs beyond the obvious.
    """
    
    # Weights for combining shadow costs
    WEIGHTS = {
        ShadowCostType.STRESS_ACCUMULATION: 0.35,
        ShadowCostType.TRUST_DECAY: 0.30,
        ShadowCostType.OPTIONALITY_LOSS: 0.20,
        ShadowCostType.COMPLEXITY_CREEP: 0.15
    }
    
    def __init__(self):
        self.history: List[ShadowCostResult] = []
    
    def calculate(
        self,
        action: str,
        context: Dict[str, Any],
        expected_benefit: float = 1.0
    ) -> ShadowCostResult:
        """
        Calculate shadow costs for a proposed action.
        
        Args:
            action: Description of the action
            context: Current system state including:
                - steward_stress: Current stress level
                - steward_coherence: Current coherence
                - recent_conflicts: Count of recent conflicts/misalignments
                - commitment_count: Number of active commitments
                - reversibility: How reversible is this action (0-1)
                - entity_count: Number of active entities
                - adds_complexity: Whether this adds complexity
            expected_benefit: Expected benefit (for ratio calculation)
        
        Returns:
            ShadowCostResult with all calculated costs and recommendation
        """
        costs = {}
        
        # Calculate each shadow cost
        costs[ShadowCostType.STRESS_ACCUMULATION] = self._calculate_stress_cost(context)
        costs[ShadowCostType.TRUST_DECAY] = self._calculate_trust_cost(context)
        costs[ShadowCostType.OPTIONALITY_LOSS] = self._calculate_optionality_cost(context)
        costs[ShadowCostType.COMPLEXITY_CREEP] = self._calculate_complexity_cost(context)
        
        # Calculate weighted total
        total_shadow_cost = 0
        for cost_type, cost in costs.items():
            # Normalize to 0-1 scale based on critical threshold
            definition = SHADOW_COST_DEFINITIONS[cost_type]
            if cost_type == ShadowCostType.TRUST_DECAY:
                # Trust decay is negative, so invert
                normalized = abs(cost.value) / abs(definition.threshold_critical)
            else:
                normalized = cost.value / definition.threshold_critical
            total_shadow_cost += normalized * self.WEIGHTS[cost_type]
        
        # Calculate ratio
        shadow_cost_ratio = total_shadow_cost / max(0.01, expected_benefit)
        
        # Generate recommendation
        if shadow_cost_ratio > 1.5:
            recommendation = "BLOCK: Shadow costs significantly exceed benefits. Do not proceed."
        elif shadow_cost_ratio > 1.0:
            recommendation = "FLAG: Shadow costs exceed benefits. Requires explicit review."
        elif any(c.is_critical for c in costs.values()):
            recommendation = "FLAG: Critical shadow cost detected. Address before proceeding."
        elif any(c.is_warning for c in costs.values()):
            recommendation = "CAUTION: Warning-level shadow costs. Monitor closely."
        else:
            recommendation = "OK: Shadow costs within acceptable range."
        
        result = ShadowCostResult(
            action=action,
            costs=costs,
            total_shadow_cost=total_shadow_cost,
            total_benefit=expected_benefit,
            shadow_cost_ratio=shadow_cost_ratio,
            recommendation=recommendation
        )
        
        self.history.append(result)
        
        if result.exceeds_benefit:
            logger.warning(f"Shadow costs exceed benefit for '{action}': ratio={shadow_cost_ratio:.2f}")
        
        return result
    
    def _calculate_stress_cost(self, context: Dict[str, Any]) -> ShadowCost:
        """Calculate stress accumulation cost."""
        definition = SHADOW_COST_DEFINITIONS[ShadowCostType.STRESS_ACCUMULATION]
        
        sources_used = []
        value = 0.0
        notes = []
        
        # Get current stress
        current_stress = context.get("steward_stress", 50)
        sources_used.append("steward_stress")
        
        # Base cost is current stress
        value = current_stress
        notes.append(f"Current stress: {current_stress}")
        
        # Add stress delta if action increases stress
        stress_impact = context.get("stress_impact", 0)
        if stress_impact > 0:
            value += stress_impact * 0.5
            notes.append(f"Action stress impact: +{stress_impact}")
            sources_used.append("stress_impact")
        
        # Add compounding factor for sustained high stress
        stress_duration = context.get("high_stress_days", 0)
        if stress_duration > 0:
            compound = stress_duration * 3
            value += compound
            notes.append(f"Sustained stress compound: +{compound}")
            sources_used.append("high_stress_days")
        
        return ShadowCost(
            cost_type=ShadowCostType.STRESS_ACCUMULATION,
            value=min(100, value),
            threshold_warning=definition.threshold_warning,
            threshold_critical=definition.threshold_critical,
            sources_used=sources_used,
            calculation_notes="; ".join(notes)
        )
    
    def _calculate_trust_cost(self, context: Dict[str, Any]) -> ShadowCost:
        """Calculate trust decay cost."""
        definition = SHADOW_COST_DEFINITIONS[ShadowCostType.TRUST_DECAY]
        
        sources_used = []
        value = 0.0  # Trust decay is measured as negative value
        notes = []
        
        # Recent conflicts or misalignments
        conflicts = context.get("recent_conflicts", 0)
        if conflicts > 0:
            decay = conflicts * -5
            value += decay
            notes.append(f"Recent conflicts: {conflicts} (decay: {decay})")
            sources_used.append("recent_conflicts")
        
        # Unmet commitments
        unmet = context.get("unmet_commitments", 0)
        if unmet > 0:
            decay = unmet * -8
            value += decay
            notes.append(f"Unmet commitments: {unmet} (decay: {decay})")
            sources_used.append("unmet_commitments")
        
        # Communication delays
        avg_delay = context.get("avg_response_delay_hours", 0)
        if avg_delay > 24:
            decay = (avg_delay - 24) * -0.5
            value += decay
            notes.append(f"Response delays (decay: {decay:.1f})")
            sources_used.append("avg_response_delay_hours")
        
        if not notes:
            notes.append("No significant trust decay factors")
        
        return ShadowCost(
            cost_type=ShadowCostType.TRUST_DECAY,
            value=value,
            threshold_warning=definition.threshold_warning,
            threshold_critical=definition.threshold_critical,
            sources_used=sources_used,
            calculation_notes="; ".join(notes)
        )
    
    def _calculate_optionality_cost(self, context: Dict[str, Any]) -> ShadowCost:
        """Calculate optionality loss cost."""
        definition = SHADOW_COST_DEFINITIONS[ShadowCostType.OPTIONALITY_LOSS]
        
        sources_used = []
        value = 0.0
        notes = []
        
        # How reversible is this action?
        reversibility = context.get("reversibility", 1.0)  # 0 = irreversible, 1 = fully reversible
        if reversibility < 1.0:
            loss = (1 - reversibility) * 3
            value += loss
            notes.append(f"Irreversibility: {(1-reversibility)*100:.0f}% (loss: {loss:.1f})")
            sources_used.append("reversibility")
        
        # Active commitments
        commitments = context.get("active_commitments", 0)
        if commitments > 3:
            loss = (commitments - 3) * 0.5
            value += loss
            notes.append(f"Active commitments: {commitments} (loss: {loss:.1f})")
            sources_used.append("active_commitments")
        
        # Lock-in decisions
        lock_ins = context.get("lock_in_count", 0)
        if lock_ins > 0:
            loss = lock_ins * 1.0
            value += loss
            notes.append(f"Lock-in decisions: {lock_ins} (loss: {loss:.1f})")
            sources_used.append("lock_in_count")
        
        if not notes:
            notes.append("No significant optionality loss")
        
        return ShadowCost(
            cost_type=ShadowCostType.OPTIONALITY_LOSS,
            value=value,
            threshold_warning=definition.threshold_warning,
            threshold_critical=definition.threshold_critical,
            sources_used=sources_used,
            calculation_notes="; ".join(notes)
        )
    
    def _calculate_complexity_cost(self, context: Dict[str, Any]) -> ShadowCost:
        """Calculate complexity creep cost."""
        definition = SHADOW_COST_DEFINITIONS[ShadowCostType.COMPLEXITY_CREEP]
        
        sources_used = []
        value = 0.0
        notes = []
        
        # Entity count
        entity_count = context.get("entity_count", 0)
        capacity = context.get("steward_capacity", 10)  # How many entities steward can handle
        if entity_count > 0:
            ratio = entity_count / max(1, capacity)
            value = ratio
            notes.append(f"Entity/capacity ratio: {entity_count}/{capacity} = {ratio:.2f}")
            sources_used.append("entity_count")
            sources_used.append("steward_capacity")
        
        # Adds complexity?
        if context.get("adds_complexity", False):
            complexity_delta = context.get("complexity_delta", 0.1)
            value += complexity_delta
            notes.append(f"Action adds complexity: +{complexity_delta}")
            sources_used.append("adds_complexity")
        
        # Connection density
        connection_density = context.get("connection_density", 0)
        if connection_density > 2:  # More than 2 connections per entity on average
            excess = (connection_density - 2) * 0.2
            value += excess
            notes.append(f"Connection density: {connection_density} (excess: +{excess:.2f})")
            sources_used.append("connection_density")
        
        if not notes:
            notes.append("Complexity within capacity")
        
        return ShadowCost(
            cost_type=ShadowCostType.COMPLEXITY_CREEP,
            value=value,
            threshold_warning=definition.threshold_warning,
            threshold_critical=definition.threshold_critical,
            sources_used=sources_used,
            calculation_notes="; ".join(notes)
        )
    
    def get_history(self, limit: int = 20) -> List[ShadowCostResult]:
        """Get recent shadow cost calculations."""
        return self.history[-limit:]
    
    def get_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get all shadow cost definitions."""
        return {
            cost_type.name: {
                "description": d.description,
                "measurement": d.measurement,
                "sources": d.sources,
                "threshold_warning": d.threshold_warning,
                "threshold_critical": d.threshold_critical
            }
            for cost_type, d in SHADOW_COST_DEFINITIONS.items()
        }


# Singleton instance
_shadow_cost_tracker: Optional[ShadowCostTracker] = None


def get_shadow_cost_tracker() -> ShadowCostTracker:
    """Get the singleton ShadowCostTracker."""
    global _shadow_cost_tracker
    if _shadow_cost_tracker is None:
        _shadow_cost_tracker = ShadowCostTracker()
    return _shadow_cost_tracker


def calculate_shadow_costs(
    action: str,
    context: Dict[str, Any],
    expected_benefit: float = 1.0
) -> ShadowCostResult:
    """
    Convenience function to calculate shadow costs.
    
    Usage:
        result = calculate_shadow_costs(
            "Launch new apprentice program",
            {
                "steward_stress": 55,
                "adds_complexity": True,
                "reversibility": 0.7
            },
            expected_benefit=2.0
        )
        if result.exceeds_benefit:
            print(f"Shadow costs exceed benefit: {result.shadow_cost_ratio:.2f}")
    """
    return get_shadow_cost_tracker().calculate(action, context, expected_benefit)


