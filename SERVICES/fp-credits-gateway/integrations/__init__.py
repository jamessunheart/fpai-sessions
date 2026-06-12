"""
FP Credits Gateway - Integration Adapters

These adapters allow existing services to migrate to the unified credits gateway
without breaking their current functionality.

Available Adapters:
- WhiteRockCreditsAdapter: For WhiteRock API member/provider credits
- ContributorCreditsAdapter: For Autonomy Optimizer contributor rewards
"""

from .whiterock_adapter import WhiteRockCreditsAdapter
from .autonomy_adapter import (
    ContributorCreditsAdapter,
    CreditRate,
    RedemptionCost,
    on_key_contributed,
    on_key_used,
    on_server_contributed,
    on_task_completed
)

__all__ = [
    "WhiteRockCreditsAdapter",
    "ContributorCreditsAdapter",
    "CreditRate",
    "RedemptionCost",
    "on_key_contributed",
    "on_key_used",
    "on_server_contributed",
    "on_task_completed"
]


