#!/usr/bin/env python3
"""
ALIGNMENT ECONOMICS - CORE DATA MODELS
========================================

Value optimized for circulation, not accumulation.
Debt engineered to self-resolve.
Forgiveness as mechanical outcome.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, List, Literal
import uuid


# ============================================================================
# ENUMS
# ============================================================================

class PositionType(str, Enum):
    EQUITY = "equity"       # Stock, ownership stakes
    DEBT = "debt"           # What we owe
    CASH = "cash"           # Liquid capital
    STAKE = "stake"         # Our ownership in institutions
    RECEIVABLE = "receivable"  # What's owed to us


class DebtClassification(str, Enum):
    PRODUCTIVE = "productive"       # Creates value, builds capacity
    TRANSITIONAL = "transitional"   # Bridge financing, temporary
    EXTRACTIVE = "extractive"       # To be refinanced/eliminated


class DebtStatus(str, Enum):
    ACTIVE = "active"
    FORGIVEN = "forgiven"
    DISSOLVED = "dissolved"
    REFINANCED = "refinanced"


class FlowPurpose(str, Enum):
    RELIEF = "relief"               # Relieve pressure/stress
    PRODUCTIVE = "productive"       # Build capacity
    TRUST_BUILDING = "trust"        # Strengthen relationships
    INSTITUTIONAL = "institutional" # Acquire stakes/influence
    RESERVE = "reserve"             # Build liquidity buffer
    RETURN = "return"               # Yield/dividend/interest back


class InstitutionType(str, Enum):
    BANK = "bank"
    LENDER = "lender"
    ASSET_MANAGER = "asset_manager"
    EXCHANGE = "exchange"
    PLATFORM = "platform"


# ============================================================================
# CORE ENTITIES
# ============================================================================

@dataclass
class Position:
    """
    A capital position in the system.
    
    Everything is a position - equity, cash, debt, stakes.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    type: PositionType = PositionType.CASH
    value: Decimal = Decimal("0")
    currency: str = "USD"
    source: str = ""  # Where it came from
    holder: str = "steward"  # Who holds it
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    last_flow_at: Optional[datetime] = None
    
    # Metadata
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    @property
    def idle_days(self) -> int:
        """Days since last capital flow."""
        if self.last_flow_at is None:
            return (datetime.now() - self.created_at).days
        return (datetime.now() - self.last_flow_at).days
    
    @property
    def is_idle(self) -> bool:
        """Capital idle > 7 days is flagged."""
        return self.idle_days > 7
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "value": str(self.value),
            "currency": self.currency,
            "source": self.source,
            "holder": self.holder,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_flow_at": self.last_flow_at.isoformat() if self.last_flow_at else None,
            "idle_days": self.idle_days,
            "is_idle": self.is_idle,
            "notes": self.notes,
            "tags": self.tags,
        }


@dataclass
class Debt:
    """
    A debt instrument with forgiveness tracking.
    
    Debts are temporary by architecture.
    No shame, no defaults, no collapse dynamics.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    classification: DebtClassification = DebtClassification.TRANSITIONAL
    
    # Principal & terms
    principal: Decimal = Decimal("0")
    interest_rate: Decimal = Decimal("0")  # Annual rate
    currency: str = "USD"
    
    # Parties
    lender: str = ""       # Who we owe
    borrower: str = "steward"  # Who borrowed (usually us)
    
    # Forgiveness tracking
    participation_score: float = 0.0  # 0-1, increases with activity
    yield_accumulated: Decimal = Decimal("0")  # Value generated
    payments_made: Decimal = Decimal("0")
    
    # Status
    status: DebtStatus = DebtStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.now)
    forgiven_at: Optional[datetime] = None
    
    # Metadata
    notes: str = ""
    metadata: Dict = field(default_factory=dict)
    
    @property
    def time_active(self) -> timedelta:
        """How long this debt has been active."""
        return datetime.now() - self.created_at
    
    @property
    def days_active(self) -> int:
        return self.time_active.days
    
    @property
    def yield_coverage(self) -> float:
        """Ratio of yield to principal. >= 1.0 means ready for forgiveness."""
        if self.principal == 0:
            return 0
        return float(self.yield_accumulated / self.principal)
    
    @property
    def remaining(self) -> Decimal:
        """Principal minus payments."""
        return max(Decimal("0"), self.principal - self.payments_made)
    
    def check_forgiveness_ready(self) -> tuple[bool, str]:
        """
        Check if this debt is ready for forgiveness.
        Returns (ready, reason).
        """
        # Rule 1: Yield exceeds principal
        if self.yield_coverage >= 1.0:
            return True, "yield_coverage"
        
        # Rule 2: Time + participation for productive debt
        if self.classification == DebtClassification.PRODUCTIVE:
            if self.days_active >= 365 and self.participation_score >= 0.8:
                return True, "time_participation"
        
        # Rule 3: Time for transitional (shorter window)
        if self.classification == DebtClassification.TRANSITIONAL:
            if self.days_active >= 180 and self.participation_score >= 0.6:
                return True, "transitional_maturity"
        
        return False, ""
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "classification": self.classification.value,
            "principal": str(self.principal),
            "interest_rate": str(self.interest_rate),
            "currency": self.currency,
            "lender": self.lender,
            "borrower": self.borrower,
            "participation_score": self.participation_score,
            "yield_accumulated": str(self.yield_accumulated),
            "payments_made": str(self.payments_made),
            "remaining": str(self.remaining),
            "yield_coverage": self.yield_coverage,
            "status": self.status.value,
            "days_active": self.days_active,
            "created_at": self.created_at.isoformat(),
            "forgiven_at": self.forgiven_at.isoformat() if self.forgiven_at else None,
            "notes": self.notes,
        }


@dataclass
class Flow:
    """
    A capital movement from one position to another.
    
    Every flow is tracked for velocity calculation.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    
    # Movement
    from_position: str = ""  # Position ID or "external"
    to_position: str = ""    # Position ID or "external"
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    
    # Purpose (for prioritization tracking)
    purpose: FlowPurpose = FlowPurpose.PRODUCTIVE
    
    # Context
    description: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Approval
    approved_by: str = "steward"  # Human approval
    auto_approved: bool = False   # Was this within autonomous limits?
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "from_position": self.from_position,
            "to_position": self.to_position,
            "amount": str(self.amount),
            "currency": self.currency,
            "purpose": self.purpose.value,
            "description": self.description,
            "timestamp": self.timestamp.isoformat(),
            "approved_by": self.approved_by,
            "auto_approved": self.auto_approved,
        }


