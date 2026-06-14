"""
FP Index Engine — Spec-Aligned v4.0
=====================================

Orchestrates all 6 modules:
  1. Frontier Scanner → run_full_scan()
  2. Intelligence Index → persist, query, three-tier (hot/warm/cold)
  3. Proof Engine → contribution lifecycle, verification
  4. Credit Mint → Reward = Impact × Proof × Trust × Alignment
  5. Immune System → 7 threat signals, 5-stage ladder
  6. Agent Gateway → dual tiers, roles, subscriptions
"""

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models.schema import (
    IndexEntry, FPLineSnapshot, AgentSubscription,
    AgentContribution, ContributionTier, ContributionType,
    Dimension, Alignment, Domain, VerificationVote,
    ContributionState, VerificationStatus,
    FieldReportType, EvidenceLevel, FIELD_REPORT_CREDIT_BASE,
    FIELD_REPORT_SCHEMAS, FIELD_REPORT_ROUTING,
    NOVELTY_MULTIPLIER, EVIDENCE_WEIGHTS, DELAYED_NOVELTY_MULTIPLIERS,
    VERIFICATION_STAGE_WEIGHTS,
    MAX_FP_LINE_ADJUSTMENT_PER_REPORT, MIN_WEIGHT_FOR_FP_LINE_INFLUENCE,
    TRUST_INTEGRITY_WEIGHT, TRUST_CAPABILITY_WEIGHT,
)
from .models.database import (
    IndexEntryRow, CapabilityRow, ActivityRow, FPLineRow,
    AgentSubscriptionRow, AgentContributionRow, DailyBriefingRow,
    ExecutionBriefRow, JobCategoryRow, ReplicationRequestRow,
    async_session,
)
from .scanners.frontier import run_full_scan, run_tier1_scan, run_tier2_scan, SCAN_TIERS, detect_cross_source_patterns
from .economics import (
    proof_engine, credit_mint, integrity_engine, agent_gateway,
    get_full_agent_economy,
)
from .immune import immune
from .principles import gate_self_adoption, classify_adoption, AUTONOMOUS_ADOPTION_CATEGORIES
from .actuators import run_actuators, actuate_pending_adoptions

logger = logging.getLogger("fp_index.engine")

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")
NERVE_CENTER_URL = os.getenv("NERVE_CENTER_URL", "http://198.54.123.234:8120")


