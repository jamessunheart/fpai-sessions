"""
Nerve Center (System Integration Hub)
====================================

Port: 8120 (Primary server)

Responsibilities:
- Receive events from subsystems (Data Service, daemons, etc.)
- Provide unified read APIs for intelligence + conscious state
- Generate a daily Action Digest and push it into Strategic Intelligence

Design goals:
- Best-effort / graceful degradation: endpoints should still return something useful even if
  upstream services are down.
- Clear "pipeline health" visibility with simple SLO checks.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Tuple

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


logger = logging.getLogger("nerve_center")
logging.basicConfig(level=logging.INFO)


# -----------------------------------------------------------------------------
# Configuration (SSOT defaults)
# -----------------------------------------------------------------------------

DATA_SERVICE_URL = os.getenv("DATA_SERVICE_URL", "http://198.54.123.234:8125")
STRATEGIC_INTEL_URL = os.getenv("STRATEGIC_INTEL_URL", "http://198.54.123.234:8500")
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")

REQUEST_TIMEOUT_S = float(os.getenv("NERVE_CENTER_HTTP_TIMEOUT_S", "6.0"))

EVENT_BUFFER_MAX = int(os.getenv("NERVE_CENTER_EVENT_BUFFER_MAX", "2000"))

DIGEST_ENABLED = os.getenv("NERVE_CENTER_DIGEST_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
DIGEST_PUSH_DEFAULT = os.getenv("NERVE_CENTER_DIGEST_PUSH_DEFAULT", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
DIGEST_HOUR_UTC = int(os.getenv("NERVE_CENTER_DIGEST_HOUR_UTC", "13"))  # 13:00 UTC default

# Coordination storage (intent & outcomes)
BASE_PATH = Path(os.getenv("FPAI_BASE_PATH", str(Path(__file__).resolve().parents[2])))
COORDINATION_PATH = Path(os.getenv("COORDINATION_PATH", str(BASE_PATH / "docs/coordination")))
INTENTS_DIR = Path(os.getenv("INTENTS_DIR", str(COORDINATION_PATH / "intents")))
OUTCOMES_DIR = Path(os.getenv("OUTCOMES_DIR", str(COORDINATION_PATH / "outcomes")))
OUTCOMES_FILE = OUTCOMES_DIR / "ledger.jsonl"

INTENTS_ENABLED = os.getenv("NERVE_CENTER_INTENTS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
INTENTS_FROM_DAILY_DIGEST = os.getenv("NERVE_CENTER_INTENTS_FROM_DAILY_DIGEST", "false").lower() in {"1", "true", "yes", "on"}
INTENTS_MAX_PER_DIGEST = int(os.getenv("NERVE_CENTER_INTENTS_MAX_PER_DIGEST", "3"))
INTENTS_TTL_HOURS = int(os.getenv("NERVE_CENTER_INTENTS_TTL_HOURS", "24"))

OUTCOMES_CACHE_MAX = int(os.getenv("NERVE_CENTER_OUTCOMES_CACHE_MAX", "2000"))
OUTCOMES_PUSH_MEM0_DEFAULT = os.getenv("NERVE_CENTER_OUTCOMES_PUSH_MEM0_DEFAULT", "true").lower() in {"1", "true", "yes", "on"}
OUTCOMES_PUSH_STRATEGIC_DEFAULT = os.getenv("NERVE_CENTER_OUTCOMES_PUSH_STRATEGIC_DEFAULT", "true").lower() in {"1", "true", "yes", "on"}


# -----------------------------------------------------------------------------
# In-memory state (events + digest)
# -----------------------------------------------------------------------------

_events: Deque[Dict[str, Any]] = deque(maxlen=EVENT_BUFFER_MAX)
_event_counts_by_type: Counter[str] = Counter()
_event_counts_by_source: Counter[str] = Counter()
_last_event_at: Optional[str] = None

_last_digest: Optional[Dict[str, Any]] = None
_last_digest_run_at: Optional[str] = None
_last_digest_push_result: Optional[Dict[str, Any]] = None

_last_intents_run_at: Optional[str] = None
_last_intents_result: Optional[Dict[str, Any]] = None

_outcomes: Deque[Dict[str, Any]] = deque(maxlen=OUTCOMES_CACHE_MAX)
_last_outcome_at: Optional[str] = None


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------


class EventIn(BaseModel):
    type: str = Field(..., description="Event type, e.g. data.item.new")
    source: str = Field(..., description="Subsystem source, e.g. data_service")
    data: Dict[str, Any] = Field(default_factory=dict)
    priority: Optional[str] = Field(default=None, description="low|medium|high|critical")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp; if omitted, server sets it")


class DigestRunRequest(BaseModel):
    hours: int = Field(default=24, ge=1, le=168)
    min_relevance: float = Field(default=0.6, ge=0.0, le=1.0)
    limit: int = Field(default=80, ge=10, le=200)
    mode: str = Field(default="both", description="trading|leadgen|both")
    push_to_strategic: bool = Field(default=DIGEST_PUSH_DEFAULT)
    create_intents: bool = Field(default=True, description="If true, drop coordination intent files for top actions")
    max_intents: int = Field(default=INTENTS_MAX_PER_DIGEST, ge=0, le=20)
    intent_ttl_hours: int = Field(default=INTENTS_TTL_HOURS, ge=1, le=168)
    dry_run: bool = Field(default=False, description="If true, do not push anywhere")


class OutcomeRecordIn(BaseModel):
    """
    Record a real-world outcome so the system learns.
    """

    category: str = Field(..., description="trading|leadgen|system|other")
    action_title: str = Field(..., description="What action was taken (ideally matches digest action title)")
    outcome: str = Field(..., description="positive|negative|neutral")
    metric_name: Optional[str] = Field(default=None, description="Optional metric name, e.g. pnl_usd, leads, uc_revenue")
    metric_value: Optional[float] = Field(default=None, description="Optional metric numeric value")
    notes: Optional[str] = Field(default=None)
    related_urls: List[str] = Field(default_factory=list)

    # Optional linkage
    intent_id: Optional[str] = Field(default=None)
    intent_file: Optional[str] = Field(default=None)
    digest_generated_at: Optional[str] = Field(default=None)

    # Learning fan-out
    push_to_mem0: bool = Field(default=OUTCOMES_PUSH_MEM0_DEFAULT)
    push_to_strategic: bool = Field(default=OUTCOMES_PUSH_STRATEGIC_DEFAULT)
    context: Optional[str] = Field(default=None, description="Context for learning (optional)")
    lesson: Optional[str] = Field(default=None, description="Explicit lesson learned (optional)")


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_coordination_dirs():
    try:
        INTENTS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create intents dir {INTENTS_DIR}: {e}")
    try:
        OUTCOMES_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.warning(f"Could not create outcomes dir {OUTCOMES_DIR}: {e}")


def _safe_slug(text: str, max_len: int = 60) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    if not cleaned:
        cleaned = "item"
    return cleaned[:max_len]


def _action_intent_id(action: Dict[str, Any]) -> str:
    title = str(action.get("title") or "").strip()
    category = str(action.get("category") or "other").strip()
    key = f"{category}|{title}".encode("utf-8", errors="ignore")
    return hashlib.sha1(key).hexdigest()[:12]


def _route_droplet_name(category: str) -> str:
    cat = (category or "").lower().strip()
    if cat == "trading":
        return "whaletrack-live"
    if cat == "leadgen":
        return "ai-automation"
    if cat == "system":
        return "nerve-center"
    return "operations"


def _intent_is_fresh(intent_path: Path, ttl_hours: int) -> bool:
    if not intent_path.exists():
        return False
    try:
        data = json.loads(intent_path.read_text())
        created_at = data.get("created_at")
        if created_at:
            created_dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        else:
            created_dt = datetime.fromtimestamp(intent_path.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - created_dt) <= timedelta(hours=ttl_hours)
    except Exception:
        # If we can't parse it, treat as "not fresh" so we can overwrite with a valid file.
        return False


def _write_json_atomic(path: Path, payload: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def _create_intents_from_digest(digest: Dict[str, Any], max_intents: int, ttl_hours: int) -> Dict[str, Any]:
    """
    Drop coordination intent files for the top digest actions.
    These are "work objects" meant to be visible and executable by humans/agents.
    """
    global _last_intents_run_at, _last_intents_result

    _ensure_coordination_dirs()

    actions = list(digest.get("actions") or [])
    if max_intents <= 0 or not actions:
        _last_intents_run_at = _utc_now_iso()
        _last_intents_result = {"created": [], "skipped": [], "reason": "no_actions_or_max_intents_0"}
        return _last_intents_result

    impact_w = {"high": 1.0, "medium": 0.8, "low": 0.6}

    def score(a: Dict[str, Any]) -> float:
        conf = float(a.get("confidence", 0.5) or 0.5)
        imp = str(a.get("expected_impact", "medium")).lower()
        return conf * impact_w.get(imp, 0.8)

    actions = sorted(actions, key=score, reverse=True)[:max_intents]

    created: List[str] = []
    skipped: List[str] = []

    for a in actions:
        title = str(a.get("title") or "").strip()
        if not title:
            continue
        category = str(a.get("category") or "other").strip().lower()
        intent_id = _action_intent_id(a)
        slug = _safe_slug(title)
        intent_path = INTENTS_DIR / f"digest-{category}-{slug}-{intent_id}.json"

        if _intent_is_fresh(intent_path, ttl_hours=ttl_hours):
            skipped.append(str(intent_path.name))
            continue

        created_at = _utc_now_iso()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()

        # For digest-driven actions, default to checkpoints to avoid surprise automation.
        approval_mode = "checkpoints"

        intent = {
            "intent_id": intent_id,
            "intent_type": "digest_action",
            "architect_intent": "\n".join(
                [
                    f"[DIGEST ACTION • {category.upper()}] {title}",
                    "",
                    f"WHY: {a.get('why')}",
                    f"NEXT STEP: {a.get('next_step')}",
                    "",
                    f"EXPECTED_IMPACT: {a.get('expected_impact', 'medium')}",
                    f"CONFIDENCE: {a.get('confidence', 0.5)}",
                    f"DIGEST_GENERATED_AT: {digest.get('generated_at')}",
                    f"WINDOW_HOURS: {digest.get('window_hours')}",
                    "",
                    f"RELATED_URLS: {a.get('related_urls') or []}",
                ]
            ),
            "droplet_name": _route_droplet_name(category),
            "approval_mode": approval_mode,
            "auto_deploy": False,
            "generated_by": "Nerve Center Digest",
            "score": int(round(score(a) * 100)),
            "created_at": created_at,
            "expires_at": expires_at,
            "metadata": {
                "category": category,
                "expected_impact": a.get("expected_impact"),
                "confidence": a.get("confidence"),
            },
        }

        _write_json_atomic(intent_path, intent)
        created.append(str(intent_path.name))

    _last_intents_run_at = _utc_now_iso()
    _last_intents_result = {"created": created, "skipped": skipped, "dir": str(INTENTS_DIR), "ttl_hours": ttl_hours}
    return _last_intents_result


def _load_outcomes_cache():
    _ensure_coordination_dirs()
    if not OUTCOMES_FILE.exists():
        return
    try:
        lines = OUTCOMES_FILE.read_text().splitlines()
        for line in lines[-OUTCOMES_CACHE_MAX:]:
            line = line.strip()
            if not line:
                continue
            try:
                _outcomes.append(json.loads(line))
            except Exception:
                continue
    except Exception as e:
        logger.warning(f"Failed to load outcomes ledger: {e}")


def _append_outcome_record(record: Dict[str, Any]):
    global _last_outcome_at
    _ensure_coordination_dirs()
    try:
        with open(OUTCOMES_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.warning(f"Failed to append outcome record: {e}")
    _outcomes.append(record)
    _last_outcome_at = record.get("recorded_at") or _utc_now_iso()


def _get_recent_outcomes(hours: int = 24, limit: int = 20) -> List[Dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent = []
    for r in list(_outcomes)[::-1]:
        try:
            dt = datetime.fromisoformat(str(r.get("recorded_at")).replace("Z", "+00:00"))
        except Exception:
            continue
        if dt < cutoff:
            break
        recent.append(r)
        if len(recent) >= limit:
            break
    return list(reversed(recent))


async def _fetch_json(url: str, method: str = "GET", json_body: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict], Optional[str]]:
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_S) as client:
            if method.upper() == "POST":
                resp = await client.post(url, json=json_body)
            else:
                resp = await client.get(url)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"{resp.status_code}"
    except Exception as e:
        return None, str(e)


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    if "{" not in text:
        return None
    try:
        json_str = text[text.find("{") : text.rfind("}") + 1]
        return json.loads(json_str)
    except Exception:
        return None


async def _call_ai_brain_json(prompt: str, system_message: str, model_preference: str = "smart", max_tokens: int = 900) -> Optional[Dict[str, Any]]:
    payload = {
        "prompt": prompt,
        "system_message": system_message,
        "model_preference": model_preference,
        "max_tokens": max_tokens,
    }
    data, err = await _fetch_json(f"{AI_BRAIN_URL}/generate", method="POST", json_body=payload)
    if err or not data:
        logger.warning(f"AI Brain call failed: {err}")
        return None
    text = data.get("text") or data.get("content") or ""
    return _extract_json_object(text)


def _heuristic_actions(items: List[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    """
    Fallback action generator when AI Brain is unavailable.
    Produces simple, high-signal next steps.
    """
    actions: List[Dict[str, Any]] = []

    def add_action(
        title: str,
        category: str,
        why: str,
        next_step: str,
        confidence: float = 0.55,
        impact: str = "medium",
        related_urls: Optional[List[str]] = None,
    ):
        actions.append(
            {
                "title": title,
                "category": category,
                "why": why,
                "next_step": next_step,
                "confidence": confidence,
                "expected_impact": impact,
                "related_urls": [u for u in (related_urls or []) if u],
            }
        )

    # Select top items by category
    by_cat: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for it in items:
        by_cat[str(it.get("category", "general"))].append(it)
    for cat in by_cat:
        by_cat[cat] = sorted(by_cat[cat], key=lambda x: float(x.get("relevance_score", 0) or 0), reverse=True)[:3]

    if mode in {"trading", "both"}:
        for it in by_cat.get("markets", [])[:3]:
            add_action(
                title=f"Trading: review market signal — {it.get('title', '')[:80]}",
                category="trading",
                why="High relevance market signal detected in the last window.",
                next_step="Check WhaleTrack Live positions + risk; decide whether to act or ignore.",
                confidence=0.6,
                impact="high",
                related_urls=[it.get("source_url")],
            )

    if mode in {"leadgen", "both"}:
        for it in (by_cat.get("ai", []) + by_cat.get("tech", []))[:3]:
            add_action(
                title=f"Leadgen: convert into outreach angle — {it.get('title', '')[:80]}",
                category="leadgen",
                why="High relevance AI/tech change that can be translated into a pain→solution message.",
                next_step="Draft 1 short outreach message + 1 offer hook; route into AI Automation pipeline.",
                confidence=0.55,
                impact="medium",
                related_urls=[it.get("source_url")],
            )

    # Always include one system hygiene action
    add_action(
        title="Data pipeline: verify collectors are fresh (HN/arXiv/RSS/CoinGlass)",
        category="system",
        why="If freshness slips, everything downstream goes blind.",
        next_step="Check /api/intelligence/pipeline/health and address any stale sources.",
        confidence=0.7,
        impact="high",
        related_urls=[],
    )

    return actions[:10]


async def _build_action_digest(hours: int, min_relevance: float, limit: int, mode: str) -> Dict[str, Any]:
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    # Pull feed + patterns + insights (best effort)
    feed_url = f"{DATA_SERVICE_URL}/api/data/feed?min_relevance={min_relevance}&since={since}&limit={limit}"
    patterns_url = f"{DATA_SERVICE_URL}/api/data/patterns"
    insights_url = f"{DATA_SERVICE_URL}/api/data/insights"

    feed_data, _ = await _fetch_json(feed_url)
    patterns_data, _ = await _fetch_json(patterns_url)
    insights_data, _ = await _fetch_json(insights_url)

    items = (feed_data or {}).get("items", []) if isinstance(feed_data, dict) else []
    patterns = (patterns_data or {}).get("patterns", []) if isinstance(patterns_data, dict) else []
    insights = (insights_data or {}).get("insights", []) if isinstance(insights_data, dict) else []

    # Convert to compact context for LLM
    top_items = sorted(items, key=lambda x: float(x.get("relevance_score", 0) or 0), reverse=True)[:25]
    context_items = [
        {
            "title": it.get("title"),
            "category": it.get("category"),
            "relevance": it.get("relevance_score"),
            "source": it.get("source"),
            "url": it.get("source_url"),
        }
        for it in top_items
    ]

    recent_outcomes = _get_recent_outcomes(hours=min(hours, 168), limit=20)

    # Try AI Brain first
    actions: Optional[List[Dict[str, Any]]] = None
    prompt = f"""You are an operator for Full Potential OS.

