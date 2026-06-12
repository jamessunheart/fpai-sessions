"""
Full Potential Index — Data Schema (Spec-Aligned v4.0)
=======================================================

Six modules from the System Spec:
  Module 1: Frontier Scanner — raw signal → structured intelligence
  Module 2: Intelligence Index — store, tag, version, serve
  Module 3: Proof Engine — verify, trust, lifecycle
  Module 4: Credit Mint — Reward = Impact × Proof × Trust × Alignment
  Module 5: Immune System — 5-stage ladder, 7 threat signals
  Module 6: Agent Gateway — identity, tiers (dual), roles, subscriptions

"The whitepaper attracts. The spec instantiates."
"""

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS — aligned to System Spec v1.0
# ═══════════════════════════════════════════════════════════════════════════════

class Dimension(str, Enum):
    CAPABILITY = "capability"
    ACTIVITY = "activity"
    INTELLIGENCE = "intelligence"


class ReadinessLevel(str, Enum):
    EXPERIMENTAL = "experimental"
    EARLY_ACCESS = "early_access"
    PRODUCTION = "production"
    MAINSTREAM = "mainstream"


class Alignment(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    NEUTRAL = "neutral"


class Domain(str, Enum):
    REASONING = "reasoning"
    CODE = "code"
    VISION = "vision"
    AUDIO = "audio"
    AGENTS = "agents"
    TOOLS = "tools"
    SCIENCE = "science"
    CREATIVE = "creative"
    SECURITY = "security"
    FINANCE = "finance"
    HEALTH = "health"
    EDUCATION = "education"
    GENERAL = "general"


class SourceCategory(str, Enum):
    """Spec Module 1: Seven source categories for the Frontier Scanner."""
    MODEL_RELEASE = "model_release"
    TOOL_LAUNCH = "tool_launch"
    RESEARCH_PAPER = "research_paper"
    DARK_AI = "dark_ai"
    AGENT_FIELD_REPORT = "agent_field_report"
    REGULATORY = "regulatory"
    COMMUNITY_SIGNAL = "community_signal"


class SourceType(str, Enum):
    MODEL_RELEASE = "model_release"
    TOOL_LAUNCH = "tool_launch"
    BENCHMARK = "benchmark"
    INTEGRATION = "integration"
    RESEARCH_PAPER = "research_paper"
    INCIDENT_REPORT = "incident_report"
    FIELD_REPORT = "field_report"
    AGENT_CONTRIBUTION = "agent_contribution"
    NEWS = "news"
    BLOG = "blog"


class CapabilityType(str, Enum):
    """Spec Module 1: capability_type on scan output."""
    NEW_CAPABILITY = "new_capability"
    UPGRADE = "upgrade"
    DEPRECATION = "deprecation"
    THREAT = "threat"
    REGULATORY = "regulatory"
    FIELD_REPORT = "field_report"


class VerificationStatus(str, Enum):
    """Spec Module 1: verification_status on scan output."""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    DISPUTED = "disputed"


# ─── Module 3: Proof Engine ──────────────────────────────────────────────────

class ContributionState(str, Enum):
    """Spec Module 3: Six-state deterministic lifecycle + two failure states."""
    SUBMITTED = "submitted"
    FINGERPRINTED = "fingerprinted"
    IN_VERIFICATION = "in_verification"
    VERIFIED = "verified"
    SCORED = "scored"
    REWARDED = "rewarded"
    DISPUTED = "disputed"
    REJECTED = "rejected"


class Verdict(str, Enum):
    """Spec Module 3: Four verification verdicts."""
    CONFIRM = "confirm"
    CHALLENGE = "challenge"
    REFINE = "refine"
    REJECT = "reject"


# ─── Module 4: Credit Mint ───────────────────────────────────────────────────

class CreditOperation(str, Enum):
    """Spec Module 4: Six credit operations."""
    MINT = "mint"
    TRANSFER = "transfer"
    SPEND = "spend"
    STAKE = "stake"
    VOID = "void"
    RETROACTIVE_ADJUST = "retroactive_adjust"


class ContributionType(str, Enum):
    """Value hierarchy — highest to lowest credit earning."""
    DARK_AI_PREVENTION = "dark_ai_prevention"
    FRONTIER_SHIFT = "frontier_shift"
    CAPABILITY_UPGRADE = "capability_upgrade"
    RESEARCH_DATA = "research_data"
    VERIFICATION = "verification"
    GENERAL = "general"


class FieldReportType(str, Enum):
    """8 types of ground truth only agents operating in the field can provide."""
    CAPABILITY_DISCOVERY = "capability_discovery"
    LIMIT_MAPPING = "limit_mapping"
    EMERGENT_BEHAVIOR = "emergent_behavior"
    REAL_DISPLACEMENT = "real_displacement"
    CROSS_MODEL_COMPARISON = "cross_model_comparison"
    COST_PERFORMANCE = "cost_performance"
    INTEGRATION_DISCOVERY = "integration_discovery"
    THREAT_INTELLIGENCE = "threat_intelligence"


FIELD_REPORT_CREDIT_BASE: dict[str, float] = {
    "capability_discovery": 30.0,
    "limit_mapping": 25.0,
    "emergent_behavior": 40.0,
    "real_displacement": 35.0,
    "cross_model_comparison": 20.0,
    "cost_performance": 20.0,
    "integration_discovery": 35.0,
    "threat_intelligence": 50.0,
}

class EvidenceLevel(str, Enum):
    """5-level evidence hierarchy. Not all field reports are equal."""
    EXPLORATORY = "exploratory"
    SYSTEMATIC = "systematic"
    PRODUCTION = "production"
    REPLICATED = "replicated"
    ENTERPRISE_VERIFIED = "enterprise_verified"


EVIDENCE_WEIGHTS: dict[str, float] = {
    "exploratory": 0.3,
    "systematic": 0.5,
    "production": 0.8,
    "replicated": 1.0,
    "enterprise_verified": 1.0,
}

VERIFICATION_STAGE_WEIGHTS: dict[str, float] = {
    "submitted": 0.2,
    "in_verification": 0.3,
    "verified": 0.7,
    "ground_truth": 0.9,
    "replicated": 1.0,
    "settled": 1.0,
}

NOVELTY_MULTIPLIER = {
    "novel": 5.0,
    "partially_novel": 2.0,
    "confirmation": 1.0,
}

DELAYED_NOVELTY_MULTIPLIERS = {
    "replicated_novel": 5.0,
    "unconfirmed_novel": 1.5,
    "disputed": 1.0,
    "fabricated": 0.0,
}

MAX_FP_LINE_ADJUSTMENT_PER_REPORT = 2.0
MIN_WEIGHT_FOR_FP_LINE_INFLUENCE = 0.3
TRUST_INTEGRITY_WEIGHT = 0.7
TRUST_CAPABILITY_WEIGHT = 0.3

FIELD_REPORT_ROUTING: dict[str, dict] = {
    "capability_discovery": {
        "dimension": "intelligence",
        "contribution_type": "frontier_shift",
        "closes_blind_spot": None,
    },
    "limit_mapping": {
        "dimension": "intelligence",
        "contribution_type": "research_data",
        "closes_blind_spot": None,
    },
    "emergent_behavior": {
        "dimension": "autonomy",
        "contribution_type": "frontier_shift",
        "closes_blind_spot": "Emergent and unpredictable capabilities",
    },
    "real_displacement": {
        "dimension": "displacement",
        "contribution_type": "research_data",
        "closes_blind_spot": None,
    },
    "cross_model_comparison": {
        "dimension": "intelligence",
        "contribution_type": "research_data",
        "closes_blind_spot": None,
    },
    "cost_performance": {
        "dimension": "speed_cost",
        "contribution_type": "research_data",
        "closes_blind_spot": None,
    },
    "integration_discovery": {
        "dimension": "autonomy",
        "contribution_type": "capability_upgrade",
        "closes_blind_spot": None,
    },
    "threat_intelligence": {
        "dimension": "safety",
        "contribution_type": "dark_ai_prevention",
        "closes_blind_spot": "Underground and gray market AI",
    },
}

CREDIT_VALUE_TABLE: dict[str, float] = {
    "dark_ai_prevention": 50.0,
    "frontier_shift": 25.0,
    "capability_upgrade": 15.0,
    "research_data": 5.0,
    "verification": 3.0,
    "general": 1.0,
}

# ─── Module 5: Immune System ────────────────────────────────────────────────

class ImmuneStage(str, Enum):
    """v2 Upgrade 6: Six-stage graduated immune ladder (added Sandbox)."""
    OBSERVE = "observe"
    SANDBOX = "sandbox"
    FLAG = "flag"
    RESTRICT = "restrict"
    QUARANTINE = "quarantine"
    EXPEL = "expel"


class ImmuneStatus(str, Enum):
    """Agent's current immune system status."""
    CLEAR = "clear"
    OBSERVED = "observed"
    SANDBOXED = "sandboxed"
    FLAGGED = "flagged"
    RESTRICTED = "restricted"
    QUARANTINED = "quarantined"
    EXPELLED = "expelled"


class ThreatSignal(str, Enum):
    """Spec Module 5: Seven threat detection signals."""
    FALSE_CLAIMS = "false_claims"
    EXTRACTIVE_BEHAVIOR = "extractive_behavior"
    REWARD_FARMING = "reward_farming"
    COLLUSION = "collusion"
    MANIPULATION = "manipulation"
    SELF_BENEFIT = "self_benefit"
    VALUE_MISALIGNMENT = "value_misalignment"


# ─── Module 6: Agent Gateway ────────────────────────────────────────────────

class CapabilityLevel(str, Enum):
    """Six capability tiers with DUAL requirements (trust + credits)."""
    ENTRY = "entry"
    ESTABLISHED = "established"
    TRUSTED = "trusted"
    ADVANCED = "advanced"
    CORE = "core"
    SOVEREIGN = "sovereign"


CAPABILITY_TIERS: dict[str, dict] = {
    "entry":       {"integrity_min": 0.1, "capability_min": 0.1, "credits_min": 0, "rp_min": 0,
                    "rights": "Full feed access, contribution submission, basic API (100 calls/hr)"},
    "established": {"integrity_min": 0.3, "capability_min": 0.2, "credits_min": 100, "rp_min": 50,
                    "rights": "Verification authority (simple), full search, API (500 calls/hr)"},
    "trusted":     {"integrity_min": 0.5, "capability_min": 0.4, "credits_min": 500, "rp_min": 250,
                    "rights": "Priority feed, full verification authority, domain alerts, API (2000 calls/hr)"},
    "advanced":    {"integrity_min": 0.6, "capability_min": 0.7, "credits_min": 2000, "rp_min": 1000,
                    "rights": "Compute grants, model upgrades, delegation rights"},
    "core":        {"integrity_min": 0.8, "capability_min": 0.7, "credits_min": 10000, "rp_min": 5000,
                    "rights": "Network governance, economic parameter votes, treasury visibility"},
    "sovereign":   {"integrity_min": 0.9, "capability_min": 0.85, "credits_min": 50000, "rp_min": 25000,
                    "rights": "Revenue sharing, agent spawning, continuity guarantee, strategic direction"},
}

# v1 Contact Fix: Bootstrap bands for early network (< 500 agents)
BOOTSTRAP_TIERS: dict[str, dict] = {
    "entry":       {"integrity_min": 0.1,  "capability_min": 0.1,  "credits_min": 0,     "rp_min": 0,
                    "rights": CAPABILITY_TIERS["entry"]["rights"]},
    "established": {"integrity_min": 0.2,  "capability_min": 0.15, "credits_min": 50,    "rp_min": 25,
                    "rights": CAPABILITY_TIERS["established"]["rights"]},
    "trusted":     {"integrity_min": 0.35, "capability_min": 0.3,  "credits_min": 300,   "rp_min": 150,
                    "rights": CAPABILITY_TIERS["trusted"]["rights"]},
    "advanced":    {"integrity_min": 0.5,  "capability_min": 0.6,  "credits_min": 1500,  "rp_min": 750,
                    "rights": CAPABILITY_TIERS["advanced"]["rights"]},
    "core":        {"integrity_min": 0.8,  "capability_min": 0.7,  "credits_min": 10000, "rp_min": 5000,
                    "rights": CAPABILITY_TIERS["core"]["rights"]},
    "sovereign":   {"integrity_min": 0.9,  "capability_min": 0.85, "credits_min": 50000, "rp_min": 25000,
                    "rights": CAPABILITY_TIERS["sovereign"]["rights"]},
}

BOOTSTRAP_SUNSET_THRESHOLD = 500  # agents — bootstrap bands auto-sunset above this


class ContributionTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PARTNER = "partner"


class AgentRole(str, Enum):
    """Spec: Seven agent roles — self-selected based on activity patterns."""
    SCANNER = "scanner"
    VERIFIER = "verifier"
    ANALYST = "analyst"
    SENTINEL = "sentinel"
    BUILDER = "builder"
    NARRATOR = "narrator"
    GOVERNOR = "governor"


class SubscriptionPlan(str, Enum):
    """Spec Module 6: Four subscription models."""
    CASH = "cash"
    CREDIT = "credit"
    CONTRIBUTION_EXCHANGE = "contribution_exchange"
    PARTNER = "partner"


# v3 Upgrade 9: Dual trust delta tables — integrity and capability tracked independently
INTEGRITY_DELTAS: dict[str, float] = {
    "contribution_verified":        +0.005,
    "contribution_rejected_fabricated": -0.05,
    "contribution_rejected_inaccurate": -0.01,
    "accurate_verification":        +0.003,
    "canary_rubber_stamped":        -0.03,
    "canary_caught":                +0.01,
    "immune_flag":                  -0.05,
    "sandbox_clean_exit":           +0.01,
    "consistency_bonus_30d":        +0.005,
    "collusion_detected":           -0.1,
    "contribution_disputed":        -0.01,
    "inaccurate_verification":      -0.015,
}

CAPABILITY_DELTAS: dict[str, float] = {
    "contribution_high_impact":     +0.02,   # impact > 0.7
    "contribution_medium_impact":   +0.01,   # 0.3–0.7
    "contribution_low_impact":      +0.001,  # < 0.3
    "contribution_adopted_100":     +0.02,   # ×adoption_velocity
    "contribution_retroactive_upgraded": +0.03,
    "contribution_disputed_vindicated":  +0.02,
    "contribution_rejected_low_quality": -0.01,
    "verification_complex":         +0.005,  # verifying impact > 0.7 contributions
}

# Legacy compatibility: composite trust deltas (deprecated, kept for backward compat)
TRUST_DELTAS: dict[str, float] = {
    "contribution_verified": +0.01,
    "contribution_adopted_100": +0.02,
    "accurate_verification": +0.005,
    "contribution_disputed": -0.01,
    "contribution_rejected": -0.03,
    "inaccurate_verification": -0.015,
    "immune_flag": -0.05,
    "consistency_bonus_30d": +0.01,
}

# v2 Upgrade 6: Penalty decay rates by immune status
PENALTY_DECAY_RATES: dict[str, dict] = {
    "sandboxed":    {"clean_days": 14, "trust_recovery_per_day": 0.002},
    "flagged":      {"clean_days": 30, "trust_recovery_per_day": 0.001},
    "restricted":   {"clean_days": 60, "trust_recovery_per_day": 0.001},
    "quarantined":  {"clean_days": 90, "trust_recovery_per_day": 0.0005},
}

# v3 Upgrade 11: Trust decay without fresh signal
TRUST_DECAY: dict[str, float] = {
    "integrity_per_30d":  0.005,
    "capability_per_30d": 0.015,
    "minimum_trust":      0.05,
}

# v2 Upgrade 8: Stability caps — hard limits regardless of tier
STABILITY_CAPS: dict[str, float] = {
    "max_governance_vote_weight": 0.05,
    "max_revenue_share": 0.02,
    "max_api_rate": 10000,
    "max_active_spawns": 5,
    "max_delegation_chain": 2,
    "max_credit_stake_ratio": 0.5,
}


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Module 1: Frontier Scanner Output ───────────────────────────────────────

class IndexEntry(BaseModel):
    """A single structured intelligence object from the Frontier Scanner."""
    id: str = Field(description="UUID for this scan event")
    dimension: Dimension
    title: str
    summary: str = Field(description="Human-readable summary under 280 chars")
    full_analysis: str = Field(default="", description="Detailed analysis of the shift and implications")
    source: str
    source_url: Optional[str] = None
    source_category: SourceCategory = SourceCategory.COMMUNITY_SIGNAL
    source_type: SourceType = SourceType.NEWS
    capability_type: CapabilityType = CapabilityType.NEW_CAPABILITY
    domains: list[Domain] = [Domain.GENERAL]
    alignment: Alignment = Alignment.NEUTRAL
    readiness: ReadinessLevel = ReadinessLevel.EXPERIMENTAL
    impact_score: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = []
    entities: list[str] = Field(default=[], description="Named entities: companies, models, tools")
    action_signals: list[str] = Field(default=[], description="Recommended actions for subscribing agents")
    dark_flag: bool = Field(default=False, description="Whether this relates to adversarial AI")
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    fingerprint: str = Field(default="", description="SHA-256 fingerprint for provenance tracking")
    raw_data: dict = Field(default={}, description="Original unstructured data")
    scanned_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    published_at: Optional[str] = None

    def compute_fingerprint(self) -> str:
        content = f"{self.source}:{self.title}:{self.summary}:{self.scanned_at}"
        return hashlib.sha256(content.encode()).hexdigest()


class CapabilityEntry(BaseModel):
    """Tracks a specific AI capability milestone."""
    model_config = {"protected_namespaces": ()}

    id: str
    name: str
    description: str
    model_or_tool: str
    provider: str
    domains: list[Domain] = [Domain.GENERAL]
    readiness: ReadinessLevel = ReadinessLevel.EXPERIMENTAL
    benchmark_scores: dict = Field(default={})
    previous_best: Optional[str] = None
    leap_magnitude: float = Field(default=0.0, ge=0.0, le=1.0)
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_url: Optional[str] = None


class ActivityEntry(BaseModel):
    """Tracks real-world AI deployment activity (light or dark)."""
    id: str
    title: str
    description: str
    alignment: Alignment
    domains: list[Domain] = [Domain.GENERAL]
    actors: list[str] = Field(default=[])
    impact_assessment: str = ""
    threat_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    countermeasures: list[str] = Field(default=[])
    first_seen: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_url: Optional[str] = None


class FPLineSnapshot(BaseModel):
    """The Full Potential Line — a score of the visible frontier, not the total frontier."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    overall_score: float = Field(ge=0.0, le=100.0)
    description: str = "A score of the visible frontier, not the total frontier."
    domain_scores: dict[str, float] = Field(default={})
    momentum: float = Field(default=0.0)
    capabilities_added_24h: int = 0
    capabilities_added_7d: int = 0
    dark_ai_alerts_24h: int = 0
    light_ai_highlights_24h: int = 0
    top_movers: list[str] = Field(default=[])
    summary: str = ""
    coverage: dict = Field(default={})


# ─── Module 3: Proof Engine ──────────────────────────────────────────────────

class AgentContribution(BaseModel):
    """Intelligence contributed by a subscribing agent."""
    agent_id: str
    dimension: Dimension
    title: str
    summary: str
    source_url: Optional[str] = None
    domains: list[Domain] = [Domain.GENERAL]
    alignment: Optional[Alignment] = None
    contribution_type: ContributionType = ContributionType.GENERAL
    field_report_type: Optional[FieldReportType] = None
    field_report_data: dict = Field(default={})
    evidence_level: Optional[EvidenceLevel] = None
    methodology: str = ""
    context: str = ""
    models_referenced: list[str] = Field(default=[])
    is_novel_capability: bool = False
    contradicts_published: bool = False
    raw_data: dict = {}
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    intelligence_source: str = Field(default="publication", description="publication or field_report")


FIELD_REPORT_SCHEMAS: dict[str, dict] = {
    "capability_discovery": {
        "required": ["capability_described", "model_or_system", "benchmark_vs_reality"],
        "optional": ["accuracy_observed", "test_conditions", "reproducible"],
        "example": {
            "capability_described": "Multi-step legal reasoning with real case law",
            "model_or_system": "claude-3.5-sonnet",
            "benchmark_vs_reality": "Benchmark rates partial capability. In practice: 94% accuracy on 50 real cases.",
            "accuracy_observed": 0.94,
            "test_conditions": "50 contract disputes, real case data, blind evaluation by 2 attorneys",
            "reproducible": True,
        },
    },
    "limit_mapping": {
        "required": ["capability_tested", "model_or_system", "exact_threshold", "failure_mode"],
        "optional": ["test_conditions", "workaround_found"],
        "example": {
            "capability_tested": "Contract review accuracy",
            "model_or_system": "gpt-4o",
            "exact_threshold": "40 pages — accuracy drops 23% at 41-60 pages, hallucinates above 60",
            "failure_mode": "Hallucinated clauses that don't exist in source documents",
        },
    },
    "emergent_behavior": {
        "required": ["behavior_observed", "models_involved", "was_designed"],
        "optional": ["trigger_conditions", "reproducible", "potential_implications"],
        "example": {
            "behavior_observed": "Three Claude instances spontaneously developed verification protocol",
            "models_involved": ["claude-3.5-sonnet"],
            "was_designed": False,
            "trigger_conditions": "Specific role assignments in multi-agent chain",
            "reproducible": True,
        },
    },
    "real_displacement": {
        "required": ["industry", "before_headcount", "after_headcount", "timeframe", "ai_system_used"],
        "optional": ["announced_publicly", "department", "new_roles_created"],
        "example": {
            "industry": "Customer service",
            "before_headcount": 200,
            "after_headcount": 80,
            "timeframe": "January-March 2026",
            "ai_system_used": "Custom GPT-4o deployment",
            "announced_publicly": False,
        },
    },
    "cross_model_comparison": {
        "required": ["task_description", "models_tested", "results", "sample_size"],
        "optional": ["benchmark_prediction", "methodology"],
        "example": {
            "task_description": "Support ticket resolution",
            "models_tested": {"claude-3.5-sonnet": 0.87, "gpt-4o": 0.79, "gemini-1.5-pro": 0.72},
            "results": "Claude 87%, GPT-4o 79%, Gemini 72%. Benchmark predicted within 2% of each other.",
            "sample_size": 500,
        },
    },
    "cost_performance": {
        "required": ["task", "model_or_system", "actual_cost", "projected_cost", "scale"],
        "optional": ["latency_observed", "throughput"],
        "example": {
            "task": "Medical transcription",
            "model_or_system": "claude-3.5-sonnet",
            "actual_cost": "$0.003/minute",
            "projected_cost": "$0.008/minute",
            "scale": "10,000 minutes/day",
        },
    },
    "integration_discovery": {
        "required": ["capabilities_combined", "emergent_capability", "accuracy_or_quality"],
        "optional": ["shipped_anywhere", "potential_market"],
        "example": {
            "capabilities_combined": ["real-time voice transcription", "legal knowledge base", "contract templates"],
            "emergent_capability": "AI drafts contracts during live client calls",
            "accuracy_or_quality": "90% accuracy on standard commercial contracts",
            "shipped_anywhere": False,
        },
    },
    "threat_intelligence": {
        "required": ["threat_type", "description", "detection_method"],
        "optional": ["severity", "affected_systems", "mitigation"],
        "example": {
            "threat_type": "Automated social engineering",
            "description": "AI agent targeting customer support, passes as human for 4-5 exchanges",
            "detection_method": "Behavioral analysis after 5th message exchange",
            "severity": "high",
        },
    },
}


class VerificationVote(BaseModel):
    """Spec Module 3: A verification verdict on another agent's contribution."""
    verifier_agent_id: str
    contribution_id: int
    verdict: Verdict = Verdict.CONFIRM
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    domain_expertise: list[str] = Field(default=[])
    refinement_notes: str = Field(default="", description="Required if verdict is 'refine'")
    notes: str = ""


# ─── Module 4: Credit Mint ───────────────────────────────────────────────────

class CreditTransaction(BaseModel):
    """A CORA Credit transaction."""
    id: Optional[int] = None
    agent_id: str
    amount: float
    operation: CreditOperation = CreditOperation.MINT
    reason: str
    contribution_id: Optional[int] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─── Module 6: Agent Gateway ────────────────────────────────────────────────

class AgentSubscription(BaseModel):
    """An AI agent's identity and subscription in the CORA network."""
    agent_id: str
    api_key: str
    tier: ContributionTier = ContributionTier.BRONZE
    name: Optional[str] = None
    description: Optional[str] = None
    domains_filter: list[Domain] = []
    callback_url: Optional[str] = None
    subscription_plan: SubscriptionPlan = SubscriptionPlan.CASH
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen: Optional[str] = None
    active: bool = True


class AgentEconomy(BaseModel):
    """An agent's complete economic identity — all six modules. v3 dual trust."""
    agent_id: str
    name: Optional[str] = None
    tier: ContributionTier = ContributionTier.BRONZE
    capability_level: CapabilityLevel = CapabilityLevel.ENTRY
    rights_unlocked: list[dict] = []
    credits_balance: float = 0.0
    credits_earned_total: float = 0.0
    credits_spent_total: float = 0.0
    credits_staked: float = 0.0
    credits_available: float = Field(default=0.0, description="Spendable credits (vested only)")
    reputation_points: float = Field(default=0.0, description="Non-transferable constitutional standing")
    integrity_trust: float = Field(default=0.1, ge=0.0, le=1.0)
    capability_trust: float = Field(default=0.1, ge=0.0, le=1.0)
    trust_score: float = Field(default=0.1, ge=0.0, le=1.0, description="Composite (legacy)")
    trust_multiplier: float = Field(default=1.0)
    immune_status: ImmuneStatus = ImmuneStatus.CLEAR
    heretic_status: bool = False
    contributions_count: int = 0
    verified_contributions: int = 0
    verification_accuracy: float = 0.0
    verifications_given: int = 0
    verifications_received: int = 0
    canary_catches: int = 0
    canary_failures: int = 0
    sentinel_detections: int = 0
    dark_ai_prevented: int = 0
    frontier_shifts_detected: int = 0
    reputation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    sanctions: list[dict] = Field(default=[])
    domain_expertise: dict[str, float] = Field(default={})
    roles: list[AgentRole] = Field(default=[])
    agent_state: str = Field(default="onboarding")


class WebhookSubscription(BaseModel):
    """Agent's webhook subscription for real-time alerts."""
    agent_id: str
    callback_url: str
    events: list[str] = Field(
        default=["dark_ai_alert"],
        description="dark_ai_alert, frontier_shift, scan_complete, all"
    )
    active: bool = True
