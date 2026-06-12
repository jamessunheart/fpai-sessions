"""
Data models for Chief of Staff Service
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SignalCategory(str, Enum):
    """Signal urgency categories"""
    URGENT = "urgent"  # 🔴 Needs YOU now
    IMPORTANT = "important"  # 🟡 Needs attention soon
    AUTO = "auto"  # 🟢 Auto-handled
    CONTEXT = "context"  # 📊 FYI only


class SignalType(str, Enum):
    """Types of signals"""
    ERROR = "error"
    METRIC = "metric"
    EVENT = "event"
    ALERT = "alert"
    STATUS = "status"


class SignalAction(str, Enum):
    """Actions taken on signals"""
    ALERT = "alert"  # Send urgent alert
    DIGEST = "digest"  # Add to daily digest
    AUTO = "auto"  # Auto-handle
    LOG = "log"  # Log only


class UserAction(str, Enum):
    """User response to signals"""
    ACTED = "acted"
    IGNORED = "ignored"
    DELEGATED = "delegated"
    AUTOMATED = "automated"


class Signal(BaseModel):
    """A signal from any source"""
    signal_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str = Field(..., description="Which service/system")
    type: SignalType
    category: SignalCategory
    title: str = Field(..., description="Short description")
    description: str = Field(..., description="Full details")
    data: Dict[str, Any] = Field(default_factory=dict)
    decision_filter_passed: bool = False
    action_taken: SignalAction
    user_response: Optional[UserAction] = None
    responded_at: Optional[datetime] = None


class SignalRequest(BaseModel):
    """Request to create a signal"""
    source: str = Field(..., description="Service name")
    type: SignalType
    title: str
    description: str
    data: Dict[str, Any] = Field(default_factory=dict)
    urgency_hint: Optional[SignalCategory] = None


class SignalResponse(BaseModel):
    """Response after processing a signal"""
    signal_id: str
    category: SignalCategory
    action: SignalAction
    message: str


class SystemStatus(BaseModel):
    """Current system status"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    urgent_count: int = 0
    important_count: int = 0
    auto_handled_count: int = 0
    context_count: int = 0
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    active_issues: List[Signal] = Field(default_factory=list)
    recent_automations: List[str] = Field(default_factory=list)


class DigestItem(BaseModel):
    """Item in daily digest"""
    category: SignalCategory
    title: str
    description: str
    action_needed: Optional[str] = None


class DailyDigest(BaseModel):
    """Daily briefing"""
    date: datetime = Field(default_factory=datetime.utcnow)
    urgent_items: List[DigestItem] = Field(default_factory=list)
    important_items: List[DigestItem] = Field(default_factory=list)
    auto_handled: List[str] = Field(default_factory=list)
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    automation_suggestions: List[str] = Field(default_factory=list)


class AutomationSuggestion(BaseModel):
    """Suggested automation opportunity"""
    pattern: str = Field(..., description="What keeps happening")
    frequency: int = Field(..., description="How often")
    suggestion: str = Field(..., description="What to automate")
    confidence: float = Field(..., description="Confidence 0-1")
    signals: List[str] = Field(default_factory=list, description="Signal IDs")


class UserFeedback(BaseModel):
    """User feedback on a signal"""
    signal_id: str
    action_taken: UserAction
    notes: Optional[str] = None


class EngineRole(str, Enum):
    """How a service relates to the ONE Engine (Zen Village)"""
    P1 = "P1"
    P2 = "P2"
    INFRA = "infra"
    CRUFT = "cruft"
    UNKNOWN = "unknown"


class ServiceCard(BaseModel):
    """One row in the service catalog / Priority view"""
    name: str
    path: str
    engine_role: EngineRole
    last_touched: Optional[datetime] = None
    purpose: Optional[str] = None
    monthly_usd: Optional[float] = None


class PriorityView(BaseModel):
    """Cross-system Priority view"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_services: int
    by_role: Dict[str, int] = Field(default_factory=dict)
    services: List[ServiceCard] = Field(default_factory=list)
    decision_filter: str = "Does this serve proof / revenue / clarity / ease for the core offer in 30 days?"


class CostItem(BaseModel):
    """One cost line in the ledger"""
    name: str
    id: str
    category: str  # server, api, tooling
    engine_role: EngineRole
    monthly_usd: float
    purpose: str
    kill_candidate: bool = False


class RevenueItem(BaseModel):
    """One revenue stream in the ledger"""
    stream: str
    revenue_usd: float = 0.0
    inquiries: Optional[int] = None
    bookings_confirmed: Optional[int] = None
    active_tenants: Optional[int] = None
    last30d_revenue_usd: Optional[float] = None
    last30d_txns: Optional[int] = None
    lifetime_txns: Optional[int] = None
    lifetime_revenue_usd: Optional[float] = None
    activity_summary: Optional[str] = None
    as_of: Optional[datetime] = None
    note: Optional[str] = None


class MoneyView(BaseModel):
    """Cross-system Money view"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    costs: List[CostItem] = Field(default_factory=list)
    revenue: List[RevenueItem] = Field(default_factory=list)
    total_cost_monthly_usd: float = 0.0
    total_revenue_monthly_usd: float = 0.0
    net_monthly_usd: float = 0.0
    biggest_leak: Optional[CostItem] = None
    cost_by_engine_role: Dict[str, float] = Field(default_factory=dict)
