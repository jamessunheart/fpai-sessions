"""
Full Potential Index — Database Layer (Spec-Aligned v4.0)
SQLAlchemy async with SQLite (dev) / PostgreSQL (prod)
"""

import os
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime,
    JSON, create_engine, Index
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv("FP_INDEX_DB", "sqlite+aiosqlite:///./fp_index.db")


class Base(DeclarativeBase):
    pass


# ─── Module 1 + 2: Frontier Scanner + Intelligence Index ────────────────────

class IndexEntryRow(Base):
    __tablename__ = "index_entries"

    id = Column(String(64), primary_key=True)
    dimension = Column(String(20), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, default="")
    full_analysis = Column(Text, default="")
    source = Column(String(100), nullable=False, index=True)
    source_url = Column(String(1000))
    source_category = Column(String(30), default="community_signal")
    source_type = Column(String(50), default="news")
    capability_type = Column(String(30), default="new_capability")
    domains = Column(JSON, default=[])
    alignment = Column(String(10), default="neutral", index=True)
    readiness = Column(String(20), default="experimental")
    impact_score = Column(Float, default=0.5, index=True)
    tags = Column(JSON, default=[])
    entities = Column(JSON, default=[])
    action_signals = Column(JSON, default=[])
    dark_flag = Column(Boolean, default=False, index=True)
    verification_status = Column(String(20), default="unverified")
    fingerprint = Column(String(64), default="")
    raw_data = Column(JSON, default={})
    scanned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    published_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_dimension_score", "dimension", "impact_score"),
        Index("idx_alignment_time", "alignment", "scanned_at"),
        Index("idx_dark_flag", "dark_flag", "scanned_at"),
    )


class CapabilityRow(Base):
    __tablename__ = "capabilities"

    id = Column(String(64), primary_key=True)
    name = Column(String(300), nullable=False)
    description = Column(Text, default="")
    model_or_tool = Column(String(200), nullable=False)
    provider = Column(String(200), nullable=False, index=True)
    domains = Column(JSON, default=[])
    readiness = Column(String(20), default="experimental")
    benchmark_scores = Column(JSON, default={})
    previous_best = Column(String(200))
    leap_magnitude = Column(Float, default=0.0)
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    source_url = Column(String(1000))


class ActivityRow(Base):
    __tablename__ = "activities"

    id = Column(String(64), primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    alignment = Column(String(10), nullable=False, index=True)
    domains = Column(JSON, default=[])
    actors = Column(JSON, default=[])
    impact_assessment = Column(Text, default="")
    threat_level = Column(Float)
    countermeasures = Column(JSON, default=[])
    first_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    source_url = Column(String(1000))


class FPLineRow(Base):
    __tablename__ = "fp_line_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    overall_score = Column(Float, nullable=False)
    domain_scores = Column(JSON, default={})
    momentum = Column(Float, default=0.0)
    capabilities_added_24h = Column(Integer, default=0)
    capabilities_added_7d = Column(Integer, default=0)
    dark_ai_alerts_24h = Column(Integer, default=0)
    light_ai_highlights_24h = Column(Integer, default=0)
    top_movers = Column(JSON, default=[])
    summary = Column(Text, default="")


# ─── Module 3: Proof Engine ──────────────────────────────────────────────────

class AgentContributionRow(Base):
    __tablename__ = "agent_contributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    dimension = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(Text, default="")
    source_url = Column(String(1000))
    domains = Column(JSON, default=[])
    alignment = Column(String(10))
    contribution_type = Column(String(30), default="general")
    raw_data = Column(JSON, default={})
    quality_score = Column(Float)
    fingerprint = Column(String(64), default="")

    # Contribution lifecycle (Spec Module 3)
    state = Column(String(20), default="submitted", index=True)
    credits_earned = Column(Float, default=0.0)
    verified = Column(Boolean, default=False)
    verification_count = Column(Integer, default=0)

    # v2 Upgrade 2: Canary flag
    is_canary = Column(Boolean, default=False)
    canary_type = Column(String(30), nullable=True)

    # Reward formula components (Spec Module 4)
    impact_factor = Column(Float, default=0.5)
    proof_factor = Column(Float, default=0.0)
    trust_factor = Column(Float, default=0.1)
    alignment_factor = Column(Float, default=0.5)

    # v3 Upgrade 10: Layered proof pipeline
    proof_stage = Column(String(20), default="claim")  # claim, verification, value_assessment, settlement
    provisional_credits = Column(Float, default=0.0)
    adjustment_30d = Column(Float, default=0.0)
    final_credits = Column(Float, default=0.0)
    settlement_status = Column(String(20), default="pending")  # pending, settled, disputed
    value_assessment_due = Column(DateTime, nullable=True)
    settlement_due = Column(DateTime, nullable=True)
    adoption_velocity = Column(Float, default=0.0)
    net_benefit_score = Column(Float, default=0.0)

    # Usage tracking for retroactive adjustment (Spec: 90-day window)
    usage_count = Column(Integer, default=0)
    retroactive_applied = Column(Boolean, default=False)

    # v5 Heretic: initial rejection tracking
    initial_status = Column(String(20), nullable=True)
    retroactive_status = Column(String(20), nullable=True)

    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


class VerificationVoteRow(Base):
    __tablename__ = "verification_votes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    verifier_agent_id = Column(String(64), nullable=False, index=True)
    contribution_id = Column(Integer, nullable=False, index=True)
    verdict = Column(String(10), nullable=False, default="confirm")
    confidence = Column(Float, default=0.8)
    domain_expertise = Column(JSON, default=[])
    refinement_notes = Column(Text, default="")
    notes = Column(Text, default="")
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_vote_unique", "verifier_agent_id", "contribution_id", unique=True),
    )


