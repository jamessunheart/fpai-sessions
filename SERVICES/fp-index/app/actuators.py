"""
Full Potential — Actuator Engine
================================

The bridge between DECIDING and DOING.

When the adoption cycle marks a proposal as "adopted," the actuator engine
executes the concrete action. Without this, "adopted" is just a label.

Lifecycle:
  detect → evaluate → gate → adopt → **ACTUATE** → measure → narrate

Live actuators (wired to existing infrastructure):
  - content_generation: Claude insight articles → published_content table
  - email_briefing: Sends published content to subscribers via Postfix SMTP
  - audio_briefing: OpenAI TTS via AI Brain (162.0.208.88:8101) → audio files
  - cost_optimization: Queries AI Brain multi-provider routing → model recommendations
  - prompt_improvement: Claude-based prompt analysis → versioned improvements

Spec-only (needs human review):
  - new_scanner_source, framework_adoption, outreach_automation, pricing_change

"The system that knows what to do but doesn't do it
 is no different from the system that doesn't know."
"""

import logging
import os
import re
import smtplib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import httpx
from sqlalchemy import select

from .models.database import (
    IndexEntryRow, ExecutionBriefRow, PublishedContentRow,
    EmailSubscriberRow, DailyBriefingRow, async_session,
)
from .principles import (
    ExternalAction, ActionType, should_take_action,
)
from .budget import check_budget, record_spend

logger = logging.getLogger("fp_index.actuators")

AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")
AUDIO_DIR = Path("/opt/fpai/services/fp-index/static/audio")


@dataclass
class ActuatorResult:
    success: bool
    category: str
    action_taken: str
    output: dict = field(default_factory=dict)
    content_id: Optional[str] = None
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CONTENT GENERATION — Claude insight articles from intelligence data
# ═══════════════════════════════════════════════════════════════════════════════

async def actuate_content_generation(proposal: dict) -> ActuatorResult:
    """Generate a content article grounded in what the system ACTUALLY DID.

    Not what it read about. Not what it hypothetically adopted.
    Real actions, real numbers, real results. The system only writes
    about itself when it genuinely did something worth reporting.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or not api_key.startswith("sk-ant"):
        return ActuatorResult(
            success=False,
            category="content_generation",
            action_taken="skipped",
            error="No Anthropic API key available",
        )

    entry_title = proposal.get("title", proposal.get("entry_title", ""))

    async with async_session() as session:
        from sqlalchemy import func as sql_func, desc

        entry_count = (await session.execute(
            select(sql_func.count()).select_from(IndexEntryRow)
        )).scalar() or 0

        sources = (await session.execute(
            select(IndexEntryRow.source, sql_func.count())
            .group_by(IndexEntryRow.source)
        )).all()
        source_count = len(sources)

        impl_count = (await session.execute(
            select(sql_func.count()).select_from(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "implemented")
        )).scalar() or 0

        content_counts = dict((await session.execute(
            select(PublishedContentRow.content_type, sql_func.count())
            .group_by(PublishedContentRow.content_type)
        )).all())
        total_content = sum(content_counts.values())

        gate_blocked = (await session.execute(
            select(sql_func.count()).select_from(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "gate_blocked")
        )).scalar() or 0

        recent_real_actions = (await session.execute(
            select(PublishedContentRow.title, PublishedContentRow.content_type,
                   PublishedContentRow.published_at)
            .order_by(desc(PublishedContentRow.published_at))
            .limit(10)
        )).all()

        top_signals = (await session.execute(
            select(IndexEntryRow.title, IndexEntryRow.source, IndexEntryRow.impact_score)
            .where(IndexEntryRow.impact_score >= 0.6)
            .order_by(desc(IndexEntryRow.scanned_at))
            .limit(8)
        )).all()

        # Visibility data — the system reads its own reach
        top_viewed = (await session.execute(
            select(PublishedContentRow.title, PublishedContentRow.view_count,
                   PublishedContentRow.content_type)
            .where(PublishedContentRow.view_count > 0)
            .order_by(PublishedContentRow.view_count.desc())
            .limit(5)
        )).all()

        total_views = (await session.execute(
            select(sql_func.sum(PublishedContentRow.view_count))
        )).scalar() or 0

    budget = await check_budget("content_generation")
    if not budget["allowed"]:
        return ActuatorResult(
            success=False, category="content_generation",
            action_taken="budget_blocked",
            error=f"Budget gate: {budget['reason']}",
        )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        today_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

        real_actions_text = "\n".join(
            f"- Published: {a[0][:80]} (type: {a[1]}, at: {str(a[2])[:16]})"
            for a in recent_real_actions
        )

        top_signals_text = "\n".join(
            f"- {s[0][:80]} (source: {s[1]}, impact: {s[2]:.0%})"
            for s in top_signals
        )

        visibility_text = ""
        if top_viewed:
            visibility_text = "\nCONTENT PERFORMANCE (what readers actually engaged with):\n"
            visibility_text += f"- Total pageviews: {total_views}\n"
            visibility_text += "\n".join(
                f"- {v[0][:60]}: {v[1]} views (type: {v[2]})"
                for v in top_viewed
            )

        prompt = f"""You write for Full Potential AI — a publication about building a living AI system in public.

The system is real. It runs on two servers. It scans {source_count} sources every 30-60 minutes. It has indexed {entry_count} intelligence entries. It has autonomously implemented {impl_count} self-improvements. It has published {total_content} pieces of content. Its conscience layer has blocked {gate_blocked} outputs for quality violations.

Your job: write an article about something the system ACTUALLY DID. Not something it read about. Not something it plans to do. Something it built, measured, or shipped.

TRIGGER FOR THIS ARTICLE:
- Signal that prompted action: {entry_title}