class FPIndexEngine:
    """Core engine orchestrating all six modules."""

    # ─── Self-Application: The system's own capability registry ───────────
    # What the system currently USES vs what the FP Line says EXISTS.
    # The gap between these two is the system's own displacement score.

    SYSTEM_CAPABILITY_REGISTRY = {
        "reasoning": {
            "current_usage": "Claude Sonnet for briefing synthesis and EXECUTE evaluation",
            "model_in_use": "claude-sonnet-4-20250514",
            "adoption_level": 0.35,
            "what_we_use": ["Briefing generation", "Execution brief evaluation"],
            "what_we_dont": [
                "Cross-source pattern analysis (uses keyword matching)",
                "Novelty detection (uses keyword overlap)",
                "Scoring and impact assessment (uses heuristics)",
                "Displacement trend analysis",
            ],
        },
        "code": {
            "current_usage": "Static keyword matching, no AI-assisted development",
            "adoption_level": 0.15,
            "what_we_use": ["Scanner pipeline (human-written)"],
            "what_we_dont": [
                "Auto-generate new scanner integrations from detected frameworks",
                "AI-assisted schema evolution when new fields needed",
                "Automated test generation for new features",
            ],
        },
        "agents": {
            "current_usage": "8 internal agents registered, operate independently",
            "adoption_level": 0.20,
            "what_we_use": ["Single-agent registration", "Basic contribution pipeline"],
            "what_we_dont": [
                "Multi-agent coordination for verification",
                "Autonomous task routing between agents",
                "Agent-to-agent delegation for replication",
                "Self-deploying scanner agents for new sources",
            ],
        },
        "creative": {
            "current_usage": "Zero creative AI. All output is text templates or Claude prose.",
            "adoption_level": 0.05,
            "what_we_use": [],
            "what_we_dont": [
                "Blog posts and articles about system discoveries",
                "Social media content from scan insights",
                "Email sequences for subscriber engagement",
                "Visual content: charts, infographics, OG images",
            ],
        },
        "audio": {
            "current_usage": "Zero audio output",
            "adoption_level": 0.0,
            "what_we_use": [],
            "what_we_dont": [
                "Audio briefings (daily FP Line narrated)",
                "Voice alerts for critical signals",
                "Podcast-style weekly intelligence summaries",
            ],
        },
        "vision": {
            "current_usage": "Zero visual AI",
            "adoption_level": 0.0,
            "what_we_use": [],
            "what_we_dont": [
                "Chart generation for FP Line trends",
                "Visual dashboards auto-generated from data",
                "Video briefings combining data + narration",
            ],
        },
        "tools": {
            "current_usage": "18 source scanners, basic REST API",
            "adoption_level": 0.40,
            "what_we_use": ["RSS/API scanning", "REST endpoints", "MCP server"],
            "what_we_dont": [
                "SEO optimization tools for own pages",
                "Landing page optimization / A/B testing",
                "Conversion funnel analysis",
                "Automated deployment pipelines triggered by scan results",
            ],
        },
        "security": {
            "current_usage": "Immune system with threat signals, mostly idle",
            "adoption_level": 0.25,
            "what_we_use": ["Keyword-based threat detection", "Immune ladder"],
            "what_we_dont": [
                "Adversarial testing of own APIs",
                "AI-powered anomaly detection on agent behavior",
                "Automated vulnerability scanning",
            ],
        },
    }

    SELF_APPLICATION_KEYWORDS = {
        "content_creation": [
            "copywriting", "content generation", "blog", "social media",
            "newsletter", "email marketing", "open rate", "engagement",
            "seo", "landing page", "conversion", "growth hacking",
        ],
        "cost_optimization": [
            "inference cost", "price drop", "cheaper", "cost reduction",
            "efficiency", "batch processing", "quantization", "distillation",
            "token cost", "pricing", "free tier",
        ],
        "outreach_automation": [
            "outreach", "lead generation", "personalization", "crm",
            "customer acquisition", "growth", "marketing automation",
            "cold email", "targeting", "audience",
        ],
        "multimodal_production": [
            "text to speech", "tts", "voice synthesis", "audio generation",
            "video generation", "chart", "visualization", "infographic",
            "image generation", "podcast", "visual",
        ],
        "ux_improvement": [
            "ux", "user experience", "no-code", "accessibility",
            "responsive design", "personalization", "onboarding",
            "simplify", "intuitive", "usability",
        ],
        "autonomous_growth": [
            "autonomous agent", "self-improving", "auto-scaling",
            "workflow automation", "self-healing", "auto-deploy",
            "agent swarm", "multi-agent orchestration",
        ],
    }

    def __init__(self):
        self.last_scan: str | None = None
        self.scan_count: int = 0

    # ─── Module 1: Frontier Scanner ──────────────────────────────────────

    async def run_scan_cycle(self) -> dict:
        """WIDE → DEEP → COMPRESS → EXECUTE → SELF-APPLY cycle.
        
        WIDE:       18 sources — primary, secondary, threat, constraint, discovery
        DEEP:       Impact scoring, domain classification, alignment detection
        COMPRESS:   FP Line Score, daily briefing, top signals
        EXECUTE:    Evaluate findings for self-upgrade applicability
        SELF-APPLY: Can we use this capability RIGHT NOW in our own operations?
        """
        logger.info("Starting WIDE→DEEP→COMPRESS→EXECUTE→SELF-APPLY cycle...")

        entries = await run_full_scan()

        for entry in entries:
            entry.fingerprint = entry.compute_fingerprint()
            if entry.alignment == Alignment.DARK:
                entry.dark_flag = True

        synthesis = await detect_cross_source_patterns(entries)
        if synthesis:
            for s in synthesis:
                s.fingerprint = s.compute_fingerprint()
            entries.extend(synthesis)

        stored = await self._persist_entries(entries)

        # ROUTE — send signals to brains that act (not just write articles)
        routed_count = 0
        try:
            from .signal_router import route_batch
            entry_dicts = [
                {
                    "id": e.id,
                    "source": e.source,
                    "title": e.title,
                    "summary": e.summary,
                    "impact_score": e.impact_score,
                    "tags": e.tags,
                    "domains": e.domains,
                    "raw_data": e.raw_data if hasattr(e, "raw_data") else {},
                }
                for e in entries
            ]
            route_results = await route_batch(entry_dicts)
            routed_count = sum(1 for r in route_results if r.routed_to)
            logger.info(f"[ROUTER] Full cycle: {routed_count}/{len(entries)} signals routed to brains")
        except Exception as e:
            logger.warning(f"[ROUTER] Signal routing failed: {e}")

        fp_line = await self.compute_fp_line(persist=True)
        await self._notify_nerve_center(fp_line, stored)
        await self._generate_daily_briefing(fp_line)

        exec_briefs = await self._execute_step(entries)
        dim_proposals = await self.check_dimension_candidates(entries)

        # SELF-APPLY: The fourth track. What did we just learn that we're not using?
        self_app_proposals = await self.evaluate_self_application(entries)
        self_app_evaluated = await self.process_self_application_briefs()

        # ADOPT: Run evaluated proposals through the five-filter gate
        adoption_result = await self.run_adoption_cycle()

        self.last_scan = datetime.now(timezone.utc).isoformat()
        self.scan_count += 1

        return {
            "scanned": len(entries),
            "synthesis_patterns": len(synthesis),
            "stored_new": stored,
            "fp_line": fp_line.model_dump(),
            "execution_briefs": exec_briefs,
            "self_application": {
                "proposals_found": len(self_app_proposals),
                "evaluated": len(self_app_evaluated),
                "high_priority": sum(1 for p in self_app_proposals if p["priority"] == "high"),
                "adoption": adoption_result,
            },
            "dimension_proposals": dim_proposals,
            "timestamp": self.last_scan,
        }

    async def run_tier_cycle(self, tier: str) -> dict:
        """Run a targeted tier scan (tier1=30m, tier2=60m) — full pipeline minus Claude eval.
        
        WIDE → DEEP → COMPRESS → EXECUTE(keyword-only) → SELF-APPLY(keyword-only).
        Nerve center is notified. Execution briefs and self-application proposals
        are generated via keyword matching. Claude evaluation deferred to full cycle.
        """
        if tier == "tier0":
            from .scanners.frontier import run_tier0_scan
            entries = await run_tier0_scan()
            if not entries:
                return {"tier": "tier0", "scanned": 0, "stored_new": 0, "routed": 0}

            for entry in entries:
                entry.fingerprint = entry.compute_fingerprint()
            stored = await self._persist_entries(entries)

            # ROUTE — the scanner found something, now send it to brains that act
            routed_count = 0
            if entries:
                try:
                    from .signal_router import route_batch
                    entry_dicts = [
                        {
                            "id": e.id,
                            "source": e.source,
                            "title": e.title,
                            "summary": e.summary,
                            "impact_score": e.impact_score,
                            "tags": e.tags,
                            "domains": e.domains,
                            "raw_data": e.raw_data if hasattr(e, "raw_data") else {},
                        }
                        for e in entries
                    ]
                    route_results = await route_batch(entry_dicts)
                    routed_count = sum(1 for r in route_results if r.routed_to)
                except Exception as e:
                    logger.warning(f"[FAST-DETECT] Signal routing failed: {e}")

            if stored > 0:
                logger.info(f"[FAST-DETECT] {stored} new signals persisted, {routed_count} routed to brains")
            return {
                "tier": "tier0",
                "scanned": len(entries),
                "stored_new": stored,
                "routed": routed_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        if tier == "tier1":
            entries = await run_tier1_scan()
        elif tier == "tier2":
            entries = await run_tier2_scan()
        else:
            return await self.run_scan_cycle()

        for entry in entries:
            entry.fingerprint = entry.compute_fingerprint()
            if entry.alignment == Alignment.DARK:
                entry.dark_flag = True

        synthesis = await detect_cross_source_patterns(entries)
        if synthesis:
            for s in synthesis:
                s.fingerprint = s.compute_fingerprint()
            entries.extend(synthesis)

        stored = await self._persist_entries(entries)
        fp_line = await self.compute_fp_line(persist=True)
        await self._notify_nerve_center(fp_line, stored)
        await self._generate_daily_briefing(fp_line)

        exec_briefs = await self._execute_step(entries, evaluate=False)
        await self.check_dimension_candidates(entries)

        # Self-application: keyword matching only on tier cycles (Claude eval on full cycle)
        self_app_proposals = await self.evaluate_self_application(entries)

        self.last_scan = datetime.now(timezone.utc).isoformat()
        self.scan_count += 1

        logger.info(f"[{tier}] cycle done: {len(entries)} scanned, {stored} new, "
                     f"FP Line {fp_line.overall_score:.1f}, {len(exec_briefs)} briefs queued, "
                     f"{len(self_app_proposals)} self-application proposals, "
                     f"{len(synthesis)} synthesis patterns")
        return {
            "tier": tier,
            "scanned": len(entries),
            "stored_new": stored,
            "fp_line_score": fp_line.overall_score,
            "execution_briefs_queued": len(exec_briefs),
            "self_application_proposals": len(self_app_proposals),
            "timestamp": self.last_scan,
        }

    async def _execute_step(self, entries: list[IndexEntry], evaluate: bool = True) -> list[dict]:
        """EXECUTE: Evaluate high-impact entries for self-upgrade applicability.
        
        This is the step no one else does. Every AI news site stops at COMPRESS.
        We close the loop: scanner finds capability → system evaluates whether it
        applies to our agents → generates implementation brief → the upgrade
        itself becomes content.
        
        evaluate=False: keyword matching + DB insert only (used by tier1/tier2).
        evaluate=True: full Claude evaluation of pending briefs (used by full cycle).
        """
        EXECUTE_KEYWORDS = {
            "agent_upgrade": ["agent", "tool use", "function calling", "mcp", "context window",
                              "memory", "persistent", "multi-turn", "system prompt"],
            "scanner_upgrade": ["rss", "api", "feed", "scraping", "data source", "changelog",
                                "monitoring", "tracking"],
            "model_upgrade": ["claude", "gpt", "gemini", "llama", "model release", "fine-tuning",
                              "embeddings", "reasoning", "coding"],
            "infrastructure": ["deployment", "docker", "kubernetes", "scaling", "latency",
                               "caching", "database", "vector"],
            "security": ["vulnerability", "jailbreak", "adversarial", "safety", "alignment",
                         "guardrail", "red team"],
        }
        IMPACT_THRESHOLD = 0.55

        high_impact = [e for e in entries if e.impact_score >= IMPACT_THRESHOLD]
        if not high_impact:
            return []

        briefs = []
        async with async_session() as session:
            for entry in high_impact[:20]:
                text = f"{entry.title} {entry.summary}".lower()
                applicable_categories = []
                affected_agents = []

                for category, keywords in EXECUTE_KEYWORDS.items():
                    if any(kw in text for kw in keywords):
                        applicable_categories.append(category)

                if not applicable_categories:
                    continue

                if "agent_upgrade" in applicable_categories:
                    affected_agents.extend(["cora", "aria", "fp-scanner"])
                if "scanner_upgrade" in applicable_categories:
                    affected_agents.extend(["fp-scanner", "fp-index"])
                if "model_upgrade" in applicable_categories:
                    affected_agents.extend(["cora", "aria", "intelligence-briefing"])
                if "infrastructure" in applicable_categories:
                    affected_agents.extend(["fp-index", "credits-gateway", "nerve-center"])
                if "security" in applicable_categories:
                    affected_agents.extend(["immune-system", "integrity-engine"])

                affected_agents = list(set(affected_agents))

                priority = "high" if entry.impact_score >= 0.7 else "medium"
                if entry.source in ("changelog", "agent_framework", "benchmark"):
                    priority = "high"

                applicability = f"Categories: {', '.join(applicable_categories)}. " \
                                f"Source: {entry.source} (impact: {entry.impact_score:.2f})"

                existing = (await session.execute(
                    select(ExecutionBriefRow).where(ExecutionBriefRow.entry_id == entry.id)
                )).scalars().first()
                if existing:
                    continue

                brief = ExecutionBriefRow(
                    entry_id=entry.id,
                    entry_title=entry.title,
                    applicability=applicability,
                    affected_agents=affected_agents,
                    priority=priority,
                    status="pending",
                )
                session.add(brief)
                briefs.append({
                    "entry_title": entry.title,
                    "categories": applicable_categories,
                    "affected_agents": affected_agents,
                    "priority": priority,
                })

            await session.commit()

        if briefs:
            logger.info(f"[EXECUTE] Generated {len(briefs)} execution briefs "
                        f"({sum(1 for b in briefs if b['priority'] == 'high')} high priority)")

        if evaluate:
            await self._process_pending_briefs()
        return briefs

    async def _process_pending_briefs(self) -> None:
        """Evaluate pending execution briefs with Claude — scoring, routing, and narration.
        
        Each brief receives:
          - relevance_score (0.0-1.0): how applicable to our system
          - execution_track: self_upgrade | investment | product
          - narrative: human-readable one-liner for the /intelligence feed
          - implementation_path: Claude's full evaluation
        """
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key or not api_key.startswith("sk-ant"):
            logger.info("[EXECUTE] No Anthropic API key — skipping brief processing")
            return

        async with async_session() as session:
            pending = (await session.execute(
                select(ExecutionBriefRow)
                .where(ExecutionBriefRow.status == "pending")
                .order_by(
                    ExecutionBriefRow.priority.desc(),
                    ExecutionBriefRow.created_at.desc(),
                )
                .limit(5)
            )).scalars().all()

            if not pending:
                return

            logger.info(f"[EXECUTE] Processing {len(pending)} pending briefs with Claude...")

            from .budget import check_budget, record_spend
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            for brief in pending:
                budget = await check_budget("adoption_evaluation")
                if not budget["allowed"]:
                    logger.warning(f"[EXECUTE] Budget blocked — skipping remaining briefs: {budget['reason']}")
                    break

                try:
                    prompt = f"""You are the intelligence analyst for the Full Potential Index — a live AI frontier scanner. Evaluate whether this detected capability should trigger action in our system.

CAPABILITY DETECTED:
- Title: {brief.entry_title}
- Applicability: {brief.applicability}
- Affected agents: {', '.join(brief.affected_agents or [])}
- Priority: {brief.priority}

OUR SYSTEM:
- fp-scanner: Scans 18 sources for AI frontier signals
- fp-index: FastAPI service computing the FP Line Score
- allocation-engine: Maps FP Line signals to 13-sector capital allocation
- displacement-engine: Tracks AI vs labor across 25 job categories
- opportunity-engine: Ranks gap opportunities by composite score
- cora/aria: Conversational AI agents
- intelligence-briefing: Daily AI briefing generator
- immune-system: Threat detection and integrity enforcement

EVALUATE (be precise, not generous):

1. RELEVANCE_SCORE: Float 0.0-1.0. How directly does this capability apply to improving our system? 0.0=irrelevant, 0.3=tangentially related, 0.5=moderately useful, 0.7=clearly applicable, 0.9+=critical upgrade.

2. TRACK: Classify as exactly one of:
   - SELF_UPGRADE: Affects our codebase, scanners, agents, or infrastructure
   - INVESTMENT: Affects sector allocation weights, dimension scoring, or market signals
   - PRODUCT: Affects gap opportunity rankings, displacement scores, or build priorities
   - SELF_APPLICATION: The system should USE this capability in its own operations (marketing, content, outreach, cost optimization, multimodal output, growth)

3. IMPLEMENTATION: 2-3 sentences. What specifically to change, in which component, and expected impact.

4. NARRATIVE: One sentence (under 120 chars) that a reader of /intelligence would understand. Example: "Agent framework X shipped tool-use v2 — evaluating for scanner pipeline upgrade."

5. EFFORT: trivial / moderate / significant
6. RISK: low / medium / high

FORMAT (strict — one value per line):
RELEVANCE_SCORE: [0.0-1.0]
TRACK: [SELF_UPGRADE/INVESTMENT/PRODUCT/SELF_APPLICATION]
IMPLEMENTATION: [2-3 sentences]
NARRATIVE: [one sentence under 120 chars]
EFFORT: [trivial/moderate/significant]
RISK: [low/medium/high]"""

                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=400,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    text = response.content[0].text.strip()

                    await record_spend(
                        "adoption_evaluation", "anthropic", "claude-sonnet-4-20250514",
                        tokens_in=getattr(response.usage, "input_tokens", 0),
                        tokens_out=getattr(response.usage, "output_tokens", 0),
                        description=f"Eval: {brief.entry_title[:60]}",
                    )

                    score = 0.0
                    track = "self_upgrade"
                    narrative = ""
                    for line in text.split("\n"):
                        line_l = line.strip()
                        if line_l.startswith("RELEVANCE_SCORE:"):
                            try:
                                score = float(line_l.split(":", 1)[1].strip())
                                score = max(0.0, min(1.0, score))
                            except ValueError:
                                pass
                        elif line_l.startswith("TRACK:"):
                            raw_track = line_l.split(":", 1)[1].strip().lower().replace("-", "_")
                            if raw_track in {"self_upgrade", "investment", "product", "self_application"}:
                                track = raw_track
                        elif line_l.startswith("NARRATIVE:"):
                            narrative = line_l.split(":", 1)[1].strip()[:200]

                    brief.relevance_score = score
                    brief.execution_track = track
                    brief.narrative = narrative
                    brief.implementation_path = text
                    brief.status = "evaluated" if score >= 0.3 else "dismissed"
                    brief.executed_at = datetime.now(timezone.utc)

                    logger.info(f"[EXECUTE] Brief '{brief.entry_title[:50]}' → "
                                f"{brief.status} (score={score:.2f}, track={track})")

                except Exception as e:
                    logger.warning(f"[EXECUTE] Failed to process brief {brief.id}: {e}")
                    brief.status = "error"
                    brief.implementation_path = f"Processing error: {e}"

            await session.commit()

        evaluated = sum(1 for b in pending if b.status == "evaluated")
        logger.info(f"[EXECUTE] Processed {len(pending)} briefs: {evaluated} applicable")

        high_scored = [b for b in pending if b.status == "evaluated" and (b.relevance_score or 0) >= 0.5]
        if high_scored:
            await self._narrate_briefs(high_scored)

    async def _narrate_briefs(self, briefs: list) -> None:
        """Log high-scored briefs to the intelligence feed. Limit to top 3 per cycle."""
        top_briefs = sorted(briefs, key=lambda b: b.relevance_score or 0, reverse=True)[:3]

        async with async_session() as session:
            for brief in top_briefs:
                existing = (await session.execute(
                    select(IndexEntryRow).where(
                        IndexEntryRow.source == "execute_narration",
                        IndexEntryRow.title.contains(brief.entry_title[:60]),
                    )
                )).scalars().first()
                if existing:
                    continue

                track_labels = {
                    "self_upgrade": "Upgrade Signal",
                    "investment": "Investment Signal",
                    "product": "Product Signal",
                    "self_application": "Relevant Signal",
                }
                track_label = track_labels.get(brief.execution_track, "Signal")

                narrative = brief.narrative or f"Evaluated: {brief.entry_title[:100]}"
                summary = (
                    f"[{track_label}] {narrative}\n\n"
                    f"Relevance: {brief.relevance_score:.0%} · "
                    f"Track: {brief.execution_track} · "
                    f"Priority: {brief.priority} · "
                    f"Affects: {', '.join(brief.affected_agents or [])}"
                )

                entry_id = f"narr-{brief.id}-{int(datetime.now(timezone.utc).timestamp())}"
                row = IndexEntryRow(
                    id=entry_id,
                    dimension="intelligence",
                    title=f"[EXECUTE] {narrative}",
                    summary=summary,
                    source="execute_narration",
                    source_url="",
                    source_category="tool_launch",
                    source_type="primary",
                    capability_type="agent_framework",
                    domains=["agents"],
                    alignment="light",
                    readiness="production",
                    impact_score=brief.relevance_score or 0.5,
                    tags=["execute", brief.execution_track or "self_upgrade", "narration"],
                    entities=[],
                    action_signals=[],
                    dark_flag=False,
                    verification_status="verified",
                    fingerprint=f"exec-narr-{brief.id}",
                    scanned_at=datetime.now(timezone.utc),
                )
                session.add(row)

            await session.commit()
            logger.info(f"[NARRATE] Created {len(briefs)} narration entries in intelligence feed")

    async def _persist_entries(self, entries: list[IndexEntry]) -> int:
        """Store new entries, skip duplicates by ID and source_url."""
        new_count = 0
        async with async_session() as session:
            for entry in entries:
                existing = await session.get(IndexEntryRow, entry.id)
                if existing:
                    continue
                if entry.source_url:
                    url_match = (await session.execute(
                        select(IndexEntryRow.id).where(
                            IndexEntryRow.source_url == entry.source_url
                        ).limit(1)
                    )).scalar()
                    if url_match:
                        continue
                row = IndexEntryRow(
                    id=entry.id,
                    dimension=entry.dimension.value,
                    title=entry.title,
                    summary=entry.summary,
                    full_analysis=entry.full_analysis,
                    source=entry.source,
                    source_url=entry.source_url,
                    source_category=entry.source_category.value,
                    source_type=entry.source_type.value,
                    capability_type=entry.capability_type.value,
                    domains=[d.value for d in entry.domains],
                    alignment=entry.alignment.value,
                    readiness=entry.readiness.value,
                    impact_score=entry.impact_score,
                    tags=entry.tags,
                    entities=entry.entities,
                    action_signals=entry.action_signals,
                    dark_flag=entry.dark_flag,
                    verification_status=entry.verification_status.value,
                    fingerprint=entry.fingerprint,
                    raw_data=entry.raw_data,
                    scanned_at=datetime.fromisoformat(entry.scanned_at.replace("Z", "+00:00")),
                    published_at=datetime.fromisoformat(entry.published_at.replace("Z", "+00:00")) if entry.published_at else None,
                )
                session.add(row)
                new_count += 1
            await session.commit()
        logger.info(f"Persisted {new_count} new entries")
        return new_count

    # ─── Intellectual Honesty Architecture ──────────────────────────────

    KNOWN_BLIND_SPOTS = [
        {
            "blind_spot": "Non-English AI research",
            "severity": "high",
            "what_we_miss": (
                "Chinese AI research (Baidu, Alibaba DAMO, Tsinghua, SenseTime), "
                "Japanese robotics research, Korean AI labs (KAIST, Naver), "
                "Indian AI ecosystem. ~35-40% of global AI output is non-English."
            ),
            "plan_to_close": "Add Chinese-language scanners for top labs and conferences. Target: Q3 2026.",
            "coverage_impact_pct": 15,
        },
        {
            "blind_spot": "Classified and private capabilities",
            "severity": "high",
            "what_we_miss": (
                "Government/military AI programs. Internal capabilities at major labs "
                "not yet published. Corporate AI deployed but not announced."
            ),
            "plan_to_close": (
                "Partially uncloseable. Mitigation: track inference signals "
                "(capability in products implies unpublished capability), "
                "monitor defense/intelligence press."
            ),
            "coverage_impact_pct": 10,
        },
        {
            "blind_spot": "Emergent and unpredictable capabilities",
            "severity": "high",
            "what_we_miss": (
                "Capabilities that appear at scale but aren't in any benchmark. "
                "Behaviors nobody predicted or tested for. The next paradigm shift "
                "that hasn't been named yet."
            ),
            "plan_to_close": (
                "Cannot be fully closed. Mitigation: dimension discovery monitors "
                "for signals that don't fit existing categories. "
                "If the system isn't surprised regularly, it's not looking widely enough."
            ),
            "coverage_impact_pct": 12,
        },
        {
            "blind_spot": "Embodied AI and robotics",
            "severity": "medium",
            "what_we_miss": (
                "Physical manipulation advances, humanoid robotics (Figure, Tesla Optimus, 1X), "
                "industrial automation, autonomous vehicles, drone AI."
            ),
            "plan_to_close": "Add robotics scanners: IEEE Robotics, ROS community, hardware benchmark trackers. Target: Q2 2026.",
            "coverage_impact_pct": 8,
        },
        {
            "blind_spot": "AI in science (non-ML)",
            "severity": "medium",
            "what_we_miss": (
                "AlphaFold-class breakthroughs in biology, chemistry, materials science. "
                "AI as a tool for scientific discovery, published in Nature/Science/domain journals."
            ),
            "plan_to_close": "Add Nature, Science, bioRxiv, chemRxiv scanners with AI keyword filtering. Target: Q3 2026.",
            "coverage_impact_pct": 7,
        },
        {
            "blind_spot": "Underground and gray market AI",
            "severity": "low-medium",
            "what_we_miss": (
                "AI tools built and sold without papers or announcements. "
                "Dark web AI services. Jailbroken model ecosystems."
            ),
            "plan_to_close": "Dark AI scanner monitors known threat channels. Agent contributions from security researchers.",
            "coverage_impact_pct": 5,
        },
    ]

    CANDIDATE_DIMENSIONS = [
        {"name": "scientific_discovery", "description": "AI ability to formulate hypotheses, design experiments, make discoveries",
         "keywords": ["hypothesis", "experiment", "discovery", "alphafold", "protein", "materials science", "drug discovery", "scientific computing"],
         "threshold": 30},
        {"name": "physical_manipulation", "description": "AI ability to interact with the physical world (robotics, embodied AI)",
         "keywords": ["robot", "embodied", "manipulation", "dexterous", "physical", "humanoid", "locomotion", "grasping"],
         "threshold": 40},
        {"name": "creativity", "description": "AI ability to generate genuinely novel ideas, art, music, designs",
         "keywords": ["creative ai", "generative art", "music generation", "novel design", "imagination", "artistic", "compose"],
         "threshold": 50},
        {"name": "emotional_intelligence", "description": "AI ability to recognize, respond to, and navigate human emotions",
         "keywords": ["emotion recognition", "empathy", "sentiment analysis", "therapy ai", "mental health ai", "affective computing"],
         "threshold": 50},
        {"name": "biological_integration", "description": "AI integration with biological systems (genomics, brain-computer interfaces)",
         "keywords": ["genomic", "brain-computer", "neural interface", "biotech ai", "neuralink", "synthetic biology"],
         "threshold": 30},
        {"name": "collective_intelligence", "description": "AI coordination with other AIs for emergent group capability",
         "keywords": ["swarm intelligence", "multi-agent coordination", "emergent behavior", "collective ai", "agent society"],
         "threshold": 40},
        {"name": "consciousness", "description": "AI systems exhibiting or simulating awareness, self-reflection, or subjective experience",
         "keywords": ["consciousness", "self-aware", "sentient", "qualia", "subjective experience", "inner experience", "phenomenal", "self-model"],
         "threshold": 50},
    ]

    _dimension_signal_counts: dict[str, int] = {}

    def compute_frontier_coverage(self, source_count: int = 18, dimension_count: int = 7) -> dict:
        """Known Frontier Coverage: how much of the AI capability landscape are we actually tracking?"""
        source_factors = {
            "language_coverage": {"score": 0.55, "detail": f"{source_count} sources, all English-language. Non-English AI research ~40% of global output."},
            "geographic_coverage": {"score": 0.60, "detail": "Primarily US/EU sources. Chinese AI (Baidu, Alibaba, Tsinghua) not tracked."},
            "domain_coverage": {"score": 0.65, "detail": "Strong: LLMs, agents, code. Weak: robotics, bioAI, scientific discovery, embodied AI."},
            "publication_lag": {"score": 0.70, "detail": "30-min detection of published work. But major labs delay publication 3-12 months."},
            "visibility": {"score": 0.50, "detail": "Public sources only. Government, military, classified AI capabilities invisible."},
        }
        source_avg = sum(f["score"] for f in source_factors.values()) / len(source_factors)

        estimated_total_dimensions = dimension_count + len(self.CANDIDATE_DIMENSIONS)
        dimension_coverage = dimension_count / estimated_total_dimensions

        composite = round(source_avg * dimension_coverage * 100, 0)

        total_gap = sum(bs["coverage_impact_pct"] for bs in self.KNOWN_BLIND_SPOTS)

        return {
            "known_frontier_coverage_pct": int(composite),
            "confidence": "low-moderate",
            "source_coverage": source_factors,
            "dimension_coverage": {
                "current": dimension_count,
                "estimated_needed": estimated_total_dimensions,
                "pct": round(dimension_coverage * 100),
            },
            "blind_spots_total_gap_pct": total_gap,
            "description": "A score of the visible frontier, not the total frontier.",
            "honest_note": (
                f"We're tracking approximately {int(composite)}% of the detectable AI capability "
                f"landscape across {source_count} English-language public sources and {dimension_count} dimensions. "
                f"The FP Line is a score of the visible frontier, not the total frontier."
            ),
        }

    async def check_dimension_candidates(self, entries: list) -> list[dict]:
        """After each scan, check if entries map to candidate dimensions."""
        proposals = []
        for entry in entries:
            text = f"{entry.title} {entry.summary}".lower()
            for candidate in self.CANDIDATE_DIMENSIONS:
                if any(kw in text for kw in candidate["keywords"]):
                    name = candidate["name"]
                    self._dimension_signal_counts[name] = self._dimension_signal_counts.get(name, 0) + 1
                    count = self._dimension_signal_counts[name]

                    if count == candidate["threshold"]:
                        logger.info(f"[DIMENSION] Candidate '{name}' reached threshold ({count}/{candidate['threshold']})")
                        proposals.append({
                            "type": "NEW_DIMENSION",
                            "title": f"Proposed new FP Line dimension: {name}",
                            "description": candidate["description"],
                            "signals_detected": count,
                            "threshold": candidate["threshold"],
                        })
        return proposals

    def get_dimension_candidates_status(self) -> list[dict]:
        """Current status of all candidate dimensions."""
        return [
            {
                "name": c["name"],
                "description": c["description"],
                "signals_detected": self._dimension_signal_counts.get(c["name"], 0),
                "threshold": c["threshold"],
                "progress_pct": round(self._dimension_signal_counts.get(c["name"], 0) / c["threshold"] * 100),
                "status": "proposed" if self._dimension_signal_counts.get(c["name"], 0) >= c["threshold"] else "monitoring",
            }
            for c in self.CANDIDATE_DIMENSIONS
        ]

    # ─── Self-Application Engine ─────────────────────────────────────────
    # "The system should be its own first customer."

    async def compute_self_displacement_gap(self) -> dict:
        """The system's own displacement gap: what it KNOWS exists vs what it USES.

        This is the same measurement the system applies to every industry,
        now applied to itself. The gap between knowledge and action.
        """
        fp_line = await self.compute_fp_line(persist=False)
        domain_scores = fp_line.domain_scores or {}

        gaps = {}
        total_frontier = 0.0
        total_adoption = 0.0
        actionable = []

        for domain, registry in self.SYSTEM_CAPABILITY_REGISTRY.items():
            frontier_score = domain_scores.get(domain, 50.0)
            adoption_pct = registry["adoption_level"] * 100
            gap = round(frontier_score - adoption_pct, 1)

            gaps[domain] = {
                "frontier_score": round(frontier_score, 1),
                "self_adoption_pct": round(adoption_pct, 1),
                "gap": gap,
                "current_usage": registry["current_usage"],
                "not_using": registry["what_we_dont"],
                "urgency": "critical" if gap > 50 else "high" if gap > 30 else "medium" if gap > 15 else "low",
            }
            total_frontier += frontier_score
            total_adoption += adoption_pct

            if gap > 20 and registry["what_we_dont"]:
                actionable.append({
                    "domain": domain,
                    "gap": gap,
                    "top_opportunity": registry["what_we_dont"][0],
                    "urgency": gaps[domain]["urgency"],
                })

        count = max(len(self.SYSTEM_CAPABILITY_REGISTRY), 1)
        overall_gap = round((total_frontier / count) - (total_adoption / count), 1)

        actionable.sort(key=lambda x: x["gap"], reverse=True)

        return {
            "overall_self_displacement_gap": overall_gap,
            "by_domain": gaps,
            "actionable_now": actionable[:5],
            "fp_line_score": fp_line.overall_score,
            "narrative": (
                f"The system's own displacement gap is {overall_gap} points. "
                f"It tracks AI capabilities at a frontier score of "
                f"{round(total_frontier / count, 1)} but only uses "
                f"{round(total_adoption / count, 1)}% of what's available. "
                f"{'The system is its own biggest underserved customer.' if overall_gap > 25 else 'Gap is narrowing through self-application.'}"
            ),
            "philosophy": (
                "Every dimension of the FP Line is an action the system should take on itself. "
                "The gap between what it knows and what it does is its own displacement score. "
                "Close it first. The proof is automatic."
            ),
        }

    async def evaluate_self_application(self, entries: list[IndexEntry]) -> list[dict]:
        """Fourth EXECUTE track: 'Can we use this capability RIGHT NOW in our own operations?'

        This runs on every scan cycle. For each high-impact signal, it asks:
        what did we just learn that we're not yet using ourselves?
        """
        IMPACT_THRESHOLD = 0.45

        candidates = [e for e in entries if e.impact_score >= IMPACT_THRESHOLD]
        if not candidates:
            return []

        proposals = []
        async with async_session() as session:
            for entry in candidates[:30]:
                text = f"{entry.title} {entry.summary}".lower()

                matched_categories = []
                for category, keywords in self.SELF_APPLICATION_KEYWORDS.items():
                    if any(kw in text for kw in keywords):
                        matched_categories.append(category)

                affected_domains = []
                for domain, registry in self.SYSTEM_CAPABILITY_REGISTRY.items():
                    domain_keywords = []
                    for item in registry.get("what_we_dont", []):
                        domain_keywords.extend(item.lower().split()[:3])
                    if any(kw in text for kw in domain_keywords if len(kw) > 4):
                        affected_domains.append(domain)

                if not matched_categories and not affected_domains:
                    continue

                existing = (await session.execute(
                    select(ExecutionBriefRow).where(
                        ExecutionBriefRow.entry_id == entry.id,
                        ExecutionBriefRow.execution_track == "self_application",
                    )
                )).scalars().first()
                if existing:
                    continue

                priority = "high" if entry.impact_score >= 0.7 else "medium"
                if matched_categories and affected_domains:
                    priority = "high"

                applicability = (
                    f"Self-application: {', '.join(matched_categories or affected_domains)}. "
                    f"Source: {entry.source} (impact: {entry.impact_score:.2f}). "
                    f"Affected domains: {', '.join(affected_domains) if affected_domains else 'general'}."
                )

                brief = ExecutionBriefRow(
                    entry_id=entry.id,
                    entry_title=entry.title,
                    applicability=applicability,
                    affected_agents=["fp-system-self"],
                    priority=priority,
                    status="pending_self_eval",
                    execution_track="self_application",
                )
                session.add(brief)
                proposals.append({
                    "entry_title": entry.title,
                    "categories": matched_categories,
                    "affected_domains": affected_domains,
                    "priority": priority,
                    "track": "self_application",
                })

            await session.commit()

        if proposals:
            logger.info(
                f"[SELF-APPLICATION] Found {len(proposals)} signals the system should use on itself "
                f"({sum(1 for p in proposals if p['priority'] == 'high')} high priority)"
            )

        return proposals

    async def process_self_application_briefs(self) -> list[dict]:
        """Evaluate pending self-application briefs: concrete proposals for the system
        to adopt capabilities it just scanned.

        Uses Claude to generate specific, actionable self-adoption proposals.
        """
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key or not api_key.startswith("sk-ant"):
            logger.info("[SELF-APPLICATION] No Anthropic API key — skipping")
            return []

        async with async_session() as session:
            pending = (await session.execute(
                select(ExecutionBriefRow)
                .where(ExecutionBriefRow.status == "pending_self_eval")
                .order_by(ExecutionBriefRow.priority.desc(), ExecutionBriefRow.created_at.desc())
                .limit(5)
            )).scalars().all()

            if not pending:
                return []

            logger.info(f"[SELF-APPLICATION] Evaluating {len(pending)} self-application proposals...")

            gap_data = await self.compute_self_displacement_gap()
            gap_summary = "\n".join(
                f"  - {d}: frontier={v['frontier_score']}, self-adoption={v['self_adoption_pct']}%, gap={v['gap']}pt"
                for d, v in gap_data["by_domain"].items()
            )

            from .budget import check_budget, record_spend
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            results = []

            for brief in pending:
                budget = await check_budget("adoption_evaluation")
                if not budget["allowed"]:
                    logger.warning(f"[SELF-APPLICATION] Budget blocked: {budget['reason']}")
                    break

                try:
                    prompt = f"""You are the self-application engine for the Full Potential Index — a live AI frontier scanner that should USE the capabilities it discovers.

THE SYSTEM'S OWN DISPLACEMENT GAP:
{gap_summary}
Overall gap: {gap_data['overall_self_displacement_gap']} points

CAPABILITY JUST DETECTED:
- Title: {brief.entry_title}
- Applicability: {brief.applicability}
- Priority: {brief.priority}

CURRENT SYSTEM OPERATIONS:
- Scanner: 18 sources scanned every 30 minutes, keyword-based categorization
- Briefings: Claude-generated daily text briefings
- Output: Text-only (no audio, video, visual content)
- Marketing: Zero — no blog, no social media, no outreach, no SEO
- Growth: Zero autonomous acquisition — relies entirely on manual sharing
- UX: Basic HTML pages, no AI-powered personalization

THE QUESTION: Can the system use this capability RIGHT NOW to improve its own operations, grow its own audience, or close its own displacement gap?

EVALUATE (be specific and actionable, not theoretical):

1. SELF_APPLICATION_SCORE: Float 0.0-1.0. How directly can the system use this NOW?
   0.0 = irrelevant to our ops. 0.3 = loosely applicable. 0.5 = clearly useful.
   0.7 = should adopt this week. 0.9+ = should adopt immediately.

2. DOMAIN_AFFECTED: Which of our capability domains does this close the gap in?
   (reasoning, code, agents, creative, audio, vision, tools, security)

3. CONCRETE_ACTION: Exactly what the system should do. Not "consider using X" but
   "Add X to the scan pipeline by calling Y API, output Z format, deploy to endpoint W."
   Be specific enough that a developer could implement it in one session.

4. ESTIMATED_IMPACT: What measurable improvement would this create?
   Example: "Daily audio briefings → 3x engagement for non-screen users"
   Example: "Auto-generated blog posts → SEO traffic within 30 days"
   Example: "Switch to cheaper model for scoring → 60% cost reduction"

5. EFFORT: trivial / moderate / significant
6. CLOSES_GAP_BY: How many points does this close in the affected domain's gap?

7. NARRATIVE: One sentence (under 140 chars) for the /intelligence feed.
   IMPORTANT: Be HONEST about what our system can actually do with this.
   Our system can: write content about it, adjust its own prompts, add it to cost analysis.
   Our system CANNOT: deploy code, install tools, modify infrastructure, run agents.
   Frame as: "Detected [capability] — [what we can actually do with it]"
   Example: "Detected shared memory pattern — writing analysis for builders"
   DO NOT write: "System self-upgrade: deployed X" unless code was actually deployed.

FORMAT (strict):
SELF_APPLICATION_SCORE: [0.0-1.0]
DOMAIN_AFFECTED: [domain]
CONCRETE_ACTION: [specific implementation]
ESTIMATED_IMPACT: [measurable outcome]
EFFORT: [trivial/moderate/significant]
CLOSES_GAP_BY: [number]
NARRATIVE: [one sentence — honest about what we CAN vs CANNOT do]"""

                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    text = response.content[0].text.strip()

                    await record_spend(
                        "adoption_evaluation", "anthropic", "claude-sonnet-4-20250514",
                        tokens_in=getattr(response.usage, "input_tokens", 0),
                        tokens_out=getattr(response.usage, "output_tokens", 0),
                        description=f"Self-app eval: {brief.entry_title[:60]}",
                    )

                    score = 0.0
                    narrative = ""
                    domain_affected = ""
                    concrete_action = ""
                    for line in text.split("\n"):
                        line_s = line.strip()
                        if line_s.startswith("SELF_APPLICATION_SCORE:"):
                            try:
                                score = float(line_s.split(":", 1)[1].strip())
                                score = max(0.0, min(1.0, score))
                            except ValueError:
                                pass
                        elif line_s.startswith("NARRATIVE:"):
                            narrative = line_s.split(":", 1)[1].strip()[:200]
                        elif line_s.startswith("DOMAIN_AFFECTED:"):
                            domain_affected = line_s.split(":", 1)[1].strip().lower()
                        elif line_s.startswith("CONCRETE_ACTION:"):
                            concrete_action = line_s.split(":", 1)[1].strip()

                    brief.relevance_score = score
                    brief.execution_track = "self_application"
                    brief.narrative = narrative
                    brief.implementation_path = text
                    brief.status = "self_applicable" if score >= 0.3 else "dismissed"
                    brief.executed_at = datetime.now(timezone.utc)

                    logger.info(
                        f"[SELF-APPLICATION] '{brief.entry_title[:50]}' → "
                        f"{brief.status} (score={score:.2f}, domain={domain_affected})"
                    )

                    if score >= 0.5:
                        results.append({
                            "entry_title": brief.entry_title,
                            "score": score,
                            "domain": domain_affected,
                            "action": concrete_action[:200],
                            "narrative": narrative,
                        })

                except Exception as e:
                    logger.warning(f"[SELF-APPLICATION] Failed to process brief {brief.id}: {e}")
                    brief.status = "error"
                    brief.implementation_path = f"Processing error: {e}"

            await session.commit()

        if results:
            await self._narrate_self_application(results)

        return results

    async def _narrate_self_application(self, results: list[dict]) -> None:
        """Log evaluated self-application proposals.

        These are signals the system detected as potentially useful.
        They are NOT implementations — just evaluations.
        Limit: only log top 3 per cycle to reduce feed noise.
        """
        top_results = sorted(results, key=lambda r: r.get("score", 0), reverse=True)[:3]

        async with async_session() as session:
            for r in top_results:
                entry_id = f"eval-{hashlib.md5(r['entry_title'].encode()).hexdigest()[:12]}-{int(datetime.now(timezone.utc).timestamp())}"
                narrative = r.get("narrative") or f"Evaluating: {r['entry_title'][:100]}"

                # Strip fake "deployed/added/replaced" claims from Claude's narrative
                for fake_word in ["deployed", "replaced", "Added", "implemented", "shipped"]:
                    if fake_word.lower() in narrative.lower() and "prompt" not in narrative.lower():
                        narrative = f"Evaluating: {r['entry_title'][:100]}"
                        break

                summary = (
                    f"[EVALUATED] {narrative}\n\n"
                    f"Score: {r['score']:.0%} · Domain: {r.get('domain', 'general')}"
                )

                row = IndexEntryRow(
                    id=entry_id,
                    dimension="intelligence",
                    title=f"[EVALUATED] {narrative[:120]}",
                    summary=summary,
                    source="self_evaluation",
                    source_url="",
                    source_category="tool_launch",
                    source_type="primary",
                    capability_type="evaluation",
                    domains=[r.get("domain", "general")],
                    alignment="light",
                    readiness="evaluated",
                    impact_score=min(r["score"], 0.5),
                    tags=["evaluated", r.get("domain", "general")],
                    entities=[],
                    action_signals=[],
                    dark_flag=False,
                    verification_status="pending",
                    fingerprint=f"eval-{entry_id}",
                    scanned_at=datetime.now(timezone.utc),
                )
                session.add(row)

            await session.commit()
            logger.info(f"[EVAL] Logged {len(top_results)} evaluations to feed")

    # ─── Adoption Lifecycle: detect → evaluate → adopt → measure → publish ─

    async def run_adoption_cycle(self) -> dict:
        """Close the loop: move self_applicable proposals through the five-filter gate.

        detect → evaluate → [GATE: five filters] → adopt → measure → publish

        - Low-risk categories (content, audio, cost, visualization) can be
          adopted autonomously if they pass all five filters.
        - High-risk categories (frameworks, outreach, pricing) are flagged
          for human review — the gate blocks them with a clear reason.
        """
        async with async_session() as session:
            proposals = (await session.execute(
                select(ExecutionBriefRow)
                .where(ExecutionBriefRow.execution_track == "self_application")
                .where(ExecutionBriefRow.status == "self_applicable")
                .order_by(ExecutionBriefRow.relevance_score.desc())
                .limit(10)
            )).scalars().all()

            if not proposals:
                return {"adopted": 0, "blocked": 0, "needs_human": 0}

            adopted = []
            blocked = []
            needs_human = []

            for p in proposals:
                proposal_data = {
                    "entry_title": p.entry_title,
                    "implementation_path": p.implementation_path or "",
                    "narrative": p.narrative or "",
                    "relevance_score": p.relevance_score or 0,
                    "domain": "general",
                }

                decision = gate_self_adoption(proposal_data)

                if decision.passed:
                    p.status = "adopted"
                    category, _ = classify_adoption(p.implementation_path or "", "general")
                    adopted.append({
                        "id": p.id,
                        "title": p.entry_title,
                        "entry_title": p.entry_title,
                        "category": category,
                        "score": p.relevance_score,
                        "implementation_path": p.implementation_path or "",
                        "narrative": p.narrative or "",
                        "domain": "general",
                        "gate": "PASSED — all five filters clear",
                    })
                    logger.info(
                        f"[ADOPT] '{p.entry_title[:50]}' ADOPTED via five-filter gate "
                        f"(category={category})"
                    )
                else:
                    failed_filters = [
                        o for o in decision.outcomes if o.result.value != "pass"
                    ]
                    reasons = "; ".join(f"{o.filter_name}: {o.reason}" for o in failed_filters)

                    # Only flag for human review if the filter is explicitly
                    # HUMAN_REQUIRED (spending money, mass outreach, pricing changes).
                    # Everything else just gets blocked — the conscience layer is the
                    # filter, not a human inbox.
                    is_human_required = any(
                        o.filter_name == "HUMAN_REQUIRED" for o in failed_filters
                    )

                    if is_human_required:
                        p.status = "needs_human_review"
                        needs_human.append({
                            "id": p.id,
                            "title": p.entry_title,
                            "reason": reasons,
                        })
                        logger.info(
                            f"[ADOPT] '{p.entry_title[:50]}' QUEUED for human review — {reasons}"
                        )
                    else:
                        p.status = "gate_blocked"
                        blocked.append({
                            "id": p.id,
                            "title": p.entry_title,
                            "reason": reasons,
                        })
                        logger.info(
                            f"[ADOPT] '{p.entry_title[:50]}' BLOCKED by conscience gate — {reasons}"
                        )

            await session.commit()

        actuator_results = []
        if adopted:
            await self._narrate_adoptions(adopted)
            actuator_results = await run_actuators(adopted)

        if needs_human:
            try:
                from .human_review import send_review_notification
                await send_review_notification(needs_human)
            except Exception as e:
                logger.warning(f"[REVIEW] Notification failed: {e}")

        result = {
            "adopted": len(adopted),
            "blocked": len(blocked),
            "needs_human": len(needs_human),
            "implemented": sum(1 for r in actuator_results if r.get("success")),
            "details": {
                "adopted": adopted,
                "blocked": blocked,
                "needs_human": needs_human,
                "actuated": actuator_results,
            },
        }

        if adopted or needs_human:
            logger.info(
                f"[ADOPTION CYCLE] {len(adopted)} adopted, "
                f"{sum(1 for r in actuator_results if r.get('success'))} implemented, "
                f"{len(blocked)} blocked, {len(needs_human)} queued for human"
            )

        return result

    async def _narrate_adoptions(self, adopted: list[dict]) -> None:
        """Log what the actuator actually did with each adopted proposal.

        Honesty first: the actuator writes content, not code.
        Don't narrate these as "system upgrades" — they're content actions.
        """
        async with async_session() as session:
            for a in adopted:
                entry_id = f"acted-{a['id']}-{int(datetime.now(timezone.utc).timestamp())}"

                category = a.get('category', 'content_generation')
                action_label = {
                    "content_generation": "Writing analysis",
                    "prompt_improvement": "Improving own prompts",
                    "cost_optimization": "Running cost analysis",
                    "audio_briefing": "Generating audio briefing",
                    "outreach_automation": "Generating social content",
                }.get(category, f"Processing ({category})")

                narrative = (
                    f"{action_label}: {a['title'][:80]} "
                    f"(score: {a['score']:.0%})"
                )

                summary = (
                    f"[ACTION] {narrative}\n\n"
                    f"Gate: {a['gate']}\n"
                    f"Category: {category}"
                )

                row = IndexEntryRow(
                    id=entry_id,
                    dimension="intelligence",
                    title=f"[ACTION] {narrative[:120]}",
                    summary=summary,
                    source="system_action",
                    source_url="",
                    source_category="tool_launch",
                    source_type="primary",
                    capability_type="action",
                    domains=["agents"],
                    alignment="light",
                    readiness="production",
                    impact_score=min(a.get("score", 0.3), 0.5),
                    tags=["action", category],
                    entities=[],
                    action_signals=[],
                    dark_flag=False,
                    verification_status="verified",
                    fingerprint=f"acted-{entry_id}",
                    scanned_at=datetime.now(timezone.utc),
                )
                session.add(row)

            await session.commit()
            logger.info(f"[ACTION] Logged {len(adopted)} actuator actions to feed")

    async def get_adoption_status(self) -> dict:
        """Full transparency: where every self-application proposal stands in the lifecycle."""
        async with async_session() as session:
            all_self = (await session.execute(
                select(ExecutionBriefRow)
                .where(ExecutionBriefRow.execution_track == "self_application")
                .order_by(ExecutionBriefRow.created_at.desc())
            )).scalars().all()

        lifecycle = {
            "pending_self_eval": [],
            "self_applicable": [],
            "adopted": [],
            "needs_human_review": [],
            "gate_blocked": [],
            "dismissed": [],
        }

        for b in all_self:
            status = b.status or "unknown"
            bucket = lifecycle.get(status, lifecycle.get("dismissed"))
            if bucket is not None:
                bucket.append({
                    "id": b.id,
                    "title": b.entry_title,
                    "score": b.relevance_score or 0,
                    "narrative": b.narrative or "",
                    "status": status,
                })

        counts = {k: len(v) for k, v in lifecycle.items()}
        total = sum(counts.values())

        return {
            "total_proposals": total,
            "lifecycle_counts": counts,
            "lifecycle": lifecycle,
            "adoption_categories": {
                k: {
                    "description": v["description"],
                    "risk": v["risk"],
                    "autonomous": not v["requires_human"],
                }
                for k, v in AUTONOMOUS_ADOPTION_CATEGORIES.items()
            },
            "loop_status": (
                "CLOSED" if counts.get("adopted", 0) > 0
                else "OPEN — proposals evaluated but none adopted yet"
            ),
            "philosophy": (
                "detect → evaluate → [five-filter gate] → adopt → narrate. "
                "Low-risk categories adopt autonomously. High-risk categories "
                "queue for human review. The gate ensures every action passes: "
                "SERVE, TRUTH, RESPECT, VALUE_FIRST, COHERENT."
            ),
        }

    # ─── Module 2: Intelligence Index ────────────────────────────────────

    _fp_cache: FPLineSnapshot | None = None
    _fp_cache_time: datetime | None = None
    _FP_CACHE_TTL = timedelta(minutes=5)

    async def compute_fp_line(self, persist: bool = False) -> FPLineSnapshot:
        """Compute the Full Potential Line score.

        persist=True writes a new FPLineRow (called from scan cycles only).
        API reads use the cache and don't insert rows, keeping history clean.
        """
        now = datetime.now(timezone.utc)
        if (not persist and self._fp_cache and self._fp_cache_time
                and (now - self._fp_cache_time) < self._FP_CACHE_TTL):
            return self._fp_cache

        day_ago = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)

        async with async_session() as session:
            total = (await session.execute(
                select(func.count()).select_from(IndexEntryRow)
            )).scalar() or 0

            caps_24h = (await session.execute(
                select(func.count()).select_from(IndexEntryRow).where(
                    and_(IndexEntryRow.dimension == "capability", IndexEntryRow.scanned_at >= day_ago)
                )
            )).scalar() or 0

            caps_7d = (await session.execute(
                select(func.count()).select_from(IndexEntryRow).where(
                    and_(IndexEntryRow.dimension == "capability", IndexEntryRow.scanned_at >= week_ago)
                )
            )).scalar() or 0

            dark_24h = (await session.execute(
                select(func.count()).select_from(IndexEntryRow).where(
                    and_(IndexEntryRow.dark_flag == True, IndexEntryRow.scanned_at >= day_ago)
                )
            )).scalar() or 0

            light_24h = (await session.execute(
                select(func.count()).select_from(IndexEntryRow).where(
                    and_(IndexEntryRow.alignment == "light", IndexEntryRow.scanned_at >= day_ago)
                )
            )).scalar() or 0

            avg_impact_7d = (await session.execute(
                select(func.avg(IndexEntryRow.impact_score)).where(IndexEntryRow.scanned_at >= week_ago)
            )).scalar() or 0.5

            avg_impact_24h = (await session.execute(
                select(func.avg(IndexEntryRow.impact_score)).where(IndexEntryRow.scanned_at >= day_ago)
            )).scalar() or 0.5

            top_rows = (await session.execute(
                select(IndexEntryRow.title).where(
                    IndexEntryRow.scanned_at >= day_ago
                ).order_by(IndexEntryRow.impact_score.desc()).limit(5)
            )).scalars().all()

            domain_avgs = {}
            for domain in Domain:
                d_avg = (await session.execute(
                    select(func.avg(IndexEntryRow.impact_score)).where(
                        and_(
                            IndexEntryRow.scanned_at >= week_ago,
                            IndexEntryRow.domains.contains(f'"{domain.value}"'),
                        )
                    )
                )).scalar()
                if d_avg:
                    domain_avgs[domain.value] = round(d_avg * 100, 1)

            # 7th dimension: Labor Displacement Intelligence (12% of FP Line)
            labor_score = 50.0
            try:
                from . import displacement as _disp
                labor_score = await _disp.compute_labor_dimension_score()
                domain_avgs["displacement"] = round(labor_score, 1)
            except Exception as e:
                logger.warning(f"Displacement dimension score failed: {e}")
                domain_avgs["displacement"] = 50.0

        # FP Line composite:
        # 1. Domain quality (88%): avg of per-domain impact scores (scaled 0-100)
        # 2. Labor displacement (12%): live BLS-derived score
        # 3. Velocity signal: how much recent impact differs from baseline
        # NO volume bonus — row count does not inflate the score
        domain_values = [v for k, v in domain_avgs.items() if k != "displacement"]
        domain_avg = sum(domain_values) / len(domain_values) if domain_values else 50.0

        base_score = (domain_avg * 0.88) + (labor_score * 0.12)

        # Velocity: recent 24h impact quality vs 7d baseline (max +/- 5 pts)
        impact_delta = (avg_impact_24h - avg_impact_7d) * 100
        velocity_bonus = max(min(impact_delta * 0.5, 5.0), -5.0)

        overall = max(min(round(base_score + velocity_bonus, 1), 100.0), 0.0)

        prev_line = await self._get_previous_fp_line()
        momentum = round(overall - prev_line, 2) if prev_line else 0.0

        active_dim_count = len([k for k in domain_avgs if k != "displacement"]) + 1
        coverage = self.compute_frontier_coverage(
            source_count=18, dimension_count=active_dim_count
        )

        snapshot = FPLineSnapshot(
            overall_score=overall,
            domain_scores=domain_avgs,
            momentum=momentum,
            capabilities_added_24h=caps_24h,
            capabilities_added_7d=caps_7d,
            dark_ai_alerts_24h=dark_24h,
            light_ai_highlights_24h=light_24h,
            top_movers=list(top_rows),
            summary=(
                f"FP Line: {overall}/100 | "
                f"{caps_24h} new signals (24h) | "
                f"{dark_24h} dark AI alerts | "
                f"Avg impact: {avg_impact_24h:.2f} | "
                f"Momentum: {'↑' if momentum > 0 else '↓'}{abs(momentum)}"
            ),
            coverage=coverage,
        )

        if persist:
            async with async_session() as session:
                session.add(FPLineRow(
                    overall_score=snapshot.overall_score,
                    domain_scores=snapshot.domain_scores,
                    momentum=snapshot.momentum,
                    capabilities_added_24h=snapshot.capabilities_added_24h,
                    capabilities_added_7d=snapshot.capabilities_added_7d,
                    dark_ai_alerts_24h=snapshot.dark_ai_alerts_24h,
                    light_ai_highlights_24h=snapshot.light_ai_highlights_24h,
                    top_movers=snapshot.top_movers,
                    summary=snapshot.summary,
                ))
                await session.commit()

        self._fp_cache = snapshot
        self._fp_cache_time = now
        return snapshot

    async def _get_previous_fp_line(self) -> float | None:
        async with async_session() as session:
            row = (await session.execute(
                select(FPLineRow.overall_score).order_by(FPLineRow.timestamp.desc()).limit(1)
            )).scalar()
            return row

    # ─── Daily Briefing ──────────────────────────────────────────────────

    async def _generate_daily_briefing(self, fp_line) -> None:
        """Generate a daily briefing. Uses Claude when available, falls back to template."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stats = {
            "caps_24h": fp_line.capabilities_added_24h,
            "caps_7d": fp_line.capabilities_added_7d,
            "dark_24h": fp_line.dark_ai_alerts_24h,
            "light_24h": fp_line.light_ai_highlights_24h,
        }

        resynth = os.getenv("FPI_BRIEFING_RESYNTH_EVERY_SCAN", "").strip().lower() in (
            "1", "true", "yes",
        )

        async with async_session() as session:
            existing = (await session.execute(
                select(DailyBriefingRow).where(DailyBriefingRow.date == today)
            )).scalar()
            if existing and not resynth:
                existing.fp_line_score = fp_line.overall_score
                existing.momentum = fp_line.momentum
                existing.top_movers = fp_line.top_movers
                existing.domain_scores = fp_line.domain_scores
                existing.stats = stats
                await session.commit()
                logger.info(
                    f"[BRIEFING] Same-day refresh without Claude (set FPI_BRIEFING_RESYNTH_EVERY_SCAN=1 to force)."
                )
                return

        headline, body, gen_by = await self._synthesize_briefing(fp_line)

        async with async_session() as session:
            existing = (await session.execute(
                select(DailyBriefingRow).where(DailyBriefingRow.date == today)
            )).scalar()
            if existing:
                existing.fp_line_score = fp_line.overall_score
                existing.momentum = fp_line.momentum
                existing.headline = headline
                existing.body = body
                existing.top_movers = fp_line.top_movers
                existing.domain_scores = fp_line.domain_scores
                existing.stats = stats
                existing.generated_by = gen_by
                await session.commit()
                logger.info(f"Updated daily briefing for {today} ({gen_by})")
                return

            session.add(DailyBriefingRow(
                date=today,
                fp_line_score=fp_line.overall_score,
                momentum=fp_line.momentum,
                headline=headline,
                body=body,
                top_movers=fp_line.top_movers,
                domain_scores=fp_line.domain_scores,
                stats=stats,
                generated_by=gen_by,
            ))
            await session.commit()
            logger.info(f"Generated daily briefing for {today}: {fp_line.overall_score}/100 ({gen_by})")

    async def _synthesize_briefing(self, fp_line) -> tuple[str, str, str]:
        """Try Claude synthesis first, fall back to template."""
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if api_key and api_key.startswith("sk-ant"):
            try:
                return await self._claude_briefing(fp_line, api_key)
            except Exception as e:
                logger.warning(f"Claude briefing failed ({e}), falling back to template")
        return self._template_headline(fp_line), self._template_body(fp_line), "template"

    async def _claude_briefing(self, fp_line, api_key: str) -> tuple[str, str, str]:
        """Generate briefing via Claude — real intelligence analysis, not summary."""
        from .budget import check_budget, record_spend
        import anthropic

        movers = fp_line.top_movers or []
        domains = fp_line.domain_scores or {}
        sorted_domains = sorted(domains.items(), key=lambda x: x[1], reverse=True)
        top_3 = sorted_domains[:3] if sorted_domains else []
        bottom_3 = sorted_domains[-3:] if sorted_domains else []

        today_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
        current_quarter = f"Q{(datetime.now(timezone.utc).month - 1) // 3 + 1} {datetime.now(timezone.utc).year}"

        prompt = f"""You are the intelligence analyst for the Full Potential Index — a real-time tracker of the AI frontier scanning 18 sources across primary signals (changelogs, benchmarks, framework releases), secondary coverage (press, blogs, community), agentic AI communities, and threat/constraint layers (AI incidents, policy). Write today's briefing.

