"""
BPO Referral Commission Calculator
==================================

Commission tiers based on OneBPO structure:
- $8 and below: 5.00%
- $8.01 to $8.49: 5.50%
- $8.50 to $9.99: 6.50%
- $10.00 to $11.99: 8.00%
- $12.00 and above: 10.00%
"""

from decimal import Decimal, ROUND_HALF_UP
from dataclasses import dataclass
from typing import List, Optional
from datetime import date


# Commission tier configuration
COMMISSION_TIERS = [
    {"max_rate": Decimal("8.00"), "commission": Decimal("0.0500")},
    {"max_rate": Decimal("8.49"), "commission": Decimal("0.0550")},
    {"max_rate": Decimal("9.99"), "commission": Decimal("0.0650")},
    {"max_rate": Decimal("11.99"), "commission": Decimal("0.0800")},
    {"max_rate": None, "commission": Decimal("0.1000")},  # $12+ gets 10%
]


@dataclass
class CommissionResult:
    """Result of commission calculation."""
    hourly_rate: Decimal
    hours_worked: Decimal
    gross_revenue: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    tier_description: str

    def to_dict(self) -> dict:
        return {
            "hourly_rate": float(self.hourly_rate),
            "hours_worked": float(self.hours_worked),
            "gross_revenue": float(self.gross_revenue),
            "commission_rate": f"{float(self.commission_rate) * 100:.2f}%",
            "commission_amount": float(self.commission_amount),
            "tier_description": self.tier_description
        }


@dataclass
class ReferralPlacement:
    """A referral placement with client and worker details."""
    referral_id: str
    client_name: str
    worker_name: Optional[str]
    hourly_rate: Decimal
    hours_per_month: Decimal
    start_date: date
    status: str = "active"


def get_commission_rate(hourly_rate: float | Decimal) -> Decimal:
    """
    Get commission rate based on hourly rate tier.
    
    Args:
        hourly_rate: The hourly rate for the placement
        
    Returns:
        Commission rate as a Decimal (e.g., 0.0650 for 6.50%)
    """
    rate = Decimal(str(hourly_rate))
    
    for tier in COMMISSION_TIERS:
        if tier["max_rate"] is None or rate <= tier["max_rate"]:
            return tier["commission"]
    
    # Default to highest tier
    return COMMISSION_TIERS[-1]["commission"]


def get_tier_description(hourly_rate: float | Decimal) -> str:
    """Get human-readable tier description."""
    rate = Decimal(str(hourly_rate))
    
    if rate <= Decimal("8.00"):
        return "$8.00 and below (5.00%)"
    elif rate <= Decimal("8.49"):
        return "$8.01 - $8.49 (5.50%)"
    elif rate <= Decimal("9.99"):
        return "$8.50 - $9.99 (6.50%)"
    elif rate <= Decimal("11.99"):
        return "$10.00 - $11.99 (8.00%)"
    else:
        return "$12.00 and above (10.00%)"


def calculate_commission(
    hourly_rate: float | Decimal,
    hours_worked: float | Decimal
) -> CommissionResult:
    """
    Calculate commission for a referral placement.
    
    Args:
        hourly_rate: The hourly rate for the placement
        hours_worked: Number of hours worked in the period
        
    Returns:
        CommissionResult with all calculation details
        
    Example:
        >>> result = calculate_commission(12.00, 160)
        >>> print(result.commission_amount)
        192.00
    """
    rate = Decimal(str(hourly_rate))
    hours = Decimal(str(hours_worked))
    
    gross_revenue = rate * hours
    commission_rate = get_commission_rate(rate)
    commission_amount = (gross_revenue * commission_rate).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    
    return CommissionResult(
        hourly_rate=rate,
        hours_worked=hours,
        gross_revenue=gross_revenue.quantize(Decimal("0.01")),
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        tier_description=get_tier_description(rate)
    )


def calculate_monthly_earnings(placements: List[ReferralPlacement]) -> dict:
    """
    Calculate total monthly earnings for a referrer from all placements.
    
    Args:
        placements: List of active placement referrals
        
    Returns:
        Summary of total earnings and per-placement breakdown
    """
    total_commission = Decimal("0.00")
    total_revenue = Decimal("0.00")
    breakdown = []
    
    for placement in placements:
        if placement.status != "active":
            continue
            
        result = calculate_commission(
            placement.hourly_rate,
            placement.hours_per_month
        )
        
        total_commission += result.commission_amount
        total_revenue += result.gross_revenue
        
        breakdown.append({
            "referral_id": placement.referral_id,
            "client": placement.client_name,
            "worker": placement.worker_name,
            "hourly_rate": float(placement.hourly_rate),
            "hours": float(placement.hours_per_month),
            "revenue": float(result.gross_revenue),
            "commission": float(result.commission_amount),
            "tier": result.tier_description
        })
    
    return {
        "total_gross_revenue": float(total_revenue),
        "total_commission": float(total_commission),
        "active_placements": len([p for p in placements if p.status == "active"]),
        "breakdown": breakdown,
        "annual_projection": float(total_commission * 12)
    }


def estimate_annual_income(placements: List[ReferralPlacement]) -> dict:
    """
    Estimate annual income from referral placements.
    
    Args:
        placements: List of referral placements
        
    Returns:
        Annual projection with various scenarios
    """
    monthly = calculate_monthly_earnings(placements)
    base_monthly = Decimal(str(monthly["total_commission"]))
    
    return {
        "current_monthly": float(base_monthly),
        "current_annual": float(base_monthly * 12),
        "with_10pct_growth": float(base_monthly * 12 * Decimal("1.10")),
        "with_20pct_growth": float(base_monthly * 12 * Decimal("1.20")),
        "placements_needed_for_1k_monthly": _placements_for_target(1000),
        "placements_needed_for_5k_monthly": _placements_for_target(5000),
    }


def _placements_for_target(target_monthly: float) -> int:
    """
    Estimate placements needed to reach a target monthly income.
    Assumes average $10/hr, 160 hours/month, 8% commission ($128/placement).
    """
    avg_commission_per_placement = 128  # $10/hr * 160hr * 8%
    return max(1, int(target_monthly / avg_commission_per_placement) + 1)


# Example usage and testing
if __name__ == "__main__":
    # Test single calculation
    print("=== Single Calculation ===")
    result = calculate_commission(12.00, 160)
    print(f"Rate: ${result.hourly_rate}/hr")
    print(f"Hours: {result.hours_worked}")
    print(f"Revenue: ${result.gross_revenue}")
    print(f"Commission: ${result.commission_amount} ({result.tier_description})")
    
    print("\n=== Multiple Placements ===")
    placements = [
        ReferralPlacement("REF001", "TechCorp Inc", "Maria Santos", Decimal("12.00"), Decimal("160"), date(2024, 1, 1)),
        ReferralPlacement("REF002", "StartupXYZ", "Juan Cruz", Decimal("10.00"), Decimal("80"), date(2024, 2, 1)),
        ReferralPlacement("REF003", "LocalBiz LLC", "Ana Reyes", Decimal("8.00"), Decimal("120"), date(2024, 3, 1)),
    ]
    
    earnings = calculate_monthly_earnings(placements)
    print(f"Total Monthly Commission: ${earnings['total_commission']:.2f}")
    print(f"Annual Projection: ${earnings['annual_projection']:.2f}")
    print(f"\nBreakdown:")
    for p in earnings['breakdown']:
        print(f"  - {p['client']}: ${p['commission']:.2f}/month ({p['tier']})")




