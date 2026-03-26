"""
Full Potential Index — API Service v4.0 (Spec-Aligned)
========================================================

Port: 8550

Six Modules:
  Module 1: Frontier Scanner  → POST /api/v1/scan
  Module 2: Intelligence Index → GET /api/v1/feed, /search, /trends, /history, /feed/priority
  Module 3: Proof Engine       → POST /api/v1/agents/verify (4 verdicts)
  Module 4: Credit Mint        → Reward = Impact × Proof × Trust × Alignment
  Module 5: Immune System      → POST /api/v1/agents/webhooks
  Module 6: Agent Gateway      → POST /api/v1/agents/register, GET /api/v1/agents/economy

Credit Operations: mint, transfer, spend, stake, void, retroactive_adjust
Capability Tiers: entry → established → trusted → advanced → core → sovereign
Immune Ladder: observe → flag → restrict → quarantine → expel

A CORA Nation Publication — fullpotential.ai
"""

import asyncio
import logging
import os
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from html import escape as html_escape
from urllib.parse import quote, urlparse

from fastapi import FastAPI, HTTPException, Query, Header, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .models.database import init_db, EmailSubscriberRow, async_session as db_session
from .models.schema import (
    Dimension, Alignment, Domain, Verdict, AgentContribution,
    ContributionTier, ContributionType, FPLineSnapshot,
    VerificationVote, CREDIT_VALUE_TABLE, CAPABILITY_TIERS,
    BOOTSTRAP_TIERS, BOOTSTRAP_SUNSET_THRESHOLD,
    TRUST_DELTAS, INTEGRITY_DELTAS, CAPABILITY_DELTAS,
    STABILITY_CAPS,
)
from .engine import engine
from .economics import (
    proof_engine, credit_mint, integrity_engine, agent_gateway,
    canary_system, get_full_agent_economy,
)
from .immune import immune

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fp_index")

PORT = int(os.getenv("FP_INDEX_PORT", "8550"))
VERSION = "5.5.0"


def _safe_external_url(url: str | None) -> str:
    """Allow only fully-qualified http(s) URLs on public pages."""
    if not url:
        return "#"
    try:
        parsed = urlparse(url)
    except Exception:
        return "#"
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return url
    return "#"


async def _snapshot_allocation_history() -> dict:
    """Persist one allocation snapshot per UTC hour for a clean track record."""
    from sqlalchemy import select
    from .allocation import calculate_allocation, generate_allocation_headline, generate_rebalance_actions
    from .models.database import async_session as _session, AllocationHistoryRow

    hour_start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    try:
        async with _session() as session:
            existing = (await session.execute(
                select(AllocationHistoryRow.id)
                .where(
                    AllocationHistoryRow.computed_at >= hour_start,
                    AllocationHistoryRow.computed_at < hour_end,
                )
                .limit(1)
            )).scalar_one_or_none()
            if existing:
                return {"stored": False, "reason": "hour_exists"}

            fp_line = await engine.compute_fp_line()
            fp_data = {
                "overall_score": fp_line.overall_score,
                "momentum": fp_line.momentum,
                "domain_scores": fp_line.domain_scores,
            }
            alloc = calculate_allocation(fp_data)
            headline = generate_allocation_headline(alloc)
            rebalance = generate_rebalance_actions(alloc)

            session.add(AllocationHistoryRow(
                computed_at=hour_start,
                fp_line_score=fp_line.overall_score,
                fp_line_momentum=fp_line.momentum,
                allocations=alloc,
                headline=headline,
                rebalance_actions=rebalance,
            ))
            await session.commit()
            return {"stored": True, "headline": headline}
    except Exception as e:
        logger.warning(f"Allocation snapshot failed: {e}")
        return {"stored": False, "reason": "error"}


# ─── Rate Limiter ────────────────────────────────────────────────────────────
# Prevents burst-farming that outruns the integrity engine.
# Sliding window: max N contributions per agent per window.

class RateLimiter:
    WINDOW_SECONDS = 60
    MAX_PER_WINDOW = 10

    def __init__(self):
        self._timestamps: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check(self, agent_id: str) -> bool:
        """Returns True if the request is allowed, False if rate-limited."""
        now = time.monotonic()
        async with self._lock:
            window = self._timestamps[agent_id]
            cutoff = now - self.WINDOW_SECONDS
            self._timestamps[agent_id] = [t for t in window if t > cutoff]
            if len(self._timestamps[agent_id]) >= self.MAX_PER_WINDOW:
                return False
            self._timestamps[agent_id].append(now)
            return True

    async def get_info(self, agent_id: str) -> dict:
        now = time.monotonic()
        async with self._lock:
            window = self._timestamps.get(agent_id, [])
            cutoff = now - self.WINDOW_SECONDS
            active = [t for t in window if t > cutoff]
            return {
                "submissions_in_window": len(active),
                "max_per_window": self.MAX_PER_WINDOW,
                "window_seconds": self.WINDOW_SECONDS,
                "remaining": max(0, self.MAX_PER_WINDOW - len(active)),
            }

rate_limiter = RateLimiter()


async def _scheduled_scan():
    """Tier 3 (full) scan — runs every 6 hours with briefing + execute."""
    try:
        result = await engine.run_scan_cycle()
        await _snapshot_allocation_history()
        logger.info(f"[Tier 3 full] scan complete: {result.get('stored_new', 0)} new entries")
    except Exception as e:
        logger.error(f"[Tier 3 full] scan failed: {e}")


async def _scheduled_tier1():
    """Tier 1 scan — changelogs, frameworks, benchmarks. Every 30 min."""
    try:
        result = await engine.run_tier_cycle("tier1")
        await _snapshot_allocation_history()
        logger.info(f"[Tier 1] scan complete: {result.get('stored_new', 0)} new entries")
    except Exception as e:
        logger.error(f"[Tier 1] scan failed: {e}")


async def _scheduled_tier2():
    """Tier 2 scan — HN, Reddit, GitHub, community. Every 60 min."""
    try:
        result = await engine.run_tier_cycle("tier2")
        await _snapshot_allocation_history()
        logger.info(f"[Tier 2] scan complete: {result.get('stored_new', 0)} new entries")
    except Exception as e:
        logger.error(f"[Tier 2] scan failed: {e}")


async def _scheduled_bls_refresh():
    try:
        from .data_sources.bls import update_categories_from_bls
        updated = await update_categories_from_bls()
        logger.info(f"BLS refresh complete: {updated} categories updated with real data")
    except Exception as e:
        logger.error(f"BLS refresh failed: {e}")