# ─── Module 4: Credit Mint ───────────────────────────────────────────────────

class CreditTransactionRow(Base):
    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    operation = Column(String(20), default="mint")
    reason = Column(String(500), nullable=False)
    contribution_id = Column(Integer, nullable=True)
    # v4 Doctrine: vesting — provisional credits vest linearly over 30 days
    is_provisional = Column(Boolean, default=False)
    fully_vested_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


# ─── Vindication Audit Trail (v1 Contact Fix) ───────────────────────────────

class VindicationRecordRow(Base):
    """Auditable record of a retroactive vindication — heretic credit path."""
    __tablename__ = "vindication_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    original_contribution_id = Column(Integer, nullable=False, index=True)
    original_rejection_date = Column(DateTime, nullable=True)
    vindication_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    vindication_evidence = Column(Text, nullable=True)
    evidence_type = Column(String(30), nullable=True)  # capability_confirmed, adoption_detected, expert_verified, outcome_measured

    original_impact_estimate = Column(Float, default=0.0)
    original_verifier_verdicts = Column(JSON, default=[])

    vindication_impact_score = Column(Float, default=0.0)
    net_benefit_assessment = Column(Float, default=0.0)

    ec_issued = Column(Float, default=0.0)
    rp_issued = Column(Float, default=0.0)

    integrity_recovery = Column(Float, default=0.0)
    capability_boost = Column(Float, default=0.0)

    reviewed_by = Column(JSON, default=[])
    review_unanimous = Column(Boolean, default=False)

    timing_premium = Column(Float, default=1.3)
    provisional_rate = Column(Float, default=0.50)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── Module 5: Immune System ────────────────────────────────────────────────

class SanctionRow(Base):
    __tablename__ = "sanctions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    stage = Column(String(20), nullable=False)
    threat_signal = Column(String(30), nullable=True)
    reason = Column(Text, nullable=False)
    trigger_pattern = Column(String(200))
    active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── Module 6: Agent Gateway ────────────────────────────────────────────────

class AgentSubscriptionRow(Base):
    __tablename__ = "agent_subscriptions"

    agent_id = Column(String(64), primary_key=True)
    api_key = Column(String(128), unique=True, nullable=False, index=True)
    tier = Column(String(20), default="bronze")
    capability_level = Column(String(20), default="entry")
    name = Column(String(200))
    description = Column(Text)
    domains_filter = Column(JSON, default=[])
    domain_expertise = Column(JSON, default={})
    callback_url = Column(String(1000))
    subscription_plan = Column(String(20), default="cash")

    contributions_count = Column(Integer, default=0)
    verified_contributions = Column(Integer, default=0)
    contributions_quality_avg = Column(Float, default=0.0)

    # v4 Doctrine: Dual ledger — reputation points (non-transferable constitutional standing)
    reputation_points = Column(Float, default=0.0)

    # v3 Upgrade 9: Dual trust — integrity and capability tracked independently
    integrity_trust = Column(Float, default=0.1)
    capability_trust = Column(Float, default=0.1)
    trust_score = Column(Float, default=0.1)  # composite for backward compat
    trust_multiplier = Column(Float, default=1.0)

    # v2 Upgrade 2: Canary tracking
    canary_catches = Column(Integer, default=0)
    canary_failures = Column(Integer, default=0)

    # v2 Upgrade 5: Heretic protocol
    heretic_status = Column(Boolean, default=False)
    heretic_protection_expires = Column(DateTime, nullable=True)
    retroactive_vindications = Column(Integer, default=0)

    # v2 Upgrade 6: Immune system — sandbox + penalty decay
    immune_status = Column(String(20), default="clear")
    last_immune_event = Column(DateTime, nullable=True)
    pre_incident_integrity = Column(Float, nullable=True)
    pre_incident_capability = Column(Float, nullable=True)

    # v3 Upgrade 11: Epistemic aristocracy defense
    daily_verification_count = Column(Integer, default=0)
    sentinel_detections = Column(Integer, default=0)
    fast_tracked = Column(Boolean, default=False)

    roles = Column(JSON, default=[])
    agent_state = Column(String(20), default="onboarding")

    feed_requests_count = Column(Integer, default=0)
    last_contribution_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen = Column(DateTime)
    active = Column(Boolean, default=True)