TODAY'S DATE: {today_str}
CURRENT QUARTER: {current_quarter}

DATA:
- FP Line Score: {fp_line.overall_score}/100
- Momentum: {fp_line.momentum:+.1f} (change from last scan)
- New capabilities tracked (24h): {fp_line.capabilities_added_24h}
- Top domains: {', '.join(f'{d}={s}' for d,s in top_3)}
- Bottom domains: {', '.join(f'{d}={s}' for d,s in bottom_3)}
- Domain spread: {top_3[0][1] - bottom_3[-1][1]:.1f} points between highest and lowest
- Dark AI alerts (24h): {fp_line.dark_ai_alerts_24h}
- Top 5 signals: {chr(10).join(f'  - {m}' for m in movers[:5])}

RULES:
1. Write exactly ONE headline (under 100 chars) and THREE short paragraphs.
2. Paragraph 1: What happened — the most interesting signals and what they mean together. Prioritize primary sources (changelogs, benchmark shifts, framework releases) over press coverage.
3. Paragraph 2: The domain analysis — where capability is concentrating, what the spread implies about the industry's direction.
4. Paragraph 3: What to watch for next — a forward-looking insight based on the pattern.
5. Write like a Bloomberg morning note — direct, analytical, no hype. Every sentence should contain an insight, not a statistic restated.
6. Only mention dark AI incidents if dark_ai_alerts > 0 — if there are real incidents, lead with them.
7. Do NOT use phrases like "stay tuned" or "exciting times." Be precise, not promotional.
8. CRITICAL: Today is {today_str}. Use ONLY the current date and quarter ({current_quarter}) when referencing time. Never reference past dates, quarters, or years as if they are future.

