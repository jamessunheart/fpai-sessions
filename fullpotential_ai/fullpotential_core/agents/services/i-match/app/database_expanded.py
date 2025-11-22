"""Expanded database schema for Full Potential Realization Engine"""

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import enum

from .config import settings

# Create engine
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {})

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()


# === Enums ===

class UserType(str, enum.Enum):
    SEEKER = "seeker"
    PROVIDER = "provider"
    BOTH = "both"

class MatchType(str, enum.Enum):
    PROVIDER = "provider"
    PRODUCT = "product"
    OPPORTUNITY = "opportunity"
    RESOURCE = "resource"
    EXPERIENCE = "experience"

class OpportunityType(str, enum.Enum):
    JOB = "job"
    INVESTMENT = "investment"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    COLLABORATION = "collaboration"

class ResourceType(str, enum.Enum):
    CAPITAL = "capital"
    KNOWLEDGE = "knowledge"
    CONNECTION = "connection"
    ACCESS = "access"
    DATA = "data"
    TOOL = "tool"

class ExperienceType(str, enum.Enum):
    COURSE = "course"
    EVENT = "event"
    MASTERMIND = "mastermind"
    RETREAT = "retreat"
    MENTORSHIP = "mentorship"
    WORKSHOP = "workshop"

class TokenTransactionType(str, enum.Enum):
    EARN_MATCH_REWARD = "earn_match_reward"
    SPEND_MATCH_ACCESS = "spend_match_access"
    STAKE_QUALITY = "stake_quality"
    UNSTAKE = "unstake"
    EARN_COMMISSION = "earn_commission"
    REFERRAL_BONUS = "referral_bonus"


# === Unified User Model ===

class User(Base):
    """Unified user model for seekers and providers"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)

    # User type
    user_type = Column(String, default=UserType.SEEKER)

    # Goals and challenges
    goals = Column(JSON, default=[])  # ["Scale to $10M", "Build better team"]
    challenges = Column(JSON, default=[])  # ["Low conversion", "Poor hiring"]

    # Preferences and values
    preferences = Column(JSON, default={})
    values = Column(JSON, default={})

    # Budget
    budget_low = Column(Float)
    budget_high = Column(Float)

    # Location
    location_city = Column(String)
    location_state = Column(String)
    location_country = Column(String, default="USA")

    # Token economy
    token_balance = Column(Float, default=0.0)  # FPAI tokens held
    tokens_earned_total = Column(Float, default=0.0)
    tokens_spent_total = Column(Float, default=0.0)
    tokens_staked = Column(Float, default=0.0)

    # Performance
    match_success_rate = Column(Float, default=0.0)
    total_value_unlocked = Column(Float, default=0.0)  # Total USD value from all matches

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    active = Column(Boolean, default=True)

    # Relationships
    matches = relationship("MatchUnified", back_populates="user")
    token_transactions = relationship("TokenTransaction", back_populates="user")


# === Products ===

class Product(Base):
    """Products that can be matched to users"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    category = Column(String, nullable=False, index=True)  # saas, software, equipment, tools
    subcategory = Column(String)

    # Vendor
    vendor_name = Column(String)
    vendor_email = Column(String)
    vendor_website = Column(String)

    # Pricing
    price_model = Column(String)  # one-time, subscription, usage-based, tiered
    price_low = Column(Float)
    price_high = Column(Float)
    currency = Column(String, default="USD")

    # Affiliate program
    affiliate_program = Column(String)  # partnerstack, impact, sharesale, amazon
    affiliate_commission_percent = Column(Float)  # 10-30%
    affiliate_commission_type = Column(String)  # one-time, recurring, hybrid
    affiliate_link = Column(String)

    # Product details
    features = Column(JSON, default=[])
    integrations = Column(JSON, default=[])
    target_audience = Column(JSON, default=[])
    use_cases = Column(JSON, default=[])

    # Trial/Demo
    trial_available = Column(Boolean, default=False)
    demo_available = Column(Boolean, default=False)

    # Performance
    ratings_avg = Column(Float)
    reviews_count = Column(Integer, default=0)
    total_matches = Column(Integer, default=0)
    successful_matches = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    active = Column(Boolean, default=True)


# === Opportunities ===

class Opportunity(Base):
    """Job, investment, partnership, acquisition opportunities"""
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    opportunity_type = Column(String, nullable=False, index=True)  # job, investment, partnership, acquisition

    # Company/Organization
    company_name = Column(String)
    company_industry = Column(String)
    company_stage = Column(String)  # startup, growth, mature
    company_website = Column(String)

    # Value
    value_low = Column(Float)
    value_high = Column(Float)
    currency = Column(String, default="USD")

    # Additional compensation
    equity_offered = Column(Float)  # Percentage
    token_offered = Column(Float)  # Number of tokens

    # Requirements and benefits
    requirements = Column(JSON, default=[])
    benefits = Column(JSON, default=[])

    # Timing
    time_commitment = Column(String)  # full-time, part-time, contract, one-time
    location_requirement = Column(String)  # remote, hybrid, on-site
    application_deadline = Column(DateTime)
    start_date = Column(DateTime)

    # Commission structure
    finder_fee_percent = Column(Float)  # 3-20%
    finder_fee_fixed = Column(Float)  # Fixed fee in USD
    commission_structure = Column(JSON, default={})  # Detailed structure

    # Status
    status = Column(String, default="open")  # open, filled, closed

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    active = Column(Boolean, default=True)


# === Resources ===