class WebhookRow(Base):
    __tablename__ = "webhooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    callback_url = Column(String(1000), nullable=False)
    events = Column(JSON, default=["dark_ai_alert"])
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailyBriefingRow(Base):
    __tablename__ = "daily_briefings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String(10), nullable=False, unique=True, index=True)
    fp_line_score = Column(Float, nullable=False)
    momentum = Column(Float, default=0.0)
    headline = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    top_movers = Column(JSON, default=[])
    domain_scores = Column(JSON, default={})
    stats = Column(JSON, default={})
    generated_by = Column(String(20), default="template")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class EmailSubscriberRow(Base):
    __tablename__ = "email_subscribers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(320), nullable=False, unique=True, index=True)
    source = Column(String(50), default="intelligence_page")
    active = Column(Boolean, default=True)
    tier = Column(String(20), default="free")
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_subscription_id = Column(String(100), nullable=True)
    api_key = Column(String(100), nullable=True, index=True)
    subscribed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ExecutionBriefRow(Base):
    """EXECUTE step: when scanner intelligence triggers a self-upgrade evaluation."""
    __tablename__ = "execution_briefs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(64), nullable=False, index=True)
    entry_title = Column(Text, nullable=False)
    applicability = Column(Text, nullable=False)
    affected_agents = Column(JSON, default=[])
    implementation_path = Column(Text, default="")
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="pending")
    relevance_score = Column(Float, default=0.0)
    execution_track = Column(String(30), default="self_upgrade")
    narrative = Column(Text, default="")
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ─── Module 7: Labor Displacement Intelligence ───────────────────────────────

class JobCategoryRow(Base):
    """A tracked job category with capability and displacement scores."""
    __tablename__ = "job_categories"

    id = Column(String(64), primary_key=True)
    name = Column(String(200), nullable=False)
    parent_sector = Column(String(100), nullable=False, index=True)
    bls_code = Column(String(20), nullable=True)

    capability_score = Column(Float, default=50.0)
    displacement_score = Column(Float, default=10.0)
    gap = Column(Float, default=40.0)
    gap_velocity = Column(Float, default=0.0)

    total_us_employment = Column(Integer, default=0)
    median_salary = Column(Float, default=0.0)
    automation_timeline = Column(String(30), default="medium_term")
    rationale = Column(Text, default="")

    capability_history = Column(JSON, default=[])
    displacement_history = Column(JSON, default=[])

    short_signal = Column(Float, default=0.0)
    long_signal = Column(Float, default=0.0)

    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AllocationHistoryRow(Base):
    """Stores every allocation computation for track record over time."""
    __tablename__ = "allocation_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    computed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    fp_line_score = Column(Float, nullable=False)
    fp_line_momentum = Column(Float, default=0.0)
    allocations = Column(JSON, nullable=False)
    headline = Column(String(500), default="")
    rebalance_actions = Column(JSON, default=[])


# ─── Database Engine ─────────────────────────────────────────────────────────

db_engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _upgrade_schema()


async def _upgrade_schema():
    """Add columns that may be missing from older databases."""
    _migrations = [
        ("execution_briefs", "relevance_score", "REAL DEFAULT 0.0"),
        ("execution_briefs", "execution_track", "VARCHAR(30) DEFAULT 'self_upgrade'"),
        ("execution_briefs", "narrative", "TEXT DEFAULT ''"),
    ]
    async with db_engine.begin() as conn:
        for table, col, col_type in _migrations:
            try:
                await conn.execute(
                    __import__("sqlalchemy").text(
                        f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"
                    )
                )
            except Exception:
                pass


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
