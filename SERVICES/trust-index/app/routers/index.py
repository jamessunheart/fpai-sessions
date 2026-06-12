"""Trust Index endpoints."""
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional

from ..calculator import (
    calculate_trust_index, get_cached_trust_index,
    get_policy, get_policy_posture, get_policy_parameters
)
from ..models import (
    TrustIndexResponse, PolicyResponse, HistoryResponse, HistoryEntry,
    SimulationRequest, SimulationResponse, PolicyPosture
)
from ..config import settings, GUARDRAILS

router = APIRouter(prefix="/api/trust-index", tags=["trust-index"])


@router.get("", response_model=TrustIndexResponse)
async def get_trust_index(
    force_refresh: bool = Query(False, description="Force recalculation")
):
    """Get current Trust Index and components."""
    
    # Check cache first
    if not force_refresh:
        cached = get_cached_trust_index()
        if cached:
            return cached
    
    # Calculate fresh - REAL DATA from Credits Gateway
    return await calculate_trust_index(use_mocks=False)


@router.get("/policy", response_model=PolicyResponse)
async def get_current_policy():
    """Get current policy parameters based on Trust Index."""
    
    # Get current Trust Index
    cached = get_cached_trust_index()
    if not cached:
        cached = await calculate_trust_index(use_mocks=False)
    
    return get_policy(cached.trust_index)


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    period: str = Query("7d", regex="^(1d|7d|30d|90d)$"),
    granularity: str = Query("daily", regex="^(hourly|daily)$")
):
    """Get historical Trust Index values."""
    
    # Generate mock history for now
    entries = []
    
    now = datetime.utcnow()
    days = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}[period]
    
    for i in range(days):
        timestamp = now - timedelta(days=i)
        # Generate slightly varying values
        base = 0.65
        variation = (i % 5) * 0.03
        trust_index = round(base + variation, 3)
        
        entries.append(HistoryEntry(
            timestamp=timestamp,
            trust_index=trust_index,
            posture=get_policy_posture(trust_index),
            components={
                "solvency": round(0.85 + variation, 3),
                "commons_health": round(0.60 + variation, 3),
                "participation": round(0.55 + variation, 3)
            }
        ))
    
    return HistoryResponse(
        period=period,
        granularity=granularity,
        entries=entries
    )


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_trust_index(request: SimulationRequest):
    """Simulate Trust Index under hypothetical conditions."""
    
    # Start with current values
    cached = get_cached_trust_index()
    if not cached:
        cached = await calculate_trust_index(use_mocks=False)
    
    # Apply overrides
    solvency = cached.components["solvency"].score
    commons = cached.components["commons_health"].score
    participation = cached.components["participation"].score
    
    if request.ths_override is not None:
        solvency = min(1.0, request.ths_override / 1.5)
    
    if request.reserve_ratio_override is not None:
        commons = min(1.0, request.reserve_ratio_override / 2.0)
    
    if request.active_ratio_override is not None:
        participation = min(1.0, request.active_ratio_override)
    
    # Calculate simulated index
    simulated_index = round(
        solvency * settings.WEIGHT_SOLVENCY +
        commons * settings.WEIGHT_COMMONS_HEALTH +
        participation * settings.WEIGHT_PARTICIPATION,
        3
    )
    
    posture = get_policy_posture(simulated_index)
    parameters = get_policy_parameters(posture)
    
    return SimulationResponse(
        simulated_trust_index=simulated_index,
        simulated_posture=posture,
        components={
            "solvency": round(solvency, 3),
            "commons_health": round(commons, 3),
            "participation": round(participation, 3)
        },
        parameters=parameters
    )


@router.get("/guardrails")
async def get_guardrails():
    """Get hard guardrails that cannot be overridden."""
    return {
        "guardrails": GUARDRAILS,
        "description": "These limits cannot be overridden by AI systems",
        "human_override": "Always available via Trustee or Church council"
    }

