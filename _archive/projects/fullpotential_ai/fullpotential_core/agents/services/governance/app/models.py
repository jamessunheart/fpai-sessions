"""Data models for governance service"""
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from uuid import uuid4

class GovernanceDecision(BaseModel):
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    intent_id: str
    service_name: str

    # Alignment
    alignment_score: float  # 0-1
    aligned: bool  # True if score >= threshold (0.85)
    alignment_reasoning: str

    # Risk
    risk_level: str  # low, medium, high
    risk_factors: List[str] = []

    # Decision
    decision: str  # auto_approve, requires_approval, blocked
    policy_matched: str
    decision_reasoning: str

    # Recommendations
    recommendations: List[str] = []

    # Override
    overridden: bool = False
    override_decision: Optional[str] = None
    override_reason: Optional[str] = None
    overridden_by: Optional[str] = None
    overridden_at: Optional[datetime] = None

    # Metadata
    decided_at: datetime = Field(default_factory=datetime.now)
    claude_api_cost: float = 0.0
    processing_time_ms: int = 0

class GovernancePolicy(BaseModel):
    policy_id: str
    name: str
    description: str = ""
    rule: str  # Python expression evaluated with context
    action: str  # auto_approve, requires_approval, blocked
    priority: int  # Higher priority evaluated first
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class GovernanceMode(BaseModel):
    mode: str  # supervised, autonomous, aggressive
    active_policies: List[str]
    schedule: Optional[Dict] = None
    user_present: bool = False
    updated_at: datetime = Field(default_factory=datetime.now)

class CheckAlignmentRequest(BaseModel):
    intent: Dict
    blueprint_context: str

class CheckAlignmentResponse(BaseModel):
    aligned: bool
    alignment_score: float
    reasoning: str
    decision: str
    policy_applied: str
    risk_level: str
    risk_factors: List[str] = []
    recommendations: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)

class DecideRequest(BaseModel):
    intent_id: str
    intent: Dict
    check_alignment: bool = True
    apply_policies: bool = True

class DecideResponse(BaseModel):
    intent_id: str
    decision: str
    reasoning: str
    alignment_score: float
    risk_level: str
    policy_matched: str
    next_action: str
    timestamp: datetime = Field(default_factory=datetime.now)

class SetModeRequest(BaseModel):
    mode: str
    active_policies: Optional[List[str]] = None
    schedule: Optional[Dict] = None

class SetModeResponse(BaseModel):
    mode: str
    previous_mode: str
    active_policies: int
    auto_approve_enabled: bool
    schedule_enabled: bool
    updated_at: datetime = Field(default_factory=datetime.now)

class CreatePolicyRequest(BaseModel):
    name: str
    rule: str
    action: str
    priority: int = 50
    description: str = ""

class CreatePolicyResponse(BaseModel):
    policy_id: str
    created_at: datetime = Field(default_factory=datetime.now)
    active: bool = True

class OverrideRequest(BaseModel):
    intent_id: str
    override_decision: str
    reason: str
    overridden_by: str = "user"

class OverrideResponse(BaseModel):
    intent_id: str
    original_decision: str
    new_decision: str
    overridden_by: str
    overridden_at: datetime = Field(default_factory=datetime.now)

class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    action: str
    intent_id: str
    details: Dict = {}
