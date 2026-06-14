"""
SHADOW COSTS COMPUTATION
========================

Makes invisible costs measurable and instrumentable.

Four shadow costs:
1. stress_accumulation - Compound pressure on steward nervous system
2. trust_decay - Erosion of relational capital
3. optionality_loss - Closing future paths through commitments
4. complexity_creep - Incremental additions exceeding coherence capacity

Usage:
    from governance.shadow_costs_compute import compute_all_shadow_costs
    
    costs = await compute_all_shadow_costs()
    if costs["stress_accumulation"] > 60:
        # Take action
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("aria.governance.shadow_costs")

# Thresholds from ontology
THRESHOLDS_PATH = Path("/opt/fpai/apprentice-os/core/decision-engine/thresholds.json")


@dataclass
class ShadowCostResult:
    """Result of a shadow cost computation."""
    value: float
    threshold_warning: float
    threshold_critical: float
    status: str  # healthy, warning, critical
    details: Dict[str, Any]
    computed_at: str


def load_thresholds() -> Dict[str, Any]:
    """Load thresholds from ontology."""
    try:
        if THRESHOLDS_PATH.exists():
            with open(THRESHOLDS_PATH) as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load thresholds: {e}")
    
    # Defaults
    return {
        "shadow_costs": {
            "stress_accumulation": {"warning": 60, "critical": 80},
            "trust_decay": {"warning": -10, "critical": -25},
            "optionality_loss": {"warning": 30, "critical": 50},
            "complexity_creep": {"warning": 1.2, "critical": 1.5}
        }
    }


async def compute_stress_accumulation(
    self_reported_stress: Optional[float] = None,
    override_count: int = 0,
    decision_count: int = 1,
    response_gaps_24h: int = 0
) -> ShadowCostResult:
    """
    Compute stress accumulation shadow cost.
    
    Formula:
        (self_report * 0.4) + (interaction_pattern_score * 0.3) + (decision_quality_delta * 0.3)
    
    Args:
        self_reported_stress: Manual stress level input (0-100)
        override_count: Number of rule overrides recently
        decision_count: Total decisions made
        response_gaps_24h: Number of 24h+ response gaps
    """
    thresholds = load_thresholds()["shadow_costs"]["stress_accumulation"]
    
    # Default stress if not reported
    stress = self_reported_stress if self_reported_stress is not None else 50
    
    # Interaction pattern score
    interaction_score = (response_gaps_24h * 10) + (override_count * 5)
    interaction_score = min(100, interaction_score)  # Cap at 100
    
    # Decision quality delta (higher override rate = worse quality)
    override_rate = override_count / max(decision_count, 1)
    quality_delta = override_rate * 100  # 0-100 scale
    
    # Final computation
    value = (stress * 0.4) + (interaction_score * 0.3) + (quality_delta * 0.3)
    
    # Determine status
    if value >= thresholds["critical"]:
        status = "critical"
    elif value >= thresholds["warning"]:
        status = "warning"
    else:
        status = "healthy"
    
    return ShadowCostResult(
        value=round(value, 2),
        threshold_warning=thresholds["warning"],
        threshold_critical=thresholds["critical"],
        status=status,
        details={
            "self_reported_stress": stress,
            "interaction_pattern_score": interaction_score,
            "decision_quality_delta": quality_delta,
            "override_rate": override_rate,
            "response_gaps_24h": response_gaps_24h
        },
        computed_at=datetime.utcnow().isoformat()
    )


async def compute_trust_decay(
    current_trust: float = 85,
    previous_trust: float = 85,
    avg_response_time_hours: float = 1,
    clarification_count: int = 0,
    total_interactions: int = 10
) -> ShadowCostResult:
    """
    Compute trust decay shadow cost.
    
    Formula:
        (latency_score * 0.25) + (friction_score * 0.35) + (feedback_delta * 0.4)
    
    A negative result indicates trust is decaying.
    """
    thresholds = load_thresholds()["shadow_costs"]["trust_decay"]
    
    # Latency score (expected = 2 hours)
    expected_response = 2
    latency_score = (avg_response_time_hours / expected_response - 1) * 50
    latency_score = max(-50, min(50, latency_score))  # Clamp
    
    # Friction score
    friction_rate = clarification_count / max(total_interactions, 1)
    friction_score = friction_rate * 100
    
    # Feedback delta (trust change)
    feedback_delta = current_trust - previous_trust
    
    # Final computation (negative = decay)
    value = -(latency_score * 0.25) - (friction_score * 0.35) + (feedback_delta * 0.4)
    
    # Determine status
    if value <= thresholds["critical"]:
        status = "critical"
    elif value <= thresholds["warning"]:
        status = "warning"
    else:
        status = "healthy"
    
    return ShadowCostResult(
        value=round(value, 2),
        threshold_warning=thresholds["warning"],
        threshold_critical=thresholds["critical"],
        status=status,
        details={
            "latency_score": latency_score,
            "friction_score": friction_score,
            "feedback_delta": feedback_delta,
            "current_trust": current_trust,
            "previous_trust": previous_trust
        },
        computed_at=datetime.utcnow().isoformat()
    )


async def compute_optionality_loss(
    commitments: Optional[List[Dict]] = None,
    lock_in_count_30d: int = 0
) -> ShadowCostResult:
    """
    Compute optionality loss shadow cost.
    
    Formula:
        (5 - AVG(reversibility_scores)) * 20 + (lock_in_count * 10)
    
    Higher score = more optionality lost.
    
    Args:
        commitments: List of {"name": str, "reversibility": 1-5} where 5=easily reversible
        lock_in_count_30d: Irreversible decisions in last 30 days
    """
    thresholds = load_thresholds()["shadow_costs"]["optionality_loss"]
    
    # Default commitments if none provided
    if commitments is None:
        commitments = []
    
    # Calculate average reversibility
    if commitments:
        avg_reversibility = sum(c.get("reversibility", 3) for c in commitments) / len(commitments)
    else:
        avg_reversibility = 5  # No commitments = full optionality
    
    # Final computation
    value = (5 - avg_reversibility) * 20 + (lock_in_count_30d * 10)
    
    # Determine status
    if value >= thresholds["critical"]:
        status = "critical"
    elif value >= thresholds["warning"]:
        status = "warning"
    else:
        status = "healthy"
    
    return ShadowCostResult(
        value=round(value, 2),
        threshold_warning=thresholds["warning"],
        threshold_critical=thresholds["critical"],
        status=status,
        details={
            "avg_reversibility": avg_reversibility,
            "commitment_count": len(commitments),
            "lock_in_count_30d": lock_in_count_30d
        },
        computed_at=datetime.utcnow().isoformat()
    )


async def compute_complexity_creep(
    entity_count: Optional[int] = None,
    relationship_count: Optional[int] = None,
    rule_count: int = 20,
    baseline_complexity: float = 1.0
) -> ShadowCostResult:
    """
    Compute complexity creep shadow cost.
    
    Formula:
        current_complexity / baseline_complexity
        where current_complexity = entity_count * (1 + connection_density) * log(rule_count)
    
    Result is a ratio (1.0 = at baseline).
    """
    import math
    
    thresholds = load_thresholds()["shadow_costs"]["complexity_creep"]
    
    # Try to count entities from ontology
    if entity_count is None:
        entity_count = await _count_entities()
    
    if relationship_count is None:
        relationship_count = await _count_relationships()
    
    # Connection density
    connection_density = relationship_count / max(entity_count, 1)
    
    # Current complexity
    current_complexity = entity_count * (1 + connection_density) * math.log(max(rule_count, 1))
    
    # Baseline (if not provided, use current as baseline on first run)
    if baseline_complexity == 0:
        baseline_complexity = current_complexity
    
    # Final computation (ratio)
    value = current_complexity / max(baseline_complexity, 1)
    
    # Determine status
    if value >= thresholds["critical"]:
        status = "critical"
    elif value >= thresholds["warning"]:
        status = "warning"
    else:
        status = "healthy"
    
    return ShadowCostResult(
        value=round(value, 3),
        threshold_warning=thresholds["warning"],
        threshold_critical=thresholds["critical"],
        status=status,
        details={
            "entity_count": entity_count,
            "relationship_count": relationship_count,
            "connection_density": connection_density,
            "rule_count": rule_count,
            "current_complexity": current_complexity,
            "baseline_complexity": baseline_complexity
        },
        computed_at=datetime.utcnow().isoformat()
    )


async def _count_entities() -> int:
    """Count entities from graph.json."""
    try:
        graph_path = Path("/opt/fpai/apprentice-os/active/graph.json")
        if graph_path.exists():
            with open(graph_path) as f:
                graph = json.load(f)
                return len(graph.get("nodes", []))
    except Exception as e:
        logger.warning(f"Could not count entities: {e}")
    return 5  # Default


async def _count_relationships() -> int:
    """Count relationships from graph.json."""
    try:
        graph_path = Path("/opt/fpai/apprentice-os/active/graph.json")
        if graph_path.exists():
            with open(graph_path) as f:
                graph = json.load(f)
                return len(graph.get("edges", []))
    except Exception as e:
        logger.warning(f"Could not count relationships: {e}")
    return 4  # Default


async def compute_all_shadow_costs(
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, ShadowCostResult]:
    """
    Compute all four shadow costs.
    
    Args:
        context: Optional context with values for computation:
            - self_reported_stress: float (0-100)
            - override_count: int
            - decision_count: int
            - current_trust: float
            - previous_trust: float
            - commitments: List[Dict]
            - etc.
    
    Returns:
        Dict with all four shadow costs
    """
    ctx = context or {}
    
    stress = await compute_stress_accumulation(
        self_reported_stress=ctx.get("self_reported_stress"),
        override_count=ctx.get("override_count", 0),
        decision_count=ctx.get("decision_count", 1),
        response_gaps_24h=ctx.get("response_gaps_24h", 0)
    )
    
    trust = await compute_trust_decay(
        current_trust=ctx.get("current_trust", 85),
        previous_trust=ctx.get("previous_trust", 85),
        avg_response_time_hours=ctx.get("avg_response_time_hours", 1),
        clarification_count=ctx.get("clarification_count", 0),
        total_interactions=ctx.get("total_interactions", 10)
    )
    
    optionality = await compute_optionality_loss(
        commitments=ctx.get("commitments"),
        lock_in_count_30d=ctx.get("lock_in_count_30d", 0)
    )
    
    complexity = await compute_complexity_creep(
        entity_count=ctx.get("entity_count"),
        relationship_count=ctx.get("relationship_count"),
        rule_count=ctx.get("rule_count", 20),
        baseline_complexity=ctx.get("baseline_complexity", 50)
    )
    
    return {
        "stress_accumulation": stress,
        "trust_decay": trust,
        "optionality_loss": optionality,
        "complexity_creep": complexity
    }


def format_shadow_costs_report(costs: Dict[str, ShadowCostResult]) -> str:
    """Format shadow costs as a human-readable report."""
    lines = ["## Shadow Costs Report", ""]
    
    status_emoji = {"healthy": "🟢", "warning": "🟡", "critical": "🔴"}
    
    for name, cost in costs.items():
        emoji = status_emoji.get(cost.status, "⚪")
        lines.append(f"### {name.replace('_', ' ').title()}")
        lines.append(f"{emoji} **Status:** {cost.status.upper()}")
        lines.append(f"**Value:** {cost.value}")
        lines.append(f"**Thresholds:** Warning: {cost.threshold_warning}, Critical: {cost.threshold_critical}")
        lines.append("")
    
    return "\n".join(lines)


