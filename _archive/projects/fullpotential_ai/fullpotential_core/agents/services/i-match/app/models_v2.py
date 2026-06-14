"""
Database Models V2 for I MATCH Marketplace
Supports multi-category marketplace + POTENTIAL (POT) token system
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, DECIMAL, CheckConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


# ============================================================================
# CORE IDENTITY & CURRENCY
# ============================================================================

class User(Base):
    """Unified user identity across platform"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50))
    password_hash = Column(String(255))  # For future auth system

    # POT Token balances
    pot_balance = Column(Integer, default=0)
    total_pot_earned = Column(Integer, default=0)
    total_pot_spent = Column(Integer, default=0)
    total_pot_burned = Column(Integer, default=0)

    # Account metadata
    account_type = Column(String(20), default='seeker')  # 'seeker', 'provider', 'both'
    verified = Column(Boolean, default=False)
    verified_at = Column(DateTime)

    # Reputation
    rating_average = Column(DECIMAL(3, 2), default=0.00)
    rating_count = Column(Integer, default=0)

    # Status
    status = Column(String(20), default='active')  # 'active', 'suspended', 'deleted'

    # Tracking
    last_login_at = Column(DateTime)
    login_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    seekers = relationship("Seeker", back_populates="user")
    providers = relationship("Provider", back_populates="user")
    pot_transactions = relationship("POTTransaction", back_populates="user")
    referrals_made = relationship("Referral", foreign_keys="Referral.referrer_id", back_populates="referrer")
    referrals_received = relationship("Referral", foreign_keys="Referral.referred_id", back_populates="referred")
    content = relationship("Content", back_populates="user")

    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_status', 'status'),
        Index('idx_users_account_type', 'account_type'),
    )


