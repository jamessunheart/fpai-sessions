"""
ARIA GOVERNANCE FRAMEWORK
=========================

The governance layer that transforms Aria from a tool into a principled partner.
Based on Apprentice OS - embedding coherence, circulation, and resilience into every decision.

This is Aria's first apprentice task: learning governance by implementing it.
"""

from .principles import (
    PriorityStack,
    Priority,
    evaluate_priority,
    get_priority_stack,
)

from .three_nevers import (
    ThreeNevers,
    NeverViolation,
    check_never_constraints,
    get_never_checker,
)

from .steward_state import (
    StewardState,
    StewardMetrics,
    get_steward_state,
    update_steward_state,
)

from .shadow_costs import (
    ShadowCost,
    ShadowCostType,
    calculate_shadow_costs,
    get_shadow_cost_tracker,
)

from .decision_engine import (
    DecisionEngine,
    Decision,
    DecisionType,
    evaluate_action,
    get_decision_engine,
)

__all__ = [
    # Principles
    "PriorityStack",
    "Priority",
    "evaluate_priority",
    "get_priority_stack",
    # Three Nevers
    "ThreeNevers",
    "NeverViolation",
    "check_never_constraints",
    "get_never_checker",
    # Steward State
    "StewardState",
    "StewardMetrics",
    "get_steward_state",
    "update_steward_state",
    # Shadow Costs
    "ShadowCost",
    "ShadowCostType",
    "calculate_shadow_costs",
    "get_shadow_cost_tracker",
    # Decision Engine
    "DecisionEngine",
    "Decision",
    "DecisionType",
    "evaluate_action",
    "get_decision_engine",
]

# Governance version - tracks Aria's evolution through the apprentice loop
__version__ = "0.1.0"
__phase__ = "alignment"  # Phase 1 of Aria's apprentice journey


