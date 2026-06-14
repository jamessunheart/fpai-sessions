"""Pydantic models for Contribution Tracker."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ContributionType(str, Enum):
    """Types of contributions."""
    SERVICE = "service"
    GOVERNANCE = "governance"
    ART = "art"
    REFERRAL = "referral"
    FINANCIAL = "financial"
    COMMUNITY = "community"


class ContributionStatus(str, Enum):
    """Status of a contribution."""
    PENDING = "pending"
    VERIFIED = "verified"
    DENIED = "denied"
    EXPIRED = "expired"


class MemberTier(str, Enum):
    """Member contribution tiers."""
    FOUNDER = "founder"
    ACTIVE = "active"
    ENGAGED = "engaged"
    INACTIVE = "inactive"


# Request Models
class ContributionCreate(BaseModel):
    """Create a new contribution."""
    member_id: str
    type: ContributionType
    description: str
    hours: Optional[float] = None  # For service type
    amount: Optional[float] = None  # For financial type
    recipient_id: Optional[str] = None  # For service verification
    reference_id: Optional[str] = None  # External reference (art ID, vote ID, etc.)
    evidence: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ContributionVerify(BaseModel):
    """Verify a contribution."""
    verifier_id: str
    verified: bool
    notes: Optional[str] = None


# Response Models
class Contribution(BaseModel):
    """Contribution record."""
    id: str
    member_id: str
    type: ContributionType
    description: str
    status: ContributionStatus
    trust_potential: int
    trust_issued: int = 0
    hours: Optional[float] = None
    amount: Optional[float] = None
    recipient_id: Optional[str] = None
    reference_id: Optional[str] = None
    verifier_id: Optional[str] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ContributionResponse(BaseModel):
    """Response for contribution creation."""
    contribution_id: str
    member_id: str
    type: ContributionType
    status: ContributionStatus
    trust_potential: int
    verification_method: str
    verification_deadline: Optional[datetime] = None


class MemberScore(BaseModel):
    """Member contribution score."""
    member_id: str
    current_quarter: str
    quarterly_score: int
    tier: MemberTier
    trust_balance: int
    voting_multiplier: float
    benefit_eligible: bool
    eligible_categories: List[str]
    is_founder: bool = False
    next_tier: Optional[MemberTier] = None
    points_to_next_tier: int = 0


class MemberContributions(BaseModel):
    """Member contribution history."""
    member_id: str
    period: str
    total_score: int
    tier: MemberTier
    trust_earned: int
    contributions: List[Contribution]
    by_type: Dict[str, int]


class AggregateMetrics(BaseModel):
    """Aggregate contribution metrics."""
    period: str
    total_members: int
    active_contributors: int
    active_ratio: float
    avg_quarterly_score: float
    total_trust_issued: int
    by_type: Dict[str, int]


class Leaderboard(BaseModel):
    """Contribution leaderboard."""
    period: str
    entries: List[Dict[str, Any]]


class TrustIssuance(BaseModel):
    """TRUST token issuance record."""
    member_id: str
    amount: int
    contribution_id: str
    reason: str
    issued_at: datetime