class Category(Base):
    """Marketplace categories (financial_advisors, career_coaches, etc.)"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # 'financial_advisors'
    display_name = Column(String(255), nullable=False)  # 'Financial Advisors'
    description = Column(Text)
    icon = Column(String(50))  # Emoji or icon identifier

    # Launch tracking
    launched_at = Column(DateTime)
    active = Column(Boolean, default=True)

    # Economics
    commission_rate = Column(DECIMAL(5, 2), default=20.00)  # % commission

    # Matching configuration
    matching_criteria = Column(JSON)  # Category-specific criteria weights
    intake_questions = Column(JSON)   # Questions to ask seekers
    profile_fields = Column(JSON)     # Required provider profile fields

    # Metrics
    provider_count = Column(Integer, default=0)
    seeker_count = Column(Integer, default=0)
    match_count = Column(Integer, default=0)
    engagement_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    seekers = relationship("Seeker", back_populates="category")
    providers = relationship("Provider", back_populates="category")
    matches = relationship("Match", back_populates="category")
    engagements = relationship("Engagement", back_populates="category")

    __table_args__ = (
        Index('idx_categories_active', 'active'),
        Index('idx_categories_name', 'name'),
    )


# ============================================================================
# MARKETPLACE PARTICIPANTS
# ============================================================================

class Seeker(Base):
    """People looking for growth opportunities (customers)"""
    __tablename__ = "seekers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Core needs
    needs_description = Column(Text, nullable=False)
    budget_min = Column(Integer)
    budget_max = Column(Integer)
    location = Column(String(255))

    # Preferences
    format_preference = Column(String(20))  # 'in-person', 'remote', 'either'
    urgency = Column(String(20))  # 'immediate', 'this_week', 'this_month', 'flexible'

    # Category-specific data
    additional_criteria = Column(JSON)

    # Status
    status = Column(String(20), default='active')  # 'active', 'matched', 'engaged', 'completed'

    # Tracking
    match_count = Column(Integer, default=0)
    engagement_count = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship("User", back_populates="seekers")
    category = relationship("Category", back_populates="seekers")
    matches = relationship("Match", back_populates="seeker")
    engagements = relationship("Engagement", back_populates="seeker")

    __table_args__ = (
        Index('idx_seekers_user_id', 'user_id'),
        Index('idx_seekers_category_id', 'category_id'),
        Index('idx_seekers_status', 'status'),
    )


class Provider(Base):
    """Service providers across all categories"""
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Business info
    business_name = Column(String(255))
    bio = Column(Text)
    website = Column(String(500))
    linkedin_url = Column(String(500))

    # Expertise
    specialties = Column(JSON)  # Array of specialization strings
    years_experience = Column(Integer)
    certifications = Column(JSON)  # Array of certification objects
    languages = Column(JSON)  # Array of language strings

    # Pricing
    pricing_min = Column(Integer)
    pricing_max = Column(Integer)
    pricing_model = Column(String(50))  # 'hourly', 'project', 'retainer', 'commission'

    # Logistics
    location = Column(String(255))
    formats_offered = Column(JSON)  # ['in-person', 'remote', 'hybrid']
    availability = Column(String(100))  # 'full-time', 'part-time', 'weekends'

    # Category-specific profile
    additional_profile = Column(JSON)

    # Status
    status = Column(String(20), default='pending')  # 'pending', 'approved', 'active', 'suspended'
    approved_at = Column(DateTime)

    # Premium features
    boosted_until = Column(DateTime)  # Profile boost expiration
    featured_until = Column(DateTime)  # Featured listing expiration
    verified_badge = Column(Boolean, default=False)

    # Tracking
    lead_count = Column(Integer, default=0)
    engagement_count = Column(Integer, default=0)
    response_count = Column(Integer, default=0)
    avg_response_time_hours = Column(DECIMAL(6, 2))

    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # Relationships
    user = relationship("User", back_populates="providers")
    category = relationship("Category", back_populates="providers")
    matches = relationship("Match", back_populates="provider")
    engagements = relationship("Engagement", back_populates="provider")

    __table_args__ = (
        Index('idx_providers_user_id', 'user_id'),
        Index('idx_providers_category_id', 'category_id'),
        Index('idx_providers_status', 'status'),
        Index('idx_providers_boosted', 'boosted_until'),
    )


# ============================================================================
# MATCHING & ENGAGEMENT
# ============================================================================

class Match(Base):
    """AI-generated seeker-provider matches"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    seeker_id = Column(Integer, ForeignKey("seekers.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Match quality
    match_score = Column(DECIMAL(5, 2), nullable=False)  # 0.00 to 100.00
    match_reasoning = Column(Text)  # AI-generated explanation
    criteria_breakdown = Column(JSON)  # Scores for each criterion
    strengths = Column(JSON)  # Array of strength strings
    concerns = Column(JSON)  # Array of concern strings

    # Status tracking
    status = Column(String(20), default='suggested')  # 'suggested', 'viewed', 'contacted', 'engaged'

    # Engagement tracking
    viewed_at = Column(DateTime)
    contacted_at = Column(DateTime)
    engaged_at = Column(DateTime)
    declined_at = Column(DateTime)
    decline_reason = Column(Text)

    # Metadata
    match_batch_id = Column(String(100))  # Group matches from same request

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    seeker = relationship("Seeker", back_populates="matches")
    provider = relationship("Provider", back_populates="matches")
    category = relationship("Category", back_populates="matches")
    engagement = relationship("Engagement", back_populates="match", uselist=False)

    __table_args__ = (
        Index('idx_matches_seeker_id', 'seeker_id'),
        Index('idx_matches_provider_id', 'provider_id'),
        Index('idx_matches_category_id', 'category_id'),
        Index('idx_matches_status', 'status'),
        Index('idx_matches_score', 'match_score'),
    )


class Engagement(Base):
    """Confirmed seeker-provider relationships (revenue events)"""
    __tablename__ = "engagements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    seeker_id = Column(Integer, ForeignKey("seekers.id", ondelete="CASCADE"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    # Deal economics (USD)
    deal_value_usd = Column(DECIMAL(10, 2), nullable=False)
    commission_rate = Column(DECIMAL(5, 2), nullable=False)  # % commission
    commission_usd = Column(DECIMAL(10, 2), nullable=False)

    # Deal economics (POT)
    commission_pot = Column(Integer, default=0)  # Provider bonus in POT
    seeker_bonus_pot = Column(Integer, default=100)  # Seeker bonus

    # Status
    status = Column(String(20), default='confirmed')  # 'confirmed', 'active', 'completed', 'cancelled'

    # Lifecycle
    confirmed_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)

    # Invoicing
    invoice_sent_at = Column(DateTime)
    invoice_due_at = Column(DateTime)
    payment_received_at = Column(DateTime)
    payment_amount = Column(DECIMAL(10, 2))

    # Metadata
    notes = Column(Text)

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    match = relationship("Match", back_populates="engagement")
    seeker = relationship("Seeker", back_populates="engagements")
    provider = relationship("Provider", back_populates="engagements")
    category = relationship("Category", back_populates="engagements")
    ratings = relationship("Rating", back_populates="engagement")

    __table_args__ = (
        Index('idx_engagements_match_id', 'match_id'),
        Index('idx_engagements_seeker_id', 'seeker_id'),
        Index('idx_engagements_provider_id', 'provider_id'),
        Index('idx_engagements_category_id', 'category_id'),
        Index('idx_engagements_status', 'status'),
    )


