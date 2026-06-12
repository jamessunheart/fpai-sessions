"""Pydantic models for Trust Index Service."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class PolicyPosture(str, Enum):
    """Policy posture based on Trust Index."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    GENEROUS = "generous"
    EMERGENCY = "emergency"


class ComponentScore(BaseModel):
    """Score for a Trust Index component."""
    score: float = Field(..., ge=0, le=1)
    weight: float
    contribution: float
    source: str
    raw_value: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class TrustIndexResponse(BaseModel):
    """Full Trust Index response."""
    trust_index: float = Field(..., ge=0, le=1)
    components: Dict[str, ComponentScore]
    policy_posture: PolicyPosture
    timestamp: datetime
    next_update: Optional[datetime] = None


class PolicyParameters(BaseModel):
    """Policy parameters based on Trust Index."""
    safety_buffer: float
    distribution_categories: List[str]
    max_single_allocation: float
    daily_change_limit: float


class PolicyResponse(BaseModel):
    """Policy response."""
    trust_index: float
    posture: PolicyPosture
    parameters: PolicyParameters
    guardrails: Dict[str, Any]


class HistoryEntry(BaseModel):
    """Historical Trust Index entry."""
    timestamp: datetime
    trust_index: float
    posture: PolicyPosture
    components: Dict[str, float]


class HistoryResponse(BaseModel):
    """Historical data response."""
    period: str
    granularity: str
    entries: List[HistoryEntry]


class SimulationRequest(BaseModel):
    """Request to simulate Trust Index."""
    ths_override: Optional[float] = None
    reserve_ratio_override: Optional[float] = None
    active_ratio_override: Optional[float] = None


class SimulationResponse(BaseModel):
    """Simulation result."""
    simulated_trust_index: float
    simulated_posture: PolicyPosture
    components: Dict[str, float]
    parameters: PolicyParameters