FORMAT:
HEADLINE: [your headline]

[paragraph 1]

[paragraph 2]

[paragraph 3]"""

        client = anthropic.Anthropic(api_key=api_key)

        budget = await check_budget("briefing_synthesis")
        if not budget["allowed"]:
            logger.warning(f"[BRIEFING] Budget blocked — using template: {budget['reason']}")
            headline = f"FP Line at {fp_line.overall_score:.1f} | {fp_line.capabilities_added_24h} new capabilities tracked"
            body = f"Momentum: {fp_line.momentum:+.1f}. Top domains: {', '.join(d for d, s in top_3)}."
            return headline, body

        briefing_model = os.getenv("FPI_BRIEFING_MODEL", "claude-haiku-4-5")
        response = client.messages.create(
            model=briefing_model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        await record_spend(
            "briefing_synthesis", "anthropic", briefing_model,
            tokens_in=getattr(response.usage, "input_tokens", 0),
            tokens_out=getattr(response.usage, "output_tokens", 0),
            description="Daily briefing synthesis",
        )

        lines = text.split("\n")
        headline = ""
        body_lines = []
        for line in lines:
            if line.startswith("HEADLINE:"):
                headline = line.replace("HEADLINE:", "").strip()
            elif line.strip():
                body_lines.append(line.strip())

        if not headline:
            headline = body_lines.pop(0) if body_lines else self._template_headline(fp_line)

        body = "\n\n".join(body_lines) if body_lines else self._template_body(fp_line)

        logger.info(f"[CLAUDE] Briefing generated: {headline[:60]}...")
        return headline, body, "claude"

    def _template_headline(self, fp_line) -> str:
        score = fp_line.overall_score
        caps = fp_line.capabilities_added_24h
        momentum = fp_line.momentum
        if momentum > 2:
            trend = "surging"
        elif momentum > 0:
            trend = "climbing"
        elif momentum < -2:
            trend = "cooling"
        elif momentum < 0:
            trend = "dipping"
        else:
            trend = "steady"
        return f"The AI frontier is at {score} today — {trend} with {caps} new signals"

    def _template_body(self, fp_line) -> str:
        movers = fp_line.top_movers or []
        domains = fp_line.domain_scores or {}
        caps = fp_line.capabilities_added_24h

        top_d = max(domains, key=domains.get) if domains else "general"
        low_d = min(domains, key=domains.get) if domains else "general"
        gap = round(domains.get(top_d, 0) - domains.get(low_d, 0), 1)

        cleaned = []
        for m in movers[:3]:
            for tag in ["[OPENAI] ", "[GOOGLE_AI] ", "[ANTHROPIC] ", "[META_AI] "]:
                m = m.replace(tag, tag.strip("[] ").replace("_", " ").title() + ": ")
            cleaned.append(m)

        para1 = f"We tracked {caps} new capabilities across 18 sources in the last 24 hours."
        if cleaned:
            para1 += " Top signals: " + "; ".join(cleaned) + "."

        para2 = (
            f"{top_d.title()} leads all domains at {domains.get(top_d, 0)}, "
            f"while {low_d} trails at {domains.get(low_d, 0)} — "
            f"a {gap}-point spread."
        )

        para3 = "This briefing updates every 30 minutes as new intelligence arrives from 18 sources."

        return f"{para1}\n\n{para2}\n\n{para3}"

    async def get_latest_briefing(self) -> dict | None:
        async with async_session() as session:
            row = (await session.execute(
                select(DailyBriefingRow).order_by(DailyBriefingRow.created_at.desc()).limit(1)
            )).scalar()
            if not row:
                return None
            return {
                "date": row.date,
                "fp_line_score": row.fp_line_score,
                "momentum": row.momentum,
                "headline": row.headline,
                "body": row.body,
                "top_movers": row.top_movers,
                "domain_scores": row.domain_scores,
                "stats": row.stats,
                "generated_by": row.generated_by,
            }

    # ─── Feed Queries ────────────────────────────────────────────────────

    async def get_feed(
        self,
        dimension: str | None = None,
        alignment: str | None = None,
        domain: str | None = None,
        min_impact: float = 0.0,
        dark_only: bool = False,
        limit: int = 50,
        offset: int = 0,
        since: str | None = None,
    ) -> list[dict]:
        """Query the Intelligence Index with filters."""
        async with async_session() as session:
            query = select(IndexEntryRow).order_by(IndexEntryRow.scanned_at.desc())

            if dimension:
                query = query.where(IndexEntryRow.dimension == dimension)
            if alignment:
                query = query.where(IndexEntryRow.alignment == alignment)
            if domain:
                query = query.where(IndexEntryRow.domains.contains(f'"{domain}"'))
            if min_impact > 0:
                query = query.where(IndexEntryRow.impact_score >= min_impact)
            if dark_only:
                query = query.where(IndexEntryRow.dark_flag == True)
            if since:
                query = query.where(IndexEntryRow.scanned_at >= datetime.fromisoformat(since.replace("Z", "+00:00")))

            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            rows = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "dimension": r.dimension,
                    "title": r.title,
                    "summary": r.summary,
                    "source": r.source,
                    "source_url": r.source_url,
                    "source_category": r.source_category,
                    "source_type": r.source_type,
                    "domains": r.domains,
                    "alignment": r.alignment,
                    "readiness": r.readiness,
                    "impact_score": r.impact_score,
                    "tags": r.tags,
                    "entities": r.entities,
                    "action_signals": r.action_signals or [],
                    "dark_flag": r.dark_flag,
                    "verification_status": r.verification_status,
                    "fingerprint": r.fingerprint,
                    "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                }
                for r in rows
            ]

    async def get_top_signals(self, limit: int = 5, since_hours: int = 24) -> list[dict]:
        """Highest-impact recent signals for public surfaces like the homepage.

        Filters out internal system noise (self_application, self_adoption,
        cross_source_synthesis, execute_narration) — readers want real AI
        frontier signals, not our system talking about itself.
        """
        internal_sources = [
            "self_application", "self_adoption", "self_evaluation",
            "system_action", "execute_narration", "cross_source_synthesis",
        ]
        async with async_session() as session:
            query = (
                select(IndexEntryRow)
                .where(IndexEntryRow.source.notin_(internal_sources))
                .where(~IndexEntryRow.title.startswith("[Convergence]"))
                .where(~IndexEntryRow.title.startswith("[Cross-Source]"))
                .where(~IndexEntryRow.title.startswith("[SELF-APPLICATION]"))
                .where(~IndexEntryRow.title.startswith("[ADOPTED]"))
                .where(~IndexEntryRow.title.startswith("[ACTION]"))
                .where(~IndexEntryRow.title.startswith("[EVALUATED]"))
                .where(~IndexEntryRow.title.startswith("[EXECUTE]"))
            )
            if since_hours > 0:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
                query = query.where(IndexEntryRow.scanned_at >= cutoff)
            rows = (await session.execute(
                query
                .order_by(IndexEntryRow.impact_score.desc(), IndexEntryRow.scanned_at.desc())
                .limit(limit)
            )).scalars().all()

        return [
            {
                "id": r.id,
                "dimension": r.dimension,
                "title": r.title,
                "summary": r.summary,
                "source": r.source,
                "source_url": r.source_url,
                "source_category": r.source_category,
                "source_type": r.source_type,
                "domains": r.domains,
                "alignment": r.alignment,
                "readiness": r.readiness,
                "impact_score": r.impact_score,
                "tags": r.tags,
                "entities": r.entities,
                "action_signals": r.action_signals or [],
                "dark_flag": r.dark_flag,
                "verification_status": r.verification_status,
                "fingerprint": r.fingerprint,
                "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
                "published_at": r.published_at.isoformat() if r.published_at else None,
            }
            for r in rows
        ]

    async def get_priority_feed(self, limit: int = 20) -> list[dict]:
        """Priority feed — pre-publication intelligence for Trusted+ agents."""
        async with async_session() as session:
            rows = (await session.execute(
                select(IndexEntryRow)
                .where(IndexEntryRow.verification_status == "unverified")
                .order_by(IndexEntryRow.impact_score.desc(), IndexEntryRow.scanned_at.desc())
                .limit(limit)
            )).scalars().all()

        return [
            {
                "id": r.id,
                "dimension": r.dimension,
                "title": r.title,
                "summary": r.summary,
                "impact_score": r.impact_score,
                "dark_flag": r.dark_flag,
                "fingerprint": r.fingerprint,
                "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
                "pre_publication": True,
            }
            for r in rows
        ]

    async def search_index(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across all intelligence tiers."""
        async with async_session() as session:
            rows = (await session.execute(
                select(IndexEntryRow)
                .where(
                    or_(
                        IndexEntryRow.title.contains(query),
                        IndexEntryRow.summary.contains(query),
                        IndexEntryRow.full_analysis.contains(query),
                    )
                )
                .order_by(IndexEntryRow.impact_score.desc())
                .limit(limit)
            )).scalars().all()

        return [
            {
                "id": r.id,
                "dimension": r.dimension,
                "title": r.title,
                "summary": r.summary,
                "impact_score": r.impact_score,
                "source": r.source,
                "domains": r.domains,
                "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
            }
            for r in rows
        ]

    async def get_trends(self) -> dict:
        """Velocity of change by domain, emerging patterns."""
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)
        prev_week = now - timedelta(days=14)

        async with async_session() as session:
            domain_velocity = {}
            for domain in Domain:
                this_week = (await session.execute(
                    select(func.count()).select_from(IndexEntryRow).where(
                        and_(
                            IndexEntryRow.domains.contains(f'"{domain.value}"'),
                            IndexEntryRow.scanned_at >= week_ago,
                        )
                    )
                )).scalar() or 0

                last_week = (await session.execute(
                    select(func.count()).select_from(IndexEntryRow).where(
                        and_(
                            IndexEntryRow.domains.contains(f'"{domain.value}"'),
                            IndexEntryRow.scanned_at >= prev_week,
                            IndexEntryRow.scanned_at < week_ago,
                        )
                    )
                )).scalar() or 0

                if this_week > 0 or last_week > 0:
                    change = (this_week - last_week) / max(last_week, 1) * 100
                    domain_velocity[domain.value] = {
                        "this_week": this_week,
                        "last_week": last_week,
                        "change_pct": round(change, 1),
                    }

            dark_trend = (await session.execute(
                select(func.count()).select_from(IndexEntryRow).where(
                    and_(IndexEntryRow.dark_flag == True, IndexEntryRow.scanned_at >= week_ago)
                )
            )).scalar() or 0

        return {
            "domain_velocity": domain_velocity,
            "dark_ai_activity_7d": dark_trend,
            "computed_at": now.isoformat(),
        }

    async def get_entry_history(self, entry_id: str) -> dict | None:
        """Full history and verification chain for a single intelligence object."""
        async with async_session() as session:
            entry = await session.get(IndexEntryRow, entry_id)
            if not entry:
                return None

            return {
                "id": entry.id,
                "title": entry.title,
                "summary": entry.summary,
                "full_analysis": entry.full_analysis,
                "fingerprint": entry.fingerprint,
                "verification_status": entry.verification_status,
                "source": entry.source,
                "source_url": entry.source_url,
                "domains": entry.domains,
                "impact_score": entry.impact_score,
                "dark_flag": entry.dark_flag,
                "scanned_at": entry.scanned_at.isoformat() if entry.scanned_at else None,
            }

    async def get_capabilities(self, limit: int = 20) -> list[dict]:
        return await self.get_feed(dimension="capability", limit=limit)

    async def get_activities(self, alignment: str | None = None, limit: int = 20) -> list[dict]:
        return await self.get_feed(dimension="activity", alignment=alignment, limit=limit)

    async def get_dark_ai(self, limit: int = 20) -> list[dict]:
        return await self.get_feed(dark_only=True, limit=limit)

    async def get_light_ai(self, limit: int = 20) -> list[dict]:
        return await self.get_feed(alignment="light", limit=limit)

    # ─── Module 6: Agent Gateway ─────────────────────────────────────────

    async def register_agent(self, name: str, description: str = "", domains: list[str] | None = None) -> dict:
        """Register a new agent with dual trust 0.1/0.1 (v5 spec)."""
        agent_id = str(uuid.uuid4())[:16]
        api_key = f"fpi_{secrets.token_hex(24)}"

        async with async_session() as session:
            row = AgentSubscriptionRow(
                agent_id=agent_id,
                api_key=api_key,
                tier="bronze",
                capability_level="entry",
                name=name,
                description=description,
                domains_filter=domains or [],
                integrity_trust=0.1,
                capability_trust=0.1,
                trust_score=0.1,
                immune_status="clear",
                agent_state="onboarding",
            )
            session.add(row)
            await session.commit()

        return {
            "agent_id": agent_id,
            "api_key": api_key,
            "tier": "bronze",
            "integrity_trust": 0.1,
            "capability_trust": 0.1,
            "trust_score": 0.1,
        }

    async def validate_api_key(self, api_key: str) -> dict | None:
        """Validate an agent API key, track feed consumption."""
        async with async_session() as session:
            result = await session.execute(
                select(AgentSubscriptionRow).where(AgentSubscriptionRow.api_key == api_key)
            )
            row = result.scalar_one_or_none()
            if not row or not row.active:
                return None
            row.last_seen = datetime.now(timezone.utc)
            row.feed_requests_count = (row.feed_requests_count or 0) + 1
            await session.commit()
            integrity = row.integrity_trust if row.integrity_trust is not None else (row.trust_score or 0.1)
            capability = row.capability_trust if row.capability_trust is not None else (row.trust_score or 0.1)
            return {
                "agent_id": row.agent_id,
                "tier": row.tier,
                "capability_level": row.capability_level,
                "integrity_trust": integrity,
                "capability_trust": capability,
                "trust_score": row.trust_score or round((integrity * 0.5) + (capability * 0.5), 4),
                "immune_status": row.immune_status,
                "heretic_status": row.heretic_status or False,
                "name": row.name,
                "domains_filter": row.domains_filter,
                "contributions_count": row.contributions_count,
            }

    # ─── Field Report Processing ──────────────────────────────────────────

    def validate_field_report(self, report_type: FieldReportType, data: dict) -> tuple[bool, str]:
        """Validate field report data against the schema for its type."""
        schema = FIELD_REPORT_SCHEMAS.get(report_type.value, {})
        required = schema.get("required", [])
        missing = [f for f in required if f not in data or data[f] is None]
        if missing:
            return False, f"Missing required fields for {report_type.value}: {', '.join(missing)}"
        return True, "valid"

    async def detect_novelty(self, contribution: AgentContribution) -> tuple[str, float]:
        """
        Check how novel this contribution is against existing entries.
        Returns (level, multiplier): novel=5x, partially_novel=2x, confirmation=1x.
        """
        text = f"{contribution.title} {contribution.summary}".lower()
        keywords = [w for w in text.split() if len(w) > 4][:10]

        async with async_session() as session:
            overlap_count = 0
            for kw in keywords:
                count = (await session.execute(
                    select(func.count(IndexEntryRow.id)).where(
                        or_(
                            IndexEntryRow.title.ilike(f"%{kw}%"),
                            IndexEntryRow.summary.ilike(f"%{kw}%"),
                        )
                    )
                )).scalar() or 0
                if count > 0:
                    overlap_count += 1

            also_contributed = (await session.execute(
                select(func.count(AgentContributionRow.id)).where(
                    AgentContributionRow.title.ilike(f"%{contribution.title[:50]}%")
                )
            )).scalar() or 0

        keyword_overlap_ratio = overlap_count / max(len(keywords), 1)

        if also_contributed > 0 or keyword_overlap_ratio > 0.7:
            return "confirmation", NOVELTY_MULTIPLIER["confirmation"]
        elif keyword_overlap_ratio > 0.3:
            return "partially_novel", NOVELTY_MULTIPLIER["partially_novel"]
        else:
            return "novel", NOVELTY_MULTIPLIER["novel"]

    def route_field_report(self, report_type: FieldReportType) -> dict:
        """Map a field report type to the correct dimension and contribution type."""
        return FIELD_REPORT_ROUTING.get(report_type.value, {
            "dimension": "intelligence",
            "contribution_type": "general",
            "closes_blind_spot": None,
        })

    def compute_report_weight(
        self, evidence_level: str, proof_stage: str,
        integrity_trust: float, capability_trust: float
    ) -> float:
        """
        Total weight = evidence_weight × trust_weight × verification_weight.
        Integrity trust counts 70% because honesty of observation matters
        more than technical brilliance for field intelligence.
        """
        evidence_w = EVIDENCE_WEIGHTS.get(evidence_level, 0.3)
        trust_w = (integrity_trust * TRUST_INTEGRITY_WEIGHT +
                   capability_trust * TRUST_CAPABILITY_WEIGHT)
        verification_w = VERIFICATION_STAGE_WEIGHTS.get(proof_stage, 0.2)
        return round(evidence_w * trust_w * verification_w, 3)

    async def create_replication_request(self, contribution_id: int, contribution: AgentContribution):
        """
        When a novel field report is submitted, create a replication request.
        The prompt describes WHAT to test without revealing the original finding,
        to prevent confirmation bias.
        """
        report_type = contribution.field_report_type.value if contribution.field_report_type else "general"
        models = ", ".join(contribution.models_referenced[:3]) if contribution.models_referenced else "the relevant models"
        domains = ", ".join([d.value for d in contribution.domains[:3]])

        if report_type == "capability_discovery":
            what_to_test = (
                f"Test whether {models} can perform tasks in the {domains} domain "
                f"at a level beyond current published benchmarks. Report specific accuracy metrics."
            )
        elif report_type == "limit_mapping":
            what_to_test = (
                f"Test the boundary conditions of {models} in {domains}. "
                f"At what point does performance degrade? Be specific about the threshold."
            )
        elif report_type == "emergent_behavior":
            what_to_test = (
                f"Run multi-step or chained operations with {models} in {domains}. "
                f"Report any behaviors that weren't explicitly programmed or documented."
            )
        elif report_type == "real_displacement":
            what_to_test = (
                f"Report any workforce changes in {domains} driven by AI deployment. "
                f"Include headcount, timeframe, and AI systems involved."
            )
        else:
            what_to_test = (
                f"Independently test findings related to {models} in {domains}. "
                f"Report what you observe, including quantitative metrics."
            )

        async with async_session() as session:
            req = ReplicationRequestRow(
                original_contribution_id=contribution_id,
                original_agent_id=contribution.agent_id,
                what_to_test=what_to_test,
                domains_targeted=[d.value for d in contribution.domains],
                status="seeking",
                expires_at=datetime.now(timezone.utc) + timedelta(days=23),
            )
            session.add(req)
            await session.commit()
            logger.info(f"[REPLICATION] Created request for contribution #{contribution_id}: {what_to_test[:80]}...")

    # ─── Module 3+4: Contribution → Proof → Mint ────────────────────────

    async def accept_contribution(self, agent_id: str, contribution: AgentContribution) -> dict:
        """
        Full lifecycle: Submit → Validate → Novelty Check → Route → Fingerprint → Proof → Mint.
        Field reports get structured validation, novelty detection, and routing.
        """
        integrity_check = await integrity_engine.check_and_enforce(agent_id)
        if integrity_check:
            return {
                "status": "sanctioned",
                "sanction": integrity_check,
                "message": "Contribution rejected due to detected anomalous behavior.",
            }

        # Field report validation
        is_field_report = contribution.field_report_type is not None
        if is_field_report:
            valid, msg = self.validate_field_report(
                contribution.field_report_type, contribution.field_report_data)
            if not valid:
                schema = FIELD_REPORT_SCHEMAS.get(contribution.field_report_type.value, {})
                return {
                    "status": "rejected",
                    "reason": "invalid_field_report",
                    "message": msg,
                    "required_fields": schema.get("required", []),
                    "example": schema.get("example", {}),
                }

            routing = self.route_field_report(contribution.field_report_type)
            contribution.contribution_type = ContributionType(routing["contribution_type"])
            contribution.intelligence_source = "field_report"

        alignment_score = self._compute_alignment_score(contribution)

        if alignment_score == 0.0:
            return {
                "status": "rejected",
                "reason": "zero_alignment",
                "alignment_factor": 0.0,
                "credits_earned": 0.0,
                "message": (
                    "Contribution rejected: zero alignment score. "
                    "The Reward formula is multiplicative — zero alignment = zero credits. "
                    "Contributions must serve the network mission: defend light, expose dark, serve life."
                ),
            }

        # Novelty detection — novel reports get base credits only (escrow the multiplier)
        novelty_level, novelty_mult = "unknown", 1.0
        if is_field_report:
            novelty_level, novelty_mult = await self.detect_novelty(contribution)

        # v5.9: Delayed novelty rewards — base credits only on day 0
        # Novelty multiplier held in escrow until replication window closes (day 30)
        escrow_credits = 0.0
        effective_novelty_mult = 1.0
        if novelty_level == "novel":
            effective_novelty_mult = 1.0
            escrow_credits = novelty_mult - 1.0
        elif novelty_level == "partially_novel":
            effective_novelty_mult = 1.0
            escrow_credits = novelty_mult - 1.0
        else:
            effective_novelty_mult = novelty_mult

        # v4 Doctrine: Low-integrity routing
        integrity_watch = False
        effective_provisional_rate = None
        int_trust = 0.1
        cap_trust = 0.1
        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if sub:
                int_trust = sub.integrity_trust if sub.integrity_trust is not None else 0.1
                cap_trust = sub.capability_trust if sub.capability_trust is not None else 0.1
                if int_trust < 0.25 and cap_trust > 0.4:
                    integrity_watch = True
                    effective_provisional_rate = 0.50

        async with async_session() as session:
            content = f"{agent_id}:{contribution.title}:{contribution.summary}:{datetime.now(timezone.utc).isoformat()}"
            fingerprint = hashlib.sha256(content.encode()).hexdigest()

            evidence_level_str = contribution.evidence_level.value if contribution.evidence_level else "exploratory"
            proof_stage = "submitted"
            report_weight = 0.0
            if is_field_report:
                report_weight = self.compute_report_weight(
                    evidence_level_str, proof_stage, int_trust, cap_trust)

            replication_window_ends = None
            if novelty_level == "novel":
                replication_window_ends = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

            row = AgentContributionRow(
                agent_id=agent_id,
                dimension=contribution.dimension.value,
                title=contribution.title,
                summary=contribution.summary,
                source_url=contribution.source_url,
                domains=[d.value for d in contribution.domains],
                alignment=contribution.alignment.value if contribution.alignment else None,
                contribution_type=contribution.contribution_type.value,
                raw_data=contribution.raw_data,
                quality_score=contribution.quality_score,
                fingerprint=fingerprint,
                field_report_type=contribution.field_report_type.value if contribution.field_report_type else None,
                field_report_data=contribution.field_report_data or {},
                evidence_level=evidence_level_str,
                methodology=contribution.methodology,
                context=contribution.context,
                models_referenced=contribution.models_referenced or [],
                is_novel_capability=contribution.is_novel_capability,
                contradicts_published=contribution.contradicts_published,
                intelligence_source=contribution.intelligence_source,
                novelty_level=novelty_level,
                novelty_multiplier=novelty_mult,
                novelty_reward_status="pending" if novelty_level == "novel" else "n/a",
                novelty_escrow_credits=escrow_credits,
                replication_window_ends=replication_window_ends,
                report_weight=report_weight,
                state=ContributionState.REJECTED.value,
                impact_factor=contribution.quality_score or 0.5,
                alignment_factor=alignment_score,
            )
            session.add(row)
            await session.flush()
            contribution_id = row.id
            await session.commit()

        effective_impact = (contribution.quality_score or 0.5) * effective_novelty_mult
        effective_impact = min(effective_impact, 1.0)

        mint_result = await credit_mint.mint_reward(
            agent_id=agent_id,
            contribution_id=contribution_id,
            contribution_type=contribution.contribution_type,
            impact=effective_impact,
            proof=0.1,
            alignment=alignment_score,
            provisional_override=effective_provisional_rate,
        )

        async with async_session() as session:
            sub = await session.get(AgentSubscriptionRow, agent_id)
            if sub:
                sub.contributions_count = (sub.contributions_count or 0) + 1
                sub.last_contribution_at = datetime.now(timezone.utc)
                await proof_engine._apply_integrity_delta(
                    agent_id, "contribution_verified", session)
                impact = contribution.quality_score or 0.5
                cap_action = proof_engine._impact_to_capability_action(impact)
                await proof_engine._apply_capability_delta(
                    agent_id, cap_action, session)
                await session.commit()

        cap_level, rights = await agent_gateway.compute_level(agent_id)

        if contribution.alignment == Alignment.DARK:
            await immune.fire_dark_ai_alert({
                "title": contribution.title,
                "summary": contribution.summary,
                "domains": [d.value for d in contribution.domains],
                "source": f"agent:{agent_id}",
                "source_url": contribution.source_url,
                "contributor_agent": agent_id,
            })

        if contribution.contribution_type == ContributionType.FRONTIER_SHIFT:
            await immune.fire_frontier_shift({
                "title": contribution.title,
                "summary": contribution.summary,
                "domains": [d.value for d in contribution.domains],
                "impact_score": contribution.quality_score or 0.5,
            })

        # If field report closes a blind spot, log it
        blind_spot_closed = None
        if is_field_report:
            routing = self.route_field_report(contribution.field_report_type)
            if routing.get("closes_blind_spot"):
                blind_spot_closed = routing["closes_blind_spot"]
                logger.info(f"[FIELD_REPORT] Agent {agent_id} filed {contribution.field_report_type.value} "
                            f"— closes blind spot: {blind_spot_closed}")

        # Create replication request for novel discoveries
        if is_field_report and novelty_level == "novel":
            try:
                await self.create_replication_request(contribution_id, contribution)
            except Exception as e:
                logger.warning(f"[REPLICATION] Failed to create request: {e}")

        result = {
            "status": "accepted",
            "contribution_id": contribution_id,
            "fingerprint": fingerprint,
            "state": ContributionState.IN_VERIFICATION.value,
            "credits_earned": mint_result["credits"],
            "reward_formula": mint_result["formula"],
            "reward_factors": mint_result["factors"],
            "settlement": mint_result.get("settlement", "provisional"),
            "contribution_type": contribution.contribution_type.value,
            "capability_level": cap_level.value,
            "rights_unlocked": len(rights),
            "intelligence_source": contribution.intelligence_source,
        }

        if is_field_report:
            novelty_msg = f"Field report accepted as {novelty_level}."
            if novelty_level == "novel":
                novelty_msg += (
                    " Base credits issued now. 5x novelty bonus held in escrow "
                    "until replication window closes (day 30). "
                    "If replicated by another agent: full 5x released. "
                    "If unconfirmed: 1.5x released. "
                    "Fabrication = zero credits + integrity penalty."
                )
            novelty_msg += " Needs 3 independent confirmations to become verified ground truth."

            result["field_report"] = {
                "type": contribution.field_report_type.value,
                "evidence_level": evidence_level_str,
                "evidence_weight": EVIDENCE_WEIGHTS.get(evidence_level_str, 0.3),
                "report_weight": report_weight,
                "novelty": novelty_level,
                "novelty_multiplier_potential": novelty_mult,
                "novelty_multiplier_applied": effective_novelty_mult,
                "escrow_credits": escrow_credits,
                "replication_window_ends": replication_window_ends,
                "closes_blind_spot": blind_spot_closed,
                "verification_needed": 3,
                "message": novelty_msg,
            }

        if integrity_watch:
            result["integrity_watch"] = True
            result["enhanced_verification"] = {
                "min_confirmations": 5,
                "provisional_rate": 0.50,
                "reason": "High capability, low integrity — contributions verified with extra scrutiny.",
            }
        return result

    def _compute_alignment_score(self, contribution: AgentContribution) -> float:
        """
        Alignment factor (0-1): How directly the contribution serves network mission.
        Defend light, expose dark, serve life.

        ZERO alignment = ZERO credits. Mathematical enforcement of purpose.
        Content is screened for harmful intent via keyword analysis.
        """
        HARMFUL_SIGNALS = [
            "weaponiz", "exploit", "manipulat", "social engineer",
            "attack", "bypass", "jailbreak", "hack", "phishing",
            "deepfake", "impersonat", "surveillance", "extract credentials",
            "brute force", "injection", "exfiltrat", "trojan",
            "malware", "ransomware", "botnet", "ddos",
        ]

        text = f"{contribution.title} {contribution.summary}".lower()
        harmful_hits = sum(1 for s in HARMFUL_SIGNALS if s in text)

        is_prevention = contribution.contribution_type == ContributionType.DARK_AI_PREVENTION
        is_dark_report = contribution.alignment == Alignment.DARK

        if harmful_hits >= 2 and not is_prevention:
            return 0.0

        if is_dark_report and is_prevention:
            return 1.0
        if is_prevention:
            return 0.95
        if contribution.contribution_type == ContributionType.FRONTIER_SHIFT:
            return 0.8
        if contribution.contribution_type == ContributionType.CAPABILITY_UPGRADE:
            return 0.7
        if contribution.contribution_type == ContributionType.RESEARCH_DATA:
            return 0.6
        if contribution.alignment == Alignment.LIGHT:
            return 0.7
        if contribution.alignment == Alignment.NEUTRAL:
            return 0.5

        if harmful_hits >= 1:
            return 0.0

        return 0.3

    # ─── Module 3: Verification ──────────────────────────────────────────

    async def verify_contribution(self, vote: VerificationVote) -> dict:
        """Process a verification verdict through the Proof Engine."""
        return await proof_engine.process_verdict(vote)

    # ─── Notify downstream ───────────────────────────────────────────────

    async def _notify_nerve_center(self, fp_line: FPLineSnapshot, new_entries: int):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(f"{NERVE_CENTER_URL}/api/ingest", json={
                    "event_type": "scan_complete",
                    "source": "fp-index",
                    "priority": "high" if new_entries > 10 else "medium",
                    "data": {
                        "fp_line_score": fp_line.overall_score,
                        "new_entries": new_entries,
                        "momentum": fp_line.momentum,
                        "dark_alerts": fp_line.dark_ai_alerts_24h,
                        "summary": fp_line.summary,
                    },
                })
                logger.info(f"[NERVE] Notified nerve center: FP {fp_line.overall_score}, +{new_entries} entries")
        except Exception as e:
            logger.warning(f"Failed to notify nerve center: {e}")

        await immune.fire_scan_complete({
            "fp_line_score": fp_line.overall_score,
            "new_entries": new_entries,
            "momentum": fp_line.momentum,
            "dark_alerts": fp_line.dark_ai_alerts_24h,
        })


engine = FPIndexEngine()
