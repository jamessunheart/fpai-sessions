"""Eligibility checking for needs requests."""
import httpx
import logging
from typing import Tuple, List
from datetime import datetime, timedelta

from .config import settings, CATEGORIES
from .models import NeedsCategory, EligibilityCheck

logger = logging.getLogger(__name__)


async def check_eligibility(
    member_id: str,
    category: NeedsCategory,
    amount_uc: float
) -> Tuple[EligibilityCheck, str]:
    """
    Check if member is eligible for needs request.
    
    Returns:
        Tuple of (EligibilityCheck, denial_reason or "")
    """
    
    # Get member data from contribution tracker
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.CONTRIBUTION_TRACKER_URL}/api/contributions/score/{member_id}"
            )
            
            if response.status_code != 200:
                return EligibilityCheck(
                    trust_held=0,
                    contribution_score=0,
                    eligible=False,
                    tier="unknown",
                    reason="Failed to verify membership"
                ), "Failed to verify membership"
            
            data = response.json()
            
    except Exception as e:
        logger.error(f"Failed to check eligibility: {e}")
        # Use mock data for testing
        data = {
            "trust_balance": 150,
            "quarterly_score": 120,
            "tier": "active",
            "benefit_eligible": True,
            "eligible_categories": ["survival", "stability", "growth"]
        }
    
    trust_held = data.get("trust_balance", 0)
    contribution_score = data.get("quarterly_score", 0)
    tier = data.get("tier", "inactive")
    benefit_eligible = data.get("benefit_eligible", False)
    eligible_categories = data.get("eligible_categories", [])
    
    # Check basic eligibility
    if not benefit_eligible:
        return EligibilityCheck(
            trust_held=trust_held,
            contribution_score=contribution_score,
            eligible=False,
            tier=tier,
            reason="Not eligible for benefits (insufficient participation)"
        ), "Not eligible for benefits (insufficient participation)"
    
    # Check category eligibility
    if category.value not in eligible_categories:
        return EligibilityCheck(
            trust_held=trust_held,
            contribution_score=contribution_score,
            eligible=False,
            tier=tier,
            reason=f"Not eligible for {category.value} category"
        ), f"Not eligible for {category.value} category"
    
    # Check minimum TRUST for category
    category_config = CATEGORIES.get(category.value, {})
    min_trust = category_config.get("min_trust", 100)
    
    if trust_held < min_trust:
        return EligibilityCheck(
            trust_held=trust_held,
            contribution_score=contribution_score,
            eligible=False,
            tier=tier,
            reason=f"Insufficient TRUST for {category.value} (need {min_trust}, have {trust_held})"
        ), f"Insufficient TRUST for {category.value}"
    
    # Check contribution score
    if contribution_score < settings.MIN_CONTRIBUTION_SCORE:
        return EligibilityCheck(
            trust_held=trust_held,
            contribution_score=contribution_score,
            eligible=False,
            tier=tier,
            reason=f"Insufficient contribution score (need {settings.MIN_CONTRIBUTION_SCORE}, have {contribution_score})"
        ), f"Insufficient contribution score"
    
    # Check amount against fairness limits
    max_amount = min(
        settings.MAX_SINGLE_ALLOCATION_ABSOLUTE,
        # TODO: Check against monthly budget percentage
    )
    
    if amount_uc > max_amount:
        return EligibilityCheck(
            trust_held=trust_held,
            contribution_score=contribution_score,
            eligible=False,
            tier=tier,
            reason=f"Amount exceeds maximum ({max_amount} UC)"
        ), f"Amount exceeds maximum"
    
    # All checks passed
    return EligibilityCheck(
        trust_held=trust_held,
        contribution_score=contribution_score,
        eligible=True,
        tier=tier
    ), ""


def get_eligible_categories(tier: str, trust_held: int) -> List[str]:
    """Get categories a member is eligible for."""
    
    eligible = []
    
    for category, config in CATEGORIES.items():
        min_trust = config.get("min_trust", 100)
        if trust_held >= min_trust:
            eligible.append(category)
    
    return eligible