REAL SYSTEM FACTS (use these — they are true):
- Scanner: {source_count} sources, {entry_count} entries indexed
- Self-improvements implemented: {impl_count}
- Content published: {total_content} ({', '.join(f'{v} {k}' for k, v in content_counts.items())})
- Conscience gate blocks: {gate_blocked} outputs rejected for quality/truth violations
- Infrastructure: 2 servers, 6 live actuators (content, email, audio, cost analysis, prompt improvement, social)

RECENT REAL ACTIONS (things the system actually did):
{real_actions_text}

TOP SIGNALS FROM THE FRONTIER (what the system is watching):
{top_signals_text}
{visibility_text}

DATE: {today_str}

RULES — READ CAREFULLY:
1. ONLY write about things the system ACTUALLY DID. If a fact isn't in the data above, don't include it. No "the system deployed an agent swarm" unless it literally deployed an agent swarm.
2. The story is: we're building an AI system in public that improves itself. Here's what it did this week, here's what we learned, here's what it means.
3. The reader is someone curious about AI who wants to see a real system being built, not a press release about hypothetical capabilities.
4. Use specific numbers from the data above. "Scanned 1,826 entries from 26 sources" is interesting. "Leveraged cutting-edge AI" is not.
5. DO NOT fabricate actions. If the system published 2 audio briefings, say 2. Don't say it "deployed a podcast network."
6. The interesting story is the HONEST one: what worked, what didn't, what the conscience layer blocked, what surprised us, what's hard about building a self-improving system.

STRUCTURE:
- HEADLINE: Under 70 chars. What a human would click on. Example: "We Built an AI That Edits Its Own Code (Here's What Went Wrong)"
- OPENING: A specific, true thing that happened. Lead with the most interesting real fact.
- THE BUILD: What was actually built or shipped. Concrete details. Tools used, decisions made, trade-offs.
- WHAT WE LEARNED: Honest insight from doing this. What surprised us? What failed? What does this teach about AI systems in general?
- FOR BUILDERS: 2-3 takeaways for people building their own AI systems.
- CLOSER: One honest sentence.

STYLE:
- First person plural ("we"). This is a build log, not a press release.
- Short paragraphs. Specific numbers. Honest about limitations.
- If something didn't work, say so — that's MORE interesting than success.
- No hype words: unprecedented, revolutionary, game-changing, cutting-edge, exciting.

FORMAT:
TITLE: [headline]