class Rating(Base):
    """Reviews from both parties after engagement"""
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    engagement_id = Column(Integer, ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Rating details
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review_text = Column(Text)
    would_recommend = Column(Boolean)

    # Dimensions (optional detailed ratings)
    expertise_rating = Column(Integer)  # 1-5
    communication_rating = Column(Integer)  # 1-5
    professionalism_rating = Column(Integer)  # 1-5
    value_rating = Column(Integer)  # 1-5

    # Rewards
    pot_earned = Column(Integer, default=10)  # POT reward for rating

    # Metadata
    public = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    engagement = relationship("Engagement", back_populates="ratings")

    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
        CheckConstraint('expertise_rating IS NULL OR (expertise_rating >= 1 AND expertise_rating <= 5)', name='check_expertise_rating'),
        CheckConstraint('communication_rating IS NULL OR (communication_rating >= 1 AND communication_rating <= 5)', name='check_communication_rating'),
        CheckConstraint('professionalism_rating IS NULL OR (professionalism_rating >= 1 AND professionalism_rating <= 5)', name='check_professionalism_rating'),
        CheckConstraint('value_rating IS NULL OR (value_rating >= 1 AND value_rating <= 5)', name='check_value_rating'),
        Index('idx_ratings_engagement_id', 'engagement_id'),
        Index('idx_ratings_from_user', 'from_user_id'),
        Index('idx_ratings_to_user', 'to_user_id'),
        Index('idx_ratings_public', 'public'),
    )


# ============================================================================
# POT TOKEN SYSTEM
# ============================================================================

class POTTransaction(Base):
    """Internal currency ledger for POTENTIAL tokens"""
    __tablename__ = "pot_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Transaction details
    amount = Column(Integer, nullable=False)  # Positive = earned, Negative = spent
    transaction_type = Column(String(20), nullable=False)  # 'earn', 'spend', 'burn', 'redeem'
    category = Column(String(50), nullable=False)  # Specific reason
    description = Column(Text)

    # Reference to related record
    reference_type = Column(String(50))  # 'engagement', 'rating', 'profile', etc.
    reference_id = Column(Integer)

    # Balance tracking
    balance_before = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)

    # Metadata
    metadata = Column(JSON)

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User", back_populates="pot_transactions")

    __table_args__ = (
        Index('idx_pot_transactions_user_id', 'user_id'),
        Index('idx_pot_transactions_type', 'transaction_type'),
        Index('idx_pot_transactions_category', 'category'),
        Index('idx_pot_transactions_created_at', 'created_at'),
    )


class Referral(Base):
    """Track referral program rewards"""
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    referrer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    referred_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Referral details
    referral_type = Column(String(20), nullable=False)  # 'seeker', 'provider'
    referral_code = Column(String(50))  # Unique code (optional)

    # Status
    status = Column(String(20), default='pending')  # 'pending', 'completed', 'rewarded'

    # Rewards
    pot_bonus = Column(Integer)  # 250 for seeker, 500 for provider

    # Lifecycle
    completed_at = Column(DateTime)  # When referred user completed action
    rewarded_at = Column(DateTime)   # When POT was awarded

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    referrer = relationship("User", foreign_keys=[referrer_id], back_populates="referrals_made")
    referred = relationship("User", foreign_keys=[referred_id], back_populates="referrals_received")

    __table_args__ = (
        Index('idx_referrals_referrer_id', 'referrer_id'),
        Index('idx_referrals_referred_id', 'referred_id'),
        Index('idx_referrals_status', 'status'),
    )


class Content(Base):
    """User-generated content for POT rewards"""
    __tablename__ = "content"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Content details
    content_type = Column(String(50), nullable=False)  # 'guide', 'video', 'testimonial', etc.
    title = Column(String(500), nullable=False)
    body = Column(Text)
    url = Column(String(1000))  # If external

    # Categorization
    category_id = Column(Integer, ForeignKey("categories.id"))  # Associated category
    tags = Column(JSON)  # Array of tags

    # Review and approval
    status = Column(String(20), default='pending')  # 'pending', 'approved', 'published', 'rejected'
    reviewer_notes = Column(Text)
    approved_by = Column(Integer, ForeignKey("users.id"))

    # Rewards
    pot_earned = Column(Integer, default=0)

    # Lifecycle
    approved_at = Column(DateTime)
    published_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User", back_populates="content", foreign_keys=[user_id])

    __table_args__ = (
        Index('idx_content_user_id', 'user_id'),
        Index('idx_content_status', 'status'),
        Index('idx_content_type', 'content_type'),
    )
