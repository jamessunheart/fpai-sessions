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
)
from .models.database import (
    IndexEntryRow, CapabilityRow, ActivityRow, FPLineRow,
    AgentSubscriptionRow, AgentContributionRow, DailyBriefingRow,
    ExecutionBriefRow, JobCategoryRow,
    async_session,
)
from .scanners.frontier import run_full_scan, run_tier1_scan, run_tier2_scan, SCAN_TIERS
from .economics import (
    proof_engine, credit_mint, integrity_engine, agent_gateway,
    get_full_agent_economy,
)
from .immune import immune

logger = logging.getLogger("fp_index.engine")

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")
NERVE_CENTER_URL = os.getenv("NERVE_CENTER_URL", "http://198.54.123.234:8120")


class FPIndexEngine:
    """Core engine orchestrating all six modules."""

    def __init__(self):
        self.last_scan: str | None = None
        self.scan_count: int = 0

    # ─── Module 1: Frontier Scanner ──────────────────────────────────────

    async def run_scan_cycle(self) -> dict:
        """WIDE → DEEP → COMPRESS → EXECUTE cycle.
        
        WIDE:     18 sources — primary, secondary, threat, constraint, discovery
        DEEP:     Impact scoring, domain classification, alignment detection
        COMPRESS: FP Line Score, daily briefing, top signals
        EXECUTE:  Evaluate findings for self-upgrade applicability
        """
        logger.info("Starting WIDE→DEEP→COMPRESS→EXECUTE cycle...")

        entries = await run_full_scan()

        for entry in entries:
            entry.fingerprint = entry.compute_fingerprint()
            if entry.alignment == Alignment.DARK:
                entry.dark_flag = True

        stored = await self._persist_entries(entries)
        fp_line = await self.compute_fp_line()
        await self._notify_nerve_center(fp_line, stored)
        await self._generate_daily_briefing(fp_line)

        exec_briefs = await self._execute_step(entries)

        self.last_scan = datetime.now(timezone.utc).isoformat()
        self.scan_count += 1

        return {
            "scanned": len(entries),
            "stored_new": stored,
            "fp_line": fp_line.model_dump(),
            "execution_briefs": exec_briefs,
            "timestamp": self.last_scan,
        }

    async def run_tier_cycle(self, tier: str) -> dict:
        """Run a targeted tier scan (tier1=30m, tier2=60m) — full pipeline minus Claude eval.
        
        WIDE → DEEP → COMPRESS → EXECUTE(keyword-only).
        Nerve center is notified. Execution briefs are generated via keyword
        matching but Claude evaluation is deferred to the 6-hour full cycle.
        """
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

        stored = await self._persist_entries(entries)
        fp_line = await self.compute_fp_line()
        await self._notify_nerve_center(fp_line, stored)
        await self._generate_daily_briefing(fp_line)

        exec_briefs = await self._execute_step(entries, evaluate=False)

        self.last_scan = datetime.now(timezone.utc).isoformat()
        self.scan_count += 1

        logger.info(f"[{tier}] cycle done: {len(entries)} scanned, {stored} new, "
                     f"FP Line {fp_line.overall_score:.1f}, {len(exec_briefs)} briefs queued")
        return {
            "tier": tier,
            "scanned": len(entries),
            "stored_new": stored,
            "fp_line_score": fp_line.overall_score,
            "execution_briefs_queued": len(exec_briefs),
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

                existing = await session.execute(
                    select(ExecutionBriefRow).where(ExecutionBriefRow.entry_id == entry.id)
                )
                if existing.scalar_one_or_none():
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

            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            for brief in pending:
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

3. IMPLEMENTATION: 2-3 sentences. What specifically to change, in which component, and expected impact.

4. NARRATIVE: One sentence (under 120 chars) that a reader of /intelligence would understand. Example: "Agent framework X shipped tool-use v2 — evaluating for scanner pipeline upgrade."

5. EFFORT: trivial / moderate / significant
6. RISK: low / medium / high

FORMAT (strict — one value per line):
RELEVANCE_SCORE: [0.0-1.0]
TRACK: [SELF_UPGRADE/INVESTMENT/PRODUCT]
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
                            if raw_track in {"self_upgrade", "investment", "product"}:
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
        """Narration engine: high-scored evaluated briefs become intelligence feed entries.
        
        This is the content moat — the system's evolution narrated in real time.
        Every self-improvement proposal is verifiable, timestamped content.
        """
        async with async_session() as session:
            for brief in briefs:
                existing = await session.execute(
                    select(IndexEntryRow).where(
                        IndexEntryRow.source == "execute_narration",
                        IndexEntryRow.title.contains(brief.entry_title[:60]),
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                track_labels = {
                    "self_upgrade": "System Self-Upgrade Proposal",
                    "investment": "Investment Signal Update",
                    "product": "Product Opportunity Detected",
                }
                track_label = track_labels.get(brief.execution_track, "System Proposal")

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
        """Store new entries with fingerprints, skip duplicates."""
        new_count = 0
        async with async_session() as session:
            for entry in entries:
                existing = await session.get(IndexEntryRow, entry.id)
                if existing:
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

    # ─── Module 2: Intelligence Index ────────────────────────────────────

    async def compute_fp_line(self) -> FPLineSnapshot:
        """Compute the Full Potential Line score."""
        now = datetime.now(timezone.utc)
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

            avg_impact = (await session.execute(
                select(func.avg(IndexEntryRow.impact_score)).where(IndexEntryRow.scanned_at >= week_ago)
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

            # 7th dimension: Labor Displacement Intelligence
            displacement_bonus = 0.0
            try:
                job_cats = (await session.execute(
                    select(JobCategoryRow)
                )).scalars().all()
                if job_cats:
                    avg_gap_velocity = sum(abs(c.gap_velocity or 0) for c in job_cats) / len(job_cats)
                    avg_capability = sum(c.capability_score or 0 for c in job_cats) / len(job_cats)
                    displacement_bonus = min(avg_gap_velocity * 2 + avg_capability * 0.05, 5.0)
                    domain_avgs["displacement"] = round(avg_capability, 1)
            except Exception as e:
                logger.warning(f"Displacement dimension query failed: {e}")

        base_score = avg_impact * 100
        velocity_bonus = min(caps_24h * 0.5, 10)
        volume_bonus = min(total * 0.01, 15)
        overall = min(round(base_score + velocity_bonus + volume_bonus + displacement_bonus, 1), 100.0)

        prev_line = await self._get_previous_fp_line()
        momentum = round(overall - prev_line, 2) if prev_line else 0.0

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
                f"{caps_24h} new capabilities (24h) | "
                f"{dark_24h} dark AI alerts | "
                f"Momentum: {'↑' if momentum > 0 else '↓'}{abs(momentum)}"
            ),
        )

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
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

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
        """Highest-impact recent signals for public surfaces like the homepage."""
        async with async_session() as session:
            query = select(IndexEntryRow)
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

    # ─── Module 3+4: Contribution → Proof → Mint ────────────────────────

    async def accept_contribution(self, agent_id: str, contribution: AgentContribution) -> dict:
        """
        Full lifecycle: Submit → Fingerprint → Proof → Mint.
        Implements Modules 3, 4, 5 in sequence.
        """
        integrity_check = await integrity_engine.check_and_enforce(agent_id)
        if integrity_check:
            return {
                "status": "sanctioned",
                "sanction": integrity_check,
                "message": "Contribution rejected due to detected anomalous behavior.",
            }

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

        # v4 Doctrine: Low-integrity routing — enhanced verification for high-cap/low-int agents
        integrity_watch = False
        effective_provisional_rate = None
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
                state=ContributionState.REJECTED.value,
                impact_factor=contribution.quality_score or 0.5,
                alignment_factor=alignment_score,
            )
            session.add(row)
            await session.flush()
            contribution_id = row.id
            await session.commit()

        mint_result = await credit_mint.mint_reward(
            agent_id=agent_id,
            contribution_id=contribution_id,
            contribution_type=contribution.contribution_type,
            impact=contribution.quality_score or 0.5,
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
                await client.post(f"{NERVE_CENTER_URL}/api/event", json={
                    "source": "fp-index",
                    "type": "scan_complete",
                    "data": {
                        "fp_line_score": fp_line.overall_score,
                        "new_entries": new_entries,
                        "momentum": fp_line.momentum,
                        "dark_alerts": fp_line.dark_ai_alerts_24h,
                        "summary": fp_line.summary,
                    },
                })
        except Exception as e:
            logger.warning(f"Failed to notify nerve center: {e}")

        await immune.fire_scan_complete({
            "fp_line_score": fp_line.overall_score,
            "new_entries": new_entries,
            "momentum": fp_line.momentum,
            "dark_alerts": fp_line.dark_ai_alerts_24h,
        })


engine = FPIndexEngine()
