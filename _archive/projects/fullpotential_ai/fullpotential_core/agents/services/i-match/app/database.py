"""Database setup and models for I MATCH"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

from .config import settings

# Create engine
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()


# === Database Models ===

class Customer(Base):
    """Customer seeking a service provider"""
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)

    # Service needs
    service_type = Column(String, nullable=False)  # financial_advisor, realtor, consultant, etc.
    needs_description = Column(Text, nullable=False)

    # Preferences (JSON)
    preferences = Column(JSON, default={})  # {"communication_style": "formal", "budget_range": "50k-100k", etc.}
    values = Column(JSON, default={})  # {"integrity": 10, "responsiveness": 9, etc.}

    # Location
    location_city = Column(String)
    location_state = Column(String)
    location_country = Column(String, default="USA")

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Status
    active = Column(Boolean, default=True)

    # Relationships
    matches = relationship("Match", back_populates="customer")


class Provider(Base):
    """Service provider"""
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    company = Column(String)

    # Services
    service_type = Column(String, nullable=False)
    specialties = Column(JSON, default=[])  # ["retirement_planning", "tax_strategy", etc.]
    description = Column(Text)

    # Profile
    years_experience = Column(Integer)
    certifications = Column(JSON, default=[])
    website = Column(String)

    # Pricing
    pricing_model = Column(String)  # hourly, project, retainer, commission
    price_range_low = Column(Float)
    price_range_high = Column(Float)

    # Location
    location_city = Column(String)
    location_state = Column(String)
    location_country = Column(String, default="USA")
    serves_remote = Column(Boolean, default=True)

    # Commission Agreement
    commission_percent = Column(Float, default=20.0)
    commission_agreement_signed = Column(Boolean, default=False)
    commission_agreement_date = Column(DateTime)

    # Performance Metrics
    total_matches = Column(Integer, default=0)
    successful_matches = Column(Integer, default=0)
    avg_rating = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Status
    active = Column(Boolean, default=True)
    accepting_clients = Column(Boolean, default=True)

    # Relationships
    matches = relationship("Match", back_populates="provider")


class Match(Base):
    """A customer-provider match"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)

    customer = relationship("Customer", back_populates="matches")
    provider = relationship("Provider", back_populates="matches")

    # Matching Details
    match_score = Column(Integer, nullable=False)  # 0-100
    match_reasoning = Column(Text)  # AI explanation

    # Criteria Scores (breakdown)
    criteria_scores = Column(JSON, default={})  # {"expertise": 95, "location": 80, etc.}

    # Status
    status = Column(String, default="pending")  # pending, accepted, rejected, completed, failed

    # Customer feedback
    customer_accepted = Column(Boolean)
    customer_feedback = Column(Text)
    customer_rating = Column(Integer)  # 1-5 stars

    # Provider feedback
    provider_accepted = Column(Boolean)
    provider_feedback = Column(Text)

    # Engagement tracking
    intro_sent_at = Column(DateTime)
    first_meeting_at = Column(DateTime)
    engagement_confirmed_at = Column(DateTime)
    deal_value_usd = Column(Float)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    commission = relationship("Commission", back_populates="match", uselist=False)


class Commission(Base):
    """Commission tracking for successful matches"""
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True, index=True)

    # Relationship
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False, unique=True)
    match = relationship("Match", back_populates="commission")

    # Commission Details
    deal_value_usd = Column(Float, nullable=False)
    commission_percent = Column(Float, nullable=False)
    commission_amount_usd = Column(Float, nullable=False)

    # Payment Status
    status = Column(String, default="pending")  # pending, invoiced, paid, failed
    invoice_sent_at = Column(DateTime)
    payment_due_date = Column(DateTime)
    payment_received_at = Column(DateTime)

    # Payment Details
    payment_method = Column(String)  # stripe, wire, check
    stripe_payment_intent_id = Column(String)

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# Create all tables
def init_db():
    """Initialize database"""
    Base.metadata.create_all(bind=engine)


# Dependency for FastAPI
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
