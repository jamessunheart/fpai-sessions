"""SQLAlchemy database models for Needs Allocation."""
from sqlalchemy import Column, String, Float, DateTime, Text, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class NeedsRequestRecord(Base):
    """Database model for needs requests."""
    __tablename__ = "needs_requests"
    
    id = Column(String, primary_key=True)
    member_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    amount_uc = Column(Float, nullable=False)
    urgency = Column(String, default="medium")
    status = Column(String, default="pending")
    
    # Eligibility at time of request
    trust_held = Column(Integer, default=0)
    contribution_score = Column(Integer, default=0)
    
    # Approval/Denial
    approved_amount = Column(Float, nullable=True)
    denial_reason = Column(Text, nullable=True)
    reviewer_id = Column(String, nullable=True)
    
    # Supporting data
    supporting_docs = Column(JSON, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    fulfilled_at = Column(DateTime, nullable=True)


class AllocationRecord(Base):
    """Database model for allocations (fulfilled requests)."""
    __tablename__ = "allocations"
    
    id = Column(String, primary_key=True)
    request_id = Column(String, nullable=False, index=True)
    member_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    amount_uc = Column(Float, nullable=False)
    fulfillment_type = Column(String, nullable=False)  # "uc_credit", "service", "direct"
    fulfillment_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())


class MonthlyBudget(Base):
    """Database model for monthly budget tracking."""
    __tablename__ = "monthly_budgets"
    
    id = Column(String, primary_key=True)  # "2025-12"
    total_budget = Column(Float, default=0)
    survival_used = Column(Float, default=0)
    stability_used = Column(Float, default=0)
    growth_used = Column(Float, default=0)
    contribution_used = Column(Float, default=0)
    infrastructure_used = Column(Float, default=0)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

