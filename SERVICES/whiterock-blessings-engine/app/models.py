"""
WhiteRock Blessings Engine - SQLAlchemy Models
All database models for the member management and blessing system.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, Text, DateTime, 
    ForeignKey, Numeric, Date, CheckConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Member(Base):
    """Member model for WhiteRock community."""
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    
    # Membership & Standing
    membership_tier = Column(String(50), default="seedling")
    cora_balance = Column(Integer, default=0)
    cora_cap = Column(Integer, default=1000)
    
    # Engagement Tracking
    last_engagement_date = Column(DateTime, default=datetime.utcnow)
    decay_warning_sent_at = Column(DateTime)
    
    # Compliance
    disclosure_signed_at = Column(DateTime)
    disclosure_version = Column(String(20))
    profile_complete = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    deactivation_reason = Column(Text)
    
    # Admin flags
    is_admin = Column(Boolean, default=False)
    is_committee = Column(Boolean, default=False)
    is_auditor = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tithes = relationship("Tithe", back_populates="member", foreign_keys="Tithe.member_id")
    cora_transactions = relationship("CoraTransaction", back_populates="member", foreign_keys="CoraTransaction.member_id")
    service_hours = relationship("ServiceHours", back_populates="member", foreign_keys="ServiceHours.member_id")
    blessing_requests = relationship("BlessingRequest", back_populates="member", foreign_keys="BlessingRequest.member_id")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("cora_balance >= 0", name="chk_cora_non_negative"),
        CheckConstraint("cora_balance <= cora_cap", name="chk_cora_cap"),
    )


class MembershipTier(Base):
    """Membership tier definitions."""
    __tablename__ = "membership_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    cora_threshold = Column(Integer, nullable=False)
    cora_cap = Column(Integer, nullable=False)
    description = Column(Text)
    access_privileges = Column(JSONB, default={})


class DisclosureVersion(Base):
    """Disclosure text versions for compliance tracking."""
    __tablename__ = "disclosure_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), unique=True, nullable=False)
    disclosure_text = Column(Text, nullable=False)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Tithe(Base):
    """Tithe contributions from members."""
    __tablename__ = "tithes"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="USD")
    
    # Payment
    stripe_payment_id = Column(String(255))
    stripe_payment_status = Column(String(50))
    
    # Compliance (CRITICAL)
    disclosure_acknowledged = Column(Boolean, nullable=False, default=False)
    disclosure_text = Column(Text, nullable=False)
    disclosure_version = Column(String(20), nullable=False)
    disclosure_scrolled_confirmed = Column(Boolean, nullable=False, default=False)
    
    # Receipt
    receipt_sent_at = Column(DateTime)
    receipt_url = Column(Text)
    
    # CORA
    cora_granted = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="tithes", foreign_keys=[member_id])


class CoraTransaction(Base):
    """CORA credit transactions."""
    __tablename__ = "cora_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Integer, nullable=False)  # Positive = grant, negative = decay
    transaction_type = Column(String(50), nullable=False)
    description = Column(Text)
    granted_by = Column(Integer, ForeignKey("members.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="cora_transactions", foreign_keys=[member_id])
    granter = relationship("Member", foreign_keys=[granted_by])


class CoraDecayEvent(Base):
    """CORA decay audit trail."""
    __tablename__ = "cora_decay_events"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount_decayed = Column(Integer, nullable=False)
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    decay_reason = Column(String(50), nullable=False)
    months_inactive = Column(Integer, nullable=False)
    notification_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("Member")


class ServiceHours(Base):
    """Service hours logged by members."""
    __tablename__ = "service_hours"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    hours = Column(Numeric(5, 2), nullable=False)
    activity_type = Column(String(100), nullable=False)
    activity_date = Column(Date, nullable=False)
    description = Column(Text)
    
    # Verification
    verified_by = Column(Integer, ForeignKey("members.id"))
    verified_at = Column(DateTime)
    
    # CORA
    cora_granted = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="service_hours", foreign_keys=[member_id])
    verifier = relationship("Member", foreign_keys=[verified_by])


class BlessingRequest(Base):
    """Blessing requests with state machine."""
    __tablename__ = "blessing_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    
    # Request Details
    category = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    amount_requested_cents = Column(Integer)
    supporting_docs_url = Column(Text)
    
    # Vendor
    vendor_name = Column(String(255))
    vendor_contact = Column(String(255))
    
    # State Machine
    status = Column(String(50), default="draft")
    state_transition_log = Column(JSONB, default=[])
    
    # Committee Review
    reviewed_by = Column(Integer, ForeignKey("members.id"))
    reviewed_at = Column(DateTime)
    internal_notes = Column(Text)
    compliance_flag = Column(Boolean, default=False)
    
    # Outcome
    amount_approved_cents = Column(Integer)
    denial_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    member = relationship("Member", back_populates="blessing_requests", foreign_keys=[member_id])
    reviewer = relationship("Member", foreign_keys=[reviewed_by])
    disbursements = relationship("BlessingDisbursement", back_populates="blessing_request")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'pending', 'committee_review', 'info_requested', 'approved', 'denied', 'disbursed', 'closed')",
            name="chk_blessing_status"
        ),
    )


class BlessingDisbursement(Base):
    """Disbursement records for approved blessings."""
    __tablename__ = "blessing_disbursements"
    
    id = Column(Integer, primary_key=True, index=True)
    blessing_request_id = Column(Integer, ForeignKey("blessing_requests.id"), nullable=False)
    amount_cents = Column(Integer, nullable=False)
    
    # Disbursement Method
    disbursement_method = Column(String(50), nullable=False)
    payment_direct_to_vendor = Column(Boolean, default=True)
    
    # Vendor Info
    vendor_name = Column(String(255))
    vendor_contact = Column(String(255))
    
    # Tracking
    disbursement_reference = Column(String(255))
    disbursed_by = Column(Integer, ForeignKey("members.id"))
    
    # Audit Flag
    cash_to_member_override = Column(Boolean, default=False)
    override_approved_by = Column(Integer, ForeignKey("members.id"))
    override_reason = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    blessing_request = relationship("BlessingRequest", back_populates="disbursements")
    disburser = relationship("Member", foreign_keys=[disbursed_by])
    override_approver = relationship("Member", foreign_keys=[override_approved_by])


class CommunityCapacity(Base):
    """Community blessing capacity (external write only)."""
    __tablename__ = "community_capacity"
    
    id = Column(Integer, primary_key=True, index=True)
    capacity_level = Column(String(20), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(String(100))
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "capacity_level IN ('high', 'medium', 'low', 'paused')",
            name="chk_capacity_level"
        ),
    )


class TitheMilestone(Base):
    """CORA grant milestones for cumulative tithes."""
    __tablename__ = "tithe_milestones"
    
    id = Column(Integer, primary_key=True, index=True)
    cumulative_amount_cents = Column(Integer, unique=True, nullable=False)
    cora_grant = Column(Integer, nullable=False)
    description = Column(Text)


class AuditLog(Base):
    """Comprehensive audit log for compliance."""
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    actor_id = Column(Integer, ForeignKey("members.id"))
    actor_role = Column(String(50))
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    severity = Column(String(20), default="info")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    actor = relationship("Member")



