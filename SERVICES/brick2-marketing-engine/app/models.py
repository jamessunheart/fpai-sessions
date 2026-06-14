"""
BRICK 2 Data Models
===================
SQLAlchemy models for the marketing engine.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Referrer(Base):
    """
    BPO Referrer
    People who refer leads/VAs to the system.
    """
    __tablename__ = "referrers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    referral_code = Column(String, unique=True, index=True)  # Unique code for tracking
    
    # GHL Integration
    ghl_contact_id = Column(String, nullable=True)  # Link to GHL Contact
    
    # Financials
    total_commissions_earned = Column(Float, default=0.0)
    total_commissions_paid = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    commissions = relationship("Commission", back_populates="referrer")


class Commission(Base):
    """
    Commission Record
    Tracks earnings for a referrer from a specific placement/lead.
    """
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True, index=True)
    referrer_id = Column(Integer, ForeignKey("referrers.id"))
    
    amount = Column(Float, nullable=False)
    description = Column(String)  # e.g. "Commission for Client X - Oct 2025"
    
    # Status: pending, approved, paid
    status = Column(String, default="pending")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    
    referrer = relationship("Referrer", back_populates="commissions")


class Lead(Base):
    """
    Marketing Lead
    Captured from GHL or other sources.
    """
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    name = Column(String)
    source = Column(String)  # e.g. "ghl", "web", "referral"
    
    # AI Qualification
    qualification_score = Column(Integer, default=0)
    ai_analysis = Column(JSON, nullable=True)  # Stored JSON analysis from GPT-5/Claude
    
    # Status
    status = Column(String, default="new")  # new, qualified, converted, junk
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ContentItem(Base):
    """
    AI Generated Content
    History of what the AI has written (Emails, Posts, Ads).
    """
    __tablename__ = "content_items"

    id = Column(Integer, primary_key=True, index=True)
    
    title = Column(String)
    body = Column(Text)
    type = Column(String)  # email, social_post, blog, ad
    
    # Metadata
    provider = Column(String)  # claude, gpt-5, etc.
    model_used = Column(String)
    
    # Status
    status = Column(String, default="draft")  # draft, approved, published
    ghl_campaign_id = Column(String, nullable=True)  # If pushed to GHL
    
    created_at = Column(DateTime, default=datetime.utcnow)

