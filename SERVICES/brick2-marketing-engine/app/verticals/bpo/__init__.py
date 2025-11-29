"""
BPO Staffing & Referral Vertical
=================================

Philippine call center, VA staffing, and referral commission system.
Integrates with fullpotential.ai/missions for human task routing.
"""

from .commission import (
    calculate_commission,
    calculate_monthly_earnings,
    get_commission_rate,
    CommissionResult,
    ReferralPlacement,
)

__all__ = [
    "calculate_commission",
    "calculate_monthly_earnings", 
    "get_commission_rate",
    "CommissionResult",
    "ReferralPlacement",
]




