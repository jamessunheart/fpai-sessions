"""Trust Index calculator."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .config import settings, GUARDRAILS
from .models import (
    TrustIndexResponse, ComponentScore, PolicyPosture,
    PolicyParameters, PolicyResponse
)
from .sources.solvency import get_solvency_score, get_solvency_score_mock
from .sources.commons import get_commons_health_score
from .sources.participation import get_participation_score, get_participation_score_mock

logger = logging.getLogger(__name__)

# Cache
_cache: Dict[str, Any] = {
    "trust_index": None,
    "last_update": None
}


async def calculate_trust_index(use_mocks: bool = False) -> TrustIndexResponse:
    """
    Calculate the Trust Index from all components.
    
    Returns:
        TrustIndexResponse with full details
    """
    
    # Get component scores
    if use_mocks:
        solvency_score, solvency_details = await get_solvency_score_mock()
        participation_score, participation_details = await get_participation_score_mock()
    else:
        solvency_score, solvency_details = await get_solvency_score()
        participation_score, participation_details = await get_participation_score()
    
    commons_score, commons_details = await get_commons_health_score()
    
    # Calculate weighted Trust Index
    trust_index = (
        solvency_score * settings.WEIGHT_SOLVENCY +
        commons_score * settings.WEIGHT_COMMONS_HEALTH +
        participation_score * settings.WEIGHT_PARTICIPATION
    )
    
    # Round to 3 decimal places
    trust_index = round(trust_index, 3)
    
    # Determine policy posture
    posture = get_policy_posture(trust_index)
    
    # Build component details
    components = {
        "solvency": ComponentScore(
            score=round(solvency_score, 3),
            weight=settings.WEIGHT_SOLVENCY,
            contribution=round(solvency_score * settings.WEIGHT_SOLVENCY, 3),
            source="fp-credits-gateway",
            raw_value=solvency_details.get("raw_ths"),
            details=solvency_details
        ),
        "commons_health": ComponentScore(
            score=round(commons_score, 3),
            weight=settings.WEIGHT_COMMONS_HEALTH,
            contribution=round(commons_score * settings.WEIGHT_COMMONS_HEALTH, 3),
            source="commons-reserve",
            raw_value=commons_details.get("reserve_ratio"),
            details=commons_details
        ),
        "participation": ComponentScore(
            score=round(participation_score, 3),
            weight=settings.WEIGHT_PARTICIPATION,
            contribution=round(participation_score * settings.WEIGHT_PARTICIPATION, 3),
            source="contribution-tracker",
            raw_value=participation_details.get("active_ratio"),
            details=participation_details
        )
    }
    
    now = datetime.utcnow()
    next_update = now + timedelta(seconds=settings.UPDATE_INTERVAL)
    
    response = TrustIndexResponse(
        trust_index=trust_index,
        components=components,
        policy_posture=posture,
        timestamp=now,
        next_update=next_update
    )
    
    # Update cache
    _cache["trust_index"] = response
    _cache["last_update"] = now
    
    return response


def get_policy_posture(trust_index: float) -> PolicyPosture:
    """Get policy posture based on Trust Index."""
    
    if trust_index < settings.EMERGENCY_FREEZE_THRESHOLD:
        return PolicyPosture.EMERGENCY
    
    if trust_index < settings.THRESHOLD_CONSERVATIVE:
        return PolicyPosture.CONSERVATIVE
    
    if trust_index > settings.THRESHOLD_GENEROUS:
        return PolicyPosture.GENEROUS
    
    return PolicyPosture.BALANCED


def get_policy_parameters(posture: PolicyPosture) -> PolicyParameters:
    """Get policy parameters for a posture."""
    
    if posture == PolicyPosture.EMERGENCY:
        return PolicyParameters(
            safety_buffer=2.50,
            distribution_categories=[],
            max_single_allocation=0,
            daily_change_limit=0
        )
    
    if posture == PolicyPosture.CONSERVATIVE:
        return PolicyParameters(
            safety_buffer=2.00,
            distribution_categories=["survival"],
            max_single_allocation=0.02,
            daily_change_limit=0.02
        )
    
    if posture == PolicyPosture.GENEROUS:
        return PolicyParameters(
            safety_buffer=1.20,
            distribution_categories=["survival", "stability", "growth", "contribution", "infrastructure"],
            max_single_allocation=settings.MAX_SINGLE_ALLOCATION,
            daily_change_limit=settings.MAX_DAILY_CHANGE
        )
    
    # BALANCED
    return PolicyParameters(
        safety_buffer=1.50,
        distribution_categories=["survival", "stability"],
        max_single_allocation=0.03,
        daily_change_limit=0.03
    )


def get_policy(trust_index: float) -> PolicyResponse:
    """Get full policy response for a Trust Index."""
    
    posture = get_policy_posture(trust_index)
    parameters = get_policy_parameters(posture)
    
    return PolicyResponse(
        trust_index=trust_index,
        posture=posture,
        parameters=parameters,
        guardrails=GUARDRAILS
    )


def get_cached_trust_index() -> Optional[TrustIndexResponse]:
    """Get cached Trust Index if still valid."""
    
    if _cache["trust_index"] is None:
        return None
    
    last_update = _cache["last_update"]
    if last_update is None:
        return None
    
    # Check if cache is still valid
    age = (datetime.utcnow() - last_update).total_seconds()
    if age > settings.UPDATE_INTERVAL:
        return None
    
    return _cache["trust_index"]