class Resource(Base):
    """Capital, knowledge, connections, access, data, tools"""
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    resource_type = Column(String, nullable=False, index=True)  # capital, knowledge, connection, access, data, tool

    # Provider
    provider_name = Column(String)
    provider_type = Column(String)  # individual, company, network
    provider_contact = Column(String)

    # Access model
    access_model = Column(String)  # one-time, subscription, pay-per-use, free
    cost_low = Column(Float)
    cost_high = Column(Float)
    currency = Column(String, default="USD")

    # Commission
    commission_model = Column(String)  # percentage, fixed, hybrid
    commission_percent = Column(Float)
    commission_fixed = Column(Float)

    # Requirements and restrictions
    requirements = Column(JSON, default=[])
    restrictions = Column(JSON, default=[])

    # Availability
    availability = Column(String)  # immediate, scheduled, application-based
    capacity_limit = Column(Integer)  # Max number of users

    # Value proposition
    value_proposition = Column(JSON, default={})

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    active = Column(Boolean, default=True)


# === Experiences ===

class Experience(Base):
    """Courses, events, masterminds, retreats, mentorships"""
    __tablename__ = "experiences"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    experience_type = Column(String, nullable=False, index=True)  # course, event, mastermind, retreat, mentorship

    # Organizer
    organizer_name = Column(String)
    organizer_website = Column(String)
    organizer_contact = Column(String)

    # Format
    format = Column(String)  # online, in-person, hybrid
    duration = Column(String)  # "6 weeks", "3 days", "1 year"
    schedule = Column(JSON, default={})  # Detailed schedule

    # Pricing
    price = Column(Float)
    payment_plans = Column(JSON, default=[])

    # Commission
    commission_percent = Column(Float)  # 20-40%
    recurring_commission = Column(Boolean, default=False)

    # Capacity
    capacity = Column(Integer)
    spots_remaining = Column(Integer)

    # Timing
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    registration_deadline = Column(DateTime)

    # Requirements and outcomes
    prerequisites = Column(JSON, default=[])
    outcomes = Column(JSON, default=[])  # What participants will achieve

    # Performance
    ratings_avg = Column(Float)
    reviews_count = Column(Integer, default=0)
    total_participants = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    active = Column(Boolean, default=True)


# === Service Providers (Keep existing for backward compatibility) ===

class Provider(Base):
    """Service provider (legacy - keeping for backward compatibility)"""
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String)
    company = Column(String)

    # Services
    service_type = Column(String, nullable=False)
    specialties = Column(JSON, default=[])
    description = Column(Text)

    # Profile
    years_experience = Column(Integer)
    certifications = Column(JSON, default=[])
    website = Column(String)

    # Pricing
    pricing_model = Column(String)
    price_range_low = Column(Float)
    price_range_high = Column(Float)

    # Location
    location_city = Column(String)
    location_state = Column(String)
    location_country = Column(String, default="USA")
    serves_remote = Column(Boolean, default=True)

    # Commission
    commission_percent = Column(Float, default=20.0)
    commission_agreement_signed = Column(Boolean, default=False)
    commission_agreement_date = Column(DateTime)

    # Performance
    total_matches = Column(Integer, default=0)
    successful_matches = Column(Integer, default=0)
    avg_rating = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    active = Column(Boolean, default=True)
    accepting_clients = Column(Boolean, default=True)


# === Unified Match Model ===

class MatchUnified(Base):
    """Unified match model for all match types"""
    __tablename__ = "matches_unified"

    id = Column(Integer, primary_key=True, index=True)

    # User (seeker)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="matches")

    # Match type and item (polymorphic)
    match_type = Column(String, nullable=False, index=True)  # provider, product, opportunity, resource, experience
    match_item_id = Column(Integer, nullable=False)  # ID in respective table

    # AI Matching
    match_score = Column(Integer, nullable=False)  # 0-100
    match_reasoning = Column(Text)  # AI explanation
    criteria_scores = Column(JSON, default={})  # Breakdown

    # Status
    status = Column(String, default="pending")  # pending, accepted, rejected, completed, failed

    # Token economy
    tokens_spent = Column(Float, default=0.0)  # Tokens spent to access this match
    tokens_earned = Column(Float, default=0.0)  # Tokens earned from successful match

    # Financial
    deal_value_usd = Column(Float)
    commission_amount_usd = Column(Float)
    commission_percent = Column(Float)

    # Payment
    payment_status = Column(String, default="pending")  # pending, invoiced, paid, failed
    payment_method = Column(String)  # cash, tokens, hybrid
    payment_cash_amount = Column(Float)  # USD amount
    payment_token_amount = Column(Float)  # Token amount

    # Feedback
    user_feedback = Column(Text)
    user_rating = Column(Integer)  # 1-5 stars

    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    completed_at = Column(DateTime)


# === Token Transactions ===

class TokenTransaction(Base):
    """Token transaction ledger"""
    __tablename__ = "token_transactions"

    id = Column(Integer, primary_key=True, index=True)

    # User
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="token_transactions")

    # Transaction details
    transaction_type = Column(String, nullable=False, index=True)
    amount_tokens = Column(Float, nullable=False)  # Positive for earn, negative for spend
    amount_usd_value = Column(Float)  # USD value at time of transaction

    # Related match (if applicable)
    match_id = Column(Integer, ForeignKey("matches_unified.id"))

    # Description and metadata
    description = Column(Text)
    metadata = Column(JSON, default={})

    # Timestamp
    created_at = Column(DateTime, default=datetime.now)


# === Database Initialization ===

def init_db_expanded():
    """Initialize expanded database"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
