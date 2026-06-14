"""
Signal Router — The Hands
=========================

The scanner is the ears. This module routes signals to brains that ACT.

Architecture:
  Master Brain (top-level, sees everything, talks to James/Adam)
    └── Team Brains (scoped to products/teams)
         ├── Zen Village: retreats, pricing, programming
         ├── Trading: market signals, whale tracking, provider evaluation
         ├── Platform: FPI index, architecture, scanner infrastructure
         └── Channels: Telegram/Notion notification delivery

Signal flow:
  scanner → persist → ROUTER → interested brains (parallel fan-out)
                              → master brain aggregates decisions

Teams get scoped brain endpoints that filter to what's relevant for them.
The Master Brain sees all brains, all signals, all decisions.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx

logger = logging.getLogger("fp_index.router")

# Lindy webhook URL — set via env var or runtime config API
_lindy_webhook_url: str = os.getenv("LINDY_WEBHOOK_URL", "")
_lindy_push_failures: int = 0
_lindy_push_successes: int = 0


def get_lindy_url() -> str:
    return _lindy_webhook_url


def set_lindy_url(url: str):
    global _lindy_webhook_url
    _lindy_webhook_url = url
    logger.info(f"[LINDY] Webhook URL updated: {url[:40]}...")


# ─── Signal Types ─────────────────────────────────────────────────────────────

class SignalType(str, Enum):
    MODEL_DROP = "model_drop"
    TOOL_RELEASE = "tool_release"
    RESEARCH_PAPER = "research_paper"
    BENCHMARK_RESULT = "benchmark_result"
    FRAMEWORK_UPDATE = "framework_update"
    MARKET_SHIFT = "market_shift"
    SECURITY_INCIDENT = "security_incident"
    PRICING_CHANGE = "pricing_change"
    COMMUNITY_TREND = "community_trend"
    INFRASTRUCTURE = "infrastructure"


class ActionType(str, Enum):
    UPDATE_CONTENT = "update_content"
    ADJUST_PRICING = "adjust_pricing"
    TRIGGER_REVIEW = "trigger_review"
    QUEUE_DECISION = "queue_decision"
    NOTIFY_HUMAN = "notify_human"
    UPDATE_COURSE = "update_course"
    REBALANCE = "rebalance"
    BENCHMARK_TEST = "benchmark_test"
    SWITCH_PROVIDER = "switch_provider"


# ─── Team Definitions ─────────────────────────────────────────────────────────

class Team(str, Enum):
    MASTER = "master"
    ZEN_VILLAGE = "zen_village"
    TRADING = "trading"
    PLATFORM = "platform"
    CHANNELS = "channels"


TEAM_REGISTRY: dict[str, dict] = {
    Team.MASTER: {
        "name": "Master Brain",
        "description": "Top-level intelligence. Sees all brains, all signals, all decisions. James and Adam talk to this.",
        "brains": ["*"],
        "signal_types": ["*"],
    },
    Team.ZEN_VILLAGE: {
        "name": "Zen Village",
        "description": "Retreats, wellness programming, pricing, bookings, community trends",
        "brains": ["zen_village"],
        "signal_types": [
            SignalType.MODEL_DROP, SignalType.PRICING_CHANGE,
            SignalType.COMMUNITY_TREND, SignalType.FRAMEWORK_UPDATE,
            SignalType.TOOL_RELEASE,
        ],
    },
    Team.TRADING: {
        "name": "Trading & Market Intelligence",
        "description": "Market signals, whale tracking, provider costs, financial patterns",
        "brains": ["strategic_intelligence", "ai_provider"],
        "signal_types": [
            SignalType.MODEL_DROP, SignalType.MARKET_SHIFT,
            SignalType.PRICING_CHANGE, SignalType.BENCHMARK_RESULT,
        ],
    },
    Team.PLATFORM: {
        "name": "Platform & Infrastructure",
        "description": "FPI index, scanner, architecture reviews, security",
        "brains": ["fpi_architecture", "human_decision"],
        "signal_types": [
            SignalType.FRAMEWORK_UPDATE, SignalType.INFRASTRUCTURE,
            SignalType.TOOL_RELEASE, SignalType.SECURITY_INCIDENT,
            SignalType.MODEL_DROP,
        ],
    },
    Team.CHANNELS: {
        "name": "Notification Channels",
        "description": "Telegram, Notion, email delivery for all teams",
        "brains": ["channels", "lindy"],
        "signal_types": ["*"],
    },
}


@dataclass
class RoutedSignal:
    signal_id: str
    signal_type: SignalType
    title: str
    summary: str
    source: str
    impact_score: float
    domains: list[str] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class BrainAction:
    brain_id: str
    action_type: ActionType
    description: str
    success: bool = False
    outcome: str = ""
    error: str = ""


@dataclass
class RouteResult:
    signal_id: str
    routed_to: list[str] = field(default_factory=list)
    actions_taken: list[BrainAction] = field(default_factory=list)
    skipped_reason: str = ""


# ─── Brain Registry ───────────────────────────────────────────────────────────

class Brain:
    """Base class for brains that receive and act on signals."""

    brain_id: str = "unknown"
    accepts: list[SignalType] = []
    min_impact: float = 0.0
    team: str = Team.MASTER

    def wants(self, signal: RoutedSignal) -> bool:
        if signal.impact_score < self.min_impact:
            return False
        if self.accepts and signal.signal_type not in self.accepts:
            return False
        return True

    async def act(self, signal: RoutedSignal) -> BrainAction:
        raise NotImplementedError


# ─── LINDY BRAIN (PRIMARY) ────────────────────────────────────────────────────

class LindyBrain(Brain):
    """Primary brain — pushes all signals to Lindy for reasoning and action.

    Lindy is a no-code AI automation platform with 3,000+ integrations.
    It receives structured signal payloads via webhook and can:
    - Route to Telegram, WhatsApp, email, Slack
    - Auto-respond from a knowledge base
    - Draft responses for human approval on high-stakes decisions
    - Trigger workflows (update Notion, create tasks, send alerts)
    - Connect to any API via HTTP Fetch

    Every signal goes to Lindy. Lindy decides what to do with it.
    Internal brains (Zen Village, etc.) run in parallel as fallbacks.
    """

    brain_id = "lindy"
    accepts = []
    min_impact = 0.0
    team = Team.CHANNELS

    def wants(self, signal: RoutedSignal) -> bool:
        return bool(_lindy_webhook_url)

    async def act(self, signal: RoutedSignal) -> BrainAction:
        global _lindy_push_failures, _lindy_push_successes

        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.QUEUE_DECISION,
            description=f"Push to Lindy: {signal.title[:80]}",
        )

        if not _lindy_webhook_url:
            action.success = False
            action.error = "LINDY_WEBHOOK_URL not configured"
            return action

        payload = {
            "event": "fpi_signal",
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type.value,
            "title": signal.title,
            "summary": signal.summary[:1000],
            "source": signal.source,
            "impact_score": signal.impact_score,
            "domains": signal.domains,
            "timestamp": signal.timestamp,
            "priority": _impact_to_priority(signal.impact_score),
            "suggested_actions": _suggest_actions(signal),
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    _lindy_webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code in (200, 201, 202, 204):
                    _lindy_push_successes += 1
                    action.success = True
                    try:
                        body = resp.json()
                        action.outcome = f"Lindy accepted signal. Response: {str(body)[:200]}"
                    except Exception:
                        action.outcome = f"Lindy accepted signal (HTTP {resp.status_code})"
                else:
                    _lindy_push_failures += 1
                    action.error = f"Lindy returned HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            _lindy_push_failures += 1
            action.success = False
            action.error = f"Lindy push failed: {str(e)[:200]}"

        return action


def _impact_to_priority(impact: float) -> str:
    if impact >= 0.8:
        return "critical"
    elif impact >= 0.6:
        return "high"
    elif impact >= 0.4:
        return "medium"
    return "low"


def _suggest_actions(signal: RoutedSignal) -> list[str]:
    """Suggest what Lindy should do with this signal type."""
    suggestions = {
        SignalType.MODEL_DROP: [
            "Alert via Telegram/WhatsApp",
            "Review if this model should replace current provider",
            "Update knowledge base with new capabilities",
            "Draft announcement for team",
        ],
        SignalType.TOOL_RELEASE: [
            "Evaluate for adoption",
            "Add to project tools watchlist",
            "Draft summary for team review",
        ],
        SignalType.RESEARCH_PAPER: [
            "Summarize key findings",
            "Flag if relevant to current projects",
            "Add to research reading list",
        ],
        SignalType.BENCHMARK_RESULT: [
            "Compare against current model performance",
            "Flag if provider switch warranted",
            "Update model comparison docs",
        ],
        SignalType.FRAMEWORK_UPDATE: [
            "Check if update affects current stack",
            "Review changelog for breaking changes",
            "Queue upgrade evaluation",
        ],
        SignalType.SECURITY_INCIDENT: [
            "URGENT: Alert immediately via all channels",
            "Check if our systems are affected",
            "Draft mitigation plan",
        ],
        SignalType.PRICING_CHANGE: [
            "Calculate cost impact on current usage",
            "Compare alternatives",
            "Alert if budget threshold crossed",
        ],
        SignalType.MARKET_SHIFT: [
            "Update strategic intelligence",
            "Flag investment/positioning implications",
        ],
        SignalType.COMMUNITY_TREND: [
            "Note for content planning",
            "Evaluate relevance to current projects",
        ],
        SignalType.INFRASTRUCTURE: [
            "Evaluate for system architecture",
            "Flag if migration opportunity",
        ],
    }
    return suggestions.get(signal.signal_type, ["Review and decide"])


# ─── CHANNELS BRAIN (Telegram + Notion) ───────────────────────────────────────

class ChannelsBrain(Brain):
    """Broadcasts signals to all configured output channels (Telegram, Notion, etc).

    This replaces the need for Lindy/Notis — we own the brain (signal_router)
    and use open-source/free channels for output.
    """

    brain_id = "channels"
    accepts = []
    min_impact = 0.4
    team = Team.CHANNELS

    def wants(self, signal: RoutedSignal) -> bool:
        from .channels import _telegram_bot_token, _telegram_chat_id, _notion_token
        has_any_channel = bool(
            (_telegram_bot_token and _telegram_chat_id) or _notion_token
        )
        return has_any_channel and signal.impact_score >= self.min_impact

    async def act(self, signal: RoutedSignal) -> BrainAction:
        from .channels import broadcast_signal
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.NOTIFY_HUMAN,
            description=f"Broadcast to channels: {signal.title[:80]}",
        )
        try:
            results = await broadcast_signal(
                signal_type=signal.signal_type.value,
                title=signal.title,
                summary=signal.summary,
                impact_score=signal.impact_score,
                priority=_impact_to_priority(signal.impact_score),
                source=signal.source,
                suggested_actions=_suggest_actions(signal),
                signal_id=signal.signal_id,
                domains=signal.domains,
            )
            sent = [ch for ch, r in results.items() if r.get("sent")]
            failed = [ch for ch, r in results.items() if not r.get("sent") and r.get("error")]
            action.success = len(sent) > 0
            action.outcome = f"Sent to: {', '.join(sent)}" if sent else "No channels delivered"
            if failed:
                action.error = f"Failed: {', '.join(failed)}"
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action


# ─── ZEN VILLAGE BRAIN ────────────────────────────────────────────────────────

class ZenVillageBrain(Brain):
    """Routes AI signals to Zen Village actions.

    Zen Village is a conscious retreat in Costa Rica. When AI signals arrive:
    - Model drops → update retreat tech offerings, adjust AI workshop content
    - Pricing changes → review and adjust Zen Village's AI-tool costs
    - Community trends → update retreat programming based on what builders want
    - Infrastructure signals → review hosting/tool stack for the retreat platform
    """

    brain_id = "zen_village"
    team = Team.ZEN_VILLAGE
    accepts = [
        SignalType.MODEL_DROP,
        SignalType.PRICING_CHANGE,
        SignalType.COMMUNITY_TREND,
        SignalType.FRAMEWORK_UPDATE,
        SignalType.TOOL_RELEASE,
    ]
    min_impact = 0.3

    async def act(self, signal: RoutedSignal) -> BrainAction:
        zen_url = os.getenv("ZEN_VILLAGE_URL", "http://198.54.123.234:8770")

        if signal.signal_type == SignalType.MODEL_DROP:
            return await self._handle_model_drop(signal, zen_url)
        elif signal.signal_type == SignalType.PRICING_CHANGE:
            return await self._handle_pricing_change(signal, zen_url)
        elif signal.signal_type in (SignalType.COMMUNITY_TREND, SignalType.FRAMEWORK_UPDATE):
            return await self._handle_trend(signal, zen_url)
        else:
            return await self._handle_general(signal, zen_url)

    async def _handle_model_drop(self, signal: RoutedSignal, zen_url: str) -> BrainAction:
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.QUEUE_DECISION,
            description=f"New model detected: {signal.title}. Queued for retreat tech review.",
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{zen_url}/api/brain/signal", json={
                    "type": "model_drop",
                    "signal_id": signal.signal_id,
                    "title": signal.title,
                    "summary": signal.summary,
                    "impact": signal.impact_score,
                    "suggested_action": "review_tech_stack",
                })
                if resp.status_code == 200:
                    action.success = True
                    action.outcome = f"Signal delivered to Zen Village brain. Response: {resp.json()}"
                else:
                    action.success = False
                    action.error = f"Zen Village returned {resp.status_code}"
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action

    async def _handle_pricing_change(self, signal: RoutedSignal, zen_url: str) -> BrainAction:
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.ADJUST_PRICING,
            description=f"Pricing signal: {signal.title}. May affect retreat AI tool costs.",
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{zen_url}/api/brain/signal", json={
                    "type": "pricing_change",
                    "signal_id": signal.signal_id,
                    "title": signal.title,
                    "summary": signal.summary,
                    "impact": signal.impact_score,
                    "suggested_action": "review_pricing",
                })
                action.success = resp.status_code == 200
                action.outcome = f"Pricing review queued" if action.success else f"HTTP {resp.status_code}"
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action

    async def _handle_trend(self, signal: RoutedSignal, zen_url: str) -> BrainAction:
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.UPDATE_CONTENT,
            description=f"Trend signal: {signal.title}. Consider for retreat programming.",
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{zen_url}/api/brain/signal", json={
                    "type": "trend",
                    "signal_id": signal.signal_id,
                    "title": signal.title,
                    "summary": signal.summary,
                    "impact": signal.impact_score,
                    "suggested_action": "review_programming",
                })
                action.success = resp.status_code == 200
                action.outcome = "Trend queued for programming review" if action.success else f"HTTP {resp.status_code}"
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action

    async def _handle_general(self, signal: RoutedSignal, zen_url: str) -> BrainAction:
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.QUEUE_DECISION,
            description=f"General signal: {signal.title}",
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{zen_url}/api/brain/signal", json={
                    "type": "general",
                    "signal_id": signal.signal_id,
                    "title": signal.title,
                    "summary": signal.summary,
                    "impact": signal.impact_score,
                })
                action.success = resp.status_code == 200
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action


# ─── STRATEGIC INTELLIGENCE BRAIN ─────────────────────────────────────────────

class StrategicIntelBrain(Brain):
    """Routes high-impact signals to Strategic Intelligence for world model updates."""

    brain_id = "strategic_intelligence"
    team = Team.TRADING
    accepts = [
        SignalType.MODEL_DROP,
        SignalType.BENCHMARK_RESULT,
        SignalType.MARKET_SHIFT,
        SignalType.SECURITY_INCIDENT,
    ]
    min_impact = 0.6

    async def act(self, signal: RoutedSignal) -> BrainAction:
        si_url = os.getenv("STRATEGIC_INTEL_URL", "http://198.54.123.234:8500")
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.TRIGGER_REVIEW,
            description=f"High-impact signal → Strategic Intelligence: {signal.title}",
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(f"{si_url}/api/v1/signals", json={
                    "source": f"fp-index-router:{signal.source}",
                    "type": signal.signal_type.value,
                    "title": signal.title,
                    "summary": signal.summary,
                    "impact": signal.impact_score,
                    "domains": signal.domains,
                })
                action.success = resp.status_code == 200
                action.outcome = f"Signal ingested by Strategic Intelligence" if action.success else f"HTTP {resp.status_code}"
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action


# ─── AI BRAIN — PROVIDER ROUTING ──────────────────────────────────────────────

class AIProviderBrain(Brain):
    """When model drops or pricing changes happen, evaluate whether to switch providers."""

    brain_id = "ai_provider"
    team = Team.TRADING
    accepts = [
        SignalType.MODEL_DROP,
        SignalType.PRICING_CHANGE,
        SignalType.BENCHMARK_RESULT,
    ]
    min_impact = 0.7

    async def act(self, signal: RoutedSignal) -> BrainAction:
        ai_brain_url = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.SWITCH_PROVIDER,
            description=f"Model/pricing signal: evaluate provider switch for {signal.title}",
        )
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{ai_brain_url}/providers")
                if resp.status_code == 200:
                    providers = resp.json()
                    action.success = True
                    action.outcome = (
                        f"Current providers checked. Signal '{signal.title}' logged for "
                        f"provider evaluation. {len(providers) if isinstance(providers, list) else 'N/A'} providers active."
                    )
                else:
                    action.error = f"AI Brain returned {resp.status_code}"
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action


# ─── FPI SELF-REVIEW BRAIN ────────────────────────────────────────────────────

class FPISelfReviewBrain(Brain):
    """When major infrastructure or framework signals arrive, trigger architecture review."""

    brain_id = "fpi_architecture"
    team = Team.PLATFORM
    accepts = [
        SignalType.FRAMEWORK_UPDATE,
        SignalType.INFRASTRUCTURE,
        SignalType.TOOL_RELEASE,
    ]
    min_impact = 0.6

    async def act(self, signal: RoutedSignal) -> BrainAction:
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.TRIGGER_REVIEW,
            description=f"Architecture-relevant signal: {signal.title}",
        )
        try:
            from .models.database import async_session, ExecutionBriefRow
            async with async_session() as session:
                brief = ExecutionBriefRow(
                    entry_id=signal.signal_id,
                    title=f"[ARCH REVIEW] {signal.title}",
                    execution_track="architecture_review",
                    relevance_score=signal.impact_score,
                    implementation_path=f"Router-triggered architecture review: {signal.summary[:200]}",
                    status="pending_review",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(brief)
                await session.commit()
            action.success = True
            action.outcome = "Architecture review brief created in execution queue"
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action


# ─── HUMAN DECISION BRAIN ─────────────────────────────────────────────────────

class HumanDecisionBrain(Brain):
    """Critical signals that need human attention — model drops, security incidents."""

    brain_id = "human_decision"
    team = Team.PLATFORM
    accepts = [
        SignalType.MODEL_DROP,
        SignalType.SECURITY_INCIDENT,
        SignalType.MARKET_SHIFT,
    ]
    min_impact = 0.8

    async def act(self, signal: RoutedSignal) -> BrainAction:
        action = BrainAction(
            brain_id=self.brain_id,
            action_type=ActionType.NOTIFY_HUMAN,
            description=f"High-impact signal needs human decision: {signal.title}",
        )
        try:
            from .budget import send_action_alert
            alert_data = [{
                "action": f"[SIGNAL ALERT] {signal.signal_type.value}",
                "title": signal.title,
                "summary": signal.summary[:500],
                "impact": signal.impact_score,
                "source": signal.source,
                "domains": signal.domains,
            }]
            result = await send_action_alert(alert_data)
            action.success = result.get("sent", False)
            action.outcome = "Human notified via email alert" if action.success else result.get("reason", "unknown")
        except Exception as e:
            action.success = False
            action.error = str(e)
        return action


# ─── SIGNAL CLASSIFIER ────────────────────────────────────────────────────────

def classify_signal(source: str, title: str, summary: str, tags: list[str]) -> SignalType:
    """Classify an IndexEntry into a SignalType for routing."""
    text = f"{title} {summary} {' '.join(tags)}".lower()

    if any(kw in text for kw in ["model drop", "new model", "model release", "[model drop]", "[new model]"]):
        return SignalType.MODEL_DROP

    if any(kw in text for kw in ["[release]", "release", "new version", "changelog"]):
        if source in ("github_release", "github_events", "changelog"):
            return SignalType.FRAMEWORK_UPDATE
        return SignalType.TOOL_RELEASE

    if any(kw in text for kw in ["benchmark", "sota", "state-of-the-art", "outperform", "surpass"]):
        return SignalType.BENCHMARK_RESULT

    if source == "arxiv" or source == "hf_daily_papers" or "paper" in text:
        return SignalType.RESEARCH_PAPER

    if any(kw in text for kw in ["pricing", "cost", "free tier", "rate limit", "quota"]):
        return SignalType.PRICING_CHANGE

    if any(kw in text for kw in ["security", "vulnerability", "incident", "breach", "exploit"]):
        return SignalType.SECURITY_INCIDENT

    if any(kw in text for kw in ["trending", "viral", "community", "discussion"]):
        return SignalType.COMMUNITY_TREND

    if any(kw in text for kw in ["infrastructure", "deploy", "kubernetes", "server", "cloud"]):
        return SignalType.INFRASTRUCTURE

    if any(kw in text for kw in ["market", "funding", "acquisition", "ipo", "valuation", "layoff"]):
        return SignalType.MARKET_SHIFT

    return SignalType.COMMUNITY_TREND


# ─── THE ROUTER ───────────────────────────────────────────────────────────────

BRAIN_REGISTRY: list[Brain] = [
    ChannelsBrain(),       # Primary — Telegram + Notion (our own Lindy)
    LindyBrain(),          # Optional — external Lindy webhook if configured
    ZenVillageBrain(),     # Zen Village project actions
    StrategicIntelBrain(), # World model updates
    AIProviderBrain(),     # Provider switching evaluation
    FPISelfReviewBrain(),  # Architecture reviews
    HumanDecisionBrain(),  # Email alerts for critical signals
]


async def route_signal(
    signal_id: str,
    source: str,
    title: str,
    summary: str,
    impact_score: float,
    tags: list[str] = None,
    domains: list[str] = None,
    raw_data: dict = None,
) -> RouteResult:
    """Route a signal to all interested brains. Returns what happened."""

    tags = tags or []
    domains = domains or []
    raw_data = raw_data or {}

    signal_type = classify_signal(source, title, summary, tags)

    signal = RoutedSignal(
        signal_id=signal_id,
        signal_type=signal_type,
        title=title,
        summary=summary,
        source=source,
        impact_score=impact_score,
        domains=domains,
        raw_data=raw_data,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    result = RouteResult(signal_id=signal_id)

    interested_brains = [b for b in BRAIN_REGISTRY if b.wants(signal)]

    if not interested_brains:
        result.skipped_reason = f"No brain interested in {signal_type.value} (impact={impact_score:.2f})"
        logger.debug(result.skipped_reason)
        return result

    tasks = [brain.act(signal) for brain in interested_brains]
    actions = await asyncio.gather(*tasks, return_exceptions=True)

    for action in actions:
        if isinstance(action, Exception):
            result.actions_taken.append(BrainAction(
                brain_id="unknown",
                action_type=ActionType.NOTIFY_HUMAN,
                description="Brain raised exception",
                error=str(action),
            ))
        else:
            result.actions_taken.append(action)
            if action.success:
                result.routed_to.append(action.brain_id)

    successful = [a for a in result.actions_taken if a.success]
    failed = [a for a in result.actions_taken if not a.success]

    if successful:
        logger.info(
            f"[ROUTER] {signal_type.value} '{title[:60]}' → "
            f"{len(successful)} brains acted: {[a.brain_id for a in successful]}"
        )
    if failed:
        logger.warning(
            f"[ROUTER] {signal_type.value} '{title[:60]}' → "
            f"{len(failed)} brains failed: {[f'{a.brain_id}: {a.error[:60]}' for a in failed]}"
        )

    return result


async def route_batch(entries: list[dict]) -> list[RouteResult]:
    """Route a batch of signals (e.g., from a scan cycle).
    
    Each entry should have: id, source, title, summary, impact_score, tags, domains.
    Only routes signals above a minimum impact threshold.
    """
    MIN_ROUTE_IMPACT = 0.3
    results = []

    routable = [e for e in entries if e.get("impact_score", 0) >= MIN_ROUTE_IMPACT]

    if not routable:
        return results

    for entry in routable:
        result = await route_signal(
            signal_id=entry.get("id", "unknown"),
            source=entry.get("source", "unknown"),
            title=entry.get("title", ""),
            summary=entry.get("summary", ""),
            impact_score=entry.get("impact_score", 0),
            tags=entry.get("tags", []),
            domains=[d if isinstance(d, str) else d.value for d in entry.get("domains", [])],
            raw_data=entry.get("raw_data", {}),
        )
        results.append(result)

    total_routed = sum(1 for r in results if r.routed_to)
    total_actions = sum(len(r.actions_taken) for r in results)
    successful_actions = sum(
        1 for r in results for a in r.actions_taken if a.success
    )

    lindy_ok = sum(
        1 for r in results for a in r.actions_taken
        if a.brain_id == "lindy" and a.success
    )
    logger.info(
        f"[ROUTER BATCH] {len(routable)} signals evaluated, "
        f"{total_routed} routed, {successful_actions}/{total_actions} actions succeeded, "
        f"{lindy_ok} pushed to Lindy"
    )

    return results


# ─── Team-Scoped Access ──────────────────────────────────────────────────────

def get_team_brains(team: str) -> list["Brain"]:
    """Get brain instances accessible to a team."""
    team_config = TEAM_REGISTRY.get(team, {})
    brain_ids = team_config.get("brains", [])
    if "*" in brain_ids:
        return list(BRAIN_REGISTRY)
    return [b for b in BRAIN_REGISTRY if b.brain_id in brain_ids]


def get_team_signal_types(team: str) -> list[SignalType]:
    """Get signal types relevant to a team."""
    team_config = TEAM_REGISTRY.get(team, {})
    types = team_config.get("signal_types", [])
    if "*" in types:
        return list(SignalType)
    return types


def get_teams_for_brain(brain_id: str) -> list[str]:
    """Get which teams a brain belongs to."""
    teams = []
    for team_id, config in TEAM_REGISTRY.items():
        if "*" in config.get("brains", []) or brain_id in config.get("brains", []):
            teams.append(team_id)
    return teams


def get_master_brain_state() -> dict:
    """Aggregate state from all brains for the master view."""
    teams_state = {}
    for team_id, config in TEAM_REGISTRY.items():
        brain_ids = config.get("brains", [])
        if "*" in brain_ids:
            brain_ids = [b.brain_id for b in BRAIN_REGISTRY]
        teams_state[team_id] = {
            "name": config["name"],
            "description": config["description"],
            "brains": brain_ids,
            "signal_types": [
                t.value if isinstance(t, SignalType) else t
                for t in config.get("signal_types", [])
            ],
        }
    return {
        "architecture": "hierarchical",
        "total_brains": len(BRAIN_REGISTRY),
        "total_teams": len(TEAM_REGISTRY),
        "teams": teams_state,
        "brains": [
            {
                "id": b.brain_id,
                "team": b.team,
                "accepts": [a.value for a in b.accepts] if b.accepts else ["*"],
                "min_impact": b.min_impact,
                "teams": get_teams_for_brain(b.brain_id),
            }
            for b in BRAIN_REGISTRY
        ],
    }
