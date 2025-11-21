"""
Pydantic models for API request/response validation
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Request Models

class PauseRequest(BaseModel):
    """Request to manually pause the system"""
    reason: str = Field(..., description="Reason for pausing")
    authorization: str = Field(..., description="Admin authorization signature")


class ResumeRequest(BaseModel):
    """Request to resume system operations"""
    authorization: str = Field(..., description="Admin authorization signature")
    governance_verified: bool = Field(..., description="Confirm governance is verified >51%")


# Response Models

class GuardianStatusResponse(BaseModel):
    """Current guardian monitoring status"""
    monitoring_active: bool
    last_check: Optional[datetime]
    check_interval_seconds: int
    current_holder_control: float
    governance_level: str  # excellent|good|acceptable|caution|warning|critical
    system_status: str  # operational|redemptions_paused|fully_paused
    paused: bool
    alerts_active: int


class GovernanceMetricsResponse(BaseModel):
    """Current governance metrics from voting-weight-tracker"""
    holder_control_percentage: float
    total_votes: int
    holder_votes: int
    seller_votes: int
    threshold_level: str
    margin_above_critical: float
    is_stable: bool
    last_updated: datetime


class AlertResponse(BaseModel):
    """Individual governance alert"""
    id: int
    timestamp: datetime
    alert_type: str  # caution|warning|critical|emergency
    holder_control: float
    message: str
    action_taken: str
    resolved: bool
    resolved_at: Optional[datetime]


class AlertHistoryResponse(BaseModel):
    """Alert history"""
    alerts: List[AlertResponse]


class GovernanceEventResponse(BaseModel):
    """Individual governance event in audit log"""
    id: int
    timestamp: datetime
    event_type: str  # governance_check|threshold_crossed|pause|resume
    holder_control: float
    threshold_level: str
    action: str  # none|alert|pause|resume
    details: Optional[str]


class GovernanceEventsResponse(BaseModel):
    """Governance event audit log"""
    events: List[GovernanceEventResponse]


class PauseResponse(BaseModel):
    """Response after pausing system"""
    paused: bool
    paused_at: datetime
    reason: str
    resume_requires: str


class ResumeResponse(BaseModel):
    """Response after resuming system"""
    paused: bool
    resumed_at: datetime
    current_holder_control: float
    safe_to_resume: bool


class SystemRulesResponse(BaseModel):
    """System governance rules and thresholds"""
    critical_threshold: float
    warning_threshold: float
    caution_threshold: float
    pause_redemptions_at: float
    pause_system_at: float
    monitoring_interval_normal: int
    monitoring_interval_caution: int
    monitoring_interval_critical: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str  # "healthy" or "unhealthy"
    monitoring_active: bool
    voting_tracker_connected: bool
    database: str  # "connected" or "error"
    last_governance_check: Optional[datetime]
    seconds_since_last_check: Optional[float]
