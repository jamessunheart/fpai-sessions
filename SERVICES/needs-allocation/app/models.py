"""Pydantic models for Needs Allocation Engine."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class NeedsCategory(str, Enum):
    """Categories of needs."""
    SURVIVAL = "survival"
    STABILITY = "stability"
    GROWTH = "growth"
    CONTRIBUTION = "contribution"
    INFRASTRUCTURE = "infrastructure"


class RequestStatus(str, Enum):
    """Status of a needs request."""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class Urgency(str, Enum):
    """Urgency level."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Request Models
class NeedsRequestCreate(BaseModel):
    """Create a needs-support request."""
    member_id: str
    category: NeedsCategory
    subcategory: Optional[str] = None
    description: str
    amount_uc: float = Field(..., gt=0, le=1000)
    urgency: Urgency = Urgency.MEDIUM
    supporting_docs: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class NeedsRequestUpdate(BaseModel):
    """Update a needs request."""
    status: Optional[RequestStatus] = None
    notes: Optional[str] = None


# Response Models
class EligibilityCheck(BaseModel):
    """Eligibility check result."""
    trust_held: int
    contribution_score: int
    eligible: bool
    tier: str
    reason: Optional[str] = None


class NeedsRequest(BaseModel):
    """Needs request record."""
    id: str
    member_id: str
    category: NeedsCategory
    subcategory: Optional[str] = None
    description: str
    amount_uc: float
    urgency: Urgency
    status: RequestStatus
    eligibility: EligibilityCheck
    approved_amount: Optional[float] = None
    denial_reason: Optional[str] = None
    fulfilled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NeedsRequestResponse(BaseModel):
    """Response for request creation."""
    request_id: str
    status: RequestStatus
    estimated_decision: Optional[datetime] = None
    eligibility: EligibilityCheck


class CategoryBudget(BaseModel):
    """Budget for a category."""
    budget: float
    used: float
    available: float
    allocation_percent: float


class BudgetResponse(BaseModel):
    """Current budget allocation."""
    trust_index: float
    posture: str
    monthly_budget_uc: float
    categories: Dict[str, CategoryBudget]
    period: str
    resets: datetime


class EligibilityResponse(BaseModel):
    """Member eligibility response."""
    member_id: str
    eligible: bool
    trust_held: int
    contribution_score: int
    contribution_tier: str
    recent_allocations: int
    recent_total_uc: float
    fairness_limit_remaining: float
    eligible_categories: List[str]


class CommittedNeedsResponse(BaseModel):
    """Committed needs for Trust Index."""
    total_committed_uc: float
    pending_requests_uc: float
    approved_pending_fulfillment_uc: float
    monthly_projection_uc: float










