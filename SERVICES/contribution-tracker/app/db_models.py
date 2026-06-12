"""SQLAlchemy database models for Contribution Tracker."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum, Boolean, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
from datetime import datetime

Base = declarative_base()


class ContributionTypeEnum(enum.Enum):
    SERVICE = "service"
    GOVERNANCE = "governance"
    ART = "art"
    REFERRAL = "referral"
    FINANCIAL = "financial"
    COMMUNITY = "community"


class ContributionStatusEnum(enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    DENIED = "denied"
    EXPIRED = "expired"


class ContributionRecord(Base):
    """Database model for contributions."""
    __tablename__ = "contributions"
    
    id = Column(String, primary_key=True)
    member_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="pending")
    
    # TRUST amounts
    trust_potential = Column(Integer, default=0)
    trust_issued = Column(Integer, default=0)
    
    # Type-specific fields
    hours = Column(Float, nullable=True)
    amount = Column(Float, nullable=True)
    recipient_id = Column(String, nullable=True)
    reference_id = Column(String, nullable=True)
    
    # Verification
    verifier_id = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)
    
    # Extra data
    evidence = Column(JSON, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TrustBalance(Base):
    """Database model for TRUST token balances."""
    __tablename__ = "trust_balances"
    
    member_id = Column(String, primary_key=True)
    balance = Column(Integer, default=0)
    total_earned = Column(Integer, default=0)
    is_founder = Column(Boolean, default=False)
    joined_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class TrustTransaction(Base):
    """Database model for TRUST transactions."""
    __tablename__ = "trust_transactions"
    
    id = Column(String, primary_key=True)
    member_id = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    type = Column(String, nullable=False)  # "earn", "spend", "transfer"
    reason = Column(String, nullable=False)
    contribution_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())


class QuarterlyScore(Base):
    """Database model for quarterly contribution scores."""
    __tablename__ = "quarterly_scores"
    
    id = Column(String, primary_key=True)
    member_id = Column(String, nullable=False, index=True)
    quarter = Column(String, nullable=False)  # "2025-Q4"
    score = Column(Integer, default=0)
    tier = Column(String, default="inactive")
    
    # Breakdown by type
    service_score = Column(Integer, default=0)
    governance_score = Column(Integer, default=0)
    art_score = Column(Integer, default=0)
    referral_score = Column(Integer, default=0)
    financial_score = Column(Integer, default=0)
    community_score = Column(Integer, default=0)
    
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