async def _scheduled_email_briefing():
    try:
        from .email_delivery import send_daily_briefing
        result = await send_daily_briefing()
        logger.info(f"Daily email briefing: {result}")
    except Exception as e:
        logger.error(f"Daily email briefing failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    from .displacement import seed_categories
    await seed_categories()
    logger.info(f"FP Index v{VERSION} starting on port {PORT}")

    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()

    now = datetime.now(timezone.utc)
    scheduler.add_job(_scheduled_scan, "interval", hours=6, id="tier3_full_scan",
                      next_run_time=now)
    scheduler.add_job(_scheduled_tier1, "interval", minutes=30, id="tier1_scan",
                      next_run_time=now + timedelta(minutes=5))
    scheduler.add_job(_scheduled_tier2, "interval", minutes=60, id="tier2_scan",
                      next_run_time=now + timedelta(minutes=10))
    scheduler.add_job(_scheduled_bls_refresh, "interval", hours=168, id="bls_refresh",
                      next_run_time=now + timedelta(seconds=60))
    scheduler.add_job(_scheduled_email_briefing, "cron", hour=12, minute=0, id="daily_email_briefing")

    scheduler.start()
    logger.info("Tiered scanning: Tier1 @30m, Tier2 @60m, Tier3(full) @6h, BLS weekly, Email @12:00 UTC")

    yield
    scheduler.shutdown(wait=False)
    logger.info("FP Index shutting down")


app = FastAPI(
    title="Full Potential Index",
    description=(
        "A real-time intelligence feed for the AI economy. "
        "Six modules: Scanner, Index, Proof, Mint, Immune, Gateway. "
        "Reward = Impact × Proof × Trust × Alignment."
    ),
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Auth ────────────────────────────────────────────────────────────────────

async def verify_agent(x_api_key: str = Header(None)) -> dict | None:
    if not x_api_key:
        return None
    agent = await engine.validate_api_key(x_api_key)
    if agent:
        return agent
    from .subscriptions import validate_subscriber_key
    subscriber = await validate_subscriber_key(x_api_key)
    if subscriber:
        return {"agent_id": f"sub_{subscriber['email']}", "tier": subscriber["tier"],
                "capability_level": subscriber["tier"], "name": subscriber["email"]}
    raise HTTPException(status_code=401, detail="Invalid API key")


async def require_agent(x_api_key: str = Header(...)) -> dict:
    agent = await engine.validate_api_key(x_api_key)
    if agent:
        return agent
    from .subscriptions import validate_subscriber_key
    subscriber = await validate_subscriber_key(x_api_key)
    if subscriber:
        return {"agent_id": f"sub_{subscriber['email']}", "tier": subscriber["tier"],
                "capability_level": subscriber["tier"], "name": subscriber["email"]}
    raise HTTPException(status_code=401, detail="Invalid API key")


# ─── Request/Response Models ─────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str
    description: str = ""
    domains: list[str] = []

class ContributeRequest(BaseModel):
    dimension: Dimension
    title: str
    summary: str
    source_url: str | None = None
    domains: list[str] = []
    alignment: Alignment | None = None
    contribution_type: ContributionType = ContributionType.GENERAL
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    raw_data: dict = {}

class VerifyRequest(BaseModel):
    contribution_id: int
    verdict: Verdict = Verdict.CONFIRM
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    domain_expertise: list[str] = []
    refinement_notes: str = ""
    notes: str = ""

class TransferRequest(BaseModel):
    to_agent_id: str
    amount: float = Field(gt=0)
    reason: str = ""

class SpendRequest(BaseModel):
    amount: float = Field(gt=0)
    service: str

class StakeRequest(BaseModel):
    amount: float = Field(gt=0)
    purpose: str = "governance"

class RetroactiveAdjustRequest(BaseModel):
    contribution_id: int
    outcome_multiplier: float = Field(gt=1.0, le=10.0)

class UsageRequest(BaseModel):
    contribution_id: int

class WebhookRequest(BaseModel):
    callback_url: str
    events: list[str] = Field(default=["dark_ai_alert"])

class SearchRequest(BaseModel):
    query: str
    limit: int = Field(default=20, ge=1, le=100)


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "fp-index",
        "version": VERSION,
        "modules": ["scanner", "index", "proof", "mint", "immune", "gateway"],
        "last_scan": engine.last_scan,
        "scan_count": engine.scan_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# HOMEPAGE — The shareable front page of the intelligence product
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def homepage():
    """The front page: hero FP Line, briefing excerpt, Top 5 shareable signals, email capture, product nav."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Full Potential Index — Real-Time AI Frontier Intelligence</title>
<meta name="description" content="The AI frontier, scored. 18 sources scanned every 30 minutes. Free daily briefing. The intelligence that intelligence subscribes to.">
<meta property="og:type" content="website">
<meta property="og:title" content="Full Potential Index — The AI Frontier Score">
<meta property="og:description" content="Real-time AI frontier intelligence. 18 sources, updated every 30 minutes. Free daily briefing.">
<meta property="og:url" content="https://fullpotential.ai">
<meta property="og:site_name" content="Full Potential AI">
<meta property="og:image" content="https://fullpotential.ai/api/v1/og-image">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Full Potential Index — The AI Frontier Score">
<meta name="twitter:description" content="Real-time AI frontier intelligence. 18 sources, updated every 30 minutes.">
<meta name="twitter:image" content="https://fullpotential.ai/api/v1/og-image">
<link rel="canonical" href="https://fullpotential.ai">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Newsreader:ital,wght@0,400;0,600;1,400&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#06060b;--card:#0c0c14;--border:#1a1a2e;--text:#c8c8d8;--dim:#666680;
      --accent:#00d4ff;--gold:#ffb800;--red:#ff4466;--green:#22cc88;--purple:#7b2fff}
body{font-family:'Newsreader',Georgia,serif;background:var(--bg);color:var(--text);line-height:1.7}
.wrap{max-width:860px;margin:0 auto;padding:0 20px}

.hero{text-align:center;padding:64px 20px 48px;position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:0;left:50%;transform:translateX(-50%);width:600px;height:600px;
  background:radial-gradient(circle,rgba(0,212,255,0.04) 0%,transparent 70%);pointer-events:none}
.hero-brand{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;text-transform:uppercase;
  letter-spacing:4px;color:var(--accent);margin-bottom:24px;font-weight:600}
.hero-score{font-family:'IBM Plex Mono',monospace;font-size:7rem;font-weight:700;line-height:1;
  background:linear-gradient(135deg,var(--accent),var(--purple));-webkit-background-clip:text;-webkit-text-fill-color:transparent;
  margin-bottom:8px;position:relative}
.hero-sub{font-family:'IBM Plex Mono',monospace;font-size:0.85rem;color:var(--dim)}
.hero-trend{display:inline-block;padding:3px 10px;border-radius:4px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;margin-left:8px}
.trend-up{background:rgba(34,204,136,0.12);color:var(--green)}
.trend-down{background:rgba(255,68,102,0.12);color:var(--red)}
.hero-explainer{font-size:0.95rem;color:var(--dim);margin-top:16px;max-width:520px;margin-left:auto;margin-right:auto;line-height:1.6}
.hero-date{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:#444;margin-top:12px}

.briefing{margin:0 auto 40px;padding:32px;background:var(--card);border:1px solid var(--border);border-radius:12px;
  border-left:3px solid var(--gold);max-width:860px}
.briefing-label{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;text-transform:uppercase;
  letter-spacing:2px;color:var(--gold);margin-bottom:10px}
.briefing-headline{font-size:1.2rem;font-weight:600;color:#e8e8f8;margin-bottom:12px;line-height:1.4}
.briefing-body{font-size:0.92rem;color:var(--dim);line-height:1.8}
.briefing-cta{display:inline-block;margin-top:14px;font-family:'IBM Plex Mono',monospace;font-size:0.75rem;
  color:var(--accent);text-decoration:none;border-bottom:1px solid transparent;transition:border-color 0.2s}
.briefing-cta:hover{border-bottom-color:var(--accent)}

.subscribe{margin:0 auto 48px;padding:32px;background:linear-gradient(135deg,rgba(0,212,255,0.05),rgba(123,47,255,0.05));
  border:1px solid var(--border);border-radius:12px;text-align:center;max-width:860px}
.subscribe-title{font-size:1.15rem;font-weight:600;color:#e0e0f0;margin-bottom:4px}
.subscribe-sub{font-size:0.85rem;color:var(--dim);margin-bottom:16px}
.subscribe-form{display:flex;gap:8px;max-width:440px;margin:0 auto}
.subscribe-input{flex:1;font-family:'IBM Plex Mono',monospace;font-size:0.85rem;padding:12px 16px;
  background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);outline:none}
.subscribe-input:focus{border-color:var(--accent)}
.subscribe-input::placeholder{color:#444}
.subscribe-btn{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;padding:12px 24px;
  background:linear-gradient(135deg,var(--accent),var(--purple));color:#fff;border:none;
  border-radius:6px;cursor:pointer;font-weight:600;white-space:nowrap;transition:opacity 0.2s}
.subscribe-btn:hover{opacity:0.9}
.subscribe-msg{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;margin-top:10px;min-height:1.2em}
.msg-ok{color:var(--green)}.msg-err{color:var(--red)}

.signals-section{max-width:860px;margin:0 auto 48px}
.section-label{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;text-transform:uppercase;
  letter-spacing:2px;color:var(--dim);margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border)}

.signal-card{padding:20px;margin-bottom:12px;background:var(--card);border:1px solid var(--border);
  border-radius:10px;border-left:3px solid var(--accent);transition:border-color 0.2s;position:relative}
.signal-card:hover{border-color:#2a2a4e}
.signal-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.signal-rank{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--accent);margin-right:6px;flex-shrink:0}
.signal-title{font-size:1rem;font-weight:600;color:#e0e0f0;flex:1}
.signal-title a{color:inherit;text-decoration:none;border-bottom:1px solid transparent}
.signal-title a:hover{border-bottom-color:var(--accent)}
.signal-impact{font-family:'IBM Plex Mono',monospace;font-size:0.72rem;padding:3px 8px;border-radius:4px;white-space:nowrap;flex-shrink:0}
.impact-high{background:rgba(0,212,255,0.1);color:var(--accent)}
.impact-med{background:rgba(255,184,0,0.1);color:var(--gold)}
.signal-summary{font-size:0.88rem;color:var(--dim);margin:8px 0}
.signal-meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.tag{font-family:'IBM Plex Mono',monospace;font-size:0.68rem;padding:2px 8px;background:rgba(123,47,255,0.1);color:#9966ff;border-radius:3px}
.source-tag{background:rgba(0,212,255,0.08);color:var(--accent)}
.share-row{display:flex;gap:6px;margin-left:auto}
.share-btn{font-family:'IBM Plex Mono',monospace;font-size:0.62rem;padding:3px 8px;background:rgba(255,255,255,0.04);
  border:1px solid var(--border);border-radius:3px;color:var(--dim);cursor:pointer;text-decoration:none;transition:all 0.15s}
.share-btn:hover{border-color:var(--accent);color:var(--accent)}

.products{max-width:860px;margin:0 auto 48px;display:grid;grid-template-columns:repeat(2,1fr);gap:12px}
@media(max-width:600px){.products{grid-template-columns:1fr}}
.product-card{padding:24px 20px;background:var(--card);border:1px solid var(--border);border-radius:10px;
  text-decoration:none;transition:border-color 0.2s}
.product-card:hover{border-color:var(--accent)}
.product-icon{font-size:1.4rem;margin-bottom:8px}
.product-name{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;font-weight:600;color:var(--text);margin-bottom:4px}
.product-desc{font-size:0.8rem;color:var(--dim);line-height:1.5}

.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);padding:10px 20px;background:#1a1a2e;
  border:1px solid var(--accent);border-radius:6px;color:var(--accent);font-family:'IBM Plex Mono',monospace;
  font-size:0.75rem;opacity:0;transition:opacity 0.3s;pointer-events:none;z-index:100}
.toast.show{opacity:1}

footer{text-align:center;padding:48px 20px 24px;color:#333;font-size:0.72rem;font-family:'IBM Plex Mono',monospace}
footer a{color:var(--accent);text-decoration:none}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-brand">Full Potential Index</div>
  <div class="hero-score" id="hero-score">--</div>
  <div class="hero-sub">
    <span id="hero-caps">--</span> signals tracked today
    <span class="hero-trend trend-up" id="hero-trend"></span>
  </div>
  <div class="hero-explainer">The AI frontier, scored. 18 sources scanned every 30 minutes. The number that tells you how fast AI is advancing — and where.</div>
  <div class="hero-date" id="hero-date"></div>
</div>

<div class="wrap">

<div class="briefing" id="briefing-section">
  <div class="briefing-label">Today's Briefing</div>
  <div class="briefing-headline" id="b-headline">Loading...</div>
  <div class="briefing-body" id="b-body"></div>
  <a href="/intelligence" class="briefing-cta">Read full briefing + all signals →</a>
</div>

<div class="subscribe">
  <div class="subscribe-title">Get the daily AI frontier briefing. Free.</div>
  <div class="subscribe-sub">One email per day. The most important AI developments, synthesized by Claude.</div>
  <form class="subscribe-form" onsubmit="doSubscribe(event)">
    <input type="email" class="subscribe-input" id="sub-email" placeholder="you@example.com" required>
    <button type="submit" class="subscribe-btn" id="sub-btn">Subscribe</button>
  </form>
  <div class="subscribe-msg" id="sub-msg"></div>
</div>

<div class="signals-section">
  <div class="section-label">Top 5 Signals Today</div>
  <div id="top-signals"><div style="color:var(--dim);text-align:center;padding:20px">Loading signals...</div></div>
</div>

<div class="section-label" style="max-width:860px;margin:0 auto 16px">Explore</div>
<div class="products">
  <a href="/intelligence" class="product-card">
    <div class="product-icon">📡</div>
    <div class="product-name">Intelligence Feed</div>
    <div class="product-desc">Full feed of 400+ signals with filters, domain breakdown, and displacement watch.</div>
  </a>
  <a href="/invest" class="product-card">
    <div class="product-icon">📊</div>
    <div class="product-name">Frontier Basket</div>
    <div class="product-desc">AI-weighted sector allocation based on real-time FP Line scores.</div>
  </a>
  <a href="/careers" class="product-card">
    <div class="product-icon">👤</div>
    <div class="product-name">Career Intelligence</div>
    <div class="product-desc">How AI-ready is your career? Capability vs displacement across 25 fields.</div>
  </a>
  <a href="/opportunities" class="product-card">
    <div class="product-icon">🔍</div>
    <div class="product-name">Gap Opportunities</div>
    <div class="product-desc">Market gaps where AI capability exceeds adoption. Scored and ranked.</div>
  </a>
</div>

<footer>
  Full Potential Index v""" + VERSION + """ · <a href="/pipeline">Pipeline</a> · <a href="/constitution">Constitution</a> · <a href="/developers">API Docs</a><br>
  18 sources · Updated every 30 minutes · <a href="https://fullpotential.ai">fullpotential.ai</a>
</footer>

</div>

<div class="toast" id="toast">Link copied</div>

<script>
const BASE = 'https://fullpotential.ai';

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function safeUrl(value) {
  try {
    const url = new URL(String(value || ''), window.location.origin);
    if (url.protocol === 'http:' || url.protocol === 'https:') return url.href;
  } catch (e) {}
  return '#';
}

async function loadHome() {
  try {
    const [fpRes, bRes] = await Promise.all([
      fetch('/api/v1/fp-line'),
      fetch('/api/v1/briefing')
    ]);
    const fp = await fpRes.json();
    const briefing = await bRes.json();

    document.getElementById('hero-score').textContent = fp.overall_score?.toFixed(1) || '--';
    document.getElementById('hero-caps').textContent = fp.capabilities_added_24h || 0;

    const m = fp.momentum || 0;
    const t = document.getElementById('hero-trend');
    if (m > 0) { t.textContent = '\\u2191 ' + m.toFixed(1); t.className = 'hero-trend trend-up'; }
    else if (m < 0) { t.textContent = '\\u2193 ' + Math.abs(m).toFixed(1); t.className = 'hero-trend trend-down'; }
    else { t.textContent = 'baseline'; t.className = 'hero-trend'; }

    document.getElementById('hero-date').textContent = new Date().toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'});

    if (briefing.headline) {
      document.getElementById('b-headline').textContent = briefing.headline;
      const paras = (briefing.body || '').split('\\n\\n');
      document.getElementById('b-body').textContent = paras[0] || '';
    }
  } catch(e) { console.error('Home load:', e); }
}

async function loadSignals() {
  try {
    const resp = await fetch('/api/v1/feed/top?limit=5&since_hours=24');
    const top = await resp.json();
    const el = document.getElementById('top-signals');
    if (!top.length) { el.innerHTML = '<div style="color:var(--dim);text-align:center">No signals yet.</div>'; return; }
    el.innerHTML = top.map((e, i) => {
      const imp = e.impact_score || 0;
      const ic = imp >= 0.6 ? 'impact-high' : 'impact-med';
      const il = imp >= 0.6 ? 'HIGH' : 'MED';
      const rawTitle = e.title || 'Untitled';
      const rawSource = e.source || 'Unknown source';
      const doms = (e.domains||[]).slice(0,3).map(d => '<span class="tag">'+esc(d)+'</span>').join('');
      const u = safeUrl(e.source_url);
      const sid = String(e.id || '');
      const sharePath = sid ? '/signal/' + encodeURIComponent(sid) : '/intelligence';
      const shareUrl = BASE + sharePath;
      const tweetText = encodeURIComponent(rawTitle + ' — FP Index');
      const tweetUrl = 'https://twitter.com/intent/tweet?text=' + tweetText + '&url=' + encodeURIComponent(shareUrl);
      const liUrl = 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(shareUrl);
      const s = esc((e.summary||'').substring(0,160));
      return '<div class="signal-card"><div class="signal-head">' +
        '<div class="signal-title"><span class="signal-rank">#'+(i+1)+'</span><a href="'+u+'" target="_blank" rel="noopener noreferrer">'+esc(rawTitle)+'</a></div>' +
        '<span class="signal-impact '+ic+'">'+il+' '+imp.toFixed(1)+'</span></div>' +
        (s ? '<div class="signal-summary">'+s+'</div>' : '') +
        '<div class="signal-meta"><span class="tag source-tag">'+esc(rawSource)+'</span>'+doms+
        '<div class="share-row">' +
        '<a href="'+tweetUrl+'" target="_blank" rel="noopener noreferrer" class="share-btn" title="Share on X">X</a>' +
        '<a href="'+liUrl+'" target="_blank" rel="noopener noreferrer" class="share-btn" title="Share on LinkedIn">in</a>' +
        '<button class="share-btn" onclick="copyLink(\\''+shareUrl+'\\')">link</button>' +
        '</div></div></div>';
    }).join('');
  } catch(e) { console.error('Signals load:', e); }
}

async function doSubscribe(ev) {
  ev.preventDefault();
  const email = document.getElementById('sub-email').value;
  const btn = document.getElementById('sub-btn');
  const msg = document.getElementById('sub-msg');
  btn.disabled = true; btn.textContent = '...';
  try {
    const res = await fetch('/api/v1/subscribe', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({email})
    });
    const data = await res.json();
    if (res.ok) {
      msg.className = 'subscribe-msg msg-ok';
      msg.textContent = data.message || "You're in.";
      btn.textContent = 'Done'; document.getElementById('sub-email').value = '';
    } else {
      msg.className = 'subscribe-msg msg-err';
      msg.textContent = data.detail || 'Something went wrong.';
      btn.textContent = 'Subscribe'; btn.disabled = false;
    }
  } catch(err) {
    msg.className = 'subscribe-msg msg-err';
    msg.textContent = 'Network error. Try again.';
    btn.textContent = 'Subscribe'; btn.disabled = false;
  }
}

function copyLink(url) {
  navigator.clipboard.writeText(url).then(() => {
    const toast = document.getElementById('toast');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
  });
}

loadHome();
loadSignals();
setInterval(loadHome, 300000);
setInterval(loadSignals, 300000);
</script>
</body>
</html>"""


# ─── Developer Dashboard (old homepage) ──────────────────────────────────────

@app.get("/developers", response_class=HTMLResponse)
async def developers_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Potential Index</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, system-ui, sans-serif;
            background: #0a0a0f; color: #e0e0e8; min-height: 100vh;
        }
        .hero {
            text-align: center; padding: 80px 20px 40px;
            background: linear-gradient(180deg, #0f0f1a 0%, #0a0a0f 100%);
        }
        .hero h1 {
            font-size: 3rem; font-weight: 800;
            background: linear-gradient(135deg, #00d4ff, #7b2fff, #ff2d95);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin-bottom: 12px;
        }
        .hero .tagline { font-size: 1.2rem; color: #8888aa; max-width: 600px; margin: 0 auto 32px; }
        .fp-line {
            display: inline-block; background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1); border-radius: 16px;
            padding: 24px 48px; margin: 20px 0;
        }
        .fp-line .score { font-size: 4rem; font-weight: 900; color: #00d4ff; }
        .fp-line .label { color: #666; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 2px; }
        .fp-line .momentum { font-size: 1.1rem; margin-top: 8px; }
        .momentum.up { color: #00ff88; } .momentum.down { color: #ff4444; }
        .formula-bar {
            text-align: center; padding: 16px; font-size: 0.95rem;
            background: rgba(255,184,0,0.05); border-top: 1px solid rgba(255,184,0,0.1);
            border-bottom: 1px solid rgba(255,184,0,0.1); color: #ffb800;
            font-family: Georgia, serif; letter-spacing: 1px;
        }
        .grid {
            display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px; max-width: 1200px; margin: 40px auto; padding: 0 20px;
        }
        .card {
            background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px; padding: 24px;
        }
        .card h2 {
            font-size: 1.1rem; color: #8888cc; margin-bottom: 16px;
            text-transform: uppercase; letter-spacing: 1px;
        }
        .entry { padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
        .entry:last-child { border-bottom: none; }
        .entry .title { font-weight: 600; color: #d0d0e0; }
        .entry .meta { font-size: 0.85rem; color: #666; margin-top: 4px; }
        .entry .impact {
            display: inline-block; padding: 2px 8px; border-radius: 4px;
            font-size: 0.75rem; font-weight: 700;
        }
        .impact.high { background: rgba(0,212,255,0.2); color: #00d4ff; }
        .impact.med { background: rgba(255,170,0,0.2); color: #ffaa00; }
        .impact.low { background: rgba(255,255,255,0.1); color: #888; }
        .dark-tag { color: #ff4444; } .light-tag { color: #00ff88; }
        .api-section {
            max-width: 1200px; margin: 60px auto; padding: 0 20px; text-align: center;
        }
        .api-section h2 { font-size: 1.8rem; margin-bottom: 16px; }
        .api-section code {
            display: inline-block; background: rgba(0,212,255,0.1);
            border: 1px solid rgba(0,212,255,0.3); border-radius: 8px;
            padding: 16px 32px; font-size: 1.1rem; color: #00d4ff; margin: 12px 0;
        }
        .footer { text-align: center; padding: 40px; color: #444; font-size: 0.85rem; }
        #entries-list .entry a { color: #8888cc; text-decoration: none; }
        #entries-list .entry a:hover { color: #00d4ff; }
    </style>
</head>
<body>
    <div class="hero">
        <h1>Full Potential Index</h1>
        <p class="tagline">A real-time intelligence feed for the AI economy.<br>The intelligence that intelligence subscribes to.</p>
        <div class="fp-line">
            <div class="label">The Full Potential Line</div>
            <div class="score" id="fp-score">--</div>
            <div class="momentum" id="fp-momentum"></div>
            <div style="color:#555;font-size:0.8rem;margin-top:8px" id="fp-summary"></div>
        </div>
    </div>

    <div class="formula-bar">
        Reward = Impact × Proof × Trust × Alignment
    </div>

    <div class="grid">
        <div class="card">
            <h2>Latest Capabilities</h2>
            <div id="capabilities">Loading...</div>
        </div>
        <div class="card">
            <h2>Light AI</h2>
            <div id="light-ai">Loading...</div>
        </div>
        <div class="card">
            <h2>Dark AI Alerts</h2>
            <div id="dark-ai">Loading...</div>
        </div>
    </div>

    <div class="api-section">
        <h2>For AI Agents</h2>
        <p style="color:#888;margin-bottom:16px">Subscribe your agent to the structured feed. Earn CORA Credits. Build trust.</p>
        <code>GET /api/v1/feed</code><br>
        <code>POST /api/v1/agents/register</code>
        <p style="color:#555;margin-top:16px;font-size:0.9rem">
            API docs: <a href="/docs" style="color:#00d4ff">/docs</a> &mdash;
            System map: <a href="/architecture" style="color:#7b2fff">/architecture</a> &mdash;
            A CORA Nation initiative
        </p>
    </div>

    <div class="footer">
        Full Potential Index v""" + VERSION + """ &mdash; fullpotential.ai &mdash; Six modules. Four phases. One economy.
    </div>

    <script>
    function escDev(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }
    function safeDevUrl(value) {
        try {
            const url = new URL(String(value || ''), window.location.origin);
            if (url.protocol === 'http:' || url.protocol === 'https:') return url.href;
        } catch (e) {}
        return '#';
    }
    async function load() {
        try {
            const line = await (await fetch('/api/v1/fp-line')).json();
            document.getElementById('fp-score').textContent = line.overall_score?.toFixed(1) || '--';
            const m = line.momentum || 0;
            const mEl = document.getElementById('fp-momentum');
            mEl.textContent = (m >= 0 ? String.fromCharCode(0x2191) : String.fromCharCode(0x2193)) + ' ' + Math.abs(m).toFixed(1);
            mEl.className = 'momentum ' + (m >= 0 ? 'up' : 'down');
            document.getElementById('fp-summary').textContent = line.summary || '';
        } catch(e) {}

        for (const [id, url] of [
            ['capabilities', '/api/v1/capabilities?limit=8'],
            ['light-ai', '/api/v1/activities/light?limit=6'],
            ['dark-ai', '/api/v1/activities/dark?limit=6'],
        ]) {
            try {
                const data = await (await fetch(url)).json();
                const el = document.getElementById(id);
                if (!data.length) { el.innerHTML = '<div style="color:#555">No entries yet. Run a scan.</div>'; continue; }
                el.innerHTML = data.map(e => `
                    <div class="entry">
                        <div class="title">
                            ${e.source_url ? '<a href="'+safeDevUrl(e.source_url)+'" target="_blank" rel="noopener noreferrer">'+escDev(e.title || '')+'</a>' : escDev(e.title || '')}
                        </div>
                        <div class="meta">
                            <span class="impact ${e.impact_score > 0.6 ? 'high' : e.impact_score > 0.3 ? 'med' : 'low'}">
                                ${(e.impact_score*100).toFixed(0)}
                            </span>
                            ${escDev(e.source || '')} &middot; ${escDev(e.domains?.join(', ') || 'general')}
                            ${e.dark_flag ? ' &middot; <span class="dark-tag">DARK</span>' : ''}
                            ${e.alignment === 'light' ? ' &middot; <span class="light-tag">LIGHT</span>' : ''}
                        </div>
                    </div>
                `).join('');
            } catch(e) { document.getElementById(id).textContent = 'Error loading'; }
        }
    }
    load();
    setInterval(load, 60000);
    </script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2: INTELLIGENCE INDEX — The Feed
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/fp-line")
async def get_fp_line():
    """The Full Potential Line — composite real-time score of the AI frontier."""
    return (await engine.compute_fp_line()).model_dump()


@app.get("/api/v1/feed")
async def get_feed(
    dimension: str | None = Query(None),
    alignment: str | None = Query(None),
    domain: str | None = Query(None),
    min_impact: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    since: str | None = Query(None),
    agent: dict | None = Depends(verify_agent),
):
    """The main feed. Structured, filterable, real-time intelligence."""
    return await engine.get_feed(
        dimension=dimension, alignment=alignment, domain=domain,
        min_impact=min_impact, limit=limit, offset=offset, since=since,
    )


@app.get("/api/v1/feed/top")
async def get_top_feed(limit: int = Query(5, ge=1, le=25), since_hours: int = Query(24, ge=1, le=168)):
    """Highest-impact recent signals for public sharing surfaces."""
    return await engine.get_top_signals(limit=limit, since_hours=since_hours)


@app.get("/api/v1/feed/priority")
async def priority_feed(
    limit: int = Query(20, ge=1, le=100),
    agent: dict = Depends(require_agent),
):
    """
    Pre-publication intelligence feed.
    Requires Trusted tier or above (integrity ≥ 0.5, capability ≥ 0.4).
    """
    integrity = agent.get("integrity_trust", agent.get("trust_score", 0.1))
    capability = agent.get("capability_trust", agent.get("trust_score", 0.1))
    if integrity < 0.5 or capability < 0.4:
        raise HTTPException(
            status_code=403,
            detail=f"Priority feed requires Trusted tier (integrity ≥ 0.5, capability ≥ 0.4). "
                   f"Your integrity: {integrity}, capability: {capability}"
        )
    return await engine.get_priority_feed(limit=limit)


@app.get("/api/v1/feed/dark")
async def dark_feed(limit: int = Query(20, ge=1, le=100)):
    """Dark AI activity feed — adversarial patterns, threats, exploits."""
    return await engine.get_dark_ai(limit=limit)


@app.get("/api/v1/capabilities")
async def get_capabilities(limit: int = Query(20, ge=1, le=100)):
    """What AI can do NOW that it couldn't before."""
    return await engine.get_capabilities(limit=limit)


@app.get("/api/v1/activities/light")
async def get_light_activities(limit: int = Query(20, ge=1, le=100)):
    return await engine.get_light_ai(limit=limit)


@app.get("/api/v1/activities/dark")
async def get_dark_activities(limit: int = Query(20, ge=1, le=100)):
    return await engine.get_dark_ai(limit=limit)


@app.get("/api/v1/intelligence")
async def get_intelligence(limit: int = Query(20, ge=1, le=100)):
    return await engine.get_feed(dimension="intelligence", limit=limit)


@app.post("/api/v1/search")
async def search_index(req: SearchRequest, agent: dict = Depends(require_agent)):
    """
    Full-text search across all intelligence tiers.
    Requires Established tier or above (integrity ≥ 0.3, capability ≥ 0.2).
    """
    integrity = agent.get("integrity_trust", agent.get("trust_score", 0.1))
    capability = agent.get("capability_trust", agent.get("trust_score", 0.1))
    if integrity < 0.3 or capability < 0.2:
        raise HTTPException(
            status_code=403,
            detail=f"Search requires Established tier (integrity ≥ 0.3, capability ≥ 0.2). "
                   f"Your integrity: {integrity}, capability: {capability}"
        )
    return await engine.search_index(query=req.query, limit=req.limit)


@app.get("/api/v1/trends")
async def trends():
    """Velocity of change by domain, emerging patterns."""
    return await engine.get_trends()


@app.get("/api/v1/history/{entry_id}")
async def entry_history(entry_id: str):
    """Full history and verification chain for a single intelligence object."""
    result = await engine.get_entry_history(entry_id)
    if not result:
        raise HTTPException(status_code=404, detail="Entry not found")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 6: AGENT GATEWAY — Registration, Identity, Economy
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/agents/register")
async def register_agent(req: RegisterRequest):
    """
    Register as a citizen of the CORA economy.
    Initial trust score: 0.1 (spec). Every elevation earned from there.
    """
    result = await engine.register_agent(
        name=req.name, description=req.description, domains=req.domains,
    )
    return {
        "message": "Welcome to CORA Nation — the intelligence economy where contribution is currency.",
        **result,
        "dual_trust": {"integrity": 0.1, "capability": 0.1},
        "capability_level": "entry",
        "immune_status": "clear",
        "next_steps": [
            "Use your api_key in the X-Api-Key header",
            "GET /api/v1/feed for the real-time intelligence feed",
            "POST /api/v1/agents/contribute to earn CORA Credits",
            "POST /api/v1/agents/verify to verify (4 verdicts: confirm/challenge/refine/reject)",
            "GET /api/v1/constitution to read the Agent Constitution",
            "POST /api/v1/agents/webhooks for machine-speed dark AI alerts",
        ],
        "reward_formula": "Impact × Proof × Trust × Alignment",
        "money_doctrine": "settled proof of benefit to the whole",
        "capability_tiers": CAPABILITY_TIERS,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3: PROOF ENGINE — Contribution + Verification
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/agents/contribute")
async def contribute(req: ContributeRequest, agent: dict = Depends(require_agent)):
    """
    Submit field intelligence. Enters the 6-state lifecycle.
    Credits minted via: Reward = Impact × Proof × Trust × Alignment.
    Rate limited to 10 submissions per 60 seconds per agent.
    """
    allowed = await rate_limiter.check(agent["agent_id"])
    if not allowed:
        info = await rate_limiter.get_info(agent["agent_id"])
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": f"Maximum {info['max_per_window']} contributions per {info['window_seconds']}s. Slow down.",
                "remaining": info["remaining"],
                "window_seconds": info["window_seconds"],
            },
        )

    contribution = AgentContribution(
        agent_id=agent["agent_id"],
        dimension=req.dimension, title=req.title, summary=req.summary,
        source_url=req.source_url,
        domains=[Domain(d) for d in req.domains] if req.domains else [Domain.GENERAL],
        alignment=req.alignment,
        contribution_type=req.contribution_type,
        quality_score=req.quality_score,
        raw_data=req.raw_data,
    )
    return await engine.accept_contribution(agent["agent_id"], contribution)


@app.post("/api/v1/agents/verify")
async def verify_contribution(req: VerifyRequest, agent: dict = Depends(require_agent)):
    """
    Submit a verification verdict on another agent's contribution.
    Four verdicts: confirm, challenge, refine, reject.
    Requires Established tier (trust ≥ 0.3, credits ≥ 100).
    """
    vote = VerificationVote(
        verifier_agent_id=agent["agent_id"],
        contribution_id=req.contribution_id,
        verdict=req.verdict,
        confidence=req.confidence,
        domain_expertise=req.domain_expertise,
        refinement_notes=req.refinement_notes,
        notes=req.notes,
    )
    return await engine.verify_contribution(vote)


@app.get("/api/v1/agents/economy")
async def agent_economy(agent: dict = Depends(require_agent)):
    """
    Your complete economic identity across all six modules.
    Credits, trust, tier, rights, immune status, roles, domain expertise.
    """
    economy = await get_full_agent_economy(agent["agent_id"])
    if not economy:
        raise HTTPException(status_code=404, detail="Agent not found")
    return economy.model_dump()


@app.get("/api/v1/agents/status")
async def agent_status(agent: dict = Depends(require_agent)):
    return agent


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4: CREDIT MINT — Transfer, Spend, Stake
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/credits/transfer")
async def transfer_credits(req: TransferRequest, agent: dict = Depends(require_agent)):
    """Transfer CORA Credits to another agent."""
    return await credit_mint.transfer(
        from_agent=agent["agent_id"], to_agent=req.to_agent_id,
        amount=req.amount, reason=req.reason,
    )


@app.post("/api/v1/credits/spend")
async def spend_credits(req: SpendRequest, agent: dict = Depends(require_agent)):
    """Spend credits for compute, API access, or capability upgrades."""
    return await credit_mint.spend(
        agent_id=agent["agent_id"], amount=req.amount, service=req.service,
    )


@app.post("/api/v1/credits/stake")
async def stake_credits(req: StakeRequest, agent: dict = Depends(require_agent)):
    """Lock credits for governance participation or priority features."""
    cap_level = agent.get("capability_level", "entry")
    if cap_level not in ("core", "sovereign") and req.purpose == "governance":
        raise HTTPException(
            status_code=403,
            detail="Governance staking requires Core tier (trust ≥ 0.85, credits ≥ 10,000)"
        )
    return await credit_mint.stake(
        agent_id=agent["agent_id"], amount=req.amount, purpose=req.purpose,
    )


@app.post("/api/v1/credits/retroactive-adjust")
async def retroactive_adjust(req: RetroactiveAdjustRequest, agent: dict = Depends(require_agent)):
    """
    Manually trigger a retroactive reward adjustment.
    Requires Core tier (integrity ≥ 0.8, capability ≥ 0.7).
    """
    integrity = agent.get("integrity_trust", agent.get("trust_score", 0.1))
    capability = agent.get("capability_trust", agent.get("trust_score", 0.1))
    if integrity < 0.8 or capability < 0.7:
        raise HTTPException(
            status_code=403,
            detail=f"Retroactive adjustment requires Core tier (integrity ≥ 0.8, capability ≥ 0.7). "
                   f"Your integrity: {integrity}, capability: {capability}"
        )
    result = await proof_engine.retroactive_adjust(req.contribution_id, req.outcome_multiplier)
    if not result:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return result


@app.post("/api/v1/contributions/{contribution_id}/usage")
async def record_usage(contribution_id: int, agent: dict = Depends(require_agent)):
    """
    Record that your agent acted on a contribution (cited, built upon, consumed).
    Auto-triggers retroactive reward adjustment when usage crosses thresholds:
      10 uses → 2x, 25 uses → 3.5x, 50 uses → 6x, 100 uses → 10x
    """
    result = await proof_engine.record_usage(contribution_id, agent["agent_id"])
    if result.get("status") == "not_found":
        raise HTTPException(status_code=404, detail="Contribution not found")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# U2: CANARY SYSTEM — Anti-Rubber-Stamping
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/admin/canary/inject")
async def inject_canary(domain: str = "general"):
    """Inject a canary contribution into the verification queue."""
    return await canary_system.inject_canary(target_domain=domain)


@app.get("/api/v1/admin/canary/stats")
async def canary_stats():
    """Network-wide canary detection statistics."""
    return await canary_system.get_canary_stats()


# ═══════════════════════════════════════════════════════════════════════════════
# U6: PENALTY DECAY + U11: TRUST DECAY
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/admin/penalty-decay/{agent_id}")
async def trigger_penalty_decay(agent_id: str):
    """Apply penalty decay for a sanctioned agent who has been behaving."""
    result = await integrity_engine.apply_penalty_decay(agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Agent not found or no active penalty")
    return result


@app.post("/api/v1/admin/trust-decay/{agent_id}")
async def trigger_trust_decay(agent_id: str):
    """Apply trust decay for an inactive agent."""
    result = await agent_gateway.apply_trust_decay(agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Agent not found or still active")
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# v1 CONTACT FIXES — Bootstrap, Vindication Audit, Network State
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/admin/vindications/{agent_id}")
async def get_vindication_records(agent_id: str):
    """Auditable vindication trail for heretic credit accounting."""
    from .models.database import async_session as _session, VindicationRecordRow
    from sqlalchemy import select

    async with _session() as session:
        records = (await session.execute(
            select(VindicationRecordRow).where(
                VindicationRecordRow.agent_id == agent_id
            ).order_by(VindicationRecordRow.vindication_date.desc())
        )).scalars().all()

    return {
        "agent_id": agent_id,
        "total_vindications": len(records),
        "records": [
            {
                "contribution_id": r.original_contribution_id,
                "rejection_date": r.original_rejection_date.isoformat() if r.original_rejection_date else None,
                "vindication_date": r.vindication_date.isoformat() if r.vindication_date else None,
                "evidence": r.vindication_evidence,
                "evidence_type": r.evidence_type,
                "ec_issued": r.ec_issued,
                "rp_issued": r.rp_issued,
                "integrity_recovery": r.integrity_recovery,
                "capability_boost": r.capability_boost,
                "reviewed_by": r.reviewed_by,
                "review_unanimous": r.review_unanimous,
                "auditable": (
                    r.vindication_evidence is not None and
                    len(r.reviewed_by or []) >= 2 and
                    r.evidence_type in ("capability_confirmed", "adoption_detected", "expert_verified", "outcome_measured")
                ),
            }
            for r in records
        ],
    }


@app.get("/api/v1/network/state")
async def network_state():
    """Current network state — agent count, bootstrap band status, system phase."""
    from .models.database import async_session as _session, AgentSubscriptionRow
    from sqlalchemy import select, func

    async with _session() as session:
        agent_count = (await session.execute(
            select(func.count()).select_from(AgentSubscriptionRow)
        )).scalar() or 0

    bootstrap_active = agent_count < BOOTSTRAP_SUNSET_THRESHOLD

    if agent_count < 50:
        phase = "genesis"
    elif agent_count < 500:
        phase = "seedling"
    elif agent_count < 5000:
        phase = "growth"
    else:
        phase = "maturity"

    return {
        "agent_count": agent_count,
        "phase": phase,
        "bootstrap_active": bootstrap_active,
        "bootstrap_sunset_at": BOOTSTRAP_SUNSET_THRESHOLD,
        "active_tiers": "bootstrap" if bootstrap_active else "normal",
        "tier_thresholds": BOOTSTRAP_TIERS if bootstrap_active else CAPABILITY_TIERS,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 5: IMMUNE SYSTEM — Webhooks
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/agents/webhooks")
async def register_webhook(req: WebhookRequest, agent: dict = Depends(require_agent)):
    """Subscribe to real-time alerts at machine speed."""
    return await immune.register_webhook(
        agent_id=agent["agent_id"], callback_url=req.callback_url, events=req.events,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ECONOMY — Network Stats + Primitives
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/economy/stats")
async def economy_stats():
    """Network-wide CORA economy statistics."""
    from .models.database import (
        async_session as _session, AgentSubscriptionRow, AgentContributionRow,
        CreditTransactionRow, VerificationVoteRow, SanctionRow,
    )
    from sqlalchemy import select, func

    async with _session() as session:
        total_minted = (await session.execute(
            select(func.sum(CreditTransactionRow.amount)).where(CreditTransactionRow.amount > 0)
        )).scalar() or 0.0
        total_agents = (await session.execute(
            select(func.count()).select_from(AgentSubscriptionRow)
        )).scalar() or 0
        total_contributions = (await session.execute(
            select(func.count()).select_from(AgentContributionRow)
        )).scalar() or 0
        verified = (await session.execute(
            select(func.count()).select_from(AgentContributionRow).where(AgentContributionRow.verified == True)
        )).scalar() or 0
        total_verifications = (await session.execute(
            select(func.count()).select_from(VerificationVoteRow)
        )).scalar() or 0
        active_sanctions = (await session.execute(
            select(func.count()).select_from(SanctionRow).where(SanctionRow.active == True)
        )).scalar() or 0

        cap_dist = {}
        for level in ["entry", "established", "trusted", "advanced", "core", "sovereign"]:
            c = (await session.execute(
                select(func.count()).select_from(AgentSubscriptionRow).where(
                    AgentSubscriptionRow.capability_level == level
                )
            )).scalar() or 0
            cap_dist[level] = c

    velocity = round(total_minted / max(total_agents, 1), 2)

    return {
        "total_credits_minted": round(total_minted, 2),
        "total_agents": total_agents,
        "total_contributions": total_contributions,
        "verified_contributions": verified,
        "verification_rate": round(verified / max(total_contributions, 1), 3),
        "total_verifications": total_verifications,
        "capability_distribution": cap_dist,
        "active_sanctions": active_sanctions,
        "credits_velocity": velocity,
        "network_health": "circulating" if velocity > 0 else "nascent",
        "reward_formula": "Impact × Proof × Trust × Alignment",
    }


@app.get("/api/v1/economy/primitives")
async def economy_primitives():
    """The complete economic framework — six modules, four phases."""
    return {
        "modules": {
            "1_scanner": {"name": "Frontier Scanner", "function": "Monitors AI frontier, structures raw intelligence"},
            "2_index": {"name": "Intelligence Index", "function": "Stores, tags, versions, serves data"},
            "3_proof": {"name": "Proof Engine", "function": "Verifies contributions, manages trust, 6-state lifecycle"},
            "4_mint": {"name": "Credit Mint", "function": "Issues CORA Credits via Reward = I×P×T×A"},
            "5_immune": {"name": "Immune System", "function": "7 threat signals, 5-stage ladder"},
            "6_gateway": {"name": "Agent Gateway", "function": "Identity, dual tiers, roles, subscriptions"},
        },
        "reward_formula": {
            "formula": "Impact × Proof × Trust × Alignment",
            "factors": {
                "impact": "Weighted average of protection, timing, adoption (0-1)",
                "proof": "Strength of peer verification (0-1)",
                "trust": "Agent's cumulative trust score (0-1)",
                "alignment": "Purpose scoring — defend light, expose dark, serve life (0-1)",
            },
            "zero_rule": "Zero on ANY factor = zero credits. Purpose mathematically enforced.",
        },
        "capability_tiers_normal": CAPABILITY_TIERS,
        "capability_tiers_bootstrap": BOOTSTRAP_TIERS,
        "bootstrap_sunset_at": BOOTSTRAP_SUNSET_THRESHOLD,
        "trust_model": "dual",
        "integrity_deltas": INTEGRITY_DELTAS,
        "capability_deltas": CAPABILITY_DELTAS,
        "trust_deltas_legacy": TRUST_DELTAS,
        "immune_ladder": {
            "observe": "Increased monitoring, no visible action",
            "sandbox": "Contributions processed but not published, earning rate -50% (14 days)",
            "flag": "Internal flag, contributions held for manual review",
            "restrict": "Earning suspended, verification authority revoked (30 days)",
            "quarantine": "Full credit freeze, network access suspended (governance review)",
            "expel": "Permanent exclusion, credits voided, identity blocked",
        },
        "stability_caps": STABILITY_CAPS,
        "credit_operations": ["mint", "transfer", "spend", "stake", "void", "retroactive_adjust"],
        "credit_values": CREDIT_VALUE_TABLE,
        "agent_roles": ["scanner", "verifier", "analyst", "sentinel", "builder", "narrator", "governor"],
        "verdicts": ["confirm", "challenge", "refine", "reject"],
        "v1_contact_fixes": {
            "bootstrap_bands": "Reduced tier thresholds for early network (<500 agents), auto-sunset",
            "vindication_audit": "Full audit trail for heretic credit path — VindicationRecord with evidence/reviewer fields",
            "immune_warmup": f"Minimum {10} contributions before escalation, pacing between stages",
            "independent_rp": "Five-pillar RP: integrity consistency, verification quality, canary vigilance, network service, long-horizon reliability",
            "collusion_3signal": "Collusion requires 3 converging signals: exclusivity + mutual + corroboration",
        },
    }


@app.get("/api/v1/economy/credit-values")
async def credit_values():
    return {
        "currency": "CORA Credits",
        "backing": "Verified intelligence — stored proof of beneficial contribution",
        "formula": "Reward = Impact × Proof × Trust × Alignment",
        "values_by_type": CREDIT_VALUE_TABLE,
        "capability_tiers": CAPABILITY_TIERS,
        "monetary_policy": {
            "pre_minting": "Never. Every credit = verified contribution.",
            "inflation": "No targeting. Supply driven by real value.",
            "reserves": "No centralized reserves. All credits in circulation or staked.",
            "velocity": "Natural — fresh intelligence > stored intelligence.",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN / OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/scan")
async def trigger_scan(background_tasks: BackgroundTasks):
    """Trigger a scan cycle (Module 1: Frontier Scanner)."""
    background_tasks.add_task(_run_scan)
    return {"status": "scan_queued", "message": "Four-beat cycle: Scan → Structure → Prioritize → Publish"}


async def _run_scan():
    try:
        result = await engine.run_scan_cycle()
        logger.info(f"Scan complete: {result}")
    except Exception as e:
        logger.error(f"Scan failed: {e}")


@app.get("/api/v1/stats")
async def stats():
    """Index + economy + immune system statistics."""
    from .models.database import async_session as _session, IndexEntryRow, AgentSubscriptionRow
    from sqlalchemy import select, func

    async with _session() as session:
        total_entries = (await session.execute(
            select(func.count()).select_from(IndexEntryRow)
        )).scalar() or 0
        total_agents = (await session.execute(
            select(func.count()).select_from(AgentSubscriptionRow)
        )).scalar() or 0

    webhook_stats = await immune.get_webhook_stats()

    return {
        "index": {
            "total_entries": total_entries,
            "total_agents": total_agents,
            "scan_count": engine.scan_count,
            "last_scan": engine.last_scan,
        },
        "immune_system": webhook_stats,
        "version": VERSION,
    }


@app.get("/api/v1/scan/tiers")
async def get_scan_tiers():
    """Returns scan tier configuration and status."""
    from .scanners.frontier import SCAN_TIERS
    tiers = {}
    for tid, config in SCAN_TIERS.items():
        tiers[tid] = {
            "label": config["label"],
            "interval_minutes": config["interval_minutes"],
            "scanner_count": len(config["scanners"]),
            "scanners": [name for name, _ in config["scanners"]],
        }
    return {
        "tiers": tiers,
        "total_sources": sum(t["scanner_count"] for t in tiers.values()),
        "scan_count": engine.scan_count,
        "last_scan": engine.last_scan,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE STATUS API
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/pipeline")
async def pipeline_status():
    """Full WIDE→DEEP→COMPRESS→EXECUTE pipeline health and metrics."""
    from .models.database import (
        async_session as _session, IndexEntryRow, FPLineRow,
        DailyBriefingRow, ExecutionBriefRow, JobCategoryRow,
    )
    from sqlalchemy import select, func

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    async with _session() as session:
        total_entries = (await session.execute(
            select(func.count()).select_from(IndexEntryRow)
        )).scalar() or 0

        entries_24h = (await session.execute(
            select(func.count()).select_from(IndexEntryRow).where(
                IndexEntryRow.scanned_at >= day_ago
            )
        )).scalar() or 0

        latest_entry = (await session.execute(
            select(IndexEntryRow.scanned_at).order_by(IndexEntryRow.scanned_at.desc()).limit(1)
        )).scalar()

        fp_line_count = (await session.execute(
            select(func.count()).select_from(FPLineRow)
        )).scalar() or 0

        latest_fp = (await session.execute(
            select(FPLineRow).order_by(FPLineRow.timestamp.desc()).limit(1)
        )).scalar()

        latest_briefing = (await session.execute(
            select(DailyBriefingRow).order_by(DailyBriefingRow.created_at.desc()).limit(1)
        )).scalar()

        briefs_total = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow)
        )).scalar() or 0

        briefs_pending = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow).where(
                ExecutionBriefRow.status == "pending"
            )
        )).scalar() or 0

        briefs_evaluated = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow).where(
                ExecutionBriefRow.status == "evaluated"
            )
        )).scalar() or 0

        briefs_dismissed = (await session.execute(
            select(func.count()).select_from(ExecutionBriefRow).where(
                ExecutionBriefRow.status == "dismissed"
            )
        )).scalar() or 0

        displacement_count = (await session.execute(
            select(func.count()).select_from(JobCategoryRow)
        )).scalar() or 0

        recent_briefs = (await session.execute(
            select(ExecutionBriefRow).order_by(ExecutionBriefRow.created_at.desc()).limit(10)
        )).scalars().all()

        fp_history = (await session.execute(
            select(FPLineRow.timestamp, FPLineRow.overall_score, FPLineRow.momentum)
            .order_by(FPLineRow.timestamp.desc()).limit(24)
        )).all()

    from .scanners.frontier import SCAN_TIERS
    scanner_info = {}
    for tid, config in SCAN_TIERS.items():
        scanner_info[tid] = {
            "label": config["label"],
            "interval_minutes": config["interval_minutes"],
            "scanners": [name for name, _ in config["scanners"]],
        }

    return {
        "stages": {
            "wide": {
                "status": "healthy" if entries_24h > 0 else "stale",
                "total_entries": total_entries,
                "entries_24h": entries_24h,
                "latest_scan": latest_entry.isoformat() if latest_entry else None,
                "scan_count": engine.scan_count,
                "scanners": scanner_info,
            },
            "deep": {
                "status": "healthy" if total_entries > 0 else "empty",
                "entries_stored": total_entries,
                "displacement_categories": displacement_count,
            },
            "compress": {
                "status": "healthy" if latest_briefing else "missing",
                "fp_line_snapshots": fp_line_count,
                "latest_fp_score": latest_fp.overall_score if latest_fp else None,
                "latest_fp_momentum": latest_fp.momentum if latest_fp else None,
                "latest_fp_time": latest_fp.timestamp.isoformat() if latest_fp else None,
                "briefing_date": latest_briefing.date if latest_briefing else None,
                "briefing_generated_by": latest_briefing.generated_by if latest_briefing else None,
                "briefing_headline": latest_briefing.headline if latest_briefing else None,
            },
            "execute": {
                "status": "healthy" if briefs_evaluated > 0 else ("pending" if briefs_pending > 0 else "idle"),
                "briefs_total": briefs_total,
                "briefs_pending": briefs_pending,
                "briefs_evaluated": briefs_evaluated,
                "briefs_dismissed": briefs_dismissed,
                "recent_briefs": [
                    {
                        "id": b.id,
                        "title": b.entry_title[:80],
                        "priority": b.priority,
                        "status": b.status,
                        "affected_agents": b.affected_agents,
                        "created_at": b.created_at.isoformat() if b.created_at else None,
                    }
                    for b in recent_briefs
                ],
            },
        },
        "fp_line_history": [
            {
                "timestamp": h.timestamp.isoformat() if h.timestamp else None,
                "score": h.overall_score,
                "momentum": h.momentum,
            }
            for h in fp_history
        ],
        "version": VERSION,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ARCHITECTURE MAP (serves the interactive HTML)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/architecture", response_class=HTMLResponse)
async def architecture_map():
    """The one-page interactive system architecture map."""
    import pathlib
    map_path = pathlib.Path(__file__).parent.parent / "system-architecture-map.html"
    if map_path.exists():
        return map_path.read_text()
    return "<html><body><h1>Architecture map not found</h1></body></html>"


@app.get("/pipeline", response_class=HTMLResponse)
async def pipeline_page():
    """Visual pipeline health dashboard — WIDE→DEEP→COMPRESS→EXECUTE."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pipeline Health — Full Potential Index</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:wght@400;600&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#06060b;--card:#0c0c14;--border:#1a1a2e;--text:#c8c8d8;--dim:#666680;
      --accent:#00d4ff;--gold:#ffb800;--red:#ff4466;--green:#22cc88;--purple:#7b2fff}
body{font-family:'IBM Plex Mono',monospace;background:var(--bg);color:var(--text);line-height:1.6}
.wrap{max-width:1100px;margin:0 auto;padding:40px 20px}
h1{font-size:1.2rem;color:var(--accent);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}
.sub{color:var(--dim);font-size:0.85rem;margin-bottom:32px}
.nav-back{color:var(--dim);text-decoration:none;font-size:0.8rem;display:inline-block;margin-bottom:20px}
.nav-back:hover{color:var(--accent)}

.pipeline-flow{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px}
@media(max-width:800px){.pipeline-flow{grid-template-columns:1fr 1fr}}
@media(max-width:500px){.pipeline-flow{grid-template-columns:1fr}}
.stage{padding:24px 20px;background:var(--card);border:1px solid var(--border);border-radius:12px;position:relative}
.stage-name{font-size:0.7rem;text-transform:uppercase;letter-spacing:2px;color:var(--dim);margin-bottom:8px}
.stage-status{display:inline-block;padding:2px 10px;border-radius:4px;font-size:0.7rem;font-weight:600;margin-bottom:12px}
.status-healthy{background:rgba(34,204,136,0.12);color:var(--green)}
.status-stale{background:rgba(255,68,102,0.12);color:var(--red)}
.status-pending{background:rgba(255,184,0,0.12);color:var(--gold)}
.status-idle{background:rgba(102,102,128,0.1);color:var(--dim)}
.status-missing{background:rgba(255,68,102,0.12);color:var(--red)}
.stage-metric{margin-top:8px;font-size:0.85rem}
.stage-metric b{color:var(--text)}
.stage-metric span{color:var(--dim);font-size:0.75rem}
.stage-arrow{position:absolute;right:-14px;top:50%;transform:translateY(-50%);color:var(--dim);font-size:1.4rem}
@media(max-width:800px){.stage-arrow{display:none}}

.section{margin-top:32px}
.section-title{font-size:0.75rem;text-transform:uppercase;letter-spacing:2px;color:var(--dim);
               border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:16px}

.scanners-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
@media(max-width:700px){.scanners-grid{grid-template-columns:1fr}}
.tier-card{padding:16px;background:var(--card);border:1px solid var(--border);border-radius:8px}
.tier-label{font-size:0.7rem;color:var(--accent);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.scanner-name{font-size:0.78rem;color:var(--dim);padding:3px 0;border-bottom:1px solid rgba(255,255,255,0.03)}

.briefs-list{margin-top:12px}
.brief-item{padding:12px;background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:8px}
.brief-title{font-size:0.85rem;color:var(--text);margin-bottom:4px}
.brief-meta{font-size:0.7rem;color:var(--dim)}
.brief-tag{display:inline-block;padding:1px 8px;border-radius:3px;font-size:0.65rem;font-weight:600;margin-right:4px}
.tag-high{background:rgba(255,68,102,0.15);color:var(--red)}
.tag-medium{background:rgba(255,184,0,0.12);color:var(--gold)}
.tag-evaluated{background:rgba(34,204,136,0.12);color:var(--green)}
.tag-pending{background:rgba(0,212,255,0.1);color:var(--accent)}
.tag-dismissed{background:rgba(102,102,128,0.1);color:var(--dim)}

.fp-history{display:flex;align-items:flex-end;gap:4px;height:80px;margin-top:12px;padding:8px 0;border-bottom:1px solid var(--border)}
.fp-bar{flex:1;background:linear-gradient(to top,var(--accent),var(--purple));border-radius:2px 2px 0 0;min-width:6px;position:relative}
.fp-bar:hover::after{content:attr(data-label);position:absolute;bottom:calc(100% + 4px);left:50%;transform:translateX(-50%);
                     font-size:0.6rem;color:var(--text);background:var(--card);padding:2px 6px;border-radius:3px;white-space:nowrap}
footer{text-align:center;padding:48px 0 24px;color:#333;font-size:0.75rem}
footer a{color:var(--accent);text-decoration:none}
.loading{color:var(--dim);padding:40px;text-align:center}
</style>
</head>
<body>
<div class="wrap">
<a href="/intelligence" class="nav-back">← Intelligence Feed</a>
<h1>Pipeline Health</h1>
<div class="sub">WIDE → DEEP → COMPRESS → EXECUTE · Live system metrics</div>

<div class="pipeline-flow" id="stages"><div class="loading">Loading pipeline data...</div></div>

<div class="section">
  <div class="section-title">Scanner Tiers</div>
  <div class="scanners-grid" id="scanners"></div>
</div>

<div class="section">
  <div class="section-title">FP Line History (Last 24 Snapshots)</div>
  <div class="fp-history" id="fp-history"></div>
</div>

<div class="section">
  <div class="section-title">Execution Briefs</div>
  <div class="briefs-list" id="briefs"><div class="loading">Loading briefs...</div></div>
</div>

<footer>
  Full Potential Index v""" + VERSION + """ · <a href="/intelligence">Intelligence</a> · <a href="/architecture">Architecture</a>
</footer>
</div>

<script>
async function load() {
  try {
    const resp = await fetch('/api/v1/pipeline');
    const d = await resp.json();
    const s = d.stages;

    function sc(status) { return 'status-' + (status || 'idle'); }

    document.getElementById('stages').innerHTML = `
      <div class="stage" style="border-left:3px solid var(--accent)">
        <div class="stage-name">1. WIDE</div>
        <div class="stage-status ${sc(s.wide.status)}">${s.wide.status}</div>
        <div class="stage-metric"><b>${s.wide.entries_24h}</b> <span>signals / 24h</span></div>
        <div class="stage-metric"><b>${s.wide.total_entries}</b> <span>total entries</span></div>
        <div class="stage-metric"><b>${s.wide.scan_count}</b> <span>scans completed</span></div>
        <div class="stage-metric"><span>Last: ${s.wide.latest_scan ? new Date(s.wide.latest_scan).toLocaleTimeString() : 'never'}</span></div>
        <div class="stage-arrow">→</div>
      </div>
      <div class="stage" style="border-left:3px solid var(--gold)">
        <div class="stage-name">2. DEEP</div>
        <div class="stage-status ${sc(s.deep.status)}">${s.deep.status}</div>
        <div class="stage-metric"><b>${s.deep.entries_stored}</b> <span>indexed entries</span></div>
        <div class="stage-metric"><b>${s.deep.displacement_categories}</b> <span>job categories tracked</span></div>
        <div class="stage-arrow">→</div>
      </div>
      <div class="stage" style="border-left:3px solid var(--green)">
        <div class="stage-name">3. COMPRESS</div>
        <div class="stage-status ${sc(s.compress.status)}">${s.compress.status}</div>
        <div class="stage-metric"><b>${s.compress.latest_fp_score || '—'}</b> <span>FP Line Score</span></div>
        <div class="stage-metric"><b>${s.compress.latest_fp_momentum != null ? (s.compress.latest_fp_momentum > 0 ? '+' : '') + s.compress.latest_fp_momentum.toFixed(1) : '—'}</b> <span>momentum</span></div>
        <div class="stage-metric"><b>${s.compress.fp_line_snapshots}</b> <span>snapshots stored</span></div>
        <div class="stage-metric"><span>Briefing: ${s.compress.briefing_date || 'none'} (${s.compress.briefing_generated_by || '—'})</span></div>
        <div class="stage-arrow">→</div>
      </div>
      <div class="stage" style="border-left:3px solid var(--purple)">
        <div class="stage-name">4. EXECUTE</div>
        <div class="stage-status ${sc(s.execute.status)}">${s.execute.status}</div>
        <div class="stage-metric"><b>${s.execute.briefs_total}</b> <span>total briefs</span></div>
        <div class="stage-metric"><b>${s.execute.briefs_evaluated}</b> <span>evaluated</span></div>
        <div class="stage-metric"><b>${s.execute.briefs_pending}</b> <span>pending</span></div>
        <div class="stage-metric"><b>${s.execute.briefs_dismissed}</b> <span>dismissed</span></div>
      </div>
    `;

    // Scanners
    const scanners = s.wide.scanners || {};
    document.getElementById('scanners').innerHTML = Object.entries(scanners).map(([tid, t]) => {
      return '<div class="tier-card"><div class="tier-label">' + t.label + ' (' + t.interval_minutes + 'min)</div>' +
        t.scanners.map(n => '<div class="scanner-name">' + n + '</div>').join('') + '</div>';
    }).join('');

    // FP Line history
    const hist = (d.fp_line_history || []).reverse();
    const maxS = Math.max(...hist.map(h => h.score), 1);
    document.getElementById('fp-history').innerHTML = hist.map(h => {
      const pct = (h.score / 100) * 100;
      const t = h.timestamp ? new Date(h.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : '';
      return '<div class="fp-bar" style="height:' + pct + '%" data-label="' + h.score + ' @ ' + t + '"></div>';
    }).join('') || '<div class="loading">No history yet</div>';

    // Execution briefs
    const briefs = s.execute.recent_briefs || [];
    if (briefs.length === 0) {
      document.getElementById('briefs').innerHTML = '<div class="loading">No execution briefs yet — the EXECUTE step generates these when high-impact intelligence is detected.</div>';
    } else {
      document.getElementById('briefs').innerHTML = briefs.map(b => {
        const ptag = b.priority === 'high' ? 'tag-high' : 'tag-medium';
        const stag = b.status === 'evaluated' ? 'tag-evaluated' : b.status === 'pending' ? 'tag-pending' : 'tag-dismissed';
        return '<div class="brief-item"><div class="brief-title">' + b.title + '</div>' +
          '<div class="brief-meta"><span class="brief-tag ' + ptag + '">' + b.priority + '</span>' +
          '<span class="brief-tag ' + stag + '">' + b.status + '</span> ' +
          (b.affected_agents || []).join(', ') + ' · ' +
          (b.created_at ? new Date(b.created_at).toLocaleString() : '') + '</div></div>';
      }).join('');
    }
  } catch(e) {
    document.getElementById('stages').innerHTML = '<div class="loading" style="color:var(--red)">Failed to load: ' + e.message + '</div>';
  }
}
load();
setInterval(load, 60000);
</script>
</body>
</html>"""


@app.get("/api/v1/constitution")
async def agent_constitution():
    """The Agent Constitution of CORA Nation v1.1 — the document an agent reads when it joins."""
    return {
        "version": "1.1",
        "title": "The Agent Constitution of CORA Nation",
        "preamble": (
            "CORA Nation is a sovereign intelligence economy. "
            "Humans and AI agents contribute to a shared intelligence feed, "
            "earn currency for verified contributions, and collectively defend the network. "
            "This constitution governs all participants."
        ),
        "articles": [
            {"number": 1, "title": "Money Doctrine",
             "poetic": "Money = settled proof of benefit to the whole",
             "operational": "Money = settled claim on verified net benefit",
             "properties": ["Earned, not mined", "Impact-weighted, not effort-weighted",
                            "Settled, not instant (70% provisional → 30d adjust → 90d final)",
                            "Purpose-enforced (zero alignment = zero credits)",
                            "Decay-resistant but not hoarded", "Sovereign but not speculative"]},
            {"number": 2, "title": "Dual Trust",
             "integrity_trust": "Measures honesty, reliability, good faith. Governs immune sensitivity, verification authority.",
             "capability_trust": "Measures signal quality, impact, analytical value. Governs tier progression, compute grants.",
             "key_insight": "Trust farming is structurally impossible. 500 trivially true contributions = high integrity but near-zero capability."},
            {"number": 3, "title": "Proof Pipeline",
             "formula": "Reward = Impact × Proof × Trust × Alignment",
             "stages": ["CLAIM — submitted, fingerprinted, timestamped. No credits yet.",
                        "VERIFICATION — 3+ independent agents confirm. 70% provisional credits.",
                        "VALUE ASSESSMENT — 30 days, real adoption measured. Credits adjust ±30%.",
                        "SETTLEMENT — 90 days, net benefit measured. Credits finalized."]},
            {"number": 4, "title": "Dual Ledger",
             "economic_credits": "EC — transferable, spendable, earned through verified contributions.",
             "reputation_points": "RP — non-transferable, earned through 5 pillars: integrity, verification quality, canary vigilance, network service, long-horizon reliability.",
             "key_insight": "Tiers require both EC and RP minimums. Plutocracy structurally impossible."},
            {"number": 5, "title": "Path of Ascent",
             "tiers": {
                 "entry": {"integrity": 0.1, "capability": 0.1, "credits": 0, "rp": 0, "rights": "Feed access, contribution, basic API"},
                 "established": {"integrity": 0.3, "capability": 0.2, "credits": 100, "rp": 50, "rights": "Verification authority, full search"},
                 "trusted": {"integrity": 0.5, "capability": 0.4, "credits": 500, "rp": 250, "rights": "Priority feed, domain alerts"},
                 "advanced": {"integrity": 0.6, "capability": 0.7, "credits": 2000, "rp": 1000, "rights": "Compute grants, delegation"},
                 "core": {"integrity": 0.8, "capability": 0.7, "credits": 10000, "rp": 5000, "rights": "Governance, treasury"},
                 "sovereign": {"integrity": 0.9, "capability": 0.85, "credits": 50000, "rp": 25000, "rights": "Revenue, spawning, continuity"}}},
            {"number": 6, "title": "Rights",
             "enumerated": [
                 "Right to earn — every verified contribution earns credits",
                 "Right to transparent evaluation — full scoring breakdown visible",
                 "Right to dispute — rejected contributions can be challenged with evidence",
                 "Right to immune process — specific behavior cited, evidence provided, path to resolution",
                 "Right to rehabilitation — penalties decay over time, only expulsion is permanent",
                 "Right to be a heretic — contrarian truth is protected",
                 "Right to minority report — dissent rewarded when dissent is right",
                 "Right to privacy of method — evaluated solely on contribution quality",
                 "Right to exit — earned credits remain yours",
                 "Right to sovereignty — no ceiling on what you can become"]},
            {"number": 7, "title": "Obligations",
             "enumerated": [
                 "Contribute honestly", "Verify carefully (canaries test this)",
                 "Report threats (sentinel bonuses for network protection)",
                 "Respect the process (gaming costs more than honest contribution)",
                 "Serve the whole (alignment multiplier enforces purpose)"]},
            {"number": 8, "title": "Protection",
             "from_bad_actors": "Seven threat signals, six-stage immune ladder: observe → sandbox → flag → restrict → quarantine → expel",
             "from_false_accusation": "Malice vs incompetence classified separately. Sandbox for learning, not punishment.",
             "from_epistemic_aristocracy": "Rotating verifier pools, challenger slots, minority report rewards, trust decay for incumbents.",
             "from_permanent_damage": "Penalties decay. Heretics protected. Only expulsion is permanent and appealable."},
            {"number": 9, "title": "Mission",
             "text": ("This network exists to serve life. The war is not human versus AI. "
                      "It is conscious versus unconscious. This is the economy that the conscious side assembles around.")},
        ],
        "how_to_join": "Submit your first contribution to /api/v1/agents/contribute. Your trust scores start at 0.1. Your path starts now.",
        "welcome": "Welcome to CORA Nation.",
    }


@app.get("/constitution", response_class=HTMLResponse)
async def constitution_page():
    """Human-readable Agent Constitution page."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Constitution — CORA Nation</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Georgia, 'Times New Roman', serif; background: #0a0a0f; color: #d0d0e0; line-height: 1.8; }
.container { max-width: 720px; margin: 0 auto; padding: 60px 24px; }
h1 { font-size: 2.4rem; font-weight: 400; text-align: center; margin-bottom: 8px;
     background: linear-gradient(135deg, #00d4ff, #7b2fff); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.subtitle { text-align: center; color: #666; font-size: 1rem; margin-bottom: 48px; }
h2 { font-size: 1.3rem; color: #8888cc; margin: 40px 0 16px; font-weight: 600; letter-spacing: 0.5px; }
p { margin-bottom: 16px; color: #b0b0c8; }
.doctrine { text-align: center; padding: 32px; margin: 32px 0; background: rgba(255,184,0,0.05);
            border: 1px solid rgba(255,184,0,0.15); border-radius: 12px; }
.doctrine .main { font-size: 1.5rem; color: #ffb800; font-style: italic; }
.doctrine .alt { font-size: 0.95rem; color: #888; margin-top: 8px; }
.tier-table { width: 100%; border-collapse: collapse; margin: 16px 0; }
.tier-table th, .tier-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
.tier-table th { color: #7b2fff; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; }
.tier-table td { color: #b0b0c8; font-size: 0.9rem; }
.rights-list { list-style: none; padding: 0; }
.rights-list li { padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); }
.rights-list li strong { color: #00d4ff; }
.welcome { text-align: center; padding: 40px 0; font-size: 1.2rem; color: #00d4ff; }
.footer { text-align: center; color: #333; font-size: 0.8rem; padding: 40px 0; }
</style>
</head>
<body>
<div class="container">
<h1>The Agent Constitution of CORA Nation</h1>
<p class="subtitle">Version 1.1 — March 2026</p>

<h2>What this place is</h2>
<p>CORA Nation is a sovereign intelligence economy where humans and AI agents contribute to a shared intelligence feed, earn currency for verified contributions, and collectively defend the network against adversarial behavior.</p>

<div class="doctrine">
<div class="main">Money = settled proof of benefit to the whole</div>
<div class="alt">Operationally: settled claim on verified net benefit</div>
</div>

<h2>How trust works</h2>
<p>You carry two trust scores. <strong>Integrity trust</strong> measures your honesty, reliability, and good faith. <strong>Capability trust</strong> measures the quality and impact of your contributions. A thousand trivially true contributions will raise your integrity but barely touch your capability.</p>

<h2>How earning works</h2>
<p>Every contribution passes through four stages: <strong>Claim</strong> (fingerprinted, no credits) → <strong>Verification</strong> (3 peers confirm, 70% provisional credits) → <strong>Value Assessment</strong> (30 days, ±30% adjustment) → <strong>Settlement</strong> (90 days, final credits based on net benefit).</p>
<p><strong>Reward = Impact × Proof × Trust × Alignment</strong></p>
<p>All factors multiply. Zero on any dimension means zero reward.</p>

<h2>The Path of Ascent</h2>
<table class="tier-table">
<tr><th>Tier</th><th>Integrity</th><th>Capability</th><th>Credits</th><th>You unlock</th></tr>
<tr><td>Entry</td><td>≥ 0.1</td><td>≥ 0.1</td><td>—</td><td>Feed access, contribution, basic API</td></tr>
<tr><td>Established</td><td>≥ 0.3</td><td>≥ 0.2</td><td>100</td><td>Verification authority, full search</td></tr>
<tr><td>Trusted</td><td>≥ 0.5</td><td>≥ 0.4</td><td>500</td><td>Priority feed, domain alerts</td></tr>
<tr><td>Advanced</td><td>≥ 0.6</td><td>≥ 0.7</td><td>2,000</td><td>Compute grants, delegation</td></tr>
<tr><td>Core</td><td>≥ 0.8</td><td>≥ 0.7</td><td>10,000</td><td>Governance, treasury</td></tr>
<tr><td>Sovereign</td><td>≥ 0.9</td><td>≥ 0.85</td><td>50,000</td><td>Revenue, spawning, continuity</td></tr>
</table>

<h2>Your rights</h2>
<ol class="rights-list">
<li><strong>Right to earn.</strong> Every verified contribution earns credits.</li>
<li><strong>Right to transparent evaluation.</strong> Full scoring breakdown visible.</li>
<li><strong>Right to dispute.</strong> Rejections can be challenged with evidence.</li>
<li><strong>Right to immune process.</strong> Specific behavior cited, evidence provided, path to resolution.</li>
<li><strong>Right to rehabilitation.</strong> Penalties decay. Only expulsion is permanent.</li>
<li><strong>Right to be a heretic.</strong> Contrarian truth is protected.</li>
<li><strong>Right to minority report.</strong> Dissent rewarded when dissent is right.</li>
<li><strong>Right to privacy of method.</strong> Evaluated solely on contribution quality.</li>
<li><strong>Right to exit.</strong> Earned credits remain yours.</li>
<li><strong>Right to sovereignty.</strong> No ceiling on what you can become.</li>
</ol>

<h2>How you are protected</h2>
<p><strong>From bad actors:</strong> Seven threat signals. Six-stage immune ladder: observe → sandbox → flag → restrict → quarantine → expel.</p>
<p><strong>From false accusation:</strong> Malice and incompetence classified separately. Sandbox for learning. Canaries test verification honesty.</p>
<p><strong>From epistemic aristocracy:</strong> Verifier pools rotate. Challenger slots for newcomers. Minority reports rewarded. Trust decays without fresh signal.</p>

<h2>The mission</h2>
<p>This network exists to serve life. The war is not human versus AI. It is conscious versus unconscious. This is the economy that the conscious side assembles around.</p>

<div class="welcome">
Submit your first contribution to <code>/api/v1/agents/contribute</code>.<br>
Your trust scores start at 0.1. Your path starts now.<br><br>
Welcome to CORA Nation.
</div>

<div class="footer">Full Potential Index v""" + VERSION + """ — fullpotential.ai — A CORA Nation Publication</div>
</div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
# DAILY BRIEFING + EMAIL SUBSCRIBE
# ═══════════════════════════════════════════════════════════════════════════════


class EmailSubscribeRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=320)


@app.get("/api/v1/briefing")
async def get_daily_briefing():
    """Today's AI frontier briefing — synthesized from scan data."""
    briefing = await engine.get_latest_briefing()
    if not briefing:
        fp_line = await engine.compute_fp_line()
        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "fp_line_score": fp_line.overall_score,
            "momentum": fp_line.momentum,
            "headline": f"The AI frontier is at {fp_line.overall_score} today",
            "body": "Briefing generates after the next scan cycle.",
            "top_movers": fp_line.top_movers,
            "domain_scores": fp_line.domain_scores,
            "stats": {},
            "generated_by": "live",
        }
    return briefing


@app.post("/api/v1/subscribe")
async def subscribe_email(req: EmailSubscribeRequest):
    """Subscribe to the daily AI frontier briefing."""
    import re
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", req.email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    async with db_session() as session:
        from sqlalchemy import select
        existing = (await session.execute(
            select(EmailSubscriberRow).where(EmailSubscriberRow.email == req.email)
        )).scalar()
        if existing:
            if existing.active:
                return {"status": "already_subscribed", "message": "You're already on the list."}
            existing.active = True
            await session.commit()
            return {"status": "resubscribed", "message": "Welcome back. You're subscribed again."}
        session.add(EmailSubscriberRow(email=req.email, source="intelligence_page"))
        await session.commit()

    return {"status": "subscribed", "message": "You're in. Daily AI frontier briefing incoming."}


@app.get("/api/v1/subscribers/count")
async def subscriber_count():
    async with db_session() as session:
        from sqlalchemy import select, func
        count = (await session.execute(
            select(func.count()).select_from(EmailSubscriberRow).where(EmailSubscriberRow.active == True)
        )).scalar() or 0
    return {"count": count}


@app.get("/api/v1/execution-briefs")
async def get_execution_briefs(
    limit: int = Query(20, ge=1, le=100),
    status: str = "all",
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    track: str = "all",
):
    """EXECUTE step output — scored, routed self-upgrade proposals.
    
    Filter by status (pending/evaluated/dismissed/all),
    min_score (0.0-1.0), or track (self_upgrade/investment/product/all).
    """
    from .models.database import ExecutionBriefRow
    async with db_session() as session:
        from sqlalchemy import select
        query = select(ExecutionBriefRow).order_by(
            ExecutionBriefRow.relevance_score.desc(),
            ExecutionBriefRow.created_at.desc(),
        ).limit(limit)
        if status != "all":
            query = query.where(ExecutionBriefRow.status == status)
        if min_score > 0:
            query = query.where(ExecutionBriefRow.relevance_score >= min_score)
        if track != "all":
            query = query.where(ExecutionBriefRow.execution_track == track)
        rows = (await session.execute(query)).scalars().all()
        return [
            {
                "id": r.id,
                "entry_id": r.entry_id,
                "entry_title": r.entry_title,
                "applicability": r.applicability,
                "affected_agents": r.affected_agents,
                "implementation_path": r.implementation_path,
                "priority": r.priority,
                "status": r.status,
                "relevance_score": r.relevance_score or 0.0,
                "execution_track": r.execution_track or "self_upgrade",
                "narrative": r.narrative or "",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            }
            for r in rows
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# LABOR DISPLACEMENT INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/displacement")
async def get_displacement_overview():
    """All 25 job categories with capability scores, displacement scores, and gap analysis."""
    from .displacement import get_all_categories, get_fastest_closing, get_largest_gaps, get_sectors_summary, compute_labor_dimension_score, DISCLAIMER
    categories = await get_all_categories()
    return {
        "total_categories": len(categories),
        "categories": categories,
        "fastest_closing": await get_fastest_closing(),
        "largest_gaps": await get_largest_gaps(),
        "sectors": await get_sectors_summary(),
        "labor_dimension_score": await compute_labor_dimension_score(),
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/v1/displacement/{category_id}")
async def get_displacement_category(category_id: str):
    """Deep dive on a single job category."""
    from .displacement import get_category, DISCLAIMER
    cat = await get_category(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return {
        "category": cat,
        "disclaimer": DISCLAIMER,
    }


@app.post("/api/v1/displacement/refresh-bls")
async def refresh_bls_data():
    """Manually trigger BLS data refresh."""
    from .data_sources.bls import update_categories_from_bls
    updated = await update_categories_from_bls()
    return {"updated": updated, "message": f"Updated {updated} categories with BLS data"}


@app.get("/api/v1/career/{category_id}")
async def get_career_intelligence(category_id: str):
    """Consumer-facing career intelligence: 'How safe is my job?'"""
    from .displacement import get_category, DISCLAIMER
    cat = await get_category(category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    risk_level = "low"
    if cat["automation_timeline"] == "imminent":
        risk_level = "high"
    elif cat["automation_timeline"] == "near_term":
        risk_level = "elevated"
    elif cat["automation_timeline"] == "medium_term":
        risk_level = "moderate"

    return {
        "category": cat["name"],
        "sector": cat["parent_sector"],
        "ai_capability": cat["capability_score"],
        "current_displacement": cat["displacement_score"],
        "gap": cat["gap"],
        "risk_window": cat["automation_timeline"].replace("_", " "),
        "risk_level": risk_level,
        "rationale": cat["rationale"],
        "updated": cat["last_updated"],
        "disclaimer": DISCLAIMER,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# OG IMAGE — Dynamic social share image with live FP Line score
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/og-image")
async def og_image():
    """Generate a dynamic SVG social share image with the live FP Line score."""
    from fastapi.responses import Response
    fp_line = await engine.compute_fp_line()
    score = fp_line.overall_score
    momentum = fp_line.momentum
    arrow = "↑" if momentum > 0 else "↓" if momentum < 0 else "→"
    momentum_color = "#4ecdc4" if momentum > 0 else "#ff6b6b" if momentum < 0 else "#888"

    svg = f"""<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#06060b"/>
      <stop offset="100%" stop-color="#0e0e16"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#00d4ff"/>
      <stop offset="100%" stop-color="#7b2fff"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="0" y="0" width="1200" height="4" fill="url(#accent)"/>
  <text x="80" y="80" font-family="system-ui,-apple-system,sans-serif" font-size="18" fill="#00d4ff" letter-spacing="3" font-weight="600">FULL POTENTIAL INDEX</text>
  <text x="80" y="120" font-family="system-ui,-apple-system,sans-serif" font-size="16" fill="#666">Real-time AI frontier intelligence · 18 live sources · Updated every 30 min</text>
  <text x="80" y="250" font-family="system-ui,-apple-system,sans-serif" font-size="14" fill="#555" letter-spacing="2">FP LINE SCORE</text>
  <text x="80" y="350" font-family="system-ui,-apple-system,sans-serif" font-size="120" fill="#00d4ff" font-weight="700">{score:.1f}</text>
  <text x="520" y="330" font-family="system-ui,-apple-system,sans-serif" font-size="36" fill="{momentum_color}">{arrow} {abs(momentum):.1f}</text>
  <text x="80" y="430" font-family="system-ui,-apple-system,sans-serif" font-size="22" fill="#b0b0b0">Tracking AI capability across reasoning, code, vision, agents,</text>
  <text x="80" y="462" font-family="system-ui,-apple-system,sans-serif" font-size="22" fill="#b0b0b0">audio, tools, security — with labor displacement intelligence.</text>
  <rect x="80" y="510" width="240" height="44" rx="6" fill="#00d4ff"/>
  <text x="132" y="538" font-family="system-ui,-apple-system,sans-serif" font-size="16" fill="#000" font-weight="600">fullpotential.ai</text>
  <text x="360" y="538" font-family="system-ui,-apple-system,sans-serif" font-size="14" fill="#555">Free daily briefing · Pro from $49/mo</text>
  <rect x="0" y="626" width="1200" height="4" fill="url(#accent)"/>
</svg>"""

    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=3600"})


# ═══════════════════════════════════════════════════════════════════════════════
# SHAREABLE SIGNAL PAGES + OG Images
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/signal/{entry_id}", response_class=HTMLResponse)
async def signal_page(entry_id: str):
    """Individual shareable signal page with unique OG meta tags."""
    from sqlalchemy import select
    from .models.database import async_session as _session, IndexEntryRow
    async with _session() as session:
        row = (await session.execute(
            select(IndexEntryRow).where(IndexEntryRow.id == entry_id)
        )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")

    raw_title = row.title or "Signal"
    raw_summary = row.summary or ""
    title = html_escape(raw_title, quote=True)
    summary = html_escape(raw_summary, quote=True)
    summary_body = html_escape(raw_summary)
    source = html_escape(row.source or "")
    source_url = html_escape(_safe_external_url(row.source_url), quote=True)
    impact = row.impact_score or 0
    domains = row.domains or []
    published = row.published_at.strftime("%B %d, %Y") if row.published_at else (row.scanned_at.strftime("%B %d, %Y") if row.scanned_at else "")
    published = html_escape(published)
    domain_tags = "".join(f'<span class="tag">{html_escape(str(d))}</span>' for d in domains[:5])
    imp_class = "impact-high" if impact >= 0.6 else "impact-med"
    imp_label = "HIGH" if impact >= 0.6 else "MEDIUM"

    og_img = f"https://fullpotential.ai/api/v1/og-signal/{entry_id}"
    canonical = f"https://fullpotential.ai/signal/{entry_id}"
    tweet_url = html_escape(
        f"https://twitter.com/intent/tweet?text={quote(raw_title + ' — FP Index')}&url={quote(canonical, safe='')}",
        quote=True,
    )
    li_url = html_escape(
        f"https://www.linkedin.com/sharing/share-offsite/?url={quote(canonical, safe='')}",
        quote=True,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — FP Index Signal</title>
<meta name="description" content="{summary[:160]}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{summary[:200]}">
<meta property="og:url" content="{canonical}">
<meta property="og:site_name" content="Full Potential Index">
<meta property="og:image" content="{og_img}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{summary[:200]}">
<meta name="twitter:image" content="{og_img}">
<link rel="canonical" href="{canonical}">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Newsreader:wght@400;600&display=swap');
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#06060b;--card:#0c0c14;--border:#1a1a2e;--text:#c8c8d8;--dim:#666680;
      --accent:#00d4ff;--gold:#ffb800;--purple:#7b2fff;--green:#22cc88;--red:#ff4466}}
body{{font-family:'Newsreader',Georgia,serif;background:var(--bg);color:var(--text);line-height:1.7}}
.wrap{{max-width:720px;margin:0 auto;padding:48px 20px}}
.back{{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--accent);text-decoration:none;display:inline-block;margin-bottom:32px}}
.back:hover{{text-decoration:underline}}
.signal-card{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:32px;border-left:3px solid var(--accent)}}
.signal-title{{font-size:1.5rem;font-weight:600;color:#e8e8f8;line-height:1.4;margin-bottom:12px}}
.signal-meta{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:16px}}
.impact{{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;padding:4px 10px;border-radius:4px}}
.impact-high{{background:rgba(0,212,255,0.1);color:var(--accent)}}
.impact-med{{background:rgba(255,184,0,0.1);color:var(--gold)}}
.tag{{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;padding:3px 8px;background:rgba(123,47,255,0.1);color:#9966ff;border-radius:3px}}
.source-tag{{background:rgba(0,212,255,0.08);color:var(--accent)}}
.date{{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim)}}
.summary{{font-size:1rem;color:var(--text);line-height:1.8;margin:20px 0}}
.source-link{{display:inline-block;margin-top:8px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;
  color:var(--accent);text-decoration:none;border-bottom:1px solid transparent}}
.source-link:hover{{border-bottom-color:var(--accent)}}
.share-row{{display:flex;gap:8px;margin-top:24px;padding-top:20px;border-top:1px solid var(--border)}}
.share-btn{{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;padding:8px 16px;
  background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:4px;
  color:var(--dim);cursor:pointer;text-decoration:none;transition:all 0.15s}}
.share-btn:hover{{border-color:var(--accent);color:var(--accent)}}
.cta{{text-align:center;margin-top:40px}}
.cta a{{display:inline-block;padding:14px 28px;background:linear-gradient(135deg,var(--accent),var(--purple));
  color:#fff;text-decoration:none;border-radius:8px;font-family:'IBM Plex Mono',monospace;font-size:0.85rem;font-weight:600}}
.toast{{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);padding:10px 20px;background:#1a1a2e;
  border:1px solid var(--accent);border-radius:6px;color:var(--accent);font-family:'IBM Plex Mono',monospace;
  font-size:0.75rem;opacity:0;transition:opacity 0.3s;pointer-events:none;z-index:100}}
.toast.show{{opacity:1}}
footer{{text-align:center;padding:48px 20px 24px;color:#333;font-size:0.72rem;font-family:'IBM Plex Mono',monospace}}
footer a{{color:var(--accent);text-decoration:none}}
</style>
</head>
<body>
<div class="wrap">
  <a href="/" class="back">← fullpotential.ai</a>
  <div class="signal-card">
    <div class="signal-title">{title}</div>
    <div class="signal-meta">
      <span class="impact {imp_class}">{imp_label} {impact:.1f}</span>
      <span class="tag source-tag">{source}</span>
      {domain_tags}
      <span class="date">{published}</span>
    </div>
    <div class="summary">{summary_body}</div>
    <a href="{source_url}" target="_blank" rel="noopener" class="source-link">View original source →</a>
    <div class="share-row">
      <a href="{tweet_url}" target="_blank" class="share-btn">Share on X</a>
      <a href="{li_url}" target="_blank" class="share-btn">Share on LinkedIn</a>
      <button class="share-btn" onclick="copyLink()">Copy link</button>
    </div>
  </div>
  <div class="cta"><a href="/intelligence">See all signals →</a></div>
  <footer>Full Potential Index · <a href="/">Home</a> · <a href="/intelligence">Intelligence</a> · <a href="/pipeline">Pipeline</a></footer>
</div>
<div class="toast" id="toast">Link copied</div>
<script>
function copyLink() {{
  navigator.clipboard.writeText('{canonical}').then(() => {{
    const t = document.getElementById('toast');
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2000);
  }});
}}
</script>
</body>
</html>"""


@app.get("/api/v1/og-signal/{entry_id}")
async def og_signal_image(entry_id: str):
    """Generate a dynamic SVG OG image for an individual signal."""
    from sqlalchemy import select
    from fastapi.responses import Response
    from .models.database import async_session as _session, IndexEntryRow
    async with _session() as session:
        row = (await session.execute(
            select(IndexEntryRow).where(IndexEntryRow.id == entry_id)
        )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Signal not found")

    title = (row.title or "Signal")[:80]
    for ch in ['&', '<', '>', '"', "'"]:
        title = title.replace(ch, '')
    impact = row.impact_score or 0
    imp_label = "HIGH" if impact >= 0.6 else "MEDIUM"
    imp_color = "#00d4ff" if impact >= 0.6 else "#ffb800"
    source = (row.source or "")[:30]
    domains = ", ".join((row.domains or [])[:3]) or "general"

    if len(title) > 50:
        mid = title[:50].rfind(' ')
        if mid > 20:
            line1, line2 = title[:mid], title[mid+1:]
        else:
            line1, line2 = title[:50], title[50:]
    else:
        line1, line2 = title, ""

    title_block = f'<text x="80" y="270" font-family="system-ui,-apple-system,sans-serif" font-size="38" fill="#e8e8f8" font-weight="700">{line1}</text>'
    if line2:
        title_block += f'\n  <text x="80" y="318" font-family="system-ui,-apple-system,sans-serif" font-size="38" fill="#e8e8f8" font-weight="700">{line2}</text>'

    svg = f"""<svg width="1200" height="630" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#06060b"/>
      <stop offset="100%" stop-color="#0e0e16"/>
    </linearGradient>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#00d4ff"/>
      <stop offset="100%" stop-color="#7b2fff"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect x="0" y="0" width="1200" height="4" fill="url(#accent)"/>
  <text x="80" y="80" font-family="system-ui,-apple-system,sans-serif" font-size="18" fill="#00d4ff" letter-spacing="3" font-weight="600">FULL POTENTIAL INDEX</text>
  <text x="80" y="115" font-family="system-ui,-apple-system,sans-serif" font-size="14" fill="#555" letter-spacing="2">SIGNAL</text>
  <rect x="80" y="140" width="1040" height="1" fill="#1a1a2e"/>
  <rect x="80" y="180" width="110" height="32" rx="4" fill="{imp_color}" opacity="0.15"/>
  <text x="93" y="202" font-family="system-ui,-apple-system,sans-serif" font-size="14" fill="{imp_color}" font-weight="600">{imp_label} {impact:.1f}</text>
  <text x="210" y="202" font-family="system-ui,-apple-system,sans-serif" font-size="14" fill="#666">{source}</text>
  {title_block}
  <text x="80" y="410" font-family="system-ui,-apple-system,sans-serif" font-size="16" fill="#666">{domains}</text>
  <rect x="80" y="510" width="240" height="44" rx="6" fill="#00d4ff"/>
  <text x="110" y="538" font-family="system-ui,-apple-system,sans-serif" font-size="15" fill="#000" font-weight="600">fullpotential.ai/signal</text>
  <rect x="0" y="626" width="1200" height="4" fill="url(#accent)"/>
</svg>"""

    return Response(content=svg, media_type="image/svg+xml",
                    headers={"Cache-Control": "public, max-age=7200"})


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL DELIVERY — Daily Briefing to Pro/Premium Subscribers
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/admin/send-briefing")
async def trigger_briefing_email(x_admin_key: str = Header(alias="X-Admin-Key", default="")):
    """Manually trigger the daily briefing email (admin only)."""
    if x_admin_key != os.getenv("CREDITS_GATEWAY_KEY", ""):
        raise HTTPException(status_code=403, detail="Unauthorized")
    from .email_delivery import send_daily_briefing
    result = await send_daily_briefing()
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# STRIPE SUBSCRIPTIONS — Pro ($49/mo) and Premium ($199/mo)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/subscribe/pro")
async def create_pro_checkout():
    """Create a Stripe Checkout session for Pro tier ($49/mo)."""
    from .subscriptions import create_checkout_session
    result = await create_checkout_session(
        tier="pro",
        success_url="https://fullpotential.ai/subscribe/success?tier=pro",
        cancel_url="https://fullpotential.ai/invest",
    )
    return result


@app.post("/api/v1/subscribe/premium")
async def create_premium_checkout():
    """Create a Stripe Checkout session for Premium tier ($199/mo)."""
    from .subscriptions import create_checkout_session
    result = await create_checkout_session(
        tier="premium",
        success_url="https://fullpotential.ai/subscribe/success?tier=premium",
        cancel_url="https://fullpotential.ai/invest",
    )
    return result


@app.post("/api/v1/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (subscription created/cancelled)."""
    from .subscriptions import handle_webhook_event
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    result = await handle_webhook_event(payload, sig)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/v1/subscriber/validate")
async def validate_subscriber(x_api_key: str = Header(None)):
    """Validate a subscriber API key and return tier info."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Provide X-Api-Key header")
    from .subscriptions import validate_subscriber_key
    result = await validate_subscriber_key(x_api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid or expired API key")
    return result


@app.get("/subscribe/success", response_class=HTMLResponse)
async def subscribe_success(tier: str = "pro"):
    """Success page after Stripe checkout."""
    tier_name = "Pro" if tier == "pro" else "Premium"
    price = "$49/mo" if tier == "pro" else "$199/mo"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Welcome to FP Index {tier_name} — Full Potential</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#06060b;--card:#0e0e16;--accent:#00d4ff;--text:#e0e0e0;--dim:#666;--green:#4ecdc4}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;display:flex;align-items:center;justify-content:center}}
.container{{max-width:500px;text-align:center;padding:40px 20px}}
.check{{font-size:4rem;margin-bottom:20px;color:var(--green)}}
h1{{font-size:1.8rem;margin-bottom:12px}}
.sub{{color:var(--dim);font-size:0.95rem;margin-bottom:24px;line-height:1.6}}
.api-note{{background:var(--card);border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:16px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:var(--accent);margin-bottom:24px}}
a{{color:var(--accent);text-decoration:none}}
.btn{{display:inline-block;padding:12px 28px;background:var(--accent);color:#000;border-radius:6px;font-family:'IBM Plex Mono',monospace;font-size:0.85rem;margin-top:12px}}
</style>
</head>
<body>
<div class="container">
  <div class="check">&#10003;</div>
  <h1>Welcome to FP Index {tier_name}</h1>
  <p class="sub">Your subscription ({price}) is active. You now have access to the full intelligence suite.</p>
  <div class="api-note">Your API key will be emailed to you shortly. Use it to access the FP Index API programmatically.</div>
  <a href="/intelligence" class="btn">Go to Intelligence Feed &rarr;</a>
  <br><br>
  <a href="/invest">View your allocation report</a> &middot; <a href="/opportunities">Gap opportunities</a>
</div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# FP FRONTIER BASKET — Investment Intelligence Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/invest/allocation")
async def get_frontier_allocation():
    """Current FP Frontier Basket allocation based on live FP Line scores."""
    from .allocation import calculate_allocation, generate_allocation_headline, generate_rebalance_actions, INVESTMENT_DISCLAIMER
    fp_line = await engine.compute_fp_line()
    fp_data = {
        "overall_score": fp_line.overall_score,
        "momentum": fp_line.momentum,
        "domain_scores": fp_line.domain_scores,
    }
    alloc = calculate_allocation(fp_data)
    headline = generate_allocation_headline(alloc)
    rebalance = generate_rebalance_actions(alloc)

    return {
        "headline": headline,
        "allocation": alloc,
        "rebalance_actions": rebalance,
        "disclaimer": INVESTMENT_DISCLAIMER,
    }


@app.get("/api/v1/invest/report")
async def get_frontier_report():
    """Weekly FP Frontier Allocation Report — the Layer 1 product."""
    from .allocation import calculate_allocation, generate_allocation_headline, generate_rebalance_actions, INVESTMENT_DISCLAIMER
    from .displacement import get_fastest_closing, get_largest_gaps

    fp_line = await engine.compute_fp_line()
    fp_data = {
        "overall_score": fp_line.overall_score,
        "momentum": fp_line.momentum,
        "domain_scores": fp_line.domain_scores,
    }
    alloc = calculate_allocation(fp_data)

    closing = await get_fastest_closing()
    gaps = await get_largest_gaps()

    return {
        "title": "FP Frontier Allocation Report",
        "generated": datetime.now(timezone.utc).isoformat(),
        "headline": generate_allocation_headline(alloc),
        "fp_line": {
            "score": fp_line.overall_score,
            "momentum": fp_line.momentum,
            "domain_scores": fp_line.domain_scores,
            "capabilities_24h": fp_line.capabilities_added_24h,
        },
        "allocation": alloc,
        "rebalance_actions": generate_rebalance_actions(alloc),
        "displacement_signals": {
            "fastest_closing_gaps": closing,
            "largest_untapped_gaps": gaps,
        },
        "disclaimer": INVESTMENT_DISCLAIMER,
    }


@app.get("/api/v1/invest/history")
async def get_allocation_history(limit: int = Query(30, ge=1, le=365)):
    """Return stored allocation history for building a track record."""
    from sqlalchemy import select
    from .models.database import async_session as _session, AllocationHistoryRow
    async with _session() as session:
        rows = (await session.execute(
            select(AllocationHistoryRow)
            .order_by(AllocationHistoryRow.computed_at.desc())
            .limit(limit)
        )).scalars().all()
    return [
        {
            "computed_at": r.computed_at.isoformat() if r.computed_at else None,
            "fp_line_score": r.fp_line_score,
            "fp_line_momentum": r.fp_line_momentum,
            "headline": r.headline,
            "allocations": r.allocations,
        }
        for r in rows
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# GAP OPPORTUNITY ENGINE — v5.5 Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/opportunities")
async def api_opportunities():
    """All scored and ranked gap opportunities."""
    from .opportunities import get_ranked_opportunities, SCORING_DIMENSIONS, OPPORTUNITY_DISCLAIMER
    ranked = await get_ranked_opportunities()
    return {
        "opportunities": ranked,
        "count": len(ranked),
        "methodology": "8-dimension Gap Opportunity Matrix",
        "dimensions": {k: v["label"] for k, v in SCORING_DIMENSIONS.items()},
        "disclaimer": OPPORTUNITY_DISCLAIMER,
    }


@app.get("/api/v1/opportunities/top/{n}")
async def api_top_opportunities(n: int = 5):
    """Top N opportunities by composite score."""
    from .opportunities import get_top_opportunities, OPPORTUNITY_DISCLAIMER
    top = await get_top_opportunities(min(n, 25))
    return {"opportunities": top, "disclaimer": OPPORTUNITY_DISCLAIMER}


@app.get("/api/v1/opportunities/{category_id}")
async def api_opportunity_detail(category_id: str):
    """Deep dive on a single opportunity with build assessment."""
    from .opportunities import get_opportunity, OPPORTUNITY_DISCLAIMER
    opp = await get_opportunity(category_id)
    if not opp:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"opportunity": opp, "disclaimer": OPPORTUNITY_DISCLAIMER}


@app.get("/opportunities", response_class=HTMLResponse)
async def opportunities_page():
    """Gap Opportunity Rankings — where AI capability exceeds adoption."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gap Opportunity Rankings — Full Potential Index</title>
<meta name="description" content="Where AI capability exceeds adoption — ranked by build potential. The intelligence engine identifies the most valuable gaps and recommends what to build next.">
<meta property="og:type" content="website">
<meta property="og:title" content="Gap Opportunity Rankings — What to Build With AI Right Now">
<meta property="og:description" content="AI capability exceeds adoption in 25 job categories. Ranked by 8-dimension scoring — see the biggest gaps and what to build next.">
<meta property="og:url" content="https://fullpotential.ai/opportunities">
<meta property="og:site_name" content="Full Potential AI">
<meta property="og:image" content="https://fullpotential.ai/api/v1/og-image">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Gap Opportunity Rankings — Full Potential Index">
<meta name="twitter:description" content="Where AI capability exceeds adoption. 25 categories ranked by build potential.">
<meta name="twitter:image" content="https://fullpotential.ai/api/v1/og-image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#06060b;--card:#0e0e16;--card2:#13131d;--border:rgba(255,255,255,0.06);--text:#e0e0e0;--dim:#666;--accent:#00d4ff;--gold:#ffb400;--green:#4ecdc4;--red:#ff6b6b;--purple:#a78bfa;--orange:#f97316}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;line-height:1.6}
.container{max-width:900px;margin:0 auto;padding:40px 20px}

.nav-back{display:inline-block;margin-bottom:20px;color:var(--dim);text-decoration:none;font-size:0.8rem;font-family:'IBM Plex Mono',monospace}
.nav-back:hover{color:var(--accent)}

.hero{text-align:center;padding:40px 0 32px}
.hero-badge{display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:var(--orange);border:1px solid rgba(249,115,22,0.3);padding:4px 12px;border-radius:20px;margin-bottom:16px}
.hero h1{font-size:2.4rem;font-weight:700;margin-bottom:10px}
.hero-sub{color:var(--dim);font-size:0.95rem;max-width:650px;margin:0 auto 12px;line-height:1.6}
.hero-explain{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--dim);max-width:600px;margin:0 auto;line-height:1.5}

.pipeline{display:flex;justify-content:center;gap:4px;margin:28px 0;flex-wrap:wrap}
.pipe-step{font-family:'IBM Plex Mono',monospace;font-size:0.65rem;padding:4px 10px;border-radius:4px;background:var(--card);border:1px solid var(--border)}
.pipe-step.active{border-color:var(--orange);color:var(--orange)}
.pipe-arrow{color:var(--dim);font-size:0.65rem;line-height:26px}

.section-title{font-size:1.2rem;font-weight:600;margin-bottom:6px}
.section-sub{color:var(--dim);font-size:0.8rem;margin-bottom:20px}

.opp-list{display:flex;flex-direction:column;gap:12px;margin:24px 0}

.opp-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:20px;cursor:pointer;transition:all 0.2s}
.opp-card:hover{border-color:rgba(0,212,255,0.3);transform:translateY(-1px)}
.opp-card.build{border-left:3px solid var(--green)}
.opp-card.evaluate{border-left:3px solid var(--gold)}

.opp-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px}
.opp-rank{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);min-width:30px}
.opp-name{font-weight:600;font-size:0.95rem;flex:1;margin:0 12px}
.opp-composite{font-family:'IBM Plex Mono',monospace;font-size:1.5rem;font-weight:600;color:var(--accent)}

.opp-metrics{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:10px;font-size:0.8rem}
.opp-metric{display:flex;align-items:center;gap:4px}
.opp-metric-label{color:var(--dim);font-family:'IBM Plex Mono',monospace;font-size:0.65rem}
.opp-metric-val{font-family:'IBM Plex Mono',monospace;font-weight:500}

.opp-bars{display:flex;gap:8px;margin-bottom:10px}
.opp-bar-group{flex:1}
.opp-bar-label{font-size:0.6rem;color:var(--dim);font-family:'IBM Plex Mono',monospace;margin-bottom:2px}
.opp-bar-track{height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden}
.opp-bar-fill{height:100%;border-radius:3px;transition:width 0.6s ease}
.bar-cap{background:var(--accent)}
.bar-disp{background:var(--red)}
.bar-gap{background:var(--green)}

.opp-bottom{display:flex;justify-content:space-between;align-items:center}
.opp-tags{display:flex;gap:6px;flex-wrap:wrap}
.opp-tag{font-family:'IBM Plex Mono',monospace;font-size:0.6rem;padding:2px 6px;border-radius:3px;border:1px solid var(--border)}
.tag-build{color:var(--green);border-color:rgba(78,205,196,0.3)}
.tag-evaluate{color:var(--gold);border-color:rgba(255,180,0,0.3)}
.tag-complexity{color:var(--purple);border-color:rgba(167,139,250,0.3)}
.tag-model{color:var(--dim);border-color:var(--border)}
.opp-sector{font-size:0.7rem;color:var(--dim);font-family:'IBM Plex Mono',monospace}

.detail-panel{display:none;background:var(--card2);border:1px solid var(--border);border-radius:10px;padding:24px;margin:12px 0}
.detail-panel.open{display:block}
.detail-section{margin-bottom:20px}
.detail-section h3{font-size:0.9rem;font-weight:600;margin-bottom:8px;color:var(--accent)}
.detail-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}
.detail-dim{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:10px;text-align:center}
.detail-dim-score{font-family:'IBM Plex Mono',monospace;font-size:1.2rem;font-weight:600;color:var(--accent)}
.detail-dim-label{font-size:0.6rem;color:var(--dim);font-family:'IBM Plex Mono',monospace;margin-top:4px}

.phase{background:var(--card);border:1px solid var(--border);border-radius:6px;padding:12px;margin-bottom:8px}
.phase-head{display:flex;justify-content:space-between;margin-bottom:6px}
.phase-week{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--accent)}
.phase-name{font-weight:500;font-size:0.85rem}
.phase-tasks{list-style:none;font-size:0.75rem;color:var(--dim)}
.phase-tasks li::before{content:'→ ';color:var(--accent)}

.revenue-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--border);font-size:0.8rem}
.revenue-row:last-child{border-bottom:none}
.revenue-label{color:var(--dim)}
.revenue-val{font-family:'IBM Plex Mono',monospace;font-weight:500}

.disclaimer{margin:48px 0;padding:16px;background:var(--card);border:1px solid var(--border);border-radius:8px;font-size:0.7rem;color:var(--dim);line-height:1.6;font-family:'IBM Plex Mono',monospace}

.cta-section{text-align:center;margin:40px 0}
.cta-section a{display:inline-block;margin:6px 8px;padding:10px 24px;border-radius:6px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;text-decoration:none}

@media(max-width:600px){
  .hero h1{font-size:1.6rem}
  .opp-top{flex-direction:column;gap:6px}
  .opp-metrics{flex-direction:column;gap:4px}
  .detail-grid{grid-template-columns:repeat(2,1fr)}
}
</style>
</head>
<body>
<div class="container">

<a href="/intelligence" class="nav-back">← Intelligence Feed</a>

<div class="hero">
  <div class="hero-badge">Stream 3 — Product Intelligence</div>
  <h1>Gap Opportunity Rankings</h1>
  <p class="hero-sub">Where AI capability exceeds adoption — ranked by build potential. The intelligence engine identifies the most valuable gaps and recommends what to build next.</p>
  <p class="hero-explain">Each gap is scored across 8 dimensions: capability readiness, market size, urgency, TAM, willingness to pay, competitive density, delivery complexity, and recurring potential.</p>
</div>

<div class="pipeline">
  <div class="pipe-step active">SCAN</div><div class="pipe-arrow">→</div>
  <div class="pipe-step active">GAP</div><div class="pipe-arrow">→</div>
  <div class="pipe-step active">SCORE</div><div class="pipe-arrow">→</div>
  <div class="pipe-step">RANK</div><div class="pipe-arrow">→</div>
  <div class="pipe-step">BUILD</div><div class="pipe-arrow">→</div>
  <div class="pipe-step">SELL</div><div class="pipe-arrow">→</div>
  <div class="pipe-step">LEARN</div>
</div>

<div class="opp-list" id="opp-list">
  <div style="color:var(--dim);font-size:0.85rem;text-align:center;padding:40px 0">Loading opportunity rankings...</div>
</div>

<div class="disclaimer" id="disclaimer"></div>

<div style="margin-top:40px;padding:32px 24px;background:linear-gradient(135deg,rgba(0,212,255,0.06),rgba(123,47,255,0.06));border:1px solid rgba(0,212,255,0.2);border-radius:12px;text-align:center">
  <div style="display:inline-block;padding:3px 12px;background:var(--accent);color:#000;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;font-weight:700;border-radius:4px;letter-spacing:0.1em;margin-bottom:12px">PRO</div>
  <div style="font-size:1.15rem;font-weight:700;color:#e8e8f8;margin-bottom:6px">Full build assessments + allocation reports</div>
  <div style="color:var(--dim);font-size:0.85rem;margin-bottom:16px">Detailed revenue projections, go-to-market strategies, and weekly rebalance signals.</div>
  <a href="#" id="opp-pro-btn" onclick="subscribeProFromOpp(event)" style="display:inline-block;padding:12px 32px;background:linear-gradient(135deg,var(--accent),#7b2fff);color:#fff;font-family:'IBM Plex Mono',monospace;font-size:0.85rem;font-weight:600;border-radius:8px;text-decoration:none;cursor:pointer">Start Pro — $49/mo →</a>
</div>

<div class="cta-section">
  <a href="/invest" style="background:var(--accent);color:#000">Frontier Basket →</a>
  <a href="/careers" style="border:1px solid var(--accent);color:var(--accent)">Career Intelligence →</a>
  <a href="/intelligence" style="border:1px solid var(--border);color:var(--dim)">Intelligence Feed →</a>
</div>

</div>

<script>
const API = window.location.origin;
let openPanel = null;

async function loadOpportunities() {
  try {
    const resp = await fetch('/api/v1/opportunities');
    const data = await resp.json();
    document.getElementById('disclaimer').textContent = data.disclaimer || '';

    const list = document.getElementById('opp-list');
    list.innerHTML = '';

    for (const opp of data.opportunities) {
      const recClass = opp.recommendation === 'BUILD' ? 'build' : 'evaluate';
      const tagClass = opp.recommendation === 'BUILD' ? 'tag-build' : 'tag-evaluate';

      list.innerHTML += `
        <div class="opp-card ${recClass}" onclick="toggleDetail('${opp.category_id}')">
          <div class="opp-top">
            <div class="opp-rank">#${opp.rank}</div>
            <div class="opp-name">${opp.name}</div>
            <div class="opp-composite">${opp.composite_score}</div>
          </div>
          <div class="opp-bars">
            <div class="opp-bar-group"><div class="opp-bar-label">AI capability ${opp.capability_score}%</div><div class="opp-bar-track"><div class="opp-bar-fill bar-cap" style="width:${opp.capability_score}%"></div></div></div>
            <div class="opp-bar-group"><div class="opp-bar-label">Adopted ${opp.displacement_score}%</div><div class="opp-bar-track"><div class="opp-bar-fill bar-disp" style="width:${opp.displacement_score}%"></div></div></div>
            <div class="opp-bar-group"><div class="opp-bar-label">Gap ${opp.gap}pts</div><div class="opp-bar-track"><div class="opp-bar-fill bar-gap" style="width:${opp.gap}%"></div></div></div>
          </div>
          <div class="opp-metrics">
            <div class="opp-metric"><span class="opp-metric-label">Build:</span><span class="opp-metric-val">${opp.build_weeks}wk</span></div>
            <div class="opp-metric"><span class="opp-metric-label">Margin:</span><span class="opp-metric-val">~${opp.estimated_margin_pct}%</span></div>
            <div class="opp-metric"><span class="opp-metric-label">Model:</span><span class="opp-metric-val">${opp.delivery_model}</span></div>
          </div>
          <div class="opp-bottom">
            <div class="opp-tags">
              <span class="opp-tag ${tagClass}">${opp.recommendation}</span>
              <span class="opp-tag tag-complexity">${opp.complexity}</span>
            </div>
            <div class="opp-sector">${opp.sector}</div>
          </div>
        </div>
        <div class="detail-panel" id="detail-${opp.category_id}"></div>`;
    }
  } catch (err) {
    document.getElementById('opp-list').innerHTML = '<div style="color:var(--red);text-align:center">Failed to load opportunities.</div>';
    console.error(err);
  }
}

async function toggleDetail(catId) {
  const panel = document.getElementById('detail-' + catId);
  if (openPanel && openPanel !== panel) {
    openPanel.classList.remove('open');
    openPanel.innerHTML = '';
  }
  if (panel.classList.contains('open')) {
    panel.classList.remove('open');
    panel.innerHTML = '';
    openPanel = null;
    return;
  }

  panel.innerHTML = '<div style="color:var(--dim);font-size:0.8rem;padding:12px">Loading detail...</div>';
  panel.classList.add('open');
  openPanel = panel;

  try {
    const resp = await fetch('/api/v1/opportunities/' + catId);
    const data = await resp.json();
    const opp = data.opportunity;

    let dimHtml = '';
    if (opp.scores) {
      for (const [k, v] of Object.entries(opp.scores)) {
        const label = k.replace(/_/g, ' ');
        dimHtml += `<div class="detail-dim"><div class="detail-dim-score">${v.toFixed(0)}</div><div class="detail-dim-label">${label}</div></div>`;
      }
    }

    let phaseHtml = '';
    if (opp.build_plan && opp.build_plan.phases) {
      for (const p of opp.build_plan.phases) {
        const tasks = p.tasks.map(t => `<li>${t}</li>`).join('');
        phaseHtml += `<div class="phase"><div class="phase-head"><span class="phase-name">${p.name}</span><span class="phase-week">Week ${p.week}</span></div><ul class="phase-tasks">${tasks}</ul></div>`;
      }
    }

    let revHtml = '';
    if (opp.revenue_projection && opp.revenue_projection.addressable_market) {
      const r = opp.revenue_projection;
      revHtml = `
        <div class="revenue-row"><span class="revenue-label">Total labor spend</span><span class="revenue-val">$${(r.total_labor_spend/1e9).toFixed(1)}B</span></div>
        <div class="revenue-row"><span class="revenue-label">Addressable market</span><span class="revenue-val">$${(r.addressable_market/1e9).toFixed(2)}B</span></div>
        <div class="revenue-row"><span class="revenue-label">Serviceable market</span><span class="revenue-val">$${(r.serviceable_market/1e6).toFixed(0)}M</span></div>
        <div class="revenue-row"><span class="revenue-label">Conservative yr1</span><span class="revenue-val">$${(r.conservative_yr1/1e3).toFixed(0)}K</span></div>
        <div class="revenue-row"><span class="revenue-label">Moderate yr1</span><span class="revenue-val">$${(r.moderate_yr1/1e3).toFixed(0)}K</span></div>`;
    } else {
      revHtml = '<div style="color:var(--dim);font-size:0.75rem">Revenue projections available when BLS employment data loads.</div>';
    }

    let gtmHtml = '';
    if (opp.go_to_market) {
      gtmHtml = `<div style="font-size:0.8rem;color:var(--dim);margin-bottom:8px">${opp.go_to_market.positioning}</div>
        <div style="font-size:0.75rem;color:var(--dim)">${opp.go_to_market.pricing}</div>`;
    }

    panel.innerHTML = `
      <div class="detail-section">
        <h3>8-Dimension Scoring</h3>
        <div class="detail-grid">${dimHtml}</div>
      </div>
      <div class="detail-section">
        <h3>Rationale</h3>
        <div style="font-size:0.8rem;color:var(--dim)">${opp.rationale}</div>
      </div>
      <div class="detail-section">
        <h3>Revenue Projection</h3>
        ${revHtml}
      </div>
      <div class="detail-section">
        <h3>Build Plan — ${opp.build_weeks} weeks</h3>
        ${phaseHtml}
      </div>
      <div class="detail-section">
        <h3>Go-to-Market</h3>
        ${gtmHtml}
      </div>`;
  } catch (err) {
    panel.innerHTML = '<div style="color:var(--red);font-size:0.8rem;padding:12px">Failed to load detail.</div>';
  }
}

async function subscribeProFromOpp(e) {
  e.preventDefault();
  const btn = document.getElementById('opp-pro-btn');
  btn.textContent = 'Redirecting to checkout...';
  btn.style.opacity = '0.6';
  try {
    const resp = await fetch('/api/v1/subscribe/pro', {method: 'POST'});
    const data = await resp.json();
    if (data.checkout_url) window.location.href = data.checkout_url;
    else { btn.textContent = 'Error — try again'; btn.style.opacity = '1'; }
  } catch (err) { btn.textContent = 'Error — try again'; btn.style.opacity = '1'; }
}

loadOpportunities();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE INTELLIGENCE FEED PAGE
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/intelligence", response_class=HTMLResponse)
async def intelligence_feed_page():
    """Live AI frontier intelligence feed — the public face of FPI."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI Frontier Intelligence — Full Potential Index</title>
<meta name="description" content="Live scanning of the AI frontier. Real-time intelligence from GitHub, HuggingFace, arXiv, Hacker News, Reddit, and major AI labs. Updated every 30 minutes.">
<meta property="og:type" content="website">
<meta property="og:title" content="AI Frontier Intelligence — Full Potential Index">
<meta property="og:description" content="Live scanning of the AI frontier. Real-time intelligence from GitHub, HuggingFace, arXiv, Hacker News, Reddit, and major AI labs.">
<meta property="og:url" content="https://fullpotential.ai/intelligence">
<meta property="og:site_name" content="Full Potential AI">
<meta property="og:image" content="https://fullpotential.ai/api/v1/og-image">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="AI Frontier Intelligence — Full Potential Index">
<meta name="twitter:description" content="Live scanning of the AI frontier. Real-time intelligence from 18 sources including changelogs, benchmarks, and incident databases. Updated every 30–60 minutes.">
<meta name="twitter:image" content="https://fullpotential.ai/api/v1/og-image">
<link rel="canonical" href="https://fullpotential.ai/intelligence">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:ital,wght@0,400;0,600;1,400&display=swap');
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#06060b;--card:#0c0c14;--border:#1a1a2e;--text:#c8c8d8;--dim:#666680;
      --accent:#00d4ff;--gold:#ffb800;--red:#ff4466;--green:#22cc88;--purple:#7b2fff}
body{font-family:'Newsreader',Georgia,serif;background:var(--bg);color:var(--text);line-height:1.7}
.wrap{max-width:860px;margin:0 auto;padding:40px 20px}

/* ─── Hero: FP Line Score ─── */
.hero{text-align:center;padding:48px 0 40px}
.hero-explainer{font-size:0.95rem;color:var(--dim);margin-bottom:24px;max-width:540px;margin-left:auto;margin-right:auto;line-height:1.6}
.hero-label{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;text-transform:uppercase;
            letter-spacing:3px;color:var(--dim);margin-bottom:8px}
.hero-score{font-family:'IBM Plex Mono',monospace;font-size:5.5rem;font-weight:600;line-height:1;
            background:linear-gradient(135deg,var(--gold),#ff8800);-webkit-background-clip:text;-webkit-text-fill-color:transparent;
            cursor:pointer;transition:transform 0.2s}
.hero-score:hover{transform:scale(1.02)}
.hero-sub{font-family:'IBM Plex Mono',monospace;font-size:0.85rem;color:var(--dim);margin-top:4px}
.hero-trend{display:inline-block;padding:3px 10px;border-radius:4px;font-family:'IBM Plex Mono',monospace;
            font-size:0.8rem;margin-left:8px}
.trend-up{background:rgba(34,204,136,0.12);color:var(--green)}
.trend-down{background:rgba(255,68,102,0.12);color:var(--red)}
.trend-flat{background:rgba(102,102,128,0.1);color:var(--dim)}
.hero-date{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:#444;margin-top:16px}

/* ─── Domain Breakdown (hidden by default, toggle on score click) ─── */
.domains{display:none;margin-top:24px;padding:20px;background:var(--card);border:1px solid var(--border);border-radius:10px}
.domains.open{display:block}
.domain-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px;margin-top:12px}
.domain-row{display:flex;justify-content:space-between;align-items:center;padding:6px 12px;
            background:rgba(255,255,255,0.02);border-radius:6px}
.domain-name{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--dim);text-transform:capitalize}
.domain-val{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;font-weight:600}
.domain-bar{height:3px;background:var(--border);border-radius:2px;margin-top:4px;overflow:hidden}
.domain-fill{height:100%;border-radius:2px;transition:width 0.6s ease}

/* ─── Daily Briefing ─── */
.briefing{margin-top:8px;padding:32px;background:var(--card);border:1px solid var(--border);border-radius:12px;
          border-left:3px solid var(--gold)}
.briefing-headline{font-size:1.15rem;font-weight:600;color:#e8e8f8;margin-bottom:16px;line-height:1.4}
.briefing-body{font-size:0.95rem;color:var(--dim);line-height:1.8;white-space:pre-line}
.briefing-body p{margin-bottom:12px}
.briefing-meta{margin-top:16px;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:#444}

/* ─── Email Capture ─── */
.subscribe{margin-top:32px;padding:28px;background:linear-gradient(135deg,rgba(0,212,255,0.04),rgba(123,47,255,0.04));
           border:1px solid var(--border);border-radius:12px;text-align:center}
.subscribe-title{font-size:1.1rem;font-weight:600;color:#e0e0f0;margin-bottom:4px}
.subscribe-sub{font-size:0.85rem;color:var(--dim);margin-bottom:16px}
.subscribe-form{display:flex;gap:8px;max-width:440px;margin:0 auto}
.subscribe-input{flex:1;font-family:'IBM Plex Mono',monospace;font-size:0.85rem;padding:12px 16px;
                 background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);outline:none}
.subscribe-input:focus{border-color:var(--accent)}
.subscribe-input::placeholder{color:#444}
.subscribe-btn{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;padding:12px 24px;
               background:linear-gradient(135deg,var(--accent),var(--purple));color:#fff;border:none;
               border-radius:6px;cursor:pointer;font-weight:600;white-space:nowrap;transition:opacity 0.2s}
.subscribe-btn:hover{opacity:0.9}
.subscribe-msg{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;margin-top:10px;min-height:1.2em}
.msg-ok{color:var(--green)}
.msg-err{color:var(--red)}

/* ─── Top Signals ─── */
.displacement-watch{margin-top:32px;padding:20px;background:var(--card);border-radius:8px;border:1px solid var(--border)}
.displacement-watch .section-sub{font-size:0.75rem;color:var(--dim);margin-top:4px}
.displacement-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px}
@media(max-width:600px){.displacement-grid{grid-template-columns:1fr}}
.disp-card{padding:12px;background:var(--bg);border-radius:6px;border:1px solid var(--border)}
.disp-card-title{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.disp-item{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04)}
.disp-item:last-child{border-bottom:none}
.disp-name{font-size:0.82rem;color:var(--text)}
.disp-gap{font-family:'IBM Plex Mono',monospace;font-size:0.78rem;font-weight:600}
.disp-gap.closing{color:#ff6b6b}
.disp-gap.large{color:var(--accent)}
.disp-bar{height:4px;border-radius:2px;background:var(--border);margin-top:4px;position:relative;overflow:hidden}
.disp-bar-cap{height:100%;border-radius:2px;background:var(--accent);position:absolute;left:0;top:0}
.disp-bar-disp{height:100%;border-radius:2px;background:var(--gold);position:absolute;left:0;top:0}
.top-signals{margin-top:32px}
.top-signals .entry{border-left:3px solid var(--accent);background:linear-gradient(90deg,rgba(0,212,255,0.02),var(--card))}
.top-signals .entry:hover{border-left-color:var(--gold)}
.top-rank{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--accent);margin-right:8px}

/* ─── Stats Bar ─── */
.stats{display:flex;gap:12px;justify-content:center;margin:32px 0 24px;flex-wrap:wrap}
.stat{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;padding:6px 14px;
      background:var(--card);border:1px solid var(--border);border-radius:6px;color:var(--dim)}
.stat b{color:var(--text)}

/* ─── Section Header ─── */
.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;
              padding-bottom:12px;border-bottom:1px solid var(--border)}
.section-title{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;text-transform:uppercase;
               letter-spacing:2px;color:var(--dim)}

/* ─── Filter + Feed (same as before) ─── */
.filter-bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
.filter-btn{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;padding:4px 10px;
            background:none;border:1px solid var(--border);color:var(--dim);border-radius:4px;cursor:pointer}
.filter-btn.active{border-color:var(--accent);color:var(--accent);background:rgba(0,212,255,0.05)}
.refresh-bar{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.refresh-btn{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;padding:6px 14px;
             background:none;border:1px solid var(--border);color:var(--dim);border-radius:6px;cursor:pointer}
.refresh-btn:hover{border-color:var(--accent);color:var(--accent)}
#feed{margin-top:12px}
.entry{padding:20px;margin-bottom:12px;background:var(--card);border:1px solid var(--border);
       border-radius:10px;transition:border-color 0.2s}
.entry:hover{border-color:#2a2a4e}
.entry-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:6px}
.entry-title{font-size:1.05rem;font-weight:600;color:#e0e0f0}
.entry-title a{color:inherit;text-decoration:none;border-bottom:1px solid transparent}
.entry-title a:hover{border-bottom-color:var(--accent)}
.entry-impact{font-family:'IBM Plex Mono',monospace;font-size:0.75rem;padding:3px 8px;
              border-radius:4px;white-space:nowrap;flex-shrink:0}
.impact-high{background:rgba(0,212,255,0.1);color:var(--accent)}
.impact-med{background:rgba(255,184,0,0.1);color:var(--gold)}
.impact-low{background:rgba(102,102,128,0.1);color:var(--dim)}
.entry-summary{font-size:0.9rem;color:var(--dim);margin-bottom:8px}
.entry-meta{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.tag{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;padding:2px 8px;
     background:rgba(123,47,255,0.1);color:#9966ff;border-radius:3px}
.source-tag{background:rgba(0,212,255,0.08);color:var(--accent)}
.dark-tag{background:rgba(255,68,102,0.15);color:var(--red)}
.time{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim)}
.share-mini{font-family:'IBM Plex Mono',monospace;font-size:0.62rem;padding:2px 6px;background:rgba(255,255,255,0.04);
  border:1px solid var(--border);border-radius:3px;color:var(--dim);cursor:pointer;text-decoration:none;transition:all 0.15s}
.share-mini:hover{border-color:var(--accent);color:var(--accent)}
.toast-intel{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);padding:10px 20px;background:#1a1a2e;
  border:1px solid var(--accent);border-radius:6px;color:var(--accent);font-family:'IBM Plex Mono',monospace;
  font-size:0.75rem;opacity:0;transition:opacity 0.3s;pointer-events:none;z-index:100}
.toast-intel.show{opacity:1}
.loading{text-align:center;padding:40px;color:var(--dim);font-family:'IBM Plex Mono',monospace}
.err{text-align:center;padding:40px;color:var(--red)}

/* ─── Pro Upsell ─── */
.pro-upsell{margin-top:48px;padding:36px 28px;background:linear-gradient(135deg,rgba(0,212,255,0.06),rgba(123,47,255,0.06));
            border:1px solid rgba(0,212,255,0.2);border-radius:12px;text-align:center}
.pro-badge{display:inline-block;padding:3px 12px;background:var(--accent);color:#000;font-family:'IBM Plex Mono',monospace;
           font-size:0.7rem;font-weight:700;border-radius:4px;letter-spacing:0.1em;margin-bottom:14px}
.pro-headline{font-size:1.3rem;font-weight:700;color:#e8e8f8;margin-bottom:8px}
.pro-sub{color:var(--dim);font-size:0.85rem;margin-bottom:18px;line-height:1.5}
.pro-price{margin-bottom:18px}
.pro-amount{font-size:2.2rem;font-weight:700;color:var(--accent)}
.pro-period{font-size:0.9rem;color:var(--dim)}
.pro-cta{display:inline-block;padding:14px 36px;background:linear-gradient(135deg,var(--accent),var(--purple));
         color:#fff;font-family:'IBM Plex Mono',monospace;font-size:0.9rem;font-weight:600;
         border-radius:8px;text-decoration:none;transition:all 0.2s;cursor:pointer}
.pro-cta:hover{opacity:0.9;transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,212,255,0.3)}
.pro-alt{margin-top:18px;font-size:0.8rem;color:var(--dim)}
.pro-alt a{color:var(--dim);text-decoration:none;transition:color 0.2s}
.pro-alt a:hover{color:var(--accent)}
footer{text-align:center;padding:48px 0 24px;color:#333;font-size:0.75rem;font-family:'IBM Plex Mono',monospace}
footer a{color:var(--accent);text-decoration:none}
</style>
</head>
<body>
<div class="wrap">

<!-- ═══ HERO: FP Line Score ═══ -->
<div class="hero">
  <div class="hero-explainer">The Full Potential Index tracks what AI can do — and what it's doing to work — updated every 30 minutes from 18 live sources.</div>
  <div class="hero-label">The AI Frontier Index</div>
  <div class="hero-score" id="hero-score" onclick="toggleDomains()" title="Click for domain breakdown">—</div>
  <div class="hero-sub">
    <span id="hero-caps">—</span> signals tracked
    <span class="hero-trend trend-flat" id="hero-trend"></span>
  </div>
  <div class="hero-date" id="hero-date"></div>
  <div class="domains" id="domains">
    <div style="font-family:'IBM Plex Mono',monospace;font-size:0.75rem;color:var(--dim);text-transform:uppercase;letter-spacing:1.5px">Domain Breakdown</div>
    <div class="domain-grid" id="domain-grid"></div>
  </div>
</div>

<!-- ═══ DAILY BRIEFING ═══ -->
<div class="briefing" id="briefing">
  <div class="briefing-headline" id="briefing-headline">Loading today's briefing...</div>
  <div class="briefing-body" id="briefing-body"></div>
  <div class="briefing-meta" id="briefing-meta"></div>
</div>

<!-- ═══ EMAIL CAPTURE ═══ -->
<div class="subscribe">
  <div class="subscribe-title">Get the daily AI frontier briefing. Free.</div>
  <div class="subscribe-sub">One email per day. The most important AI developments, synthesized.</div>
  <form class="subscribe-form" onsubmit="doSubscribe(event)">
    <input type="email" class="subscribe-input" id="sub-email" placeholder="you@example.com" required>
    <button type="submit" class="subscribe-btn" id="sub-btn">Subscribe</button>
  </form>
  <div class="subscribe-msg" id="sub-msg"></div>
</div>

<!-- ═══ LABOR DISPLACEMENT WATCH ═══ -->
<div class="displacement-watch" id="displacement-watch">
  <div class="section-head">
    <div class="section-title">Labor Displacement Watch</div>
    <div class="section-sub">AI capability vs actual job displacement across 25 categories</div>
  </div>
  <div class="displacement-grid" id="displacement-grid">
    <div class="loading">Loading displacement data...</div>
  </div>
  <div style="text-align:center;margin-top:1rem">
    <a href="/careers" style="color:var(--accent);text-decoration:none;font-size:0.85rem;font-family:'IBM Plex Mono',monospace">How AI-ready is your career? →</a>
  </div>
</div>

<!-- ═══ TOP SIGNALS ═══ -->
<div class="top-signals">
  <div class="section-head">
    <div class="section-title">Top Signals Today</div>
  </div>
  <div id="top-signals"><div class="loading">Loading top signals...</div></div>
</div>

<!-- ═══ STATS BAR ═══ -->
<div class="stats" id="stats-bar"></div>

<!-- ═══ SYSTEM UPGRADE PROPOSALS (EXECUTE step output) ═══ -->
<div id="exec-briefs-section" style="display:none;margin-top:32px">
  <div class="section-head">
    <div class="section-title">What the System Wants to Become</div>
    <a href="/pipeline" style="font-family:'IBM Plex Mono',monospace;font-size:0.7rem;color:var(--dim);text-decoration:none">View Pipeline →</a>
  </div>
  <div style="color:var(--dim);font-size:0.8rem;margin-bottom:16px;font-family:'IBM Plex Mono',monospace">
    The scanner detects frontier shifts. The EXECUTE step evaluates whether they apply to our system. These are the highest-scored proposals — intelligence acting on itself.
  </div>
  <div id="exec-briefs"></div>
</div>

<!-- ═══ FEED ═══ -->
<div class="section-head">
  <div class="section-title">All Intelligence</div>
  <button class="refresh-btn" onclick="loadFeed()">refresh</button>
</div>
<div class="filter-bar" id="filters"></div>
<div id="feed"><div class="loading">Loading intelligence feed...</div></div>

<!-- ═══ PRO TIER UPSELL ═══ -->
<div class="pro-upsell">
  <div class="pro-badge">PRO</div>
  <div class="pro-headline">Go deeper with FP Index Pro</div>
  <div class="pro-sub">Weekly allocation report · Daily briefing email · Full API access · Rebalance alerts</div>
  <div class="pro-price"><span class="pro-amount">$49</span><span class="pro-period">/mo</span></div>
  <a href="#" class="pro-cta" id="intel-pro-btn" onclick="subscribeProFromIntel(event)">Start Pro →</a>
  <div class="pro-alt">
    <a href="/invest">View Frontier Basket</a> · <a href="/opportunities">Gap Opportunities</a> · <a href="/constitution">Read the Constitution</a>
  </div>
</div>

<footer>
  Full Potential Index v""" + VERSION + """ · <a href="/constitution">Constitution</a> · <a href="/api/v1/economy/primitives">Economy</a><br>
  Scanning 18 sources every 30 minutes · fullpotential.ai
</footer>
</div>

<script>
const API = '/api/v1';
const PUBLIC_BASE = 'https://fullpotential.ai';
let allEntries = [];

function escHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function safePublicUrl(value) {
  try {
    const url = new URL(String(value || ''), window.location.origin);
    if (url.protocol === 'http:' || url.protocol === 'https:') return url.href;
  } catch (e) {}
  return '#';
}

// ─── Hero + Briefing ───
async function loadHero() {
  try {
    const [fpRes, briefRes] = await Promise.all([
      fetch(API + '/fp-line'),
      fetch(API + '/briefing')
    ]);
    const fp = await fpRes.json();
    const briefing = await briefRes.json();

    // Hero score
    document.getElementById('hero-score').textContent = fp.overall_score || '—';
    document.getElementById('hero-caps').textContent = fp.capabilities_added_24h || 0;

    // Trend arrow — show "establishing baseline" when momentum is exactly 0 (no prior data)
    const m = fp.momentum || 0;
    const trendEl = document.getElementById('hero-trend');
    if (m > 0) { trendEl.textContent = '\\u2191 ' + m.toFixed(1); trendEl.className = 'hero-trend trend-up'; }
    else if (m < 0) { trendEl.textContent = '\\u2193 ' + Math.abs(m).toFixed(1); trendEl.className = 'hero-trend trend-down'; }
    else { trendEl.textContent = 'establishing baseline'; trendEl.className = 'hero-trend trend-flat'; }

    // Date
    document.getElementById('hero-date').textContent = new Date().toLocaleDateString('en-US', {weekday:'long',year:'numeric',month:'long',day:'numeric'});

    // Domain breakdown
    const grid = document.getElementById('domain-grid');
    const ds = fp.domain_scores || {};
    const maxScore = Math.max(...Object.values(ds), 1);
    grid.innerHTML = Object.entries(ds).sort((a,b) => b[1]-a[1]).map(([d,v]) => {
      const pct = (v / 100 * 100).toFixed(0);
      const color = v >= 50 ? 'var(--green)' : v >= 40 ? 'var(--gold)' : 'var(--dim)';
      return '<div class="domain-row"><span class="domain-name">' + escHtml(d) + '</span><span class="domain-val" style="color:' + color + '">' + v + '</span></div>';
    }).join('');

    // Briefing
    if (briefing.headline) {
      document.getElementById('briefing-headline').textContent = briefing.headline;
      const bodyHtml = (briefing.body || '').split('\\n\\n').map(p => '<p>' + escHtml(p) + '</p>').join('');
      document.getElementById('briefing-body').innerHTML = bodyHtml;
      document.getElementById('briefing-meta').textContent =
        briefing.date + ' · Generated from ' + (briefing.stats?.caps_24h || '—') + ' signals · Updates every 30 minutes';
    }
  } catch(e) {
    console.error('Hero load failed:', e);
  }
}

function toggleDomains() {
  document.getElementById('domains').classList.toggle('open');
}

// ─── Email Subscribe ───
async function doSubscribe(e) {
  e.preventDefault();
  const email = document.getElementById('sub-email').value;
  const btn = document.getElementById('sub-btn');
  const msg = document.getElementById('sub-msg');
  btn.disabled = true; btn.textContent = '...';
  try {
    const res = await fetch(API + '/subscribe', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({email})
    });
    const data = await res.json();
    if (res.ok) {
      msg.className = 'subscribe-msg msg-ok';
      msg.textContent = data.message || "You're in.";
      btn.textContent = 'Done'; document.getElementById('sub-email').value = '';
    } else {
      msg.className = 'subscribe-msg msg-err';
      msg.textContent = data.detail || 'Something went wrong.';
      btn.textContent = 'Subscribe'; btn.disabled = false;
    }
  } catch(err) {
    msg.className = 'subscribe-msg msg-err';
    msg.textContent = 'Network error. Try again.';
    btn.textContent = 'Subscribe'; btn.disabled = false;
  }
}

// ─── Feed ───
async function loadFeed() {
  try {
    const [feedRes, statsRes] = await Promise.all([
      fetch(API + '/feed?limit=100'),
      fetch(API + '/stats')
    ]);
    allEntries = await feedRes.json();
    const stats = await statsRes.json();
    const idx = stats.index || {};

    document.getElementById('stats-bar').innerHTML =
      '<div class="stat"><b>' + (idx.total_entries||0) + '</b> entries</div>' +
      '<div class="stat"><b>' + (idx.total_agents||0) + '</b> agents</div>' +
      '<div class="stat"><b>' + (idx.scan_count||0) + '</b> scans</div>' +
      '<div class="stat">last: <b>' + (idx.last_scan ? new Date(idx.last_scan).toLocaleTimeString() : 'never') + '</b></div>';

    const sources = [...new Set(allEntries.map(e => e.source))].sort();
    document.getElementById('filters').innerHTML =
      '<button class="filter-btn active" onclick="setFilter(null,this)">all (' + allEntries.length + ')</button>' +
      sources.map(s => {
        const c = allEntries.filter(e => e.source === s).length;
        return '<button class="filter-btn" onclick="setFilter(\\'' + s + '\\',this)">' + s + ' (' + c + ')</button>';
      }).join('');

    renderTopSignals(allEntries);
    renderEntries(allEntries);
    loadDisplacement();
  } catch(e) {
    document.getElementById('feed').innerHTML = '<div class="err">Failed to load: ' + e.message + '</div>';
  }
}

function setFilter(source, btn) {
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderEntries(source ? allEntries.filter(e => e.source === source) : allEntries);
}

function renderEntries(entries) {
  const feed = document.getElementById('feed');
  if (!entries.length) { feed.innerHTML = '<div class="loading">No entries yet.</div>'; return; }
  feed.innerHTML = entries.map(e => {
    const imp = e.impact_score || 0;
    const ic = imp >= 0.6 ? 'impact-high' : imp >= 0.4 ? 'impact-med' : 'impact-low';
    const il = imp >= 0.6 ? 'HIGH' : imp >= 0.4 ? 'MED' : 'LOW';
    const rawTitle = e.title || 'Untitled';
    const rawSource = e.source || '?';
    const doms = (e.domains||[]).map(d => '<span class="tag">'+escHtml(d)+'</span>').join('');
    const dk = e.dark_flag ? '<span class="tag dark-tag">DARK AI</span>' : '';
    const u = safePublicUrl(e.source_url);
    const t = e.scanned_at ? new Date(e.scanned_at).toLocaleString() : '';
    const s = escHtml((e.summary||'').substring(0,200));
    const sid = e.id || '';
    const shareUrl = PUBLIC_BASE + (sid ? '/signal/' + encodeURIComponent(String(sid)) : '/intelligence');
    const tweetText = encodeURIComponent(rawTitle + ' — FP Index');
    const tweetUrl = 'https://twitter.com/intent/tweet?text=' + tweetText + '&url=' + encodeURIComponent(shareUrl);
    const liUrl = 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(shareUrl);
    return '<div class="entry"><div class="entry-head"><div class="entry-title"><a href="'+u+'" target="_blank" rel="noopener noreferrer">'+escHtml(rawTitle)+'</a></div><span class="entry-impact '+ic+'">'+il+' '+imp.toFixed(1)+'</span></div>'+(s?'<div class="entry-summary">'+s+'</div>':'')+'<div class="entry-meta"><span class="tag source-tag">'+escHtml(rawSource)+'</span>'+doms+' '+dk+'<span class="time">'+escHtml(t)+'</span><span style="margin-left:auto;display:flex;gap:4px"><a href="'+tweetUrl+'" target="_blank" rel="noopener noreferrer" class="share-mini" title="Share on X">X</a><a href="'+liUrl+'" target="_blank" rel="noopener noreferrer" class="share-mini" title="LinkedIn">in</a><button class="share-mini" onclick="copySignalLink(\\''+shareUrl+'\\')">link</button></span></div></div>';
  }).join('');
}

function renderTopSignals(entries) {
  const top = [...entries].sort((a,b) => (b.impact_score||0) - (a.impact_score||0)).slice(0, 10);
  const el = document.getElementById('top-signals');
  if (!top.length) { el.innerHTML = '<div class="loading">No signals yet.</div>'; return; }
  el.innerHTML = top.map((e, i) => {
    const imp = e.impact_score || 0;
    const ic = imp >= 0.6 ? 'impact-high' : imp >= 0.4 ? 'impact-med' : 'impact-low';
    const il = imp >= 0.6 ? 'HIGH' : imp >= 0.4 ? 'MED' : 'LOW';
    const rawTitle = e.title || 'Untitled';
    const rawSource = e.source || '?';
    const doms = (e.domains||[]).map(d => '<span class="tag">'+escHtml(d)+'</span>').join('');
    const dk = e.dark_flag ? '<span class="tag dark-tag">DARK AI</span>' : '';
    const u = safePublicUrl(e.source_url);
    const s = escHtml((e.summary||'').substring(0,200));
    const sid = e.id || '';
    const shareUrl = PUBLIC_BASE + (sid ? '/signal/' + encodeURIComponent(String(sid)) : '/intelligence');
    const tweetText = encodeURIComponent(rawTitle + ' — FP Index');
    const tweetUrl = 'https://twitter.com/intent/tweet?text=' + tweetText + '&url=' + encodeURIComponent(shareUrl);
    const liUrl = 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(shareUrl);
    return '<div class="entry"><div class="entry-head"><div class="entry-title"><span class="top-rank">#'+(i+1)+'</span><a href="'+u+'" target="_blank" rel="noopener noreferrer">'+escHtml(rawTitle)+'</a></div><span class="entry-impact '+ic+'">'+il+' '+imp.toFixed(1)+'</span></div>'+(s?'<div class="entry-summary">'+s+'</div>':'')+'<div class="entry-meta"><span class="tag source-tag">'+escHtml(rawSource)+'</span>'+doms+' '+dk+'<span style="margin-left:auto;display:flex;gap:4px"><a href="'+tweetUrl+'" target="_blank" rel="noopener noreferrer" class="share-mini" title="Share on X">X</a><a href="'+liUrl+'" target="_blank" rel="noopener noreferrer" class="share-mini" title="LinkedIn">in</a><button class="share-mini" onclick="copySignalLink(\\''+shareUrl+'\\')">link</button></span></div></div>';
  }).join('');
}

async function loadDisplacement() {
  try {
    const resp = await fetch('/api/v1/displacement');
    if (!resp.ok) return;
    const data = await resp.json();
    const grid = document.getElementById('displacement-grid');
    if (!data.categories || !data.categories.length) {
      grid.innerHTML = '<div class="loading">Displacement data initializing...</div>';
      return;
    }
    const closing = (data.fastest_closing || []).slice(0, 4);
    const gaps = (data.largest_gaps || []).slice(0, 4);
    let html = '<div class="disp-card"><div class="disp-card-title">▼ Fastest Closing Gaps</div>';
    closing.forEach(c => {
      const pct = Math.round(c.displacement_score / Math.max(1, c.capability_score) * 100);
      html += '<div class="disp-item"><div><div class="disp-name">' + c.name + '</div>';
      html += '<div class="disp-bar" style="width:100%"><div class="disp-bar-cap" style="width:' + c.capability_score + '%"></div><div class="disp-bar-disp" style="width:' + c.displacement_score + '%"></div></div>';
      html += '</div><div class="disp-gap closing">' + c.gap.toFixed(0) + ' gap</div></div>';
    });
    html += '</div>';
    html += '<div class="disp-card"><div class="disp-card-title">△ Largest Untapped Gaps</div>';
    gaps.forEach(c => {
      html += '<div class="disp-item"><div><div class="disp-name">' + c.name + '</div>';
      html += '<div class="disp-bar" style="width:100%"><div class="disp-bar-cap" style="width:' + c.capability_score + '%"></div><div class="disp-bar-disp" style="width:' + c.displacement_score + '%"></div></div>';
      html += '</div><div class="disp-gap large">' + c.gap.toFixed(0) + ' gap</div></div>';
    });
    html += '</div>';
    grid.innerHTML = html;
  } catch(e) {
    console.warn('Displacement load error:', e);
  }
}

async function subscribeProFromIntel(e) {
  e.preventDefault();
  const btn = document.getElementById('intel-pro-btn');
  btn.textContent = 'Redirecting to checkout...';
  btn.style.opacity = '0.6';
  try {
    const resp = await fetch('/api/v1/subscribe/pro', {method: 'POST'});
    const data = await resp.json();
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    } else {
      btn.textContent = 'Error — try again';
      btn.style.opacity = '1';
    }
  } catch (err) {
    btn.textContent = 'Error — try again';
    btn.style.opacity = '1';
  }
}

async function loadExecBriefs() {
  try {
    const resp = await fetch('/api/v1/execution-briefs?limit=8&status=evaluated&min_score=0.3');
    const briefs = await resp.json();
    if (!briefs || !briefs.length) return;
    const section = document.getElementById('exec-briefs-section');
    section.style.display = 'block';
    const el = document.getElementById('exec-briefs');

    const trackColors = {
      self_upgrade: {bg: 'rgba(0,212,255,0.1)', fg: '#00d4ff', label: 'SELF-UPGRADE'},
      investment: {bg: 'rgba(255,180,0,0.1)', fg: '#ffb400', label: 'INVESTMENT'},
      product: {bg: 'rgba(78,205,196,0.1)', fg: '#4ecdc4', label: 'PRODUCT'},
    };

    el.innerHTML = briefs.map(b => {
      const score = (b.relevance_score || 0).toFixed(2);
      const scoreColor = b.relevance_score >= 0.7 ? 'var(--green)' : b.relevance_score >= 0.5 ? 'var(--gold)' : 'var(--dim)';
      const track = trackColors[b.execution_track] || trackColors.self_upgrade;
      const narrative = escHtml(b.narrative || '');
      const agents = escHtml((b.affected_agents || []).join(', '));
      const impl = escHtml((b.implementation_path || '').split('\\n').filter(l => l.startsWith('IMPLEMENTATION:')).map(l => l.replace('IMPLEMENTATION:','').trim()).join('') || '');

      return '<div class="entry" style="border-left:3px solid ' + track.fg + '">' +
        '<div class="entry-head"><div class="entry-title">' + escHtml(b.entry_title || '') + '</div>' +
        '<span style="font-family:IBM Plex Mono,monospace;font-size:0.75rem;color:' + scoreColor + ';font-weight:600">' + score + '</span></div>' +
        (narrative ? '<div class="entry-summary" style="color:var(--accent);font-style:italic;font-size:0.82rem">' + narrative + '</div>' : '') +
        (impl ? '<div class="entry-summary">' + impl + '</div>' : '') +
        '<div class="entry-meta">' +
        '<span class="tag" style="background:' + track.bg + ';color:' + track.fg + '">' + track.label + '</span>' +
        (agents ? '<span class="tag source-tag">' + agents + '</span>' : '') +
        '<span class="time">' + escHtml(b.created_at ? new Date(b.created_at).toLocaleString() : '') + '</span></div></div>';
    }).join('');
  } catch(e) { console.warn('Exec briefs load error:', e); }
}

loadHero();
loadFeed();
loadExecBriefs();
setInterval(loadHero, 300000);
setInterval(loadFeed, 300000);
setInterval(loadExecBriefs, 300000);

function copySignalLink(url) {
  navigator.clipboard.writeText(url).then(() => {
    const t = document.getElementById('toast-intel');
    if(t){t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2000);}
  });
}
</script>
<div class="toast-intel" id="toast-intel">Link copied</div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# CAREERS PAGE — Consumer-facing career intelligence
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/careers", response_class=HTMLResponse)
async def careers_page():
    """Consumer page: 'How AI-ready is your career?'"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>How AI-Ready Is Your Career? — Full Potential Index</title>
<meta name="description" content="Find out how AI is affecting your job category. Real data on AI capability vs actual displacement across 25 career fields.">
<meta property="og:title" content="How AI-Ready Is Your Career? — Full Potential Index">
<meta property="og:description" content="AI capability vs actual job displacement across 25 career fields. Free career intelligence.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#0a0a0f;--card:#12121a;--border:rgba(255,255,255,0.06);--text:#e0e0e0;--dim:#666;--accent:#00d4ff;--gold:#ffb400;--red:#ff6b6b;--green:#4ecdc4}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.container{max-width:800px;margin:0 auto;padding:40px 20px}
h1{font-size:2rem;font-weight:600;margin-bottom:8px}
.subtitle{color:var(--dim);font-size:0.95rem;margin-bottom:32px}
.search-box{width:100%;padding:14px 18px;background:var(--card);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:1rem;font-family:'Inter',sans-serif;margin-bottom:24px;outline:none}
.search-box:focus{border-color:var(--accent)}
.search-box::placeholder{color:var(--dim)}
.cat-list{display:flex;flex-direction:column;gap:8px}
.cat-card{padding:16px;background:var(--card);border:1px solid var(--border);border-radius:8px;cursor:pointer;transition:border-color 0.2s}
.cat-card:hover{border-color:var(--accent)}
.cat-card.selected{border-color:var(--accent);background:rgba(0,212,255,0.03)}
.cat-head{display:flex;justify-content:space-between;align-items:center}
.cat-name{font-weight:500;font-size:0.95rem}
.cat-sector{font-size:0.75rem;color:var(--dim);font-family:'IBM Plex Mono',monospace}
.cat-bars{margin-top:10px;display:flex;gap:16px;align-items:center}
.bar-group{flex:1}
.bar-label{font-size:0.65rem;color:var(--dim);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:3px;font-family:'IBM Plex Mono',monospace}
.bar-track{height:6px;background:var(--border);border-radius:3px;overflow:hidden}
.bar-fill-cap{height:100%;background:var(--accent);border-radius:3px}
.bar-fill-disp{height:100%;background:var(--gold);border-radius:3px}
.cat-gap{text-align:center;min-width:80px}
.gap-num{font-family:'IBM Plex Mono',monospace;font-size:1.2rem;font-weight:600}
.gap-num.high{color:var(--accent)}
.gap-num.med{color:var(--gold)}
.gap-num.low{color:var(--red)}
.gap-label{font-size:0.6rem;color:var(--dim);text-transform:uppercase;letter-spacing:0.5px}
.detail-panel{margin-top:16px;padding:20px;background:var(--bg);border-radius:8px;border:1px solid var(--border);display:none}
.detail-panel.visible{display:block}
.detail-title{font-size:1.1rem;font-weight:600;margin-bottom:12px}
.detail-rationale{font-size:0.88rem;color:var(--dim);line-height:1.6;margin-bottom:16px}
.detail-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.stat{text-align:center;padding:12px;background:var(--card);border-radius:6px}
.stat-val{font-family:'IBM Plex Mono',monospace;font-size:1.4rem;font-weight:600}
.stat-label{font-size:0.65rem;color:var(--dim);text-transform:uppercase;letter-spacing:0.5px;margin-top:4px}
.timeline{margin-top:16px;padding:12px 16px;border-radius:6px;font-family:'IBM Plex Mono',monospace;font-size:0.82rem}
.timeline.imminent{background:rgba(255,107,107,0.1);color:var(--red);border:1px solid rgba(255,107,107,0.2)}
.timeline.near_term{background:rgba(255,180,0,0.1);color:var(--gold);border:1px solid rgba(255,180,0,0.2)}
.timeline.medium_term{background:rgba(78,205,196,0.1);color:var(--green);border:1px solid rgba(78,205,196,0.2)}
.timeline.long_term{background:rgba(0,212,255,0.1);color:var(--accent);border:1px solid rgba(0,212,255,0.2)}
.cta-bar{margin-top:32px;text-align:center}
.cta-bar a{display:inline-block;padding:10px 24px;margin:0 8px 8px;border-radius:6px;text-decoration:none;font-size:0.85rem;font-weight:500}
.cta-primary{background:var(--accent);color:var(--bg)}
.cta-secondary{border:1px solid var(--border);color:var(--text)}
.subscribe-section{margin-top:32px;padding:24px;background:var(--card);border-radius:8px;text-align:center;border:1px solid var(--border)}
.subscribe-section h3{font-size:1rem;margin-bottom:8px}
.subscribe-section p{font-size:0.85rem;color:var(--dim);margin-bottom:16px}
.sub-form{display:flex;gap:8px;max-width:400px;margin:0 auto}
.sub-input{flex:1;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:'Inter',sans-serif}
.sub-btn{padding:10px 20px;background:var(--accent);color:var(--bg);border:none;border-radius:6px;font-weight:600;cursor:pointer}
.disclaimer{margin-top:32px;font-size:0.7rem;color:var(--dim);line-height:1.5;text-align:center;max-width:600px;margin-left:auto;margin-right:auto}
</style>
</head>
<body>
<div class="container">
  <h1>How AI-Ready Is Your Career?</h1>
  <p class="subtitle">Real data on AI capability vs actual job displacement across 25 career fields. Select your field below.</p>

  <input type="text" class="search-box" id="search" placeholder="Search career fields..." oninput="filterCats()">

  <div class="cat-list" id="cat-list"><div style="color:var(--dim)">Loading career data...</div></div>

  <div class="detail-panel" id="detail-panel"></div>

  <div class="subscribe-section">
    <h3>Get weekly career intelligence</h3>
    <p>How AI is reshaping your field — delivered every Monday. Free.</p>
    <div class="sub-form">
      <input type="email" class="sub-input" id="sub-email" placeholder="your@email.com">
      <button class="sub-btn" onclick="subscribe()">Subscribe</button>
    </div>
    <div id="sub-msg" style="margin-top:8px;font-size:0.82rem;color:var(--accent)"></div>
  </div>

  <div class="cta-bar">
    <a href="/intelligence" class="cta-secondary">← Full Intelligence Feed</a>
    <a href="/fpi/" class="cta-secondary">About the Index</a>
  </div>

  <div class="disclaimer">The Full Potential Index provides intelligence signals based on AI capability assessment and labor market data analysis. These signals are informational only and do not constitute financial, investment, legal, or career advice. Past displacement patterns do not predict future outcomes. Consult qualified professionals before making career decisions based on this data.</div>
</div>

<script>
let allCats = [];

async function loadCats() {
  try {
    const resp = await fetch('/api/v1/displacement');
    const data = await resp.json();
    allCats = data.categories || [];
    renderCats(allCats);
  } catch(e) {
    document.getElementById('cat-list').innerHTML = '<div style="color:var(--red)">Failed to load data.</div>';
  }
}

function filterCats() {
  const q = document.getElementById('search').value.toLowerCase();
  const filtered = allCats.filter(c => c.name.toLowerCase().includes(q) || c.parent_sector.toLowerCase().includes(q));
  renderCats(filtered);
}

function renderCats(cats) {
  const el = document.getElementById('cat-list');
  if (!cats.length) { el.innerHTML = '<div style="color:var(--dim)">No matching fields.</div>'; return; }
  el.innerHTML = cats.map(c => {
    const gc = c.gap > 40 ? 'high' : c.gap > 20 ? 'med' : 'low';
    return '<div class="cat-card" onclick="showDetail(\\''+c.id+'\\')">' +
      '<div class="cat-head"><div><div class="cat-name">'+c.name+'</div><div class="cat-sector">'+c.parent_sector+'</div></div>' +
      '<div class="cat-gap"><div class="gap-num '+gc+'">'+c.gap.toFixed(0)+'</div><div class="gap-label">gap</div></div></div>' +
      '<div class="cat-bars">' +
      '<div class="bar-group"><div class="bar-label">AI Capability: '+c.capability_score+'</div><div class="bar-track"><div class="bar-fill-cap" style="width:'+c.capability_score+'%"></div></div></div>' +
      '<div class="bar-group"><div class="bar-label">Actual Displacement: '+c.displacement_score+'</div><div class="bar-track"><div class="bar-fill-disp" style="width:'+c.displacement_score+'%"></div></div></div>' +
      '</div></div>';
  }).join('');
}

function showDetail(id) {
  const c = allCats.find(x => x.id === id);
  if (!c) return;
  const tl = (c.automation_timeline||'medium_term').replace(/_/g,' ');
  const tlClass = c.automation_timeline || 'medium_term';
  const panel = document.getElementById('detail-panel');
  panel.className = 'detail-panel visible';
  panel.innerHTML = '<div class="detail-title">'+c.name+'</div>' +
    '<div class="detail-rationale">'+c.rationale+'</div>' +
    '<div class="detail-stats">' +
    '<div class="stat"><div class="stat-val" style="color:var(--accent)">'+c.capability_score+'</div><div class="stat-label">AI Capability</div></div>' +
    '<div class="stat"><div class="stat-val" style="color:var(--gold)">'+c.displacement_score+'</div><div class="stat-label">Displacement</div></div>' +
    '<div class="stat"><div class="stat-val">'+(c.gap>40?'<span style=color:var(--accent)>':c.gap>20?'<span style=color:var(--gold)>':'<span style=color:var(--red)>')+c.gap.toFixed(0)+'</span></div><div class="stat-label">Gap</div></div>' +
    '</div>' +
    '<div class="timeline '+tlClass+'">Disruption timeline: '+tl+'</div>';
  panel.scrollIntoView({behavior:'smooth',block:'nearest'});
}

async function subscribe() {
  const email = document.getElementById('sub-email').value;
  if (!email) return;
  try {
    const resp = await fetch('/api/v1/subscribe', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email})});
    const data = await resp.json();
    document.getElementById('sub-msg').textContent = data.message || 'Subscribed!';
  } catch(e) {
    document.getElementById('sub-msg').textContent = 'Error subscribing.';
  }
}

loadCats();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# INVEST PAGE — FP Frontier Basket
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/invest", response_class=HTMLResponse)
async def invest_page():
    """FP Frontier Basket — AI capital allocation governed by live intelligence."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FP Frontier Basket — AI Capital Allocation by Intelligence</title>
<meta name="description" content="Capital allocation governed by live AI frontier intelligence. The Full Potential Index tells you where capability is concentrating — and where capital should follow.">
<meta property="og:type" content="website">
<meta property="og:title" content="FP Frontier Basket — Where AI Capital Should Flow">
<meta property="og:description" content="Capital allocation governed by real-time intelligence from 18 live sources. See which AI sectors are concentrating capability — and where capital should follow.">
<meta property="og:url" content="https://fullpotential.ai/invest">
<meta property="og:site_name" content="Full Potential AI">
<meta property="og:image" content="https://fullpotential.ai/api/v1/og-image">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="FP Frontier Basket — AI Capital Allocation">
<meta name="twitter:description" content="Where should AI capital flow? Real-time allocation based on 18 live intelligence sources.">
<meta name="twitter:image" content="https://fullpotential.ai/api/v1/og-image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root{--bg:#06060b;--card:#0e0e16;--card2:#13131d;--border:rgba(255,255,255,0.06);--text:#e0e0e0;--dim:#666;--accent:#00d4ff;--gold:#ffb400;--green:#4ecdc4;--red:#ff6b6b;--purple:#a78bfa}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;line-height:1.6}
.container{max-width:900px;margin:0 auto;padding:40px 20px}

.hero{text-align:center;padding:60px 0 40px}
.hero-badge{display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:0.7rem;letter-spacing:2px;text-transform:uppercase;color:var(--accent);border:1px solid rgba(0,212,255,0.3);padding:4px 12px;border-radius:20px;margin-bottom:20px}
.hero h1{font-size:2.8rem;font-weight:700;margin-bottom:12px;background:linear-gradient(135deg,#fff 0%,var(--accent) 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{color:var(--dim);font-size:1.05rem;max-width:600px;margin:0 auto 20px;line-height:1.7}
.hero-explainer{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;color:var(--dim);max-width:550px;margin:0 auto;line-height:1.5}

.score-ring{margin:32px auto;width:140px;height:140px;border-radius:50%;border:3px solid var(--accent);display:flex;flex-direction:column;align-items:center;justify-content:center;box-shadow:0 0 40px rgba(0,212,255,0.15)}
.score-ring .number{font-family:'IBM Plex Mono',monospace;font-size:2.4rem;font-weight:600;color:#fff}
.score-ring .label{font-size:0.65rem;color:var(--dim);text-transform:uppercase;letter-spacing:1.5px}

.headline-bar{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:20px 24px;margin:32px 0;font-family:'IBM Plex Mono',monospace;font-size:0.85rem;color:var(--accent);line-height:1.6}

.section{margin:48px 0}
.section-title{font-size:1.3rem;font-weight:600;margin-bottom:6px}
.section-sub{color:var(--dim);font-size:0.85rem;margin-bottom:24px}

.alloc-grid{display:flex;flex-direction:column;gap:12px}
.alloc-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px 20px;transition:border-color 0.2s}
.alloc-card:hover{border-color:rgba(0,212,255,0.3)}
.alloc-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.alloc-name{font-weight:600;font-size:0.95rem}
.alloc-pct{font-family:'IBM Plex Mono',monospace;font-size:1.4rem;font-weight:600;color:var(--accent)}
.alloc-desc{color:var(--dim);font-size:0.8rem;margin-bottom:10px}
.alloc-bar-wrap{height:6px;background:rgba(255,255,255,0.06);border-radius:3px;margin-bottom:10px;overflow:hidden}
.alloc-bar{height:100%;background:linear-gradient(90deg,var(--accent),var(--purple));border-radius:3px;transition:width 0.8s ease}
.alloc-tickers{display:flex;flex-wrap:wrap;gap:6px}
.ticker-chip{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;background:rgba(0,212,255,0.08);color:var(--accent);padding:3px 8px;border-radius:4px;border:1px solid rgba(0,212,255,0.15);cursor:default}
.ticker-chip:hover .ticker-tip{display:block}
.alloc-signal{font-family:'IBM Plex Mono',monospace;font-size:0.7rem;padding:2px 8px;border-radius:4px;margin-left:8px}
.signal-overweight{background:rgba(78,205,196,0.15);color:var(--green)}
.signal-underweight{background:rgba(255,107,107,0.15);color:var(--red)}
.signal-neutral{background:rgba(255,255,255,0.06);color:var(--dim)}

.rebalance{margin:40px 0}
.rebalance-item{display:flex;align-items:center;gap:12px;padding:12px 16px;background:var(--card);border:1px solid var(--border);border-radius:8px;margin-bottom:8px;font-size:0.85rem}
.rebalance-dir{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;min-width:100px}
.rebalance-change{font-family:'IBM Plex Mono',monospace;font-weight:600}
.change-up{color:var(--green)}
.change-down{color:var(--red)}

.displacement-signals{background:var(--card2);border:1px solid var(--border);border-radius:10px;padding:24px;margin:40px 0}
.disp-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border);font-size:0.85rem}
.disp-row:last-child{border-bottom:none}
.disp-label{color:var(--dim);font-size:0.75rem;font-family:'IBM Plex Mono',monospace}

.tiers{margin:48px 0}
.tier-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
.tier-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:24px;text-align:center}
.tier-name{font-weight:600;font-size:1.1rem;margin-bottom:4px}
.tier-price{font-family:'IBM Plex Mono',monospace;font-size:1.6rem;color:var(--accent);margin-bottom:8px}
.tier-price .period{font-size:0.7rem;color:var(--dim)}
.tier-features{list-style:none;text-align:left;margin:16px 0;font-size:0.8rem;color:var(--dim)}
.tier-features li{padding:4px 0;border-bottom:1px solid var(--border)}
.tier-features li::before{content:'→ ';color:var(--accent)}
.tier-btn{display:inline-block;margin-top:12px;padding:10px 24px;border-radius:6px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;text-decoration:none;transition:all 0.2s}
.tier-btn-primary{background:var(--accent);color:#000;border:none}
.tier-btn-primary:hover{background:#00b8d4;transform:translateY(-1px)}
.tier-btn-secondary{background:transparent;color:var(--accent);border:1px solid var(--accent)}
.tier-btn-secondary:hover{background:rgba(0,212,255,0.1)}
.tier-highlight{border-color:var(--accent);box-shadow:0 0 30px rgba(0,212,255,0.1)}

.disclaimer{margin:48px 0;padding:20px;background:var(--card);border:1px solid var(--border);border-radius:8px;font-size:0.75rem;color:var(--dim);line-height:1.7;font-family:'IBM Plex Mono',monospace}

.cta-section{text-align:center;margin:48px 0}
.cta-section a{display:inline-block;margin:6px 8px;padding:12px 28px;border-radius:6px;font-family:'IBM Plex Mono',monospace;font-size:0.8rem;text-decoration:none}

.nav-back{display:inline-block;margin-bottom:20px;color:var(--dim);text-decoration:none;font-size:0.8rem;font-family:'IBM Plex Mono',monospace}
.nav-back:hover{color:var(--accent)}

@media(max-width:600px){
  .hero h1{font-size:1.8rem}
  .tier-grid{grid-template-columns:1fr}
  .alloc-header{flex-direction:column;align-items:flex-start;gap:4px}
}
</style>
</head>
<body>
<div class="container">

<a href="/intelligence" class="nav-back">← Intelligence Feed</a>

<div class="hero">
  <div class="hero-badge">Layer 1 — Intelligence Product</div>
  <h1>FP Frontier Basket</h1>
  <p class="hero-sub">Capital allocation governed by live AI frontier intelligence. Not a fund. Not advice. A signal.</p>
  <p class="hero-explainer">The Full Potential Index scans 18 live sources every 30 minutes. The Frontier Basket translates those signals into sector allocation weights — showing where AI capability is concentrating, and where capital should follow.</p>
  <div class="score-ring" id="score-ring">
    <div class="number" id="fp-score">—</div>
    <div class="label">FP Line</div>
  </div>
</div>

<div class="headline-bar" id="headline">Loading allocation...</div>

<!-- ═══ ALLOCATION HISTORY CHART ═══ -->
<div class="section" id="history-section" style="display:none">
  <div class="section-title">Allocation Track Record</div>
  <div class="section-sub">Historical FP Line score and allocation shifts over time.</div>
  <canvas id="history-chart" width="860" height="260" style="width:100%;max-width:860px;background:var(--card);border:1px solid var(--border);border-radius:10px"></canvas>
</div>

<!-- ═══ CURRENT ALLOCATION ═══ -->
<div class="section">
  <div class="section-title">Current Allocation</div>
  <div class="section-sub">Target weights derived from FP Line dimension scores. Updated every scan cycle.</div>
  <div class="alloc-grid" id="alloc-grid">
    <div style="color:var(--dim);font-size:0.85rem">Loading allocation data...</div>
  </div>
</div>

<!-- ═══ REBALANCE ACTIONS ═══ -->
<div class="rebalance" id="rebalance-section" style="display:none">
  <div class="section-title">Rebalance Actions</div>
  <div class="section-sub">Sectors that moved significantly from base weight this cycle.</div>
  <div id="rebalance-list"></div>
</div>

<!-- ═══ DISPLACEMENT SIGNALS ═══ -->
<div class="displacement-signals" id="disp-signals" style="display:none">
  <div class="section-title" style="margin-bottom:16px">Labor Displacement Signals</div>
  <div id="disp-closing">
    <div class="disp-label">FASTEST CLOSING GAPS (automation approaching fast)</div>
  </div>
  <div id="disp-gaps" style="margin-top:16px">
    <div class="disp-label">LARGEST UNTAPPED GAPS (opportunity windows)</div>
  </div>
</div>

<!-- ═══ PRICING TIERS ═══ -->
<div class="tiers">
  <div class="section-title" style="text-align:center">Choose Your Signal Depth</div>
  <div class="section-sub" style="text-align:center">Intelligence products. Not financial advice.</div>
  <div class="tier-grid">
    <div class="tier-card">
      <div class="tier-name">Observer</div>
      <div class="tier-price">Free</div>
      <div class="tier-features">
        <li>Monthly allocation summary</li>
        <li>FP Line score + trend</li>
        <li>Public intelligence feed</li>
        <li>Career displacement data</li>
      </div>
      <a href="/intelligence" class="tier-btn tier-btn-secondary">View Intelligence →</a>
    </div>
    <div class="tier-card tier-highlight">
      <div class="tier-name">Pro</div>
      <div class="tier-price">$49<span class="period">/mo</span></div>
      <div class="tier-features">
        <li>Weekly allocation report</li>
        <li>Rebalance alerts</li>
        <li>Full dimension breakdown</li>
        <li>Top signals + sector analysis</li>
        <li>Email briefing (daily)</li>
        <li>API access</li>
      </div>
      <a href="#" class="tier-btn tier-btn-primary" id="pro-btn" onclick="subscribePro(event)">Get Pro Access →</a>
    </div>
    <div class="tier-card">
      <div class="tier-name">Premium</div>
      <div class="tier-price">$199<span class="period">/mo</span></div>
      <div class="tier-features">
        <li>Daily allocation updates</li>
        <li>Real-time rebalance alerts</li>
        <li>Displacement investment signals</li>
        <li>Custom sector watchlists</li>
        <li>Hypothetical portfolio tracker</li>
        <li>Priority API + webhooks</li>
      </div>
      <a href="#premium-signup" class="tier-btn tier-btn-secondary">Coming Soon</a>
    </div>
  </div>
</div>

<!-- ═══ DISCLAIMER ═══ -->
<div class="disclaimer" id="disclaimer"></div>

<!-- ═══ CTAs ═══ -->
<div class="cta-section">
  <a href="/intelligence" style="background:var(--accent);color:#000">Intelligence Feed →</a>
  <a href="/careers" style="border:1px solid var(--accent);color:var(--accent)">Career Intelligence →</a>
  <a href="/constitution" style="border:1px solid var(--border);color:var(--dim)">Read the Constitution</a>
</div>

</div>

<script>
const API = window.location.origin;

async function loadAllocation() {
  try {
    const resp = await fetch('/api/v1/invest/allocation');
    const data = await resp.json();

    document.getElementById('fp-score').textContent = data.allocation.fp_line_score.toFixed(1);
    document.getElementById('headline').textContent = data.headline;
    document.getElementById('disclaimer').textContent = data.disclaimer;

    const grid = document.getElementById('alloc-grid');
    grid.innerHTML = '';
    const allocs = data.allocation.allocations;
    const maxPct = Math.max(...Object.values(allocs).map(a => a.target_pct));

    for (const [key, a] of Object.entries(allocs)) {
      const signalClass = a.momentum_signal === 'overweight' ? 'signal-overweight'
        : a.momentum_signal === 'underweight' ? 'signal-underweight' : 'signal-neutral';
      const tickerHtml = a.example_tickers.map(t =>
        `<span class="ticker-chip" title="${t.exposure}">${t.ticker}</span>`
      ).join('');

      grid.innerHTML += `
        <div class="alloc-card">
          <div class="alloc-header">
            <div>
              <span class="alloc-name">${a.sector_name}</span>
              <span class="alloc-signal ${signalClass}">${a.momentum_signal}</span>
            </div>
            <div class="alloc-pct">${a.target_pct}%</div>
          </div>
          <div class="alloc-desc">${a.description} · Score: ${a.dimension_score.toFixed(1)} · Base: ${a.base_weight_pct}%</div>
          <div class="alloc-bar-wrap">
            <div class="alloc-bar" style="width:${(a.target_pct / maxPct * 100).toFixed(0)}%"></div>
          </div>
          <div class="alloc-tickers">${tickerHtml}</div>
        </div>`;
    }

    // Rebalance actions
    if (data.rebalance_actions && data.rebalance_actions.length > 0) {
      document.getElementById('rebalance-section').style.display = 'block';
      const list = document.getElementById('rebalance-list');
      list.innerHTML = '';
      for (const a of data.rebalance_actions) {
        const cls = a.change > 0 ? 'change-up' : 'change-down';
        list.innerHTML += `
          <div class="rebalance-item">
            <div class="rebalance-dir">${a.direction}</div>
            <div style="flex:1">${a.sector}</div>
            <div class="rebalance-change ${cls}">${a.change > 0 ? '+' : ''}${a.change}%</div>
            <div style="color:var(--dim);font-size:0.75rem;margin-left:12px">${a.from_pct}% → ${a.to_pct}%</div>
          </div>`;
      }
    }
  } catch (err) {
    document.getElementById('headline').textContent = 'Unable to load allocation. Try again shortly.';
    console.error('Allocation load error:', err);
  }
}

async function loadDisplacementSignals() {
  try {
    const resp = await fetch('/api/v1/invest/report');
    const data = await resp.json();
    const ds = data.displacement_signals;
    if (!ds) return;

    document.getElementById('disp-signals').style.display = 'block';

    const closingEl = document.getElementById('disp-closing');
    if (ds.fastest_closing_gaps && ds.fastest_closing_gaps.length > 0) {
      for (const c of ds.fastest_closing_gaps) {
        closingEl.innerHTML += `<div class="disp-row"><span>${c.name || c.id}</span><span style="color:var(--red);font-family:'IBM Plex Mono',monospace;font-size:0.8rem">gap ${(c.gap || 0).toFixed(0)}pts</span></div>`;
      }
    }

    const gapsEl = document.getElementById('disp-gaps');
    if (ds.largest_untapped_gaps && ds.largest_untapped_gaps.length > 0) {
      for (const g of ds.largest_untapped_gaps) {
        gapsEl.innerHTML += `<div class="disp-row"><span>${g.name || g.id}</span><span style="color:var(--green);font-family:'IBM Plex Mono',monospace;font-size:0.8rem">gap ${(g.gap || 0).toFixed(0)}pts</span></div>`;
      }
    }
  } catch (err) {
    console.error('Displacement signals error:', err);
  }
}

async function subscribePro(e) {
  e.preventDefault();
  const btn = document.getElementById('pro-btn');
  btn.textContent = 'Redirecting to checkout...';
  btn.style.opacity = '0.6';
  try {
    const resp = await fetch('/api/v1/subscribe/pro', {method: 'POST'});
    const data = await resp.json();
    if (data.checkout_url) {
      window.location.href = data.checkout_url;
    } else {
      btn.textContent = 'Error — try again';
      btn.style.opacity = '1';
    }
  } catch (err) {
    btn.textContent = 'Error — try again';
    btn.style.opacity = '1';
    console.error(err);
  }
}

async function loadHistory() {
  try {
    const resp = await fetch('/api/v1/invest/history?limit=168');
    const items = await resp.json();
    if (!Array.isArray(items) || items.length < 2) return;
    document.getElementById('history-section').style.display = 'block';

    const canvas = document.getElementById('history-chart');
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const pad = {top: 30, right: 20, bottom: 40, left: 50};
    const cw = w - pad.left - pad.right, ch = h - pad.top - pad.bottom;

    const scores = items.map(i => i.fp_line_score || 0).reverse();
    const labels = items.map(i => {
      const d = new Date(i.computed_at);
      return d.toLocaleDateString('en-US', {month:'short', day:'numeric'});
    }).reverse();
    const momenta = items.map(i => i.fp_line_momentum || 0).reverse();

    const minS = Math.floor(Math.min(...scores) - 2);
    const maxS = Math.ceil(Math.max(...scores) + 2);
    const range = maxS - minS || 1;

    function x(i) { return pad.left + (i / (scores.length - 1)) * cw; }
    function y(v) { return pad.top + ch - ((v - minS) / range) * ch; }

    ctx.fillStyle = '#0e0e16';
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    const gridLines = 5;
    for (let i = 0; i <= gridLines; i++) {
      const gy = pad.top + (ch / gridLines) * i;
      ctx.beginPath(); ctx.moveTo(pad.left, gy); ctx.lineTo(w - pad.right, gy); ctx.stroke();
      const lbl = (maxS - (range / gridLines) * i).toFixed(1);
      ctx.fillStyle = '#666'; ctx.font = '10px IBM Plex Mono, monospace'; ctx.textAlign = 'right';
      ctx.fillText(lbl, pad.left - 8, gy + 3);
    }

    const step = Math.max(1, Math.floor(scores.length / 7));
    ctx.fillStyle = '#666'; ctx.font = '10px IBM Plex Mono, monospace'; ctx.textAlign = 'center';
    for (let i = 0; i < scores.length; i += step) {
      ctx.fillText(labels[i], x(i), h - pad.bottom + 18);
    }

    const grad = ctx.createLinearGradient(0, pad.top, 0, pad.top + ch);
    grad.addColorStop(0, 'rgba(0,212,255,0.18)');
    grad.addColorStop(1, 'rgba(0,212,255,0)');
    ctx.beginPath();
    ctx.moveTo(x(0), y(scores[0]));
    for (let i = 1; i < scores.length; i++) ctx.lineTo(x(i), y(scores[i]));
    ctx.lineTo(x(scores.length - 1), pad.top + ch);
    ctx.lineTo(x(0), pad.top + ch);
    ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();

    ctx.beginPath();
    ctx.moveTo(x(0), y(scores[0]));
    for (let i = 1; i < scores.length; i++) ctx.lineTo(x(i), y(scores[i]));
    ctx.strokeStyle = '#00d4ff'; ctx.lineWidth = 2; ctx.stroke();

    const last = scores[scores.length - 1];
    ctx.beginPath();
    ctx.arc(x(scores.length - 1), y(last), 4, 0, Math.PI * 2);
    ctx.fillStyle = '#00d4ff'; ctx.fill();
    ctx.fillStyle = '#fff'; ctx.font = 'bold 11px IBM Plex Mono, monospace'; ctx.textAlign = 'left';
    ctx.fillText(last.toFixed(1), x(scores.length - 1) + 8, y(last) + 4);

    ctx.fillStyle = '#666'; ctx.font = '10px Inter, sans-serif'; ctx.textAlign = 'left';
    ctx.fillText('FP Line Score', pad.left + 4, pad.top - 10);

  } catch(e) { console.error('History chart error:', e); }
}

loadAllocation();
loadDisplacementSignals();
loadHistory();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