@dataclass
class Institution:
    """
    External institution we interact with or own stakes in.
    
    Goal: recursive absorption - use leverage to acquire stakes,
    close the interest loop.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    type: InstitutionType = InstitutionType.BANK
    
    # Our relationship
    ownership_stake: Decimal = Decimal("0")  # % we own
    governance_influence: float = 0.0  # 0-1 influence score
    
    # Their terms to us
    cost_of_capital: Decimal = Decimal("0")  # Interest rate
    total_exposure: Decimal = Decimal("0")   # How much we owe them
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    notes: str = ""
    
    @property
    def interest_loop_closure(self) -> float:
        """
        How much of the interest we pay comes back to us.
        ownership_stake * governance_influence
        """
        return float(self.ownership_stake / 100) * self.governance_influence
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "ownership_stake": str(self.ownership_stake),
            "governance_influence": self.governance_influence,
            "cost_of_capital": str(self.cost_of_capital),
            "total_exposure": str(self.total_exposure),
            "interest_loop_closure": self.interest_loop_closure,
            "created_at": self.created_at.isoformat(),
            "notes": self.notes,
        }


# ============================================================================
# SYSTEM HEALTH
# ============================================================================

@dataclass
class SystemHealth:
    """
    Real-time health metrics for the alignment economics system.
    
    These are the KPIs that matter.
    """
    # Circulation
    capital_velocity: float = 0.0  # Flows per period / total capital
    circulation_efficiency: float = 0.0  # % of capital actively flowing
    idle_capital_ratio: float = 0.0  # % sitting idle > 7 days
    
    # Debt
    debt_resolution_rate: float = 0.0  # Debts forgiven per period
    default_rate: float = 0.0  # Should trend toward 0
    average_time_to_forgiveness: int = 0  # Days
    
    # Stress
    stress_index: float = 0.0  # 0-1, composite indicator
    liquidity_ratio: float = 0.0  # Available / Committed
    
    # Scale
    total_capital: Decimal = Decimal("0")
    total_debt: Decimal = Decimal("0")
    net_position: Decimal = Decimal("0")
    
    # Timestamp
    calculated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_healthy(self) -> bool:
        """System is healthy if stress is low and velocity is good."""
        return self.stress_index < 0.6 and self.capital_velocity > 0.3
    
    @property
    def forgiveness_acceleration(self) -> float:
        """When healthy, forgiveness can accelerate."""
        if self.stress_index < 0.3 and self.capital_velocity > 0.5:
            return 2.0  # 2x acceleration
        return 1.0
    
    def to_dict(self) -> Dict:
        return {
            "capital_velocity": self.capital_velocity,
            "circulation_efficiency": self.circulation_efficiency,
            "idle_capital_ratio": self.idle_capital_ratio,
            "debt_resolution_rate": self.debt_resolution_rate,
            "default_rate": self.default_rate,
            "average_time_to_forgiveness": self.average_time_to_forgiveness,
            "stress_index": self.stress_index,
            "liquidity_ratio": self.liquidity_ratio,
            "total_capital": str(self.total_capital),
            "total_debt": str(self.total_debt),
            "net_position": str(self.net_position),
            "is_healthy": self.is_healthy,
            "forgiveness_acceleration": self.forgiveness_acceleration,
            "calculated_at": self.calculated_at.isoformat(),
        }


