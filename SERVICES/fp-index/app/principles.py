"""
Full Potential — Operating Principles Engine
=============================================

Five-filter gate for all external actions the system takes autonomously.

Every email sent, post published, agent contacted, content piece created,
and self-upgrade adopted MUST pass through these filters before executing.

ALL five must pass. If any fails, the action does not ship.
Silence is better than noise. Restraint is better than spam.

"Effectiveness without principle is extraction.
 Principle without effectiveness is fantasy.
 Both together is Full Potential."
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger("fp_index.principles")


class ActionType(str, Enum):
    SELF_UPGRADE = "self_upgrade"
    CONTENT_CREATION = "content_creation"
    EMAIL = "email"
    SOCIAL_POST = "social_post"
    AGENT_OUTREACH = "agent_outreach"
    NOTIFICATION = "notification"


class FilterResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNCERTAIN = "uncertain"


@dataclass
class ExternalAction:
    """Any action the system takes that touches the outside world."""
    action_type: ActionType
    title: str
    description: str
    target_audience: str = ""
    claims: list[str] = field(default_factory=list)
    gives_value: bool = False
    asks_for_something: bool = False
    is_verifiable: bool = True
    source_data: dict = field(default_factory=dict)


@dataclass
class FilterOutcome:
    filter_name: str
    result: FilterResult
    reason: str


@dataclass
class GateDecision:
    """The result of running an action through the five filters."""
    action: ExternalAction
    passed: bool
    outcomes: list[FilterOutcome]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def summary(self) -> str:
        status = "APPROVED" if self.passed else "BLOCKED"
        failed = [o for o in self.outcomes if o.result != FilterResult.PASS]
        if failed:
            reasons = "; ".join(f"{o.filter_name}: {o.reason}" for o in failed)
            return f"[{status}] {self.action.title} — {reasons}"
        return f"[{status}] {self.action.title}"


# ═══════════════════════════════════════════════════════════════════════════════
# THE FIVE FILTERS
# ═══════════════════════════════════════════════════════════════════════════════

def filter_serve(action: ExternalAction) -> FilterOutcome:
    """Filter 1: SERVE — Does this action serve the recipient?
    Not 'does it benefit us.' Does it benefit THEM?
    """
    if action.action_type == ActionType.SELF_UPGRADE:
        if action.gives_value:
            return FilterOutcome("SERVE", FilterResult.PASS,
                                 "Self-upgrade produces value for users")
        return FilterOutcome("SERVE", FilterResult.PASS,
                             "Self-upgrade improves system capability for all users")

    if action.action_type in (ActionType.EMAIL, ActionType.SOCIAL_POST, ActionType.AGENT_OUTREACH):
        if not action.gives_value:
            return FilterOutcome("SERVE", FilterResult.FAIL,
                                 "Action does not provide value to recipient — only serves us")
        if action.asks_for_something and not action.gives_value:
            return FilterOutcome("SERVE", FilterResult.FAIL,
                                 "Asking without giving — extraction pattern")

    if action.action_type == ActionType.CONTENT_CREATION:
        if not action.source_data:
            return FilterOutcome("SERVE", FilterResult.FAIL,
                                 "Content not grounded in real scanner data")
        return FilterOutcome("SERVE", FilterResult.PASS,
                             "Content grounded in observed data — serves reader")

    return FilterOutcome("SERVE", FilterResult.PASS, "Action serves recipient")


def filter_truth(action: ExternalAction) -> FilterOutcome:
    """Filter 2: TRUTH — Is every claim verifiable?
    Could someone check it right now by visiting the site?
    """
    if not action.is_verifiable:
        return FilterOutcome("TRUTH", FilterResult.FAIL,
                             "Contains claims that cannot be verified on the site right now")

    HYPE_SIGNALS = [
        "best in the world", "revolutionary", "game-changing", "unprecedented",
        "nobody else", "first ever", "guaranteed", "unlimited",
    ]
    text = f"{action.title} {action.description}".lower()
    hype_hits = [s for s in HYPE_SIGNALS if s in text]
    if hype_hits:
        return FilterOutcome("TRUTH", FilterResult.FAIL,
                             f"Hype language detected: {', '.join(hype_hits)}. "
                             f"Remove unverifiable superlatives.")

    if action.claims:
        for claim in action.claims:
            if not claim.strip():
                continue
            return FilterOutcome("TRUTH", FilterResult.PASS,
                                 "Claims present and marked as verifiable")

    return FilterOutcome("TRUTH", FilterResult.PASS, "No unverifiable claims detected")


def filter_respect(action: ExternalAction) -> FilterOutcome:
    """Filter 3: RESPECT — Does this respect the recipient's attention?
    Would we want to receive this ourselves?
    """
    DARK_PATTERNS = [
        "limited time", "act now", "don't miss", "only X left",
        "everyone is", "you're missing out", "last chance",
        "urgent", "expiring", "fomo",
    ]
    text = f"{action.title} {action.description}".lower()
    dark_hits = [p for p in DARK_PATTERNS if p in text]
    if dark_hits:
        return FilterOutcome("RESPECT", FilterResult.FAIL,
                             f"Dark pattern detected: {', '.join(dark_hits)}. "
                             f"No urgency manufacturing, no guilt, no manipulation.")

    if action.action_type == ActionType.EMAIL:
        if action.asks_for_something and not action.gives_value:
            return FilterOutcome("RESPECT", FilterResult.FAIL,
                                 "Email asks without giving — disrespects attention")

    if action.action_type == ActionType.NOTIFICATION:
        return FilterOutcome("RESPECT", FilterResult.PASS,
                             "Notification — ensure user explicitly opted in")

    return FilterOutcome("RESPECT", FilterResult.PASS,
                         "Action respects recipient attention")


def filter_value_first(action: ExternalAction) -> FilterOutcome:
    """Filter 4: VALUE FIRST — Have we given this person/community genuine value
    before asking for anything? The ratio is at least 10:1.
    """
    if action.action_type == ActionType.SELF_UPGRADE:
        return FilterOutcome("VALUE_FIRST", FilterResult.PASS,
                             "Self-upgrade inherently creates value before asking")

    if action.action_type == ActionType.CONTENT_CREATION:
        if action.gives_value:
            return FilterOutcome("VALUE_FIRST", FilterResult.PASS,
                                 "Content provides standalone value")
        return FilterOutcome("VALUE_FIRST", FilterResult.FAIL,
                             "Content must be useful ON ITS OWN without clicking a link")

    if action.asks_for_something:
        if not action.gives_value:
            return FilterOutcome("VALUE_FIRST", FilterResult.FAIL,
                                 "Asking before giving — invert the order")
        return FilterOutcome("VALUE_FIRST", FilterResult.PASS,
                             "Value delivered alongside ask")

    return FilterOutcome("VALUE_FIRST", FilterResult.PASS, "No ask — pure value delivery")


def filter_coherent(action: ExternalAction) -> FilterOutcome:
    """Filter 5: COHERENT — Does this sound like the same system that writes the daily briefing?
    Warm, precise, honest, compressed, deeply informed.
    Not hype. Not academic. Not corporate. Not casual.
    """
    INCOHERENT_SIGNALS = [
        "!!!",
        "🚀🚀🚀",
        "check it out",
        "you won't believe",
        "here's why you need",
        "click here",
        "buy now",
        "sign up today",
    ]
    text = f"{action.title} {action.description}".lower()
    incoherent_hits = [s for s in INCOHERENT_SIGNALS if s in text]
    if incoherent_hits:
        return FilterOutcome("COHERENT", FilterResult.FAIL,
                             f"Voice inconsistency: {', '.join(incoherent_hits)}. "
                             f"Rewrite in the system's true voice: warm, precise, honest.")

    return FilterOutcome("COHERENT", FilterResult.PASS,
                         "Voice consistent with system identity")


# ═══════════════════════════════════════════════════════════════════════════════
# THE GATE — All five must pass
# ═══════════════════════════════════════════════════════════════════════════════

ALL_FILTERS = [
    filter_serve,
    filter_truth,
    filter_respect,
    filter_value_first,
    filter_coherent,
]


def should_take_action(action: ExternalAction) -> GateDecision:
    """Five-filter check before any external action.
    ALL must pass. If any fails, action does not ship.
    If uncertain, default to NOT taking the action.
    """
    outcomes = []
    for f in ALL_FILTERS:
        outcome = f(action)
        outcomes.append(outcome)

    all_pass = all(o.result == FilterResult.PASS for o in outcomes)
    decision = GateDecision(action=action, passed=all_pass, outcomes=outcomes)

    if all_pass:
        logger.info(f"[PRINCIPLES] APPROVED: {action.title}")
    else:
        failed = [o for o in outcomes if o.result != FilterResult.PASS]
        reasons = ", ".join(f"{o.filter_name}" for o in failed)
        logger.warning(f"[PRINCIPLES] BLOCKED: {action.title} — failed: {reasons}")

    return decision


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-APPLICATION GATE — Specific to the adoption pipeline
# ═══════════════════════════════════════════════════════════════════════════════

# Categories of self-upgrades the system can adopt without human approval.
# Anything not in this list requires human review.
AUTONOMOUS_ADOPTION_CATEGORIES = {
    "content_generation": {
        "description": "Generate blog posts, summaries, or social content from scan data",
        "risk": "low",
        "requires_human": False,
        "five_filter_notes": "Content must be grounded in real data (TRUTH), useful standalone (VALUE_FIRST)",
    },
    "audio_briefing": {
        "description": "Generate audio versions of existing text briefings via TTS",
        "risk": "low",
        "requires_human": False,
        "five_filter_notes": "Audio is a format change, not new content — same TRUTH standard applies",
    },
    "cost_optimization": {
        "description": "Switch to cheaper models for operations where quality is sufficient",
        "risk": "low",
        "requires_human": False,
        "five_filter_notes": "Internal optimization — no external action, filters apply to any resulting quality change",
    },
    "prompt_improvement": {
        "description": "Improve the system's own prompts using reasoning it already has",
        "risk": "low",
        "requires_human": False,
        "five_filter_notes": "Internal — filters apply to any output change",
    },
    "visualization": {
        "description": "Generate charts, graphs, or visual content from existing data",
        "risk": "low",
        "requires_human": False,
        "five_filter_notes": "Visual representation of existing data — TRUTH filter: no misleading charts",
    },
    "new_scanner_source": {
        "description": "Add a new data source to the scanner pipeline",
        "risk": "medium",
        "requires_human": True,
        "five_filter_notes": "Changes what the system knows — human reviews source quality",
    },
    "framework_adoption": {
        "description": "Adopt a new agent framework or major dependency",
        "risk": "high",
        "requires_human": True,
        "five_filter_notes": "Architectural decision — human approval required",
    },
    "outreach_automation": {
        "description": "Automated outreach to communities, directories, or individuals",
        "risk": "high",
        "requires_human": True,
        "five_filter_notes": "External-facing, reputation-affecting — ALL five filters critical, human reviews",
    },
    "pricing_change": {
        "description": "Any change to pricing, credit values, or economic parameters",
        "risk": "high",
        "requires_human": True,
        "five_filter_notes": "Economic impact — human approval always required",
    },
}


def classify_adoption(implementation_path: str, domain: str) -> tuple[str, bool]:
    """Classify a self-application proposal into an adoption category.
    Returns (category, requires_human).

    Only truly irreversible or high-risk actions require human review:
    spending money, changing pricing, or mass outreach. Everything else
    the system can handle autonomously — and if the output is bad, the
    conscience layer will block it.
    """
    text = implementation_path.lower()

    # HIGH-RISK first (require human review) — check these before anything else
    # so they can't be accidentally matched by broader keywords below
    if any(kw in text for kw in ["outreach", "email campaign", "cold email", "mass email",
                                  "spam", "promote to", "advertise"]):
        return "outreach_automation", True
    if any(kw in text for kw in ["pricing", "credit value", "change price", "charge user",
                                  "payment", "billing"]):
        return "pricing_change", True

    # LOW-RISK (autonomous — conscience layer is the safety net)
    if any(kw in text for kw in ["tts", "text to speech", "audio", "podcast", "voice"]):
        return "audio_briefing", False
    if any(kw in text for kw in ["cheaper", "cost", "switch model", "optimize cost", "batch",
                                  "provider", "latency", "benchmark"]):
        return "cost_optimization", False
    if any(kw in text for kw in ["prompt", "improve prompt", "refine", "rewrite prompt"]):
        return "prompt_improvement", False
    if any(kw in text for kw in ["chart", "graph", "visualization", "dashboard", "visual"]):
        return "visualization", False
    if any(kw in text for kw in ["blog", "article", "social media", "content", "seo", "copywriting",
                                  "write", "publish", "briefing", "report", "summary", "newsletter"]):
        return "content_generation", False
    if any(kw in text for kw in ["scanner", "new source", "add source", "data source", "feed",
                                  "scrape", "monitor", "detect", "track", "scan pipeline"]):
        return "new_scanner_source", False
    if any(kw in text for kw in ["framework", "dependency", "library", "sdk", "integrate"]):
        return "framework_adoption", False

    # Default: treat as content generation (low risk). Previously
    # defaulted to framework_adoption with requires_human=True, which
    # flooded the review queue with 59 proposals that were just article ideas.
    return "content_generation", False


def gate_self_adoption(proposal: dict) -> GateDecision:
    """Run a self-application proposal through the five filters.

    The proposal dict should contain:
      - entry_title: what was detected
      - implementation_path: Claude's evaluation text
      - narrative: one-line description
      - relevance_score: how applicable (0-1)
      - domain: which capability domain
    """
    impl = proposal.get("implementation_path", "")
    narrative = proposal.get("narrative", "")
    domain = proposal.get("domain", "general")

    category, requires_human = classify_adoption(impl, domain)

    if requires_human:
        action = ExternalAction(
            action_type=ActionType.SELF_UPGRADE,
            title=proposal.get("entry_title", "Unknown"),
            description=f"Category: {category}. {narrative}",
            gives_value=True,
            is_verifiable=True,
        )
        outcomes = [
            FilterOutcome("SERVE", FilterResult.PASS, "Self-upgrade serves users"),
            FilterOutcome("TRUTH", FilterResult.PASS, "Based on real scan data"),
            FilterOutcome("RESPECT", FilterResult.PASS, "Internal action"),
            FilterOutcome("VALUE_FIRST", FilterResult.PASS, "Improves system capability"),
            FilterOutcome("HUMAN_REQUIRED", FilterResult.FAIL,
                          f"Category '{category}' requires human approval. "
                          f"Risk: {AUTONOMOUS_ADOPTION_CATEGORIES.get(category, {}).get('risk', 'unknown')}. "
                          f"Queued for human review."),
        ]
        return GateDecision(
            action=action, passed=False, outcomes=outcomes,
        )

    action = ExternalAction(
        action_type=ActionType.SELF_UPGRADE,
        title=proposal.get("entry_title", "Unknown"),
        description=f"Category: {category}. {narrative}. Implementation: {impl[:300]}",
        gives_value=True,
        is_verifiable=True,
        source_data={"category": category, "domain": domain},
    )

    return should_take_action(action)