Mission priority: REVENUE (sustainability) and trading performance.

Given these recent intelligence items (last {hours}h), generate the TOP 10 actions to take next.

Rules:
- Actions must be specific, executable in <60 minutes each.
- Output JSON only.
- Each action must include: title, category (trading|leadgen|system), why, next_step, expected_impact (low|medium|high), confidence (0-1), related_urls (list).
- Optimize for mode: {mode}.

Recent items (compact):
{json.dumps(context_items, indent=2)}

Recent patterns:
{json.dumps(patterns[-10:], indent=2)}

Recent insights:
{json.dumps(insights[-5:], indent=2)}

Recent outcomes (feedback loop):
{json.dumps(recent_outcomes, indent=2)}

Respond as:
{{"actions":[...], "notes":"..."}}"""

    ai = await _call_ai_brain_json(
        prompt=prompt,
        system_message="You are a decisive operator. Output valid JSON only. No markdown.",
        model_preference="smart",
        max_tokens=900,
    )
    if ai and isinstance(ai.get("actions"), list):
        actions = ai.get("actions")

    if actions is None:
        actions = _heuristic_actions(top_items, mode=mode)

    digest = {
        "generated_at": _utc_now_iso(),
        "window_hours": hours,
        "mode": mode,
        "data": {
            "min_relevance": min_relevance,
            "items_count": len(items),
            "items_used": len(top_items),
        },
        "recent_outcomes": recent_outcomes,
        "patterns": patterns[-10:],
        "insights": insights[-5:],
        "top_items": top_items[:10],
        "actions": actions[:10],
    }
    return digest


async def _push_digest_to_strategic(digest: Dict[str, Any]) -> Dict[str, Any]:
    actions = digest.get("actions", [])
    signals = []
    for a in actions:
        signals.append(
            {
                "title": a.get("title"),
                "category": a.get("category", "system"),
                "relevance": a.get("confidence", 0.5),
                "source": "nerve_center",
                "meta": {
                    "why": a.get("why"),
                    "next_step": a.get("next_step"),
                    "expected_impact": a.get("expected_impact"),
                    "window_hours": digest.get("window_hours"),
                },
            }
        )

    payload = {
        "source": "nerve_center",
        "signals": signals,
        "digest": {
            "generated_at": digest.get("generated_at"),
            "mode": digest.get("mode"),
            "items_count": digest.get("data", {}).get("items_count"),
        },
    }

    data, err = await _fetch_json(f"{STRATEGIC_INTEL_URL}/api/v1/signals", method="POST", json_body=payload)
    if err:
        return {"pushed": False, "error": err}
    return {"pushed": True, "response": data}


async def _daily_digest_loop():
    global _last_digest, _last_digest_run_at, _last_digest_push_result, _last_intents_result

    # Stagger startup a bit to avoid stampedes
    await asyncio.sleep(2)

    while True:
        try:
            now = datetime.now(timezone.utc)
            next_run = now.replace(hour=DIGEST_HOUR_UTC, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timedelta(days=1)
            sleep_s = (next_run - now).total_seconds()
            logger.info(f"⏰ Next Action Digest run at {next_run.isoformat()} (in {int(sleep_s)}s)")
            await asyncio.sleep(sleep_s)

            _last_digest_run_at = _utc_now_iso()
            digest = await _build_action_digest(hours=24, min_relevance=0.6, limit=80, mode="both")
            _last_digest = digest

            if INTENTS_ENABLED and INTENTS_FROM_DAILY_DIGEST:
                _last_intents_result = _create_intents_from_digest(
                    digest, max_intents=INTENTS_MAX_PER_DIGEST, ttl_hours=INTENTS_TTL_HOURS
                )

            if DIGEST_PUSH_DEFAULT:
                _last_digest_push_result = await _push_digest_to_strategic(digest)
            else:
                _last_digest_push_result = {"pushed": False, "reason": "push disabled by default"}

        except Exception as e:
            logger.error(f"Daily digest loop error: {e}")
            await asyncio.sleep(60)


# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(title="Nerve Center", version="1.0.0", description="System integration hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    _ensure_coordination_dirs()
    _load_outcomes_cache()

    if DIGEST_ENABLED:
        asyncio.create_task(_daily_digest_loop())
        logger.info("🧠 Action Digest scheduler enabled")
    else:
        logger.info("🧠 Action Digest scheduler disabled")


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "nerve-center",
        "version": "1.0.0",
        "events_buffered": len(_events),
        "last_event_at": _last_event_at,
        "last_digest_run_at": _last_digest_run_at,
        "last_intents_run_at": _last_intents_run_at,
        "outcomes_cached": len(_outcomes),
        "last_outcome_at": _last_outcome_at,
        "coordination": {
            "coordination_path": str(COORDINATION_PATH),
            "intents_dir": str(INTENTS_DIR),
            "outcomes_file": str(OUTCOMES_FILE),
            "intents_enabled": INTENTS_ENABLED,
            "intents_from_daily_digest": INTENTS_FROM_DAILY_DIGEST,
        },
        "timestamp": _utc_now_iso(),
    }


# -----------------------------------------------------------------------------
# Event ingestion
# -----------------------------------------------------------------------------


@app.post("/api/event")
async def ingest_event(event: EventIn):
    global _last_event_at

    ts = event.timestamp or _utc_now_iso()
    stored = {
        "type": event.type,
        "source": event.source,
        "data": event.data,
        "priority": event.priority,
        "timestamp": ts,
    }

    _events.append(stored)
    _event_counts_by_type[event.type] += 1
    _event_counts_by_source[event.source] += 1
    _last_event_at = ts

    return {"status": "accepted", "timestamp": ts, "buffer_size": len(_events)}


@app.get("/api/events/recent")
async def recent_events(limit: int = Query(default=50, ge=1, le=500)):
    return {
        "events": list(_events)[-limit:][::-1],
        "count": min(limit, len(_events)),
        "last_event_at": _last_event_at,
    }


# -----------------------------------------------------------------------------
# Unified read APIs
# -----------------------------------------------------------------------------


@app.get("/api/intelligence/observations")
async def get_observations(hours: int = Query(default=24, ge=1, le=168), limit: int = Query(default=50, ge=10, le=200)):
    """
    Aggregated observations for REFLECTING pillar.
    Pipeline: Observe → Analyze → Synthesize → Propose
    """
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    feed_url = f"{DATA_SERVICE_URL}/api/data/feed?since={since}&limit={limit}&min_relevance=0.4"

    feed_data, feed_err = await _fetch_json(feed_url)
    patterns_data, _ = await _fetch_json(f"{DATA_SERVICE_URL}/api/data/patterns")

    external_items = (feed_data or {}).get("items", []) if isinstance(feed_data, dict) else []
    patterns = (patterns_data or {}).get("patterns", []) if isinstance(patterns_data, dict) else []

    internal = {
        "events_last_buffer": len(_events),
        "events_by_type_top": _event_counts_by_type.most_common(10),
        "events_by_source_top": _event_counts_by_source.most_common(10),
        "last_event_at": _last_event_at,
    }

    # Proposals: prefer latest digest actions if available, else empty (client can call digest/run)
    proposals = (_last_digest or {}).get("actions", []) if _last_digest else []

    return {
        "window_hours": hours,
        "external": external_items,
        "internal": internal,
        "patterns": patterns[-20:],
        "proposals": proposals[:10],
        "upstream": {
            "data_service": {"url": DATA_SERVICE_URL, "feed_error": feed_err},
        },
        "timestamp": _utc_now_iso(),
    }


@app.get("/api/intelligence/pipeline/health")
async def pipeline_health():
    """
    Pipeline health and freshness surface.
    """
    data_health, data_health_err = await _fetch_json(f"{DATA_SERVICE_URL}/health")
    sources, sources_err = await _fetch_json(f"{DATA_SERVICE_URL}/api/data/sources")
    strategic_health, strategic_err = await _fetch_json(f"{STRATEGIC_INTEL_URL}/health")
    ai_health, ai_err = await _fetch_json(f"{AI_BRAIN_URL}/health")

    # Simple freshness SLOs (seconds)
    slo_seconds = {
        "hacker_news": 60 * 60,      # 1h
        "arxiv": 8 * 60 * 60,        # 8h
        "rss": 2 * 60 * 60,          # 2h
        "reddit": 4 * 60 * 60,       # 4h
        "github": 6 * 60 * 60,       # 6h
        "coinglass": 60 * 60,        # 1h
    }

    freshness = {}
    now = datetime.now(timezone.utc)
    last_fetch = (sources or {}).get("last_fetch", {}) if isinstance(sources, dict) else {}
    for src, ts in last_fetch.items():
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            age_s = (now - dt).total_seconds()
            allowed = slo_seconds.get(src, 24 * 60 * 60)
            freshness[src] = {
                "last_fetch": ts,
                "age_seconds": int(age_s),
                "slo_seconds": int(allowed),
                "fresh": age_s <= allowed,
            }
        except Exception:
            freshness[src] = {"last_fetch": ts, "fresh": False, "error": "bad_timestamp"}

    overall = "green"
    if any(isinstance(v, dict) and v.get("fresh") is False for v in freshness.values()):
        overall = "yellow"
    if data_health_err or strategic_err:
        overall = "red"

    return {
        "status": overall,
        "services": {
            "data_service": {"ok": data_health_err is None, "error": data_health_err, "health": data_health},
            "strategic_intelligence": {"ok": strategic_err is None, "error": strategic_err, "health": strategic_health},
            "ai_brain": {"ok": ai_err is None, "error": ai_err, "health": ai_health},
        },
        "sources": {
            "last_fetch": last_fetch,
            "freshness": freshness,
            "error": sources_err,
        },
        "events": {
            "buffered": len(_events),
            "last_event_at": _last_event_at,
        },
        "digest": {
            "enabled": DIGEST_ENABLED,
            "last_run_at": _last_digest_run_at,
            "last_push": _last_digest_push_result,
        },
        "timestamp": _utc_now_iso(),
    }


@app.post("/api/intelligence/digest/run")
async def run_digest(req: DigestRunRequest, background_tasks: BackgroundTasks):
    """
    Generate an Action Digest now (optionally push to Strategic Intelligence).
    """
    global _last_digest, _last_digest_run_at, _last_digest_push_result

    _last_digest_run_at = _utc_now_iso()
    digest = await _build_action_digest(hours=req.hours, min_relevance=req.min_relevance, limit=req.limit, mode=req.mode)
    _last_digest = digest

    intents_result: Optional[Dict[str, Any]] = None
    if req.create_intents and not req.dry_run:
        if INTENTS_ENABLED:
            intents_result = _create_intents_from_digest(digest, max_intents=req.max_intents, ttl_hours=req.intent_ttl_hours)
        else:
            intents_result = {"created": [], "skipped": [], "reason": "intents_disabled"}
    else:
        intents_result = {"created": [], "skipped": [], "reason": "create_intents_false_or_dry_run"}

    push_result: Optional[Dict[str, Any]] = None
    if req.push_to_strategic and not req.dry_run:
        # push in background to keep endpoint responsive
        async def _push():
            global _last_digest_push_result
            _last_digest_push_result = await _push_digest_to_strategic(digest)

        background_tasks.add_task(_push)
        push_result = {"scheduled": True}
    else:
        _last_digest_push_result = {"pushed": False, "reason": "push disabled or dry_run"}
        push_result = _last_digest_push_result

    return {"status": "ok", "digest": digest, "intents": intents_result, "push": push_result}


@app.get("/api/intelligence/digest/latest")
async def latest_digest():
    if not _last_digest:
        return {"status": "empty", "message": "No digest generated yet"}
    return {"status": "ok", "digest": _last_digest, "last_run_at": _last_digest_run_at, "last_push": _last_digest_push_result}


@app.post("/api/intelligence/intents/from-latest")
async def intents_from_latest(max_intents: int = Query(default=INTENTS_MAX_PER_DIGEST, ge=0, le=20), ttl_hours: int = Query(default=INTENTS_TTL_HOURS, ge=1, le=168)):
    if not _last_digest:
        raise HTTPException(status_code=404, detail="No digest generated yet")
    if not INTENTS_ENABLED:
        raise HTTPException(status_code=503, detail="Intents are disabled on this Nerve Center")
    result = _create_intents_from_digest(_last_digest, max_intents=max_intents, ttl_hours=ttl_hours)
    return {"status": "ok", "result": result}


@app.get("/api/intelligence/intents/recent")
async def recent_intents(limit: int = Query(default=20, ge=1, le=200)):
    _ensure_coordination_dirs()
    if not INTENTS_DIR.exists():
        return {"status": "ok", "intents": [], "count": 0, "dir": str(INTENTS_DIR)}

    files = sorted(INTENTS_DIR.glob("digest-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    intents: List[Dict[str, Any]] = []
    for p in files:
        try:
            data = json.loads(p.read_text())
            intents.append(
                {
                    "file": p.name,
                    "intent_id": data.get("intent_id"),
                    "intent_type": data.get("intent_type"),
                    "droplet_name": data.get("droplet_name"),
                    "approval_mode": data.get("approval_mode"),
                    "score": data.get("score"),
                    "created_at": data.get("created_at"),
                    "expires_at": data.get("expires_at"),
                    "metadata": data.get("metadata", {}),
                }
            )
        except Exception:
            intents.append({"file": p.name, "error": "unreadable"})

    return {"status": "ok", "intents": intents, "count": len(intents), "dir": str(INTENTS_DIR), "last_intents_run_at": _last_intents_run_at}


# -----------------------------------------------------------------------------
# Outcome Ledger (closed-loop learning)
# -----------------------------------------------------------------------------


@app.post("/api/outcomes/record")
async def record_outcome(req: OutcomeRecordIn, background_tasks: BackgroundTasks):
    """
    Record an outcome and (optionally) fan-out to:
    - Mem0 learning capture (via Data Service)
    - Strategic Intelligence signal ingestion
    """
    recorded_at = _utc_now_iso()

    record = {
        "id": uuid.uuid4().hex[:12],
        "recorded_at": recorded_at,
        "category": req.category,
        "action_title": req.action_title,
        "outcome": req.outcome,
        "metric_name": req.metric_name,
        "metric_value": req.metric_value,
        "notes": req.notes,
        "related_urls": req.related_urls,
        "intent_id": req.intent_id,
        "intent_file": req.intent_file,
        "digest_generated_at": req.digest_generated_at,
        "source": "nerve_center",
    }

    # Persist + cache
    _append_outcome_record(record)

    # Emit event into Nerve Center event buffer
    global _last_event_at
    evt_ts = recorded_at
    _events.append(
        {
            "type": "outcome.recorded",
            "source": "nerve_center",
            "data": record,
            "priority": "medium",
            "timestamp": evt_ts,
        }
    )
    _event_counts_by_type["outcome.recorded"] += 1
    _event_counts_by_source["nerve_center"] += 1
    _last_event_at = evt_ts

    fanout: Dict[str, Any] = {"mem0": {"scheduled": False}, "strategic": {"scheduled": False}}

    # Mem0 learning capture (best-effort)
    if req.push_to_mem0:
        context = req.context or f"Digest action outcome ({req.category})"
        action = req.action_title
        outcome = req.outcome if req.metric_value is None else f"{req.outcome} ({req.metric_name}={req.metric_value})"
        lesson = req.lesson or req.notes or "Outcome recorded; calibrate future decisions accordingly."

        async def _push_mem0_learning():
            payload = {"context": context, "action": action, "outcome": outcome, "lesson": lesson}
            _, err = await _fetch_json(f"{DATA_SERVICE_URL}/api/data/memory/learn", method="POST", json_body=payload)
            if err:
                logger.warning(f"Mem0 learning push failed: {err}")

        background_tasks.add_task(_push_mem0_learning)
        fanout["mem0"] = {"scheduled": True}

    # Strategic Intelligence outcome signal (best-effort)
    if req.push_to_strategic:
        async def _push_strategic_outcome():
            payload = {
                "source": "nerve_center",
                "signals": [
                    {
                        "title": f"Outcome ({req.category}): {req.action_title}",
                        "category": "outcome",
                        "relevance": 0.8,
                        "source": "nerve_center",
                        "meta": record,
                    }
                ],
            }
            _, err = await _fetch_json(f"{STRATEGIC_INTEL_URL}/api/v1/signals", method="POST", json_body=payload)
            if err:
                logger.warning(f"Strategic outcome push failed: {err}")

        background_tasks.add_task(_push_strategic_outcome)
        fanout["strategic"] = {"scheduled": True}

    return {"status": "ok", "record": record, "fanout": fanout}


@app.get("/api/outcomes/recent")
async def recent_outcomes(limit: int = Query(default=50, ge=1, le=500), hours: int = Query(default=168, ge=1, le=720)):
    return {"status": "ok", "outcomes": _get_recent_outcomes(hours=hours, limit=limit), "count": min(limit, len(_outcomes)), "last_outcome_at": _last_outcome_at}


@app.get("/api/outcomes/stats")
async def outcomes_stats(hours: int = Query(default=168, ge=1, le=720)):
    recent = _get_recent_outcomes(hours=hours, limit=500)
    by_category: Dict[str, int] = {}
    by_outcome: Dict[str, int] = {}
    for r in recent:
        by_category[r.get("category", "other")] = by_category.get(r.get("category", "other"), 0) + 1
        by_outcome[r.get("outcome", "unknown")] = by_outcome.get(r.get("outcome", "unknown"), 0) + 1
    return {
        "status": "ok",
        "window_hours": hours,
        "total": len(recent),
        "by_category": by_category,
        "by_outcome": by_outcome,
        "last_outcome_at": _last_outcome_at,
    }


@app.get("/api/conscious/state")
async def get_conscious_state(hours: int = Query(default=24, ge=1, le=168)):
    """
    Complete conscious system state (best-effort).
    """
    observations = await get_observations(hours=hours, limit=50)
    pipeline = await pipeline_health()
    outcomes = _get_recent_outcomes(hours=hours, limit=20)

    return {
        "reflecting": {
            "observations": observations,
        },
        "identity": {
            "compute": {
                "ai_brain_url": AI_BRAIN_URL,
                "data_service_url": DATA_SERVICE_URL,
                "strategic_intel_url": STRATEGIC_INTEL_URL,
            },
            "resources": pipeline.get("services", {}),
            "coordination": {
                "intents_enabled": INTENTS_ENABLED,
                "intents_dir": str(INTENTS_DIR),
                "last_intents_run_at": _last_intents_run_at,
                "last_intents_result": _last_intents_result,
                "outcomes_file": str(OUTCOMES_FILE),
                "outcomes_cached": len(_outcomes),
                "last_outcome_at": _last_outcome_at,
            },
        },
        "thinking": {
            "patterns": observations.get("patterns", []),
            "insights": (_last_digest or {}).get("insights", []),
            "actions": (_last_digest or {}).get("actions", []),
            "recent_outcomes": outcomes,
        },
        "doing": {
            "trading_signals": [a for a in (_last_digest or {}).get("actions", []) if a.get("category") == "trading"][:5],
            "leadgen": [a for a in (_last_digest or {}).get("actions", []) if a.get("category") == "leadgen"][:5],
            "recent_outcomes": outcomes,
        },
        "timestamp": _utc_now_iso(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8120)