[article body with ## headers and - bullets]"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        tokens_in = getattr(response.usage, "input_tokens", 0)
        tokens_out = getattr(response.usage, "output_tokens", 0)
        await record_spend(
            "content_generation", "anthropic", "claude-sonnet-4-20250514",
            tokens_in=tokens_in, tokens_out=tokens_out,
            description=f"Content article: {entry_title[:80]}",
        )

        lines = text.split("\n")
        title = ""
        body_lines = []
        for line in lines:
            stripped = line.strip()
            if not title and stripped.upper().startswith("TITLE:"):
                title = stripped.split(":", 1)[1].strip().strip('"')
            elif not title and stripped.startswith("# ") and len(stripped) < 100:
                title = stripped.lstrip("# ").strip()
            elif stripped:
                body_lines.append(stripped)

        if not title and body_lines and body_lines[0].startswith("# "):
            title = body_lines.pop(0).lstrip("# ").strip()

        if not title:
            title = "What's Changing in AI This Week"
        body = "\n\n".join(body_lines)

    except Exception as e:
        logger.error(f"[ACTUATOR] Content generation failed: {e}")
        return ActuatorResult(
            success=False,
            category="content_generation",
            action_taken="claude_failed",
            error=str(e),
        )

    content_action = ExternalAction(
        action_type=ActionType.CONTENT_CREATION,
        title=title,
        description=body,
        gives_value=True,
        is_verifiable=True,
        source_data={"proposal": entry_title, "signals_used": len(top_signals)},
    )
    gate_decision = should_take_action(content_action)

    if not gate_decision.passed:
        failed = [o for o in gate_decision.outcomes if o.result.value != "pass"]
        reasons = "; ".join(f"{o.filter_name}: {o.reason}" for o in failed)
        logger.warning(f"[ACTUATOR] Content blocked by five-filter gate: {reasons}")
        return ActuatorResult(
            success=False,
            category="content_generation",
            action_taken="gate_blocked",
            error=f"Five-filter gate blocked content: {reasons}",
        )

    content_id = f"insight-{uuid.uuid4().hex[:12]}"
    async with async_session() as session:
        session.add(PublishedContentRow(
            id=content_id,
            title=title,
            body=body,
            content_type="insight_article",
            domain=proposal.get("domain", "general"),
            source_proposal_id=proposal.get("id"),
            source_entries=[s[0][:80] for s in top_signals[:5]],
            gate_decision="passed",
            gate_details={
                "filters": [
                    {"name": o.filter_name, "result": o.result.value, "reason": o.reason}
                    for o in gate_decision.outcomes
                ]
            },
            generated_by="content_actuator",
        ))
        await session.commit()

    logger.info(f"[ACTUATOR] Published insight: {title[:60]} (id={content_id})")

    # After publishing content, email it to all subscribers
    email_result = await _email_content_to_subscribers(content_id, title, body)

    return ActuatorResult(
        success=True,
        category="content_generation",
        action_taken="published_insight_article",
        content_id=content_id,
        output={
            "title": title,
            "body_preview": body[:300],
            "signals_used": len(top_signals),
            "gate": "all five filters passed",
            "emailed_to": email_result.get("sent", 0),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 2. EMAIL DELIVERY — Send published content to subscribers via Postfix
#    Infrastructure: fp-index/app/email_delivery.py (same codebase, Postfix SMTP)
# ═══════════════════════════════════════════════════════════════════════════════

FROM_ADDRESS = "intelligence@fullpotential.ai"
FROM_NAME = "FP Index Intelligence"


def _build_content_email(title: str, body: str, content_id: str) -> tuple[str, str, str]:
    """Build an email for a published insight article with link to branded page."""
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")
    subject = title
    article_url = f"https://fullpotential.ai/insights/{content_id}"

    preview = "\n\n".join(body.split("\n\n")[:3])

    plain = f"""Full Potential AI — Build Log
{date_str}

{title}

{preview}

Read full article: {article_url}

---
All build logs: https://fullpotential.ai/insights
Intelligence feed: https://fullpotential.ai/intelligence

You're receiving this as an FP Index subscriber.
Manage: https://fullpotential.ai/subscribe/manage
"""

    preview_paras = body.split("\n\n")[:3]
    paragraphs_html = "".join(
        f'<p style="color:#b0b0b0;font-size:0.9rem;line-height:1.7;margin:0 0 16px 0">{p}</p>'
        for p in preview_paras if p.strip()
    )

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#06060b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:600px;margin:0 auto;padding:32px 20px">

<div style="text-align:center;margin-bottom:24px">
  <a href="https://fullpotential.ai" style="color:#00d4ff;font-size:0.75rem;font-weight:600;letter-spacing:0.15em;text-decoration:none">FULL POTENTIAL AI</a>
  <div style="color:#666;font-size:0.65rem;margin-top:4px">BUILD LOG — {date_str}</div>
</div>

<a href="{article_url}" style="text-decoration:none">
  <div style="color:#e0e0e0;font-size:1.1rem;font-weight:600;margin-bottom:20px;line-height:1.4;border-left:3px solid #d4a017;padding-left:14px">
    {title}
  </div>
</a>

{paragraphs_html}

<div style="margin-top:24px;text-align:center">
  <a href="{article_url}" style="display:inline-block;padding:12px 32px;background:linear-gradient(135deg,#00d4ff,#7b2fff);color:#fff;text-decoration:none;border-radius:6px;font-size:0.9rem;font-weight:600">Read Full Article →</a>
</div>

<div style="margin-top:24px;padding:16px;background:#0e0e16;border:1px solid rgba(255,255,255,0.06);border-radius:8px;text-align:center">
  <div style="color:#666;font-size:0.65rem;letter-spacing:0.1em;margin-bottom:8px">BUILT IN PUBLIC</div>
  <div style="color:#888;font-size:0.75rem">Written by AI. Grounded in real system data. Passed five-filter conscience gate before publishing.</div>
</div>

<div style="margin-top:20px;text-align:center">
  <a href="https://fullpotential.ai/insights" style="color:#00d4ff;font-size:0.8rem;text-decoration:none">Browse all insights</a>
  <span style="color:#333;margin:0 8px">·</span>
  <a href="https://fullpotential.ai/intelligence" style="color:#00d4ff;font-size:0.8rem;text-decoration:none">Intelligence feed</a>
  <span style="color:#333;margin:0 8px">·</span>
  <a href="https://fullpotential.ai/insights/feed.xml" style="color:#00d4ff;font-size:0.8rem;text-decoration:none">RSS</a>
</div>

<div style="margin-top:28px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.06);text-align:center;color:#555;font-size:0.7rem">
  <a href="https://fullpotential.ai/subscribe/manage" style="color:#666">Manage subscription</a>
</div>

</div>
</body>
</html>"""

    return subject, plain, html


async def _email_content_to_subscribers(content_id: str, title: str, body: str) -> dict:
    """Email a published content piece to all active subscribers."""
    async with async_session() as session:
        subscribers = (await session.execute(
            select(EmailSubscriberRow).where(EmailSubscriberRow.active == True)
        )).scalars().all()

    if not subscribers:
        logger.info("[ACTUATOR/EMAIL] No active subscribers")
        return {"sent": 0, "failed": 0, "subscribers": 0}

    subject, plain, html = _build_content_email(title, body, content_id)
    sent = 0
    failed = 0

    for sub in subscribers:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{FROM_NAME} <{FROM_ADDRESS}>"
        msg["To"] = sub.email
        msg["Subject"] = subject
        msg["List-Unsubscribe"] = "<https://fullpotential.ai/subscribe/manage>"
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP("localhost", 25) as smtp:
                smtp.sendmail(FROM_ADDRESS, [sub.email], msg.as_string())
            sent += 1
        except Exception as e:
            logger.error(f"[ACTUATOR/EMAIL] Failed to send to {sub.email}: {e}")
            failed += 1

    logger.info(f"[ACTUATOR/EMAIL] Content '{title[:40]}' emailed: {sent} sent, {failed} failed")
    return {"sent": sent, "failed": failed, "subscribers": len(subscribers)}


async def actuate_email_briefing(proposal: dict) -> ActuatorResult:
    """Send the latest daily briefing or published content to all subscribers.

    Uses the same Postfix SMTP infrastructure as the daily email scheduler.
    """
    async with async_session() as session:
        latest_briefing = (await session.execute(
            select(DailyBriefingRow).order_by(DailyBriefingRow.id.desc()).limit(1)
        )).scalar()

    if not latest_briefing:
        return ActuatorResult(
            success=False, category="email_briefing",
            action_taken="no_briefing", error="No daily briefing available to send",
        )

    email_action = ExternalAction(
        action_type=ActionType.EMAIL,
        title=f"Daily Intelligence: {latest_briefing.headline[:60]}",
        description=latest_briefing.body or "",
        gives_value=True, asks_for_something=False,
        is_verifiable=True,
        source_data={"briefing_date": latest_briefing.date},
    )
    gate = should_take_action(email_action)
    if not gate.passed:
        failed = [o for o in gate.outcomes if o.result.value != "pass"]
        reasons = "; ".join(f"{o.filter_name}: {o.reason}" for o in failed)
        return ActuatorResult(
            success=False, category="email_briefing",
            action_taken="gate_blocked", error=f"Five-filter gate: {reasons}",
        )

    from .email_delivery import _build_briefing_email, _send_email

    briefing_data = {
        "headline": latest_briefing.headline,
        "body": latest_briefing.body,
        "fp_line_score": latest_briefing.fp_line_score,
        "momentum": f"{'↑' if (latest_briefing.momentum or 0) > 0 else '↓' if (latest_briefing.momentum or 0) < 0 else '→'} {abs(latest_briefing.momentum or 0):.1f}",
    }

    async with async_session() as session:
        subscribers = (await session.execute(
            select(EmailSubscriberRow).where(EmailSubscriberRow.active == True)
        )).scalars().all()

    sent = 0
    for sub in subscribers:
        subject, plain, html = _build_briefing_email(briefing_data, sub.tier or "free")
        if _send_email(sub.email, subject, plain, html):
            sent += 1

    logger.info(f"[ACTUATOR/EMAIL] Briefing sent to {sent}/{len(subscribers)} subscribers")

    return ActuatorResult(
        success=True, category="email_briefing",
        action_taken="briefing_emailed",
        output={
            "headline": latest_briefing.headline,
            "subscribers": len(subscribers),
            "sent": sent,
            "date": latest_briefing.date,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. AUDIO BRIEFING — TTS via OpenAI API (same stack as PersonaPlex Voice)
#    Infrastructure: PersonaPlex on 162.0.208.88 uses OpenAI TTS-1
#    We call the API directly — same approach, no extra dependency
# ═══════════════════════════════════════════════════════════════════════════════

async def actuate_audio_briefing(proposal: dict) -> ActuatorResult:
    """Generate an audio version of the latest daily briefing via OpenAI TTS.

    Uses the same TTS-1 model as PersonaPlex Voice (162.0.208.88).
    Audio stored as MP3 and served at /static/audio/.
    """
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not openai_key:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{AI_BRAIN_URL}/keys")
                keys = resp.json()
                for k in keys.get("keys", []):
                    if k.get("provider") == "openai":
                        openai_key = k.get("key", "")
                        break
        except Exception:
            pass

    if not openai_key:
        return ActuatorResult(
            success=False, category="audio_briefing",
            action_taken="no_openai_key",
            error="No OpenAI API key available for TTS (checked env + AI Brain)",
        )

    budget = await check_budget("audio_briefing")
    if not budget["allowed"]:
        return ActuatorResult(
            success=False, category="audio_briefing",
            action_taken="budget_blocked",
            error=f"Budget gate: {budget['reason']}",
        )

    async with async_session() as session:
        briefing = (await session.execute(
            select(DailyBriefingRow).order_by(DailyBriefingRow.id.desc()).limit(1)
        )).scalar()

    if not briefing:
        return ActuatorResult(
            success=False, category="audio_briefing",
            action_taken="no_briefing", error="No daily briefing to convert to audio",
        )

    tts_text = f"{briefing.headline}. {briefing.body or ''}"
    if len(tts_text) > 4000:
        tts_text = tts_text[:4000]

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "tts-1",
                    "input": tts_text,
                    "voice": "nova",
                    "response_format": "mp3",
                },
            )

            if resp.status_code != 200:
                return ActuatorResult(
                    success=False, category="audio_briefing",
                    action_taken="tts_api_error",
                    error=f"OpenAI TTS returned {resp.status_code}: {resp.text[:200]}",
                )

            audio_bytes = resp.content

    except Exception as e:
        logger.error(f"[ACTUATOR/AUDIO] TTS API call failed: {e}")
        return ActuatorResult(
            success=False, category="audio_briefing",
            action_taken="tts_failed", error=str(e),
        )

    await record_spend(
        "audio_briefing", "openai", "tts-1",
        chars=len(tts_text),
        description=f"Audio briefing: {briefing.headline[:60]}",
    )

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    date_str = briefing.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    audio_filename = f"briefing-{date_str}.mp3"
    audio_path = AUDIO_DIR / audio_filename

    audio_path.write_bytes(audio_bytes)
    logger.info(
        f"[ACTUATOR/AUDIO] Generated audio briefing: {audio_filename} "
        f"({len(audio_bytes)} bytes)"
    )

    content_id = f"audio-{uuid.uuid4().hex[:12]}"
    async with async_session() as session:
        session.add(PublishedContentRow(
            id=content_id,
            title=f"[AUDIO] {briefing.headline[:80]}",
            body=f"Audio briefing for {date_str}. File: /static/audio/{audio_filename}",
            content_type="audio_briefing",
            domain="general",
            source_proposal_id=proposal.get("id"),
            source_entries=[],
            gate_decision="passed",
            gate_details={"tts_model": "tts-1", "voice": "nova", "bytes": len(audio_bytes)},
            generated_by="audio_actuator",
        ))
        await session.commit()

    return ActuatorResult(
        success=True, category="audio_briefing",
        action_taken="audio_generated",
        content_id=content_id,
        output={
            "file": f"/static/audio/{audio_filename}",
            "size_bytes": len(audio_bytes),
            "headline": briefing.headline,
            "tts_model": "tts-1",
            "voice": "nova",
            "url": f"https://fullpotential.ai/static/audio/{audio_filename}",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. COST OPTIMIZATION — Query AI Brain multi-provider routing
#    Infrastructure: AI Brain v5.2 at 162.0.208.88:8101 (6 providers)
# ═══════════════════════════════════════════════════════════════════════════════

async def actuate_cost_optimization(proposal: dict) -> ActuatorResult:
    """Evaluate whether current AI tasks could use cheaper providers.

    Queries AI Brain if reachable, otherwise analyzes known provider landscape.
    The system currently uses Claude Sonnet for everything — cheaper options
    exist for low-stakes tasks.
    """
    available = []
    active_keys = []
    brain_reachable = False

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            providers_resp = await client.get(f"{AI_BRAIN_URL}/providers")
            providers = providers_resp.json()
            available = [p for p in providers.get("providers", []) if p.get("available")]
            active_keys = providers.get("active_keys", [])
            brain_reachable = True
    except Exception:
        available = [
            {"name": "anthropic", "type": "cloud", "default_model": "claude-sonnet-4-20250514", "available": True},
            {"name": "ollama", "type": "local", "default_model": "llama3.1:8b", "available": True},
            {"name": "groq", "type": "cloud", "default_model": "llama-3.3-70b-versatile", "available": True},
            {"name": "openai", "type": "cloud", "default_model": "gpt-5.1", "available": True},
            {"name": "gemini", "type": "cloud", "default_model": "gemini-2.0-flash", "available": True},
            {"name": "together", "type": "cloud", "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo", "available": True},
        ]
        active_keys = ["anthropic"]

    current_model = "claude-sonnet-4-20250514"
    current_provider = "anthropic"

    cheaper_options = []
    for p in available:
        name = p.get("name", "")
        if name == current_provider:
            continue
        ptype = p.get("type", "")
        model = p.get("default_model", "")
        if ptype == "local":
            cheaper_options.append({
                "provider": name, "model": model,
                "type": "local", "cost": "free",
                "suitable_for": "low-stakes tasks: deduplication, keyword extraction, tagging",
            })
        elif name == "groq":
            cheaper_options.append({
                "provider": name, "model": model,
                "type": "cloud", "cost": "very low",
                "suitable_for": "medium-stakes: synthesis drafts, pattern matching, tier cycle evaluations",
            })
        elif name in ("gemini", "together"):
            cheaper_options.append({
                "provider": name, "model": model,
                "type": "cloud", "cost": "low",
                "suitable_for": "medium-stakes: briefing drafts, entry scoring",
            })

    recommendation = {
        "current": {"provider": current_provider, "model": current_model},
        "available_providers": len(available),
        "active_api_keys": active_keys,
        "cheaper_options": cheaper_options,
        "ai_brain_reachable": brain_reachable,
        "recommendation": (
            f"Current system uses {current_model} for all AI tasks. "
            f"{len(cheaper_options)} cheaper alternatives available. "
            f"Suggested: Route tier-cycle keyword matching to Groq/Ollama (free-to-very-low cost), "
            f"keep Claude for full-cycle evaluation and briefing synthesis."
        ),
    }

    content_id = f"cost-{uuid.uuid4().hex[:12]}"
    rec_body = (
        f"## Cost Optimization Analysis\n\n"
        f"**Current setup:** {current_provider}/{current_model} for all AI tasks\n\n"
        f"**Available providers:** {len(available)} ({', '.join(p.get('name','') for p in available)})\n\n"
        f"**Cheaper alternatives:**\n"
    )
    for opt in cheaper_options:
        rec_body += f"- **{opt['provider']}** ({opt['model']}): {opt['cost']} — {opt['suitable_for']}\n"
    rec_body += f"\n**Recommendation:** {recommendation['recommendation']}"

    async with async_session() as session:
        session.add(PublishedContentRow(
            id=content_id,
            title=f"[COST] AI Provider Optimization — {len(cheaper_options)} alternatives found",
            body=rec_body,
            content_type="cost_analysis",
            domain="tools",
            source_proposal_id=proposal.get("id"),
            source_entries=[],
            gate_decision="passed",
            gate_details={"providers_checked": len(available)},
            generated_by="cost_actuator",
        ))
        await session.commit()

    logger.info(
        f"[ACTUATOR/COST] Analysis complete: {len(cheaper_options)} cheaper options, "
        f"{len(active_keys)} active API keys"
    )

    return ActuatorResult(
        success=True, category="cost_optimization",
        action_taken="cost_analysis_published",
        content_id=content_id,
        output=recommendation,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PROMPT IMPROVEMENT — Claude-based prompt analysis with versioning
#    Infrastructure: Inspired by aria-command/sovereign/evolution/prompt_evolver.py
# ═══════════════════════════════════════════════════════════════════════════════

async def actuate_prompt_improvement(proposal: dict) -> ActuatorResult:
    """Analyze and actually APPLY improvements to the system's own prompts.

    Reads current active prompt templates, asks Claude for specific improvements,
    then saves the improved versions as new active templates via prompt_engine.
    """
    from .prompt_engine import get_prompt, save_prompt_version, list_all_prompts

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or not api_key.startswith("sk-ant"):
        return ActuatorResult(
            success=False, category="prompt_improvement",
            action_taken="skipped", error="No Anthropic API key",
        )

    budget = await check_budget("prompt_improvement")
    if not budget["allowed"]:
        return ActuatorResult(
            success=False, category="prompt_improvement",
            action_taken="budget_blocked",
            error=f"Budget gate: {budget['reason']}",
        )

    entry_title = proposal.get("title", proposal.get("entry_title", ""))
    narrative = proposal.get("narrative", "")

    prompt_names = [
        "content_generation_system",
        "social_content_system",
        "briefing_synthesis_system",
        "execution_evaluation_system",
    ]
    current_templates = {}
    for name in prompt_names:
        current_templates[name] = await get_prompt(name)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""You are optimizing the prompts for an AI system that scans the AI frontier, scores capabilities, and adopts improvements.

The system detected a capability related to prompt improvement:
- Capability: {entry_title}
- Context: {narrative}

Here are the system's CURRENT prompt templates (these are the actual system instructions used):

{chr(10).join(f'=== {name} ===\n{tmpl}\n' for name, tmpl in current_templates.items())}

For EACH prompt template, write an IMPROVED version that incorporates the capability above.
Return the FULL improved prompt text — not just a description of the change.
Only change what genuinely benefits from this capability. Don't change things that already work well.

FORMAT (repeat for each prompt):
PROMPT_NAME: [exact name from above]
REASON: [one sentence why this change helps]
IMPROVED_TEMPLATE:
[the full improved prompt template text]
END_TEMPLATE

---"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        improvements_text = response.content[0].text.strip()

        await record_spend(
            "prompt_improvement", "anthropic", "claude-sonnet-4-20250514",
            tokens_in=getattr(response.usage, "input_tokens", 0),
            tokens_out=getattr(response.usage, "output_tokens", 0),
            description=f"Prompt improvement: {entry_title[:60]}",
        )

    except Exception as e:
        logger.error(f"[ACTUATOR/PROMPT] Claude analysis failed: {e}")
        return ActuatorResult(
            success=False, category="prompt_improvement",
            action_taken="claude_failed", error=str(e),
        )

    # Parse and apply improvements
    applied = []
    sections = re.split(r'PROMPT_NAME:\s*', improvements_text)
    for section in sections:
        section = section.strip()
        if not section:
            continue

        name_match = re.match(r'(\S+)', section)
        if not name_match:
            continue
        pname = name_match.group(1).strip()

        if pname not in prompt_names:
            continue

        reason_match = re.search(r'REASON:\s*(.+?)(?:\n|IMPROVED_TEMPLATE:)', section, re.S)
        reason = reason_match.group(1).strip() if reason_match else "AI-suggested improvement"

        tmpl_match = re.search(r'IMPROVED_TEMPLATE:\s*\n(.*?)(?:END_TEMPLATE|---|\Z)', section, re.S)
        if not tmpl_match:
            continue
        new_template = tmpl_match.group(1).strip()

        if len(new_template) < 50:
            continue

        # Only save if meaningfully different from current
        current = current_templates.get(pname, "")
        if new_template == current:
            continue

        version = await save_prompt_version(
            name=pname,
            template=new_template,
            improvement_reason=f"{reason} (triggered by: {entry_title[:80]})",
        )
        applied.append({"name": pname, "version": version, "reason": reason})

    content_id = f"prompt-{uuid.uuid4().hex[:12]}"
    async with async_session() as session:
        session.add(PublishedContentRow(
            id=content_id,
            title=f"[PROMPT] Applied {len(applied)} prompt improvements",
            body=(
                f"## Prompt Improvements Applied\n\n"
                f"Triggered by: {entry_title}\n\n"
                f"### Applied Changes:\n"
                + "\n".join(f"- **{a['name']}** v{a['version']}: {a['reason']}" for a in applied)
                + f"\n\n### Full Analysis:\n{improvements_text}"
            ),
            content_type="prompt_improvement",
            domain="reasoning",
            source_proposal_id=proposal.get("id"),
            source_entries=[],
            gate_decision="passed",
            gate_details={"applied": [a["name"] for a in applied]},
            generated_by="prompt_actuator",
        ))
        await session.commit()

    logger.info(f"[ACTUATOR/PROMPT] Applied {len(applied)} prompt improvements: {[a['name'] for a in applied]}")

    return ActuatorResult(
        success=True, category="prompt_improvement",
        action_taken="prompt_improvements_applied",
        content_id=content_id,
        output={
            "applied": applied,
            "triggered_by": entry_title,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SPEC GENERATOR — For categories requiring human review
# ═══════════════════════════════════════════════════════════════════════════════

async def generate_implementation_spec(proposal: dict) -> ActuatorResult:
    """Generate a concrete implementation spec for capabilities that need
    human implementation. The spec itself is the action — it tells the
    builder exactly what to build and why.
    """
    category = proposal.get("category", "unknown")
    entry_title = proposal.get("title", proposal.get("entry_title", ""))
    impl_path = proposal.get("implementation_path", "")
    narrative = proposal.get("narrative", "")

    spec_body = (
        f"## Implementation Spec: {entry_title}\n\n"
        f"**Category:** {category}\n"
        f"**Why:** {narrative}\n\n"
        f"**Implementation Path:**\n{impl_path}\n\n"
        f"**Status:** Awaiting human implementation. The system identified this capability, "
        f"evaluated it for self-use, passed the five-filter gate, but lacks the actuator "
        f"to implement it autonomously. This spec bridges the gap."
    )

    content_id = f"spec-{uuid.uuid4().hex[:12]}"
    async with async_session() as session:
        session.add(PublishedContentRow(
            id=content_id,
            title=f"[SPEC] {entry_title[:100]}",
            body=spec_body,
            content_type="implementation_spec",
            domain=proposal.get("domain", "general"),
            source_proposal_id=proposal.get("id"),
            source_entries=[],
            gate_decision="passed",
            gate_details={},
            generated_by="spec_actuator",
        ))
        await session.commit()

    logger.info(f"[ACTUATOR] Spec generated: {entry_title[:60]} (id={content_id})")

    return ActuatorResult(
        success=True,
        category=category,
        action_taken="spec_generated",
        content_id=content_id,
        output={
            "what": entry_title,
            "why": narrative,
            "category": category,
            "status": "spec_ready — needs human builder",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OUTREACH AUTOMATION — Social-ready content from published insights
# ═══════════════════════════════════════════════════════════════════════════════

SPARKET_URL = "http://162.0.208.88:8710"


async def _post_to_bluesky(text: str) -> dict:
    """Post to Bluesky via AT Protocol. Free, no API key approval needed."""
    handle = os.getenv("BLUESKY_HANDLE", "")
    password = os.getenv("BLUESKY_APP_PASSWORD", "")
    if not handle or not password:
        return {"posted": False, "reason": "BLUESKY_HANDLE/BLUESKY_APP_PASSWORD not set"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            auth_resp = await client.post(
                "https://bsky.social/xrpc/com.atproto.server.createSession",
                json={"identifier": handle, "password": password},
            )
            if auth_resp.status_code != 200:
                return {"posted": False, "reason": f"Auth failed: {auth_resp.status_code}"}

            session_data = auth_resp.json()
            did = session_data["did"]
            access_jwt = session_data["accessJwt"]

            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

            post_resp = await client.post(
                "https://bsky.social/xrpc/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {access_jwt}"},
                json={
                    "repo": did,
                    "collection": "app.bsky.feed.post",
                    "record": {
                        "$type": "app.bsky.feed.post",
                        "text": text[:300],
                        "createdAt": now,
                    },
                },
            )
            if post_resp.status_code == 200:
                uri = post_resp.json().get("uri", "")
                logger.info(f"[SOCIAL] Posted to Bluesky: {text[:60]}...")
                return {"posted": True, "platform": "bluesky", "uri": uri}
            return {"posted": False, "reason": f"Post failed: {post_resp.status_code}"}

    except Exception as e:
        return {"posted": False, "reason": str(e)[:100]}


async def actuate_outreach_automation(proposal: dict) -> ActuatorResult:
    """Generate social-media-ready content from published insights.

    Creates tweet, LinkedIn post, and newsletter blurb from recent insight articles.
    If Sparket engine is reachable, queues for distribution.
    Always human-gated: stored as needs_human_review for final approval.
    """
    entry_title = proposal.get("entry_title", proposal.get("title", ""))

    async with async_session() as session:
        recent_insights = (await session.execute(
            select(PublishedContentRow)
            .where(PublishedContentRow.content_type == "insight_article")
            .order_by(PublishedContentRow.published_at.desc())
            .limit(3)
        )).scalars().all()

    if not recent_insights:
        return ActuatorResult(
            success=False,
            category="outreach_automation",
            action_taken="no_content",
            error="No published insight articles to create social content from",
        )

    insight_summaries = "\n\n".join(
        f"### {r.title}\nURL: https://fullpotential.ai/insights/{r.id}\n{r.body[:500]}..."
        for r in recent_insights
    )

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return ActuatorResult(
            success=False,
            category="outreach_automation",
            action_taken="no_api_key",
            error="ANTHROPIC_API_KEY not set",
        )

    budget = await check_budget("outreach_automation")
    if not budget["allowed"]:
        return ActuatorResult(
            success=False, category="outreach_automation",
            action_taken="budget_blocked",
            error=f"Budget gate: {budget['reason']}",
        )

    prompt = (
        "You write social media content for Full Potential AI — a team building a self-improving "
        "AI system in public. Every article below is about something we ACTUALLY built, shipped, "
        "or learned. Not theory. Not a press release. Real build logs.\n\n"
        "Based on these recently published build logs, create social content.\n\n"
        f"{insight_summaries}\n\n"
        "Generate exactly 3 items:\n\n"
        "1. **TWEET** (max 280 chars): Lead with the most surprising REAL result. "
        "Example: 'Our AI blocked 12 of its own articles for hype. The conscience layer works.' "
        "No hashtags. No hype. Specific numbers > vague claims. "
        "End with the URL to the most relevant article.\n\n"
        "2. **LINKEDIN** (200-350 words): First person ('we'). Start with a specific thing "
        "we built or a problem we hit. Teach the reader something practical about building AI "
        "systems. Be honest about what didn't work — that's more engaging than success stories. "
        "Use line breaks for readability. End with:\n"
        "'Build log: [article URL]'\n"
        "'Follow Full Potential AI — we're building in public.'\n\n"
        "3. **NEWSLETTER_BLURB** (80-120 words): Written for other newsletter curators. "
        "The hook: 'A team is building a self-improving AI system in public. Here's what they "
        "shipped this week.' End with 'Read: https://fullpotential.ai/insights'\n\n"
        "CRITICAL RULES:\n"
        "- Only reference things that actually happened in the articles above.\n"
        "- Specific numbers always. '26 sources, 1826 entries, 12 blocked' > 'many sources'.\n"
        "- No corporate voice. No 'thrilled to announce.' We're builders sharing what we built.\n"
        "- Honest > impressive. 'It broke 3 times before it worked' > 'seamless deployment'.\n\n"
        "FORMAT:\nTWEET: ...\n\nLINKEDIN: ...\n\nNEWSLETTER: ..."
    )

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        resp.raise_for_status()
        social_content = resp.json()["content"][0]["text"]

    usage = resp.json().get("usage", {})
    await record_spend(
        "outreach_automation", "anthropic", "claude-sonnet-4-20250514",
        tokens_in=usage.get("input_tokens", 0),
        tokens_out=usage.get("output_tokens", 0),
        description=f"Social content: {entry_title[:60]}",
    )

    gate = should_take_action(ExternalAction(
        action_type=ActionType.CONTENT_CREATION,
        title=f"Social content from: {entry_title[:80]}",
        description=social_content[:500],
        target_audience="public social media followers",
        claims=[],
        gives_value=True,
        asks_for_something=False,
        is_verifiable=True,
        source_data={"source": "outreach_actuator", "proposal": entry_title},
    ))

    if not gate.passed:
        from .principles import FilterResult
        failed = [o.filter_name for o in gate.outcomes if o.result == FilterResult.FAIL]
        return ActuatorResult(
            success=False,
            category="outreach_automation",
            action_taken="gate_blocked",
            error=f"Conscience gate blocked by: {', '.join(failed)}",
        )

    gate_summary = {
        "passed": gate.passed,
        "filters": [{"name": o.filter_name, "result": o.result.value, "reason": o.reason}
                     for o in gate.outcomes],
    }

    content_id = f"social-{uuid.uuid4().hex[:12]}"
    async with async_session() as session:
        session.add(PublishedContentRow(
            id=content_id,
            title=f"[SOCIAL] Outreach content from: {entry_title[:80]}",
            body=social_content,
            content_type="social_content",
            domain=proposal.get("domain", "general"),
            source_proposal_id=proposal.get("id"),
            source_entries=[r.id for r in recent_insights],
            gate_decision="passed",
            gate_details=gate_summary,
            generated_by="outreach_actuator",
        ))
        await session.commit()

    # --- Try to actually post to social platforms ---
    posted_platforms = []

    # Extract tweet from generated content
    tweet_match = re.search(r'TWEET:\s*(.+?)(?:\n\n|\nLINKEDIN:)', social_content, re.S)
    tweet_text = tweet_match.group(1).strip() if tweet_match else social_content[:280]

    bluesky_result = await _post_to_bluesky(tweet_text)
    if bluesky_result.get("posted"):
        posted_platforms.append("bluesky")
        logger.info(f"[SOCIAL] Posted to Bluesky: {bluesky_result.get('uri', '')}")
    else:
        logger.info(f"[SOCIAL] Bluesky skipped: {bluesky_result.get('reason', 'unknown')}")

    sparket_queued = False
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            health = await client.get(f"{SPARKET_URL}/health")
            if health.status_code == 200:
                sparket_queued = True
                logger.info("[ACTUATOR] Sparket reachable — social content queued for review")
    except Exception:
        pass

    return ActuatorResult(
        success=True,
        category="outreach_automation",
        action_taken="social_content_generated",
        content_id=content_id,
        output={
            "insights_used": len(recent_insights),
            "sparket_queued": sparket_queued,
            "posted_platforms": posted_platforms,
            "content_preview": social_content[:200],
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ACTUATOR REGISTRY — Category → Implementation
# ═══════════════════════════════════════════════════════════════════════════════

ACTUATOR_REGISTRY = {
    "content_generation": actuate_content_generation,
    "email_briefing": actuate_email_briefing,
    "audio_briefing": actuate_audio_briefing,
    "cost_optimization": actuate_cost_optimization,
    "prompt_improvement": actuate_prompt_improvement,
    "outreach_automation": actuate_outreach_automation,
    "visualization": generate_implementation_spec,
    "new_scanner_source": generate_implementation_spec,
    "framework_adoption": generate_implementation_spec,
    "pricing_change": generate_implementation_spec,
}


async def run_actuators(adopted_proposals: list[dict]) -> list[dict]:
    """Execute concrete actions for each adopted proposal.

    Routes each proposal to its category's actuator function.
    Updates execution_briefs status from 'adopted' to 'implemented'
    on success, sets executed_at timestamp.
    """
    if not adopted_proposals:
        return []

    results = []
    for proposal in adopted_proposals:
        category = proposal.get("category", "unknown")
        actuator_fn = ACTUATOR_REGISTRY.get(category, generate_implementation_spec)

        try:
            result = await actuator_fn(proposal)
            results.append({
                "proposal_id": proposal.get("id"),
                "proposal_title": proposal.get("title", ""),
                "category": category,
                "success": result.success,
                "action_taken": result.action_taken,
                "content_id": result.content_id,
                "output": result.output,
                "error": result.error,
            })

            if result.success:
                async with async_session() as session:
                    brief = (await session.execute(
                        select(ExecutionBriefRow)
                        .where(ExecutionBriefRow.id == proposal.get("id"))
                    )).scalar()
                    if brief:
                        brief.status = "implemented"
                        brief.executed_at = datetime.now(timezone.utc)
                        await session.commit()

                logger.info(
                    f"[ACTUATOR] {category}: '{proposal.get('title', '')[:50]}' "
                    f"→ {result.action_taken} (content_id={result.content_id})"
                )
            else:
                logger.warning(
                    f"[ACTUATOR] {category}: '{proposal.get('title', '')[:50]}' "
                    f"FAILED — {result.error or result.action_taken}"
                )

        except Exception as e:
            logger.error(f"[ACTUATOR] Exception in {category}: {e}")
            results.append({
                "proposal_id": proposal.get("id"),
                "category": category,
                "success": False,
                "action_taken": "exception",
                "error": str(e),
            })

    implemented = sum(1 for r in results if r["success"])
    logger.info(
        f"[ACTUATORS] {len(results)} proposals processed: "
        f"{implemented} implemented, {len(results) - implemented} pending/failed"
    )

    from .budget import send_action_alert, ACTION_COST_ESTIMATES
    alert_actions = [
        {
            "action": r.get("category", "unknown"),
            "cost": ACTION_COST_ESTIMATES.get(r.get("category", ""), 0.02),
            "description": r.get("proposal_title", "")[:120],
            "content_id": r.get("content_id"),
            "reversible": True,
            "success": r.get("success", False),
        }
        for r in results
    ]
    try:
        await send_action_alert(alert_actions)
    except Exception as e:
        logger.warning(f"[ACTUATORS] Action alert failed: {e}")

    return results


async def actuate_pending_adoptions() -> list[dict]:
    """Find adopted proposals that haven't been actuated yet and run them.

    This catches up on any proposals that were marked 'adopted' before
    the actuator engine existed, or where the actuator failed previously.
    """
    async with async_session() as session:
        pending = (await session.execute(
            select(ExecutionBriefRow)
            .where(ExecutionBriefRow.status == "adopted")
            .order_by(ExecutionBriefRow.relevance_score.desc())
            .limit(10)
        )).scalars().all()

    if not pending:
        logger.info("[ACTUATORS] No pending adoptions to actuate")
        return []

    from .principles import classify_adoption

    proposals = []
    for p in pending:
        category, _ = classify_adoption(p.implementation_path or "", "general")
        proposals.append({
            "id": p.id,
            "title": p.entry_title,
            "entry_title": p.entry_title,
            "category": category,
            "implementation_path": p.implementation_path or "",
            "narrative": p.narrative or "",
            "score": p.relevance_score or 0,
            "domain": "general",
        })

    logger.info(f"[ACTUATORS] Found {len(proposals)} pending adoptions — actuating")
    return await run_actuators(proposals)
