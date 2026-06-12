"""
Reasoning Engine - transforms raw system state and external data into
actionable intelligence for God Mode.

Now with Graduated Intelligence:
- Queries past learnings before making recommendations
- Tracks decision outcomes for confidence calibration
- Adjusts recommendations based on historical accuracy
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("reasoning_engine")


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
TEAM_HUB_URL = os.getenv("TEAM_HUB_URL", "http://localhost:8355")
DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://162.0.208.88:8125")
REASONING_INTERVAL = int(os.getenv("REASONING_INTERVAL_SECONDS", "300"))
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# In-memory stores
SNAPSHOTS: List[Dict[str, Any]] = []
DECISIONS: List[Any] = []  # List of Decision objects
LAST_RUN: Optional[datetime] = None

# Outcome tracking for confidence calibration
OUTCOME_HISTORY: List[Dict[str, Any]] = []
CONFIDENCE_CALIBRATION: Dict[str, Dict] = {}  # decision_type -> {predicted_sum, actual_sum, count}
DECISION_TYPE_ACCURACY: Dict[str, Dict] = {}  # Track accuracy by decision type

app = FastAPI(title="Reasoning Engine", version="0.2.0")


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class DecisionOption(BaseModel):
    id: str
    label: str
    description: Optional[str] = None
    api_endpoint: Optional[str] = None
    http_method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None


class EvidenceItem(BaseModel):
    """Evidence from past learnings supporting a decision."""
    memory_id: Optional[str] = None
    summary: str
    outcome: str  # positive, negative, neutral
    relevance_score: float = 0.0
    timestamp: Optional[str] = None


class Decision(BaseModel):
    id: str
    type: str  # SCALE | INVESTIGATE | ALERT | OPTIMIZE | INTEGRATE
    priority: str  # low | medium | high | critical
    title: str
    description: str
    why: str
    why_detailed: Optional[str] = None  # Evidence-based explanation
    cost_estimate: Optional[str] = None
    benefit_estimate: Optional[str] = None
    time_estimate: Optional[str] = None
    confidence: float = 0.5
    base_confidence: float = 0.5  # Before calibration
    calibrated: bool = False  # Whether confidence was adjusted based on history
    evidence: List[EvidenceItem] = []  # Past learnings supporting this decision
    similar_situations_count: int = 0
    historical_success_rate: Optional[float] = None
    options: List[DecisionOption] = []
    created_at: datetime
    expires_at: Optional[datetime] = None
    status: str = "pending"  # pending | executed | dismissed | expired


class Briefing(BaseModel):
    summary: str
    highlights: List[str]
    trends: Dict[str, Any]
    top_decisions: List[Decision]
    coherence_score: float
    generated_at: datetime
    ai_generated: bool = False


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def fetch_json(url: str, timeout: float = 30.0) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            logger.warning(f"fetch_json failed: {url} returned {resp.status_code}")
            return {}  # Return empty dict instead of raising to allow partial data
        return resp.json()


def pct_change(current: float, previous: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100


def record_snapshot(state: Dict[str, Any]) -> None:
    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "treasury": state.get("identity", {}).get("treasury", {}).get("total_assets", 0),
        "runway_days": state.get("identity", {}).get("treasury", {}).get("runway_days", 0),
        "gpu_cost_hourly": state.get("identity", {}).get("compute", {}).get("hourly_cost", 0),
        "gpu_running": state.get("identity", {}).get("compute", {}).get("running_pods", 0),
        "gpu_total": state.get("identity", {}).get("compute", {}).get("gpu_count", 0),
        "coherence": state.get("coherence_score", 0),
        "diamond_count": state.get("reflecting", {}).get("diamond_count", 0),
    }
    SNAPSHOTS.append(snapshot)
    # keep last 200 snapshots (~16 hours at 5m cadence)
    if len(SNAPSHOTS) > 200:
        SNAPSHOTS.pop(0)


def compare_snapshot(current: Dict[str, Any], hours_ago: int = 24) -> Dict[str, Any]:
    if not SNAPSHOTS:
        return {}
    cutoff = datetime.utcnow() - timedelta(hours=hours_ago)
    past = None
    for snap in reversed(SNAPSHOTS):
        ts = datetime.fromisoformat(snap["timestamp"])
        if ts <= cutoff:
            past = snap
            break
    if not past:
        past = SNAPSHOTS[0]
    trends = {}
    for key in ["treasury", "gpu_cost_hourly", "coherence", "runway_days", "diamond_count"]:
        cur_val = current.get(key, 0)
        past_val = past.get(key, 0)
        delta_pct = pct_change(cur_val, past_val) if past_val else 0
        trends[key] = {
            "current": cur_val,
            "previous": past_val,
            "delta_pct": round(delta_pct, 2),
            "direction": "up" if delta_pct > 1 else "down" if delta_pct < -1 else "flat",
        }
    return trends


# --------------------------------------------------------------------------- #
# Mem0 Learning Query Functions
# --------------------------------------------------------------------------- #

async def search_learnings(query: str, limit: int = 5) -> List[Dict]:
    """Search Mem0 for relevant past learnings."""
    if not MEM0_API_KEY:
        return []
    
    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.mem0.ai/v1/memories/search/",
                headers=headers,
                json={
                    "query": query,
                    "user_id": "fpai_intelligence_learnings",
                    "limit": limit
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                return data if isinstance(data, list) else data.get("results", [])
    except Exception as e:
        logger.warning(f"Failed to search learnings: {e}")
    
    return []


async def get_decision_type_history(decision_type: str) -> Dict[str, Any]:
    """Get historical accuracy for a decision type."""
    if decision_type not in DECISION_TYPE_ACCURACY:
        DECISION_TYPE_ACCURACY[decision_type] = {
            "total": 0,
            "accepted": 0,
            "positive_outcomes": 0,
            "avg_confidence": 0.5
        }
    return DECISION_TYPE_ACCURACY[decision_type]


def calculate_calibrated_confidence(base_confidence: float, decision_type: str) -> float:
    """
    Calibrate confidence based on historical accuracy.
    
    If we consistently overestimate (say 80% but only 50% accurate),
    we adjust down. If we underestimate, we adjust up.
    """
    if decision_type not in CONFIDENCE_CALIBRATION:
        return base_confidence
    
    cal = CONFIDENCE_CALIBRATION[decision_type]
    if cal.get("count", 0) < 5:
        return base_confidence  # Need more data
    
    avg_predicted = cal["predicted_sum"] / cal["count"]
    avg_actual = cal["actual_sum"] / cal["count"]
    
    # Calibration factor: if we predicted 0.8 avg but got 0.5 actual, factor = 0.625
    if avg_predicted > 0:
        calibration_factor = avg_actual / avg_predicted
        # Dampen the adjustment (don't swing too wildly)
        calibration_factor = 0.5 + (calibration_factor - 0.5) * 0.5
        return min(0.95, max(0.1, base_confidence * calibration_factor))
    
    return base_confidence


def build_evidence_explanation(evidence: List[EvidenceItem], success_rate: float) -> str:
    """Build a detailed explanation based on evidence."""
    if not evidence:
        return "No historical data available for this decision type."
    
    positive = len([e for e in evidence if e.outcome == "positive"])
    total = len(evidence)
    
    explanation_parts = []
    explanation_parts.append(f"Based on {total} similar past situations, {positive} had positive outcomes ({success_rate*100:.0f}% success rate).")
    
    if evidence:
        explanation_parts.append("Recent examples:")
        for i, e in enumerate(evidence[:3], 1):
            explanation_parts.append(f"  {i}. {e.summary[:80]}... → {e.outcome}")
    
    return "\n".join(explanation_parts)


# --------------------------------------------------------------------------- #
# INTELLIGENT REASONING - Connects Trading, Treasury, Intelligence
# --------------------------------------------------------------------------- #

async def fetch_trading_data() -> Dict[str, Any]:
    """Fetch trading performance from WhaleTrack."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try different possible endpoints
            for endpoint in ["/api/live/status", "/api/paper/status", "/api/signals/stats"]:
                try:
                    resp = await client.get(f"http://localhost:8600{endpoint}")
                    if resp.status_code == 200:
                        data = resp.json()
                        # Try to extract win rate from various formats
                        return {
                            "win_rate": data.get("win_rate", data.get("winRate", 0)),
                            "total_pnl": data.get("total_pnl", data.get("totalPnl", data.get("pnl", 0))),
                            "active_positions": data.get("active_positions", data.get("positions", 0))
                        }
                except:
                    continue
    except Exception as e:
        logger.warning(f"Failed to fetch trading data: {e}")
    return {"win_rate": 0, "total_pnl": 0, "active_positions": 0}


