"""
WhiteRock Blessings Engine - Pydantic Schemas
Request/Response models with validation.
"""

from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List, Any
from datetime import datetime, date
from enum import Enum


# ===========================================
# ENUMS
# ===========================================

class MembershipTierEnum(str, Enum):
    SEEDLING = "seedling"
    SPROUT = "sprout"
    STEWARD = "steward"
    ELDER = "elder"


class BlessingStatusEnum(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    COMMITTEE_REVIEW = "committee_review"
    INFO_REQUESTED = "info_requested"
    APPROVED = "approved"
    DENIED = "denied"
    DISBURSED = "disbursed"
    CLOSED = "closed"


class BlessingCategoryEnum(str, Enum):
    HOUSING = "housing"
    FOOD = "food"
    MEDICAL = "medical"
    EDUCATION = "education"
    EMERGENCY = "emergency"
    UTILITIES = "utilities"
    OTHER = "other"


class CoraTransactionType(str, Enum):
    TITHE_MILESTONE = "tithe_milestone"
    SERVICE_GRANT = "service_grant"
    ADMIN_ADJUSTMENT = "admin_adjustment"
    DECAY_INACTIVITY = "decay_inactivity"
    CAP_ADJUSTMENT = "cap_adjustment"


class CapacityLevelEnum(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    PAUSED = "paused"


class ServiceStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


# ===========================================
# MEMBER SCHEMAS
# ===========================================

class MemberRegister(BaseModel):
    """Request schema for member registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class MemberUpdate(BaseModel):
    """Request schema for updating member profile."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class MemberLogin(BaseModel):
    """Request schema for login."""
    email: EmailStr
    password: str


class MemberResponse(BaseModel):
    """Response schema for member data."""
    id: int
    email: str
    full_name: str
    phone: Optional[str]
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    membership_tier: str
    cora_balance: int
    cora_cap: int
    last_engagement_date: datetime
    disclosure_signed_at: Optional[datetime]
    disclosure_version: Optional[str]
    profile_complete: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class MemberMeResponse(MemberResponse):
    """Extended response for /members/me with computed fields."""
    days_until_decay_warning: Optional[int] = None
    can_request_blessing: bool = False
    recent_activity: List[dict] = []


class DisclosureAcknowledge(BaseModel):
    """Request to acknowledge disclosure."""
    disclosure_version: str
    scrolled_confirmed: bool = Field(..., description="User scrolled to bottom")
    checkbox_confirmed: bool = Field(..., description="User checked agreement box")
    
    @field_validator('scrolled_confirmed', 'checkbox_confirmed')
    @classmethod
    def must_be_true(cls, v):
        if not v:
            raise ValueError("Both scroll and checkbox confirmations are required")
        return v


# ===========================================
# TITHE SCHEMAS
# ===========================================

class TitheCreate(BaseModel):
    """Request schema for creating a tithe."""
    amount_cents: int = Field(..., gt=0)
    payment_method_id: str  # Stripe payment method
    disclosure_acknowledged: bool = True
    disclosure_scrolled: bool = True
    disclosure_version: str
    
    @field_validator('disclosure_acknowledged', 'disclosure_scrolled')
    @classmethod
    def must_be_true(cls, v):
        if not v:
            raise ValueError("Disclosure acknowledgment required")
        return v


class TitheResponse(BaseModel):
    """Response schema for tithe data."""
    id: int
    amount_cents: int
    currency: str
    disclosure_version: str
    receipt_url: Optional[str]
    cora_granted: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class TitheListResponse(BaseModel):
    """Response for list of tithes."""
    tithes: List[TitheResponse]
    total_contributed_cents: int


# ===========================================
# CORA SCHEMAS
# ===========================================

class CoraBalanceResponse(BaseModel):
    """Response schema for CORA balance."""
    balance: int
    cap: int
    tier: str
    next_tier_threshold: Optional[int]
    last_engagement_date: datetime
    months_since_engagement: int
    decay_warning: bool
    transaction_history: List[dict]


class CoraGrant(BaseModel):
    """Request to grant CORA credits (admin only)."""
    member_id: int
    amount: int = Field(..., gt=0)
    transaction_type: CoraTransactionType
    description: Optional[str] = None


class CoraGrantResponse(BaseModel):
    """Response for CORA grant."""
    transaction_id: int
    new_balance: int


class CoraTierResponse(BaseModel):
    """Response for CORA tier info."""
    name: str
    threshold: int
    cap: int
    privileges: dict
    
    class Config:
        from_attributes = True


# ===========================================
# SERVICE HOURS SCHEMAS
# ===========================================

class ServiceHoursLog(BaseModel):
    """Request to log service hours."""
    hours: float = Field(..., gt=0, le=24)
    activity_type: str = Field(..., min_length=2)
    activity_date: date
    description: Optional[str] = None


class ServiceHoursResponse(BaseModel):
    """Response for service hours."""
    id: int
    hours: float
    activity_type: str
    activity_date: date
    description: Optional[str]
    verified_at: Optional[datetime]
    cora_granted: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ServiceHoursVerify(BaseModel):
    """Request to verify service hours (admin)."""
    verified: bool = True
    cora_grant_amount: int = Field(..., ge=0)


# ===========================================
# BLESSING SCHEMAS
# ===========================================

class BlessingEligibilityResponse(BaseModel):
    """Response for blessing eligibility check."""
    eligible: bool
    reasons: List[str] = []
    community_capacity: CapacityLevelEnum


class BlessingRequestCreate(BaseModel):
    """Request to create a blessing request."""
    category: BlessingCategoryEnum
    description: str = Field(..., min_length=10)
    amount_requested_cents: Optional[int] = Field(None, gt=0)
    vendor_name: Optional[str] = None
    vendor_contact: Optional[str] = None
    supporting_docs_url: Optional[str] = None


class BlessingRequestResponse(BaseModel):
    """Response for blessing request."""
    id: int
    category: str
    description: str
    amount_requested_cents: Optional[int]
    vendor_name: Optional[str]
    vendor_contact: Optional[str]
    status: str
    amount_approved_cents: Optional[int]
    denial_reason: Optional[str]
    created_at: datetime
    updated_at: datetime
    state_history: List[dict] = []
    
    class Config:
        from_attributes = True


class BlessingTransition(BaseModel):
    """Request to transition blessing state (committee)."""
    new_status: BlessingStatusEnum
    internal_notes: Optional[str] = None
    compliance_flag: Optional[bool] = None
    amount_approved_cents: Optional[int] = None
    denial_reason: Optional[str] = None
    
    @field_validator('compliance_flag')
    @classmethod
    def validate_compliance_for_approval(cls, v, info):
        # Note: Additional validation done in endpoint
        return v


class BlessingDisburseRequest(BaseModel):
    """Request to disburse blessing (admin)."""
    amount_cents: int = Field(..., gt=0)
    disbursement_method: str
    vendor_name: Optional[str] = None
    vendor_contact: Optional[str] = None
    disbursement_reference: Optional[str] = None
    cash_to_member_override: bool = False
    override_reason: Optional[str] = None
    
    @field_validator('override_reason')
    @classmethod
    def require_reason_for_override(cls, v, info):
        if info.data.get('cash_to_member_override') and not v:
            raise ValueError("Override reason required for cash-to-member disbursement")
        return v


class BlessingPendingResponse(BaseModel):
    """Response for pending blessings (committee view)."""
    id: int
    member_summary: dict
    category: str
    amount_requested_cents: Optional[int]
    vendor_name: Optional[str]
    vendor_contact: Optional[str]
    description: str
    status: str
    created_at: datetime
    state_transition_log: List[dict]


# ===========================================
# CAPACITY SCHEMAS
# ===========================================

class CapacityResponse(BaseModel):
    """Response for community capacity."""
    level: CapacityLevelEnum
    updated_at: datetime


# ===========================================
# REPORT SCHEMAS
# ===========================================

class CommunityReportResponse(BaseModel):
    """Response for community report."""
    total_members: int
    active_members_30d: int
    total_tithes_ytd_cents: int
    total_blessings_distributed_ytd_cents: int
    blessings_by_category: dict
    cora_in_circulation: int
    average_member_tenure_months: float


class BlessingsReportResponse(BaseModel):
    """Response for blessings report."""
    total_requests: int
    approved_count: int
    denied_count: int
    total_disbursed_cents: int
    average_processing_days: float
    by_category_summary: dict


class CoraHealthResponse(BaseModel):
    """Response for CORA health report."""
    total_cora_circulation: int
    members_at_risk_of_decay: int
    decay_events_last_90_days: int
    average_member_cora: float


# ===========================================
# AUDIT SCHEMAS
# ===========================================

class AuditLogEntry(BaseModel):
    """Audit log entry."""
    id: int
    action: str
    entity_type: str
    entity_id: int
    actor_id: Optional[int]
    actor_role: Optional[str]
    old_values: Optional[dict]
    new_values: Optional[dict]
    severity: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class IntegrityCheckResponse(BaseModel):
    """Response for integrity check."""
    check_timestamp: datetime
    foreign_key_violations: int
    orphaned_records: int
    treasury_links_found: bool
    invalid_state_transitions: int
    compliance_flag_violations: int
    status: str  # 'PASS' or 'FAIL'
    issues: List[str]


# ===========================================
# UDC HEALTH SCHEMAS
# ===========================================

class HealthResponse(BaseModel):
    """UDC Health endpoint response."""
    status: ServiceStatusEnum
    service: str
    version: str
    timestamp: datetime
    uptime_seconds: float
    database_connected: bool


class CapabilitiesResponse(BaseModel):
    """UDC Capabilities endpoint response."""
    service: str
    version: str
    features: List[str]
    integrations: List[str]
    firewall_enforced: List[str]


class StateResponse(BaseModel):
    """UDC State endpoint response."""
    total_members: int
    active_blessing_requests: int
    cora_in_circulation: int
    capacity_level: str
    last_decay_run: Optional[datetime]


class DependencyStatus(BaseModel):
    """Status of a dependency."""
    name: str
    status: str
    latency_ms: Optional[float]


class DependenciesResponse(BaseModel):
    """UDC Dependencies endpoint response."""
    dependencies: List[DependencyStatus]


class TokenResponse(BaseModel):
    """JWT token response with refresh token."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token."""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Request to logout and blacklist tokens."""
    refresh_token: Optional[str] = None

