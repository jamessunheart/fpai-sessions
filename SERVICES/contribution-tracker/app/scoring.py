"""Contribution scoring and tier calculation."""
from datetime import datetime
from typing import Optional, List, Tuple

from .config import settings
from .models import ContributionType, MemberTier


def get_current_quarter() -> str:
    """Get current quarter string (e.g., '2025-Q4')."""
    now = datetime.utcnow()
    quarter = (now.month - 1) // 3 + 1
    return f"{now.year}-Q{quarter}"


def calculate_trust_amount(
    contribution_type: ContributionType,
    hours: Optional[float] = None,
    amount: Optional[float] = None,
    custom_value: Optional[int] = None,
    is_founding_period: bool = False
) -> int:
    """Calculate TRUST amount for a contribution."""
    
    base_amount = 0
    
    if contribution_type == ContributionType.SERVICE:
        base_amount = int((hours or 0) * settings.TRUST_RATE_SERVICE_HOUR)
    
    elif contribution_type == ContributionType.GOVERNANCE:
        base_amount = settings.TRUST_RATE_GOVERNANCE_VOTE
    
    elif contribution_type == ContributionType.REFERRAL:
        base_amount = settings.TRUST_RATE_REFERRAL
    
    elif contribution_type == ContributionType.FINANCIAL:
        base_amount = int((amount or 0) * settings.TRUST_RATE_FINANCIAL_PER_UC)
    
    elif contribution_type == ContributionType.ART:
        base_amount = custom_value or 10  # Variable, default 10
    
    elif contribution_type == ContributionType.COMMUNITY:
        base_amount = custom_value or 10  # Variable, default 10
    
    # Apply founding multiplier if in founding period
    if is_founding_period:
        base_amount = int(base_amount * settings.FOUNDING_MULTIPLIER)
    
    return base_amount


def calculate_tier(quarterly_score: int, is_founder: bool = False) -> MemberTier:
    """Calculate member tier from quarterly score."""
    
    if is_founder:
        return MemberTier.FOUNDER
    
    if quarterly_score >= settings.TIER_ACTIVE_MIN:
        return MemberTier.ACTIVE
    
    if quarterly_score >= settings.TIER_ENGAGED_MIN:
        return MemberTier.ENGAGED
    
    return MemberTier.INACTIVE


def get_voting_multiplier(tier: MemberTier, quarterly_score: int) -> float:
    """Get voting multiplier based on tier and score."""
    
    if tier == MemberTier.FOUNDER:
        return 1.5
    
    if tier == MemberTier.INACTIVE:
        return 0.0
    
    if quarterly_score >= 200:
        return 2.0
    elif quarterly_score >= 150:
        return 1.5
    elif quarterly_score >= 100:
        return 1.0
    elif quarterly_score >= 50:
        return 0.5
    
    return 0.0


def get_eligible_categories(tier: MemberTier) -> List[str]:
    """Get benefit categories eligible for tier."""
    
    if tier == MemberTier.INACTIVE:
        return []
    
    if tier == MemberTier.ENGAGED:
        return ["survival"]
    
    # ACTIVE and FOUNDER get all categories
    return ["survival", "stability", "growth", "contribution", "infrastructure"]


def get_benefit_eligibility(tier: MemberTier) -> bool:
    """Check if tier is eligible for any benefits."""
    return tier != MemberTier.INACTIVE


def get_next_tier_info(tier: MemberTier, quarterly_score: int) -> Tuple[Optional[MemberTier], int]:
    """Get next tier and points needed."""
    
    if tier == MemberTier.FOUNDER:
        return None, 0
    
    if tier == MemberTier.ACTIVE:
        return None, 0  # Already at top non-founder tier
    
    if tier == MemberTier.ENGAGED:
        points_needed = settings.TIER_ACTIVE_MIN - quarterly_score
        return MemberTier.ACTIVE, max(0, points_needed)
    
    # INACTIVE
    points_needed = settings.TIER_ENGAGED_MIN - quarterly_score
    return MemberTier.ENGAGED, max(0, points_needed)


def get_verification_method(contribution_type: ContributionType) -> str:
    """Get verification method for contribution type."""
    
    methods = {
        ContributionType.SERVICE: "recipient_confirmation",
        ContributionType.GOVERNANCE: "automatic",
        ContributionType.ART: "platform_verification",
        ContributionType.REFERRAL: "member_activation",
        ContributionType.FINANCIAL: "payment_confirmation",
        ContributionType.COMMUNITY: "council_recognition"
    }
    
    return methods.get(contribution_type, "manual")


def is_auto_verified(contribution_type: ContributionType) -> bool:
    """Check if contribution type is auto-verified."""
    return contribution_type in [
        ContributionType.GOVERNANCE,
        ContributionType.FINANCIAL
    ]