async def fetch_trust_status() -> Dict[str, Any]:
    """Fetch trust status from Intelligence Core."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:8145/api/trust/status")
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch trust status: {e}")
    return {"trust_score": 0.5, "autonomy_level": "suggest_only"}


async def synthesize_decisions(state: Dict[str, Any]) -> List[Decision]:
    """
    INTELLIGENT REASONING ENGINE
    
    Connects the dots across:
    - Trading performance (WhaleTrack)
    - Treasury health
    - Intelligence pipeline (diamonds, horizon)
    - Compute resources
    - Historical learnings (Mem0)
    
    Generates actionable, contextual recommendations.
    """
    decisions: List[Decision] = []
    
    # Extract all context
    identity = state.get("identity", {})
    reflecting = state.get("reflecting", {})
    thinking = state.get("thinking", {})
    
    # Get trust status for meta-reasoning
    trust = await fetch_trust_status()
    
    treasury = identity.get("treasury", {})
    compute = identity.get("compute", {})
    
    total_assets = treasury.get("total_assets", 0)
    runway_days = treasury.get("runway_days", 0)
    
    diamonds = reflecting.get("diamond_count", 0)
    patterns = reflecting.get("patterns_found", 0)
    
    gpu_running = compute.get("running_pods", 0)
    gpu_total = compute.get("gpu_count", 0) or 1
    gpu_utilization = gpu_running / gpu_total
    hourly_cost = compute.get("hourly_cost", 0)
    daily_gpu_cost = hourly_cost * 24
    
    horizon_items = thinking.get("horizon", {}).get("external_items", 0)
    mem0_enabled = thinking.get("horizon", {}).get("mem0_enabled", False)
    
    # Fetch trading data for cross-domain reasoning
    trading = await fetch_trading_data()
    win_rate = trading.get("win_rate", 0)
    total_pnl = trading.get("total_pnl", 0)
    active_positions = trading.get("active_positions", 0)
    
    # ═══════════════════════════════════════════════════════════════════════
    # REASONING RULE 1: Trading Performance Analysis
    # ═══════════════════════════════════════════════════════════════════════
    if win_rate > 0:
        if win_rate >= 0.6:
            # Good win rate - suggest scaling up
            learnings = await search_learnings("trading win rate scaling capital", limit=3)
            evidence = [EvidenceItem(
                summary=l.get("memory", "")[:200],
                outcome=l.get("metadata", {}).get("outcome", "neutral"),
                relevance_score=l.get("score", 0.5)
            ) for l in learnings]
            
            decisions.append(Decision(
                id=f"dec_trading_scale_{int(time.time())}",
                type="OPTIMIZE",
                priority="high",
                title=f"Trading win rate at {win_rate*100:.0f}% - consider scaling",
                description=f"Win rate {win_rate*100:.0f}% exceeds 60% threshold. Current P&L: ${total_pnl:,.0f}",
                why=f"Validated trading strategy showing consistent returns. Each additional $1K deployed could generate ${total_pnl/max(1,total_assets)*1000:.0f} at current rate.",
                why_detailed=f"Trading is profitable at {win_rate*100:.0f}% win rate.\nGPU cost: ${daily_gpu_cost:.2f}/day.\nIf Intelligence finds 1 good trade/week worth ${daily_gpu_cost*7:.0f}, GPUs pay for themselves.",
                confidence=calculate_calibrated_confidence(0.75, "OPTIMIZE"),
                base_confidence=0.75,
                evidence=evidence,
                similar_situations_count=len(learnings),
                options=[
                    DecisionOption(id="opt_review", label="Review Trading Dashboard"),
                    DecisionOption(id="opt_dismiss", label="Dismiss"),
                ],
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=12),
            ))
        elif win_rate < 0.4 and active_positions > 0:
            # Poor win rate - suggest caution
            decisions.append(Decision(
                id=f"dec_trading_caution_{int(time.time())}",
                type="ALERT",
                priority="high",
                title=f"Trading win rate at {win_rate*100:.0f}% - review strategy",
                description=f"Win rate below 40% with {active_positions} active positions.",
                why="Low win rate may indicate strategy needs adjustment or market conditions have changed.",
                confidence=0.8,
                base_confidence=0.8,
                options=[
                    DecisionOption(id="opt_pause", label="Pause New Trades"),
                    DecisionOption(id="opt_review", label="Review Strategy"),
                    DecisionOption(id="opt_dismiss", label="Dismiss"),
                ],
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=6),
            ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # REASONING RULE 2: GPU Efficiency Analysis (FIXED BUG)
    # ═══════════════════════════════════════════════════════════════════════
    if gpu_running > 0 and daily_gpu_cost > 0:
        # Calculate value generated per GPU dollar
        value_per_gpu_dollar = total_pnl / max(1, daily_gpu_cost * 30) if total_pnl > 0 else 0
        
        if gpu_utilization > 0.9:
            # HIGH utilization - might need more capacity
            decisions.append(Decision(
                id=f"dec_gpu_capacity_{int(time.time())}",
                type="SCALE",
                priority="medium",
                title=f"GPU utilization at {gpu_utilization*100:.0f}% - near capacity",
                description=f"{gpu_running}/{gpu_total} GPUs running. May bottleneck intelligence processing.",
                why=f"High utilization means intelligence tasks may queue. Consider scaling if processing delays occur.",
                confidence=0.65,
                base_confidence=0.65,
                options=[
                    DecisionOption(id="opt_scale", label=f"Add 2 GPUs (+${hourly_cost*2:.2f}/hr)", 
                                   api_endpoint="/api/gpu/scale", params={"target": gpu_running + 2}),
                    DecisionOption(id="opt_dismiss", label="Dismiss"),
                ],
                created_at=datetime.utcnow(),
            ))
        elif gpu_utilization < 0.3 and diamonds < 5:
            # LOW utilization AND low backlog - consider scaling down
            savings = hourly_cost * (gpu_running - max(2, gpu_running // 2)) * 24
            decisions.append(Decision(
                id=f"dec_gpu_downscale_{int(time.time())}",
                type="OPTIMIZE",
                priority="medium",
                title=f"GPU utilization low ({gpu_utilization*100:.0f}%) - save ${savings:.0f}/day",
                description=f"Only {diamonds} diamonds waiting with {gpu_running} GPUs running.",
                why=f"Current workload doesn't justify full GPU fleet. Scaling down saves ${savings:.0f}/day (${savings*30:.0f}/month).",
                confidence=0.7,
                base_confidence=0.7,
                options=[
                    DecisionOption(id="opt_downscale", label=f"Scale to {max(2, gpu_running//2)} GPUs"),
                    DecisionOption(id="opt_dismiss", label="Dismiss"),
                ],
                created_at=datetime.utcnow(),
            ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # REASONING RULE 3: Treasury & Capital Analysis
    # ═══════════════════════════════════════════════════════════════════════
    if total_assets > 0:
        # Treasury health insight
        if total_assets > 100000:
            decisions.append(Decision(
                id=f"dec_treasury_health_{int(time.time())}",
                type="INSIGHT",
                priority="medium",
                title=f"Treasury healthy at ${total_assets:,.0f}",
                description=f"Capital available for strategic deployment.",
                why=f"With ${total_assets:,.0f} in treasury, you have resources to:\n• Scale validated trading strategies\n• Invest in intelligence infrastructure\n• Deploy capital opportunistically",
                why_detailed=f"CAPITAL ANALYSIS:\n\n• Total Assets: ${total_assets:,.0f}\n• Status: Well-capitalized\n• GPU/Infra can be scaled if needed\n\nConsider: Are there validated strategies waiting for more capital?",
                confidence=0.75,
                base_confidence=0.75,
                options=[
                    DecisionOption(id="opt_review_opportunities", label="Review Opportunities"),
                    DecisionOption(id="opt_acknowledge", label="Acknowledge"),
                ],
                created_at=datetime.utcnow(),
            ))
    
    if runway_days > 0 and runway_days < 365:
        severity = "critical" if runway_days < 90 else "high" if runway_days < 180 else "medium"
        
        # Calculate burn rate
        monthly_burn = total_assets / (runway_days / 30) if runway_days > 0 else 0
        
        decisions.append(Decision(
            id=f"dec_runway_{int(time.time())}",
            type="ALERT",
            priority=severity,
            title=f"Runway at {runway_days} days - requires attention",
            description=f"Treasury ${total_assets:,.0f}, burning ~${monthly_burn:,.0f}/month.",
            why=f"At current burn rate, runway is {runway_days} days. GPU cost is ${daily_gpu_cost*30:.0f}/month of that.",
            why_detailed=f"Monthly costs breakdown:\n- GPU: ${daily_gpu_cost*30:.0f}\n- Runway: {runway_days} days\n\nOptions: Reduce GPU, increase trading, or raise capital.",
            confidence=0.85,
            base_confidence=0.85,
            options=[
                DecisionOption(id="opt_review_costs", label="Review Cost Structure"),
                DecisionOption(id="opt_scale_trading", label="Scale Profitable Trading"),
                DecisionOption(id="opt_dismiss", label="Acknowledge"),
            ],
            created_at=datetime.utcnow(),
        ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # REASONING RULE 4: Intelligence Pipeline Analysis
    # ═══════════════════════════════════════════════════════════════════════
    if diamonds > 0 or horizon_items > 0:
        # Calculate insight density
        insight_ratio = diamonds / max(1, horizon_items) * 100  # % of horizon items becoming diamonds
        
        if diamonds >= 5:
            decisions.append(Decision(
                id=f"dec_intel_review_{int(time.time())}",
                type="INVESTIGATE",
                priority="medium",
                title=f"{diamonds} diamonds ready - intelligence awaiting action",
                description=f"{diamonds} insights synthesized from {horizon_items} external sources ({insight_ratio:.1f}% yield).",
                why=f"Your intelligence pipeline has processed {horizon_items} items and extracted {diamonds} actionable insights. Review before they go stale.",
                why_detailed=f"INTELLIGENCE ANALYSIS:\n\n• {horizon_items} items scanned from external sources\n• {diamonds} diamonds (high-value insights) extracted\n• {insight_ratio:.1f}% signal-to-noise ratio\n\nTop insights may contain trading signals or strategic opportunities.",
                confidence=0.7,
                base_confidence=0.7,
                options=[
                    DecisionOption(id="opt_review", label="Review Diamonds"),
                    DecisionOption(id="opt_dismiss", label="Dismiss"),
                ],
                created_at=datetime.utcnow(),
            ))
        
        if horizon_items > 100:
            decisions.append(Decision(
                id=f"dec_horizon_volume_{int(time.time())}",
                type="INSIGHT",
                priority="low",
                title=f"High external awareness: {horizon_items} signals tracked",
                description=f"Intelligence eyes are watching {horizon_items} external items.",
                why=f"System is actively monitoring external sources. This breadth of awareness enables pattern detection across markets, tech, and opportunities.",
                confidence=0.6,
                base_confidence=0.6,
                options=[
                    DecisionOption(id="opt_acknowledge", label="Acknowledge"),
                ],
                created_at=datetime.utcnow(),
            ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # REASONING RULE 5: Cross-Domain Insight
    # ═══════════════════════════════════════════════════════════════════════
    # The REAL intelligence: connecting dots others miss
    
    if win_rate > 0.5 and total_pnl > 0 and daily_gpu_cost > 0:
        # Calculate ROI of intelligence infrastructure
        roi_multiplier = total_pnl / max(1, daily_gpu_cost * 30)
        
        if roi_multiplier > 2:
            decisions.append(Decision(
                id=f"dec_roi_insight_{int(time.time())}",
                type="INSIGHT",
                priority="high",
                title=f"Intelligence ROI: {roi_multiplier:.1f}x - system is paying for itself",
                description=f"Trading P&L ${total_pnl:,.0f} vs GPU cost ${daily_gpu_cost*30:.0f}/month = {roi_multiplier:.1f}x return.",
                why="Your intelligence infrastructure is generating positive ROI. Each dollar spent on GPUs returns ${:.1f}.".format(roi_multiplier),
                why_detailed=f"CROSS-DOMAIN INSIGHT:\n\nTrading ({win_rate*100:.0f}% win rate) + Intelligence ({diamonds} diamonds) + Compute (${daily_gpu_cost:.0f}/day)\n= Net positive system generating {roi_multiplier:.1f}x ROI\n\nThis validates the Full Potential approach.",
                confidence=0.9,
                base_confidence=0.9,
                options=[
                    DecisionOption(id="opt_acknowledge", label="Acknowledge"),
                ],
                created_at=datetime.utcnow(),
            ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # REASONING RULE 6: Memory & Learning Status
    # ═══════════════════════════════════════════════════════════════════════
    if not mem0_enabled:
        decisions.append(Decision(
            id=f"dec_memory_{int(time.time())}",
            type="ALERT",
            priority="high",
            title="Mem0 memory offline - system cannot learn",
            description="Long-term memory is disabled. System won't remember patterns or learnings.",
            why="Without Mem0, the intelligence loop cannot accumulate wisdom across sessions.",
            confidence=0.95,
            base_confidence=0.95,
            options=[
                DecisionOption(id="opt_enable", label="Enable Mem0"),
                DecisionOption(id="opt_dismiss", label="Dismiss"),
            ],
            created_at=datetime.utcnow(),
        ))
    
    # ═══════════════════════════════════════════════════════════════════════
    # REASONING RULE 7: Meta-Insight - What Should James Do RIGHT NOW?
    # ═══════════════════════════════════════════════════════════════════════
    # The most intelligent thing: synthesize everything into ONE clear action
    
    if total_assets > 0 and diamonds > 0:
        # Calculate what the system thinks is the highest-leverage action
        
        # Build context summary
        context_parts = []
        if total_assets > 100000:
            context_parts.append(f"${total_assets:,.0f} capital available")
        if diamonds > 0:
            context_parts.append(f"{diamonds} insights ready")
        if horizon_items > 50:
            context_parts.append(f"{horizon_items} external signals tracked")
        if win_rate > 0.5:
            context_parts.append(f"{win_rate*100:.0f}% trading win rate")
        
        context_summary = ", ".join(context_parts)
        
        # Determine recommended action based on state
        if diamonds >= 5 and total_assets > 50000:
            recommended_action = "Review intelligence diamonds for trading signals"
            action_reason = f"You have {diamonds} processed insights and ${total_assets:,.0f} to deploy. The highest-leverage move is reviewing insights that could inform capital allocation."
        elif win_rate > 0.6 and total_assets > 100000:
            recommended_action = "Scale validated trading strategy"
            action_reason = f"Your {win_rate*100:.0f}% win rate is validated. With ${total_assets:,.0f} available, consider increasing position sizes."
        elif diamonds > 0:
            recommended_action = "Process waiting intelligence"
            action_reason = f"{diamonds} diamonds contain insights that may expire. Review before they go stale."
        else:
            recommended_action = "Monitor system health"
            action_reason = "System is running. No urgent actions required."
        
        decisions.insert(0, Decision(
            id=f"dec_next_action_{int(time.time())}",
            type="ACTION",
            priority="high",
            title=f"🎯 Recommended: {recommended_action}",
            description=context_summary,
            why=action_reason,
            why_detailed=f"SYSTEM STATE SYNTHESIS:\n\n• {context_summary}\n• Trust Score: {trust.get('trust_score', 0)*100:.0f}% (earning autonomy)\n• Mem0: {'Active' if mem0_enabled else 'Offline'}\n\nThis is the highest-leverage action based on current system state.",
            confidence=0.85,
            base_confidence=0.85,
            options=[
                DecisionOption(id="opt_do_it", label="Do It Now"),
                DecisionOption(id="opt_later", label="Later"),
            ],
            created_at=datetime.utcnow(),
        ))
    
    # Sort by priority and confidence
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    decisions.sort(key=lambda d: (priority_order.get(d.priority, 99), -d.confidence))
    
    return decisions[:5]


async def calculate_success_rate_from_evidence(evidence: List[EvidenceItem]) -> float:
    """Calculate success rate from evidence items."""
    if not evidence:
        return 0.5  # Default to 50% if no data
    
    positive = len([e for e in evidence if e.outcome == "positive"])
    total = len(evidence)
    
    return positive / total if total > 0 else 0.5


def generate_briefing_text(state: Dict[str, Any], trends: Dict[str, Any]) -> str:
    treasury = state.get("identity", {}).get("treasury", {})
    compute = state.get("identity", {}).get("compute", {})
    diamond_count = state.get("reflecting", {}).get("diamond_count", 0)
    coherence = trends.get("coherence", {}).get("current", 0)
    gpu_delta = trends.get("gpu_cost_hourly", {}).get("delta_pct", 0) if trends else 0

    parts = []
    parts.append(f"Coherence at {coherence:.0f}%")
    if gpu_delta < -5:
        parts.append(f"GPU costs down {abs(gpu_delta):.1f}%")
    elif gpu_delta > 5:
        parts.append(f"GPU costs up {gpu_delta:.1f}%")

    parts.append(f"Treasury ${treasury.get('total_assets', 0):,.0f} with {treasury.get('runway_days', 0)}d runway")
    parts.append(f"{diamond_count} diamonds ready")

    return ". ".join(parts) + "."


# --------------------------------------------------------------------------- #
# API Routes
# --------------------------------------------------------------------------- #
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "last_run": LAST_RUN.isoformat() if LAST_RUN else None,
        "snapshots": len(SNAPSHOTS),
    }


@app.get("/api/reasoning/briefing", response_model=Briefing)
async def api_briefing():
    global LAST_RUN, DECISIONS

    state = await fetch_json(f"{TEAM_HUB_URL}/api/consciousness/state")

    coherence_score = state.get("summary", {}).get("health_score", 0)
    state["coherence_score"] = coherence_score

    # Trends
    record_snapshot(state)
    trends = compare_snapshot(
        {
            "treasury": state.get("identity", {}).get("treasury", {}).get("total_assets", 0),
            "gpu_cost_hourly": state.get("identity", {}).get("compute", {}).get("hourly_cost", 0),
            "coherence": coherence_score,
            "runway_days": state.get("identity", {}).get("treasury", {}).get("runway_days", 0),
            "diamond_count": state.get("reflecting", {}).get("diamond_count", 0),
        },
        hours_ago=24,
    )

    # Decisions with evidence-based reasoning
    DECISIONS = await synthesize_decisions(state)

    briefing_text = generate_briefing_text(state, trends)
    highlights = []
    if "gpu_cost_hourly" in trends:
        delta = trends["gpu_cost_hourly"]["delta_pct"]
        highlights.append(
            f"GPU cost {'down' if delta < 0 else 'up'} {abs(delta):.1f}% vs 24h"
        )
    highlights.append(f"Runway: {state.get('identity', {}).get('treasury', {}).get('runway_days', 0)} days")
    highlights.append(f"Diamonds: {state.get('reflecting', {}).get('diamond_count', 0)}")
    
    # Add learning-based highlight
    if DECISIONS and any(d.similar_situations_count > 0 for d in DECISIONS):
        total_evidence = sum(d.similar_situations_count for d in DECISIONS)
        highlights.append(f"Decisions informed by {total_evidence} past learnings")

    LAST_RUN = datetime.utcnow()

    return Briefing(
        summary=briefing_text,
        highlights=highlights,
        trends=trends,
        top_decisions=DECISIONS[:3],
        coherence_score=coherence_score,
        generated_at=datetime.utcnow(),
        ai_generated=False,
    )


@app.get("/api/reasoning/recommendations")
async def api_recommendations():
    # If no fresh decisions, trigger briefing logic to recalc
    if not DECISIONS:
        await api_briefing()
    return {"recommendations": [d.dict() for d in DECISIONS], "count": len(DECISIONS)}


@app.get("/api/reasoning/learning-metrics")
async def api_learning_metrics():
    """Get learning and calibration metrics for the dashboard."""
    
    # Calculate overall calibration accuracy
    total_calibration_count = sum(
        cal.get("count", 0) for cal in CONFIDENCE_CALIBRATION.values()
    )
    
    calibration_by_type = {}
    for dtype, cal in CONFIDENCE_CALIBRATION.items():
        if cal.get("count", 0) > 0:
            avg_predicted = cal["predicted_sum"] / cal["count"]
            avg_actual = cal["actual_sum"] / cal["count"]
            calibration_error = abs(avg_predicted - avg_actual)
            calibration_by_type[dtype] = {
                "samples": cal["count"],
                "avg_predicted_confidence": round(avg_predicted, 3),
                "avg_actual_success_rate": round(avg_actual, 3),
                "calibration_error": round(calibration_error, 3),
                "is_well_calibrated": calibration_error < 0.1
            }
    
    # Decision type accuracy
    accuracy_by_type = {}
    for dtype, stats in DECISION_TYPE_ACCURACY.items():
        if stats["total"] > 0:
            acceptance_rate = stats["accepted"] / stats["total"]
            success_rate = stats["positive_outcomes"] / stats["accepted"] if stats["accepted"] > 0 else 0
            accuracy_by_type[dtype] = {
                "total_decisions": stats["total"],
                "accepted": stats["accepted"],
                "positive_outcomes": stats["positive_outcomes"],
                "acceptance_rate": round(acceptance_rate, 3),
                "success_rate": round(success_rate, 3)
            }
    
    # Recent outcomes
    recent_outcomes = OUTCOME_HISTORY[-20:] if OUTCOME_HISTORY else []
    
    # Calculate learning velocity (improvement over time)
    learning_velocity = None
    if len(OUTCOME_HISTORY) >= 20:
        first_half = OUTCOME_HISTORY[:len(OUTCOME_HISTORY)//2]
        second_half = OUTCOME_HISTORY[len(OUTCOME_HISTORY)//2:]
        
        first_success = len([o for o in first_half if o.get("outcome") == "positive"])
        second_success = len([o for o in second_half if o.get("outcome") == "positive"])
        
        first_rate = first_success / len(first_half) if first_half else 0
        second_rate = second_success / len(second_half) if second_half else 0
        
        learning_velocity = {
            "early_success_rate": round(first_rate, 3),
            "recent_success_rate": round(second_rate, 3),
            "improvement": round(second_rate - first_rate, 3),
            "is_improving": second_rate > first_rate
        }
    
    return {
        "total_outcomes_tracked": len(OUTCOME_HISTORY),
        "total_calibration_samples": total_calibration_count,
        "calibration_by_type": calibration_by_type,
        "accuracy_by_type": accuracy_by_type,
        "learning_velocity": learning_velocity,
        "recent_outcomes": recent_outcomes,
        "has_sufficient_data": total_calibration_count >= 10
    }


@app.get("/api/reasoning/trends")
async def api_trends():
    if not SNAPSHOTS:
        await api_briefing()
    if not SNAPSHOTS:
        return {"trends": {}}

    latest = SNAPSHOTS[-1]
    trends = compare_snapshot(latest, hours_ago=24)
    return {
        "window": "24h",
        "trends": trends,
        "calculated_at": datetime.utcnow().isoformat(),
    }


class Feedback(BaseModel):
    decision_id: str
    action: str  # executed | dismissed | scheduled
    outcome: Optional[str] = None  # positive | negative | neutral
    outcome_details: Optional[str] = None
    scheduled_for: Optional[str] = None


@app.post("/api/reasoning/feedback")
async def api_feedback(feedback: Feedback):
    """
    Record user feedback and update calibration data.
    
    This is critical for the learning loop:
    1. Record what the user did with the recommendation
    2. Track actual outcomes when provided
    3. Update confidence calibration for future decisions
    """
    global OUTCOME_HISTORY, CONFIDENCE_CALIBRATION, DECISION_TYPE_ACCURACY
    
    decision_found = None
    for d in DECISIONS:
        if d.id == feedback.decision_id:
            d.status = feedback.action
            decision_found = d
            break
    
    if decision_found:
        # Record in outcome history
        outcome_record = {
            "decision_id": feedback.decision_id,
            "decision_type": decision_found.type,
            "confidence_at_decision": decision_found.confidence,
            "base_confidence": decision_found.base_confidence,
            "user_action": feedback.action,
            "outcome": feedback.outcome,
            "outcome_details": feedback.outcome_details,
            "timestamp": datetime.utcnow().isoformat()
        }
        OUTCOME_HISTORY.append(outcome_record)
        
        # Keep last 500 outcomes
        if len(OUTCOME_HISTORY) > 500:
            OUTCOME_HISTORY.pop(0)
        
        # Update decision type accuracy tracking
        dtype = decision_found.type
        if dtype not in DECISION_TYPE_ACCURACY:
            DECISION_TYPE_ACCURACY[dtype] = {
                "total": 0, "accepted": 0, "positive_outcomes": 0, "avg_confidence": 0.5
            }
        
        DECISION_TYPE_ACCURACY[dtype]["total"] += 1
        if feedback.action == "executed":
            DECISION_TYPE_ACCURACY[dtype]["accepted"] += 1
            if feedback.outcome == "positive":
                DECISION_TYPE_ACCURACY[dtype]["positive_outcomes"] += 1
        
        # Update confidence calibration
        if feedback.outcome in ["positive", "negative"]:
            if dtype not in CONFIDENCE_CALIBRATION:
                CONFIDENCE_CALIBRATION[dtype] = {"predicted_sum": 0, "actual_sum": 0, "count": 0}
            
            CONFIDENCE_CALIBRATION[dtype]["predicted_sum"] += decision_found.confidence
            CONFIDENCE_CALIBRATION[dtype]["actual_sum"] += (1.0 if feedback.outcome == "positive" else 0.0)
            CONFIDENCE_CALIBRATION[dtype]["count"] += 1
        
        # Store learning in Mem0
        await store_decision_learning(decision_found, feedback)
        
        logger.info(f"Recorded feedback for {feedback.decision_id}: {feedback.action} -> {feedback.outcome}")
    
    return {
        "status": "recorded",
        "calibration_updated": feedback.outcome in ["positive", "negative"],
        "total_outcomes_tracked": len(OUTCOME_HISTORY)
    }


async def store_decision_learning(decision: Decision, feedback: Feedback):
    """Store decision outcome as a learning in Mem0."""
    if not MEM0_API_KEY:
        return
    
    headers = {
        "Authorization": f"Token {MEM0_API_KEY}",
        "Content-Type": "application/json"
    }
    
    result_text = "accepted and successful" if feedback.outcome == "positive" else \
                  "rejected by user" if feedback.action == "dismissed" else \
                  "executed with negative outcome" if feedback.outcome == "negative" else \
                  "executed with uncertain outcome"
    
    lesson = f"""
Decision recommendation was {result_text}.
Type: {decision.type}
Title: {decision.title}
Confidence at time: {decision.confidence:.0%}
User action: {feedback.action}
Outcome: {feedback.outcome or 'pending'}
Details: {feedback.outcome_details or 'none'}
Lesson: {decision.type} decisions at {decision.confidence:.0%} confidence tend to be {result_text}.
"""
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                "https://api.mem0.ai/v1/memories/",
                headers=headers,
                json={
                    "messages": [{"role": "user", "content": lesson}],
                    "user_id": "fpai_intelligence_learnings",
                    "metadata": {
                        "type": "decision_outcome",
                        "decision_type": decision.type,
                        "user_action": feedback.action,
                        "outcome": feedback.outcome,
                        "confidence": decision.confidence
                    }
                }
            )
    except Exception as e:
        logger.warning(f"Failed to store decision learning: {e}")


# --------------------------------------------------------------------------- #
# Startup Reasoning Cycle (Optional manual trigger)
# --------------------------------------------------------------------------- #
@app.on_event("startup")
async def on_startup():
    # Run once on startup to warm cache
    try:
        await api_briefing()
    except Exception:
        # Do not crash app if upstream services unreachable
        pass


