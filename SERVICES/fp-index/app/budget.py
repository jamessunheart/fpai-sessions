"""
Budget & Autonomy Governor
===========================

Gives the system a spending budget, tracks every dollar, and provides
pause/resume controls with post-action alerts to the human operator.

Architecture:
  - BudgetLedgerRow: tracks every API call and its estimated cost
  - BudgetConfig: daily/monthly caps, per-action limits, pause state
  - check_budget(): pre-flight gate — returns False if over budget
  - record_spend(): log actual spend after an API call
  - get_budget_status(): real-time spend vs limits
  - pause/resume: disk-based + DB flag for reliability
  - send_action_alert(): email after each action cycle with costs + undo links

Cost estimates (Claude Sonnet input/output, March 2026):
  - Input:  ~$3/M tokens
  - Output: ~$15/M tokens
  - Typical 800-token generation: ~$0.02-0.04 per call
  - OpenAI TTS: ~$15/M chars
  - Groq: ~$0.27/M tokens (negligible)

"A system that spends without oversight is not autonomous — it's reckless.
 A system that tracks every dollar and asks permission for big moves
 is autonomous AND trustworthy."
"""

import hashlib
import hmac
import json
import logging
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, Boolean, select, func, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession

from .models.database import Base, async_session

logger = logging.getLogger("fp_index.budget")

PAUSE_FILE = Path("/tmp/fpai_budget_paused")
REVIEWER_EMAIL = os.getenv("REVIEWER_EMAIL", "james@fullpotential.com")
BASE_URL = "https://fullpotential.ai"
REVIEW_SECRET = os.getenv("REVIEW_SECRET", "fpai-review-2026")
# Host or logical surface id for multi-server rollups (fp-index, metaclaw, dev, …).
COST_ORIGIN = (os.getenv("FPI_COST_ORIGIN") or "primary").strip()[:64] or "primary"


# ═══════════════════════════════════════════════════════════════════════════════
# Database Model
# ═══════════════════════════════════════════════════════════════════════════════

class BudgetLedgerRow(Base):
    __tablename__ = "budget_ledger"

    id = Column(Integer, primary_key=True, autoincrement=True)
    action_type = Column(String(50), nullable=False, index=True)
    provider = Column(String(30), nullable=False)
    model = Column(String(80), default="")
    tokens_in = Column(Integer, default=0)
    tokens_out = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, nullable=False)
    description = Column(Text, default="")
    reversible = Column(Boolean, default=True)
    content_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    origin = Column(String(64), default="", index=True)


class BudgetConfigRow(Base):
    __tablename__ = "budget_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    daily_limit_usd = Column(Float, nullable=False, default=5.0)
    monthly_limit_usd = Column(Float, nullable=False, default=100.0)
    per_action_limit_usd = Column(Float, nullable=False, default=1.0)
    paused = Column(Boolean, default=False)
    pause_reason = Column(Text, default="")
    paused_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CostActualRow(Base):
    """Vendor-reported or invoice amounts for reconciliation vs ledger estimates."""

    __tablename__ = "cost_actuals"
    __table_args__ = (
        UniqueConstraint("granularity", "period_key", "provider", name="uq_cost_actual_period_provider"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    granularity = Column(String(16), nullable=False, index=True)  # daily | weekly | monthly
    period_key = Column(String(32), nullable=False, index=True)  # e.g. 2026-04-24, 2026-W17, 2026-04
    provider = Column(String(32), nullable=False, index=True)  # anthropic | openai | all | …
    amount_usd = Column(Float, nullable=False)
    source = Column(String(64), nullable=False, default="manual")
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════
# Cost Estimates by Provider/Action
# ═══════════════════════════════════════════════════════════════════════════════

COST_ESTIMATES = {
    "anthropic": {
        "claude-sonnet-4-20250514": {"input_per_mtok": 3.0, "output_per_mtok": 15.0},
        "claude-sonnet-4-5": {"input_per_mtok": 3.0, "output_per_mtok": 15.0},
        "claude-haiku-4-5": {"input_per_mtok": 1.0, "output_per_mtok": 5.0},
        "claude-3-5-haiku-20241022": {"input_per_mtok": 1.0, "output_per_mtok": 5.0},
        "default": {"input_per_mtok": 3.0, "output_per_mtok": 15.0},
    },
    "openai": {
        "tts-1": {"per_1k_chars": 0.015},
        "default": {"input_per_mtok": 5.0, "output_per_mtok": 15.0},
    },
    "groq": {
        "default": {"input_per_mtok": 0.05, "output_per_mtok": 0.08},
    },
    "ollama": {
        "default": {"input_per_mtok": 0.0, "output_per_mtok": 0.0},
    },
}

ACTION_COST_ESTIMATES = {
    "content_generation":  0.04,
    "prompt_improvement":  0.04,
    "briefing_synthesis":  0.012,
    "outreach_automation": 0.05,
    "narrate_action":      0.03,
    "adoption_evaluation": 0.02,
    "audio_briefing":      0.10,
    "cost_optimization":   0.00,
    "email_briefing":      0.00,
    "provider_benchmark":  0.03,
    # Self-assembly + field (preflight only; actual charge = token × price table)
    "field_sensor_reflection": 0.008,
    "capability_probe_candidate": 0.03,
    "capability_probe_judge": 0.01,
    "integration_proposer": 0.05,
    "integration_conscience": 0.008,
}


def estimate_cost(provider: str, model: str, tokens_in: int = 0,
                  tokens_out: int = 0, chars: int = 0) -> float:
    """Estimate USD cost for an API call."""
    provider_costs = COST_ESTIMATES.get(provider, COST_ESTIMATES.get("anthropic", {}))
    model_costs = provider_costs.get(model, provider_costs.get("default", {}))

    if "per_1k_chars" in model_costs and chars > 0:
        return (chars / 1000) * model_costs["per_1k_chars"]

    input_cost = (tokens_in / 1_000_000) * model_costs.get("input_per_mtok", 3.0)
    output_cost = (tokens_out / 1_000_000) * model_costs.get("output_per_mtok", 15.0)
    return round(input_cost + output_cost, 6)


# ═══════════════════════════════════════════════════════════════════════════════
# Budget Gates
# ═══════════════════════════════════════════════════════════════════════════════

async def _ensure_config() -> BudgetConfigRow:
    """Get or create the budget config row."""
    async with async_session() as session:
        config = (await session.execute(
            select(BudgetConfigRow).limit(1)
        )).scalars().first()
        if not config:
            config = BudgetConfigRow(
                daily_limit_usd=5.0,
                monthly_limit_usd=100.0,
                per_action_limit_usd=1.0,
                paused=False,
            )
            session.add(config)
            await session.commit()
            await session.refresh(config)
        return config


async def is_paused() -> bool:
    """Check if the system is paused (disk file OR db flag)."""
    if PAUSE_FILE.exists():
        return True
    config = await _ensure_config()
    return config.paused


async def check_budget(action_type: str, estimated_cost: float = None) -> dict:
    """Pre-flight budget check. Returns {"allowed": bool, "reason": str, ...}."""
    if await is_paused():
        return {
            "allowed": False,
            "reason": "System is PAUSED. Resume via /api/v1/budget/resume or remove pause file.",
            "paused": True,
        }

    if estimated_cost is None:
        estimated_cost = ACTION_COST_ESTIMATES.get(action_type, 0.05)

    config = await _ensure_config()

    if estimated_cost > config.per_action_limit_usd:
        return {
            "allowed": False,
            "reason": f"Action cost ${estimated_cost:.4f} exceeds per-action limit ${config.per_action_limit_usd:.2f}",
            "estimated_cost": estimated_cost,
            "limit": config.per_action_limit_usd,
        }

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with async_session() as session:
        daily_spend = (await session.execute(
            select(func.coalesce(func.sum(BudgetLedgerRow.estimated_cost_usd), 0.0))
            .where(BudgetLedgerRow.timestamp >= today_start)
        )).scalar() or 0.0

        monthly_spend = (await session.execute(
            select(func.coalesce(func.sum(BudgetLedgerRow.estimated_cost_usd), 0.0))
            .where(BudgetLedgerRow.timestamp >= month_start)
        )).scalar() or 0.0

    if daily_spend + estimated_cost > config.daily_limit_usd:
        return {
            "allowed": False,
            "reason": f"Daily budget exhausted: ${daily_spend:.4f} spent of ${config.daily_limit_usd:.2f} limit",
            "daily_spend": daily_spend,
            "daily_limit": config.daily_limit_usd,
        }

    if monthly_spend + estimated_cost > config.monthly_limit_usd:
        return {
            "allowed": False,
            "reason": f"Monthly budget exhausted: ${monthly_spend:.4f} spent of ${config.monthly_limit_usd:.2f} limit",
            "monthly_spend": monthly_spend,
            "monthly_limit": config.monthly_limit_usd,
        }

    daily_remaining = config.daily_limit_usd - daily_spend
    monthly_remaining = config.monthly_limit_usd - monthly_spend
    daily_pct = (daily_spend / config.daily_limit_usd * 100) if config.daily_limit_usd > 0 else 0

    return {
        "allowed": True,
        "estimated_cost": estimated_cost,
        "daily_spend": round(daily_spend, 4),
        "daily_remaining": round(daily_remaining, 4),
        "daily_limit": config.daily_limit_usd,
        "daily_pct_used": round(daily_pct, 1),
        "monthly_spend": round(monthly_spend, 4),
        "monthly_remaining": round(monthly_remaining, 4),
        "monthly_limit": config.monthly_limit_usd,
    }


async def record_spend(action_type: str, provider: str, model: str = "",
                       tokens_in: int = 0, tokens_out: int = 0,
                       chars: int = 0, description: str = "",
                       content_id: str = None, reversible: bool = True,
                       estimated_cost: float = None) -> float:
    """Record an API spend in the ledger. Returns the estimated cost."""
    if estimated_cost is None:
        if tokens_in or tokens_out or chars:
            estimated_cost = estimate_cost(provider, model, tokens_in, tokens_out, chars)
        else:
            estimated_cost = ACTION_COST_ESTIMATES.get(action_type, 0.02)

    async with async_session() as session:
        session.add(BudgetLedgerRow(
            action_type=action_type,
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=estimated_cost,
            description=description[:500] if description else "",
            reversible=reversible,
            content_id=content_id,
            origin=COST_ORIGIN,
        ))
        await session.commit()

    logger.info(f"[BUDGET] Recorded ${estimated_cost:.4f} for {action_type} ({provider}/{model})")
    return estimated_cost


# ═══════════════════════════════════════════════════════════════════════════════
# Budget Status
# ═══════════════════════════════════════════════════════════════════════════════

async def get_budget_status() -> dict:
    """Full budget status: spend, limits, recent actions, pause state."""
    config = await _ensure_config()
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    async with async_session() as session:
        daily_spend = (await session.execute(
            select(func.coalesce(func.sum(BudgetLedgerRow.estimated_cost_usd), 0.0))
            .where(BudgetLedgerRow.timestamp >= today_start)
        )).scalar() or 0.0

        monthly_spend = (await session.execute(
            select(func.coalesce(func.sum(BudgetLedgerRow.estimated_cost_usd), 0.0))
            .where(BudgetLedgerRow.timestamp >= month_start)
        )).scalar() or 0.0

        total_all_time = (await session.execute(
            select(func.coalesce(func.sum(BudgetLedgerRow.estimated_cost_usd), 0.0))
        )).scalar() or 0.0

        daily_count = (await session.execute(
            select(func.count()).select_from(BudgetLedgerRow)
            .where(BudgetLedgerRow.timestamp >= today_start)
        )).scalar() or 0

        recent = (await session.execute(
            select(BudgetLedgerRow)
            .order_by(BudgetLedgerRow.timestamp.desc())
            .limit(10)
        )).scalars().all()

        spend_by_action = dict((await session.execute(
            select(BudgetLedgerRow.action_type,
                   func.sum(BudgetLedgerRow.estimated_cost_usd))
            .where(BudgetLedgerRow.timestamp >= month_start)
            .group_by(BudgetLedgerRow.action_type)
        )).all())

    paused = await is_paused()

    return {
        "paused": paused,
        "pause_reason": config.pause_reason if paused else None,
        "daily": {
            "spent": round(daily_spend, 4),
            "limit": config.daily_limit_usd,
            "remaining": round(config.daily_limit_usd - daily_spend, 4),
            "pct_used": round(daily_spend / config.daily_limit_usd * 100, 1) if config.daily_limit_usd > 0 else 0,
            "action_count": daily_count,
        },
        "monthly": {
            "spent": round(monthly_spend, 4),
            "limit": config.monthly_limit_usd,
            "remaining": round(config.monthly_limit_usd - monthly_spend, 4),
            "pct_used": round(monthly_spend / config.monthly_limit_usd * 100, 1) if config.monthly_limit_usd > 0 else 0,
        },
        "all_time_spend": round(total_all_time, 4),
        "per_action_limit": config.per_action_limit_usd,
        "spend_by_action_this_month": {k: round(v, 4) for k, v in spend_by_action.items()},
        "recent_actions": [
            {
                "action": r.action_type,
                "provider": r.provider,
                "cost": round(r.estimated_cost_usd, 4),
                "description": r.description[:100] if r.description else "",
                "reversible": r.reversible,
                "content_id": r.content_id,
                "when": r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else "",
            }
            for r in recent
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Pause / Resume
# ═══════════════════════════════════════════════════════════════════════════════

async def pause_system(reason: str = "Paused by operator") -> dict:
    """Pause all autonomous spending. Both disk file and DB flag for safety."""
    PAUSE_FILE.write_text(json.dumps({
        "paused_at": datetime.now(timezone.utc).isoformat(),
        "reason": reason,
    }))

    async with async_session() as session:
        config = (await session.execute(
            select(BudgetConfigRow).limit(1)
        )).scalars().first()
        if config:
            config.paused = True
            config.pause_reason = reason
            config.paused_at = datetime.now(timezone.utc)
            await session.commit()

    logger.warning(f"[BUDGET] SYSTEM PAUSED: {reason}")
    return {"paused": True, "reason": reason}


async def resume_system() -> dict:
    """Resume autonomous spending."""
    if PAUSE_FILE.exists():
        PAUSE_FILE.unlink()

    async with async_session() as session:
        config = (await session.execute(
            select(BudgetConfigRow).limit(1)
        )).scalars().first()
        if config:
            config.paused = False
            config.pause_reason = ""
            config.paused_at = None
            await session.commit()

    logger.info("[BUDGET] SYSTEM RESUMED")
    return {"paused": False}


async def update_limits(daily: float = None, monthly: float = None,
                        per_action: float = None) -> dict:
    """Update budget limits."""
    async with async_session() as session:
        config = (await session.execute(
            select(BudgetConfigRow).limit(1)
        )).scalars().first()
        if not config:
            config = BudgetConfigRow()
            session.add(config)

        if daily is not None:
            config.daily_limit_usd = daily
        if monthly is not None:
            config.monthly_limit_usd = monthly
        if per_action is not None:
            config.per_action_limit_usd = per_action
        config.updated_at = datetime.now(timezone.utc)
        await session.commit()

    logger.info(f"[BUDGET] Limits updated: daily=${config.daily_limit_usd}, "
                f"monthly=${config.monthly_limit_usd}, per_action=${config.per_action_limit_usd}")
    return {
        "daily_limit": config.daily_limit_usd,
        "monthly_limit": config.monthly_limit_usd,
        "per_action_limit": config.per_action_limit_usd,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Undo / Unpublish
# ═══════════════════════════════════════════════════════════════════════════════

async def unpublish_content(content_id: str) -> dict:
    """Unpublish a piece of content. Reversible action."""
    from .models.database import PublishedContentRow

    async with async_session() as session:
        content = (await session.execute(
            select(PublishedContentRow).where(PublishedContentRow.id == content_id)
        )).scalars().first()

        if not content:
            return {"success": False, "error": "Content not found"}

        title = content.title
        content.gate_decision = "unpublished"
        content.title = f"[UNPUBLISHED] {content.title}"
        await session.commit()

    logger.info(f"[BUDGET] Unpublished content: {content_id} — {title[:60]}")
    return {"success": True, "content_id": content_id, "title": title}


# ═══════════════════════════════════════════════════════════════════════════════
# Post-Action Alert Email
# ═══════════════════════════════════════════════════════════════════════════════

def _sign_budget_action(action: str) -> str:
    msg = f"budget:{action}:{REVIEW_SECRET}"
    return hashlib.sha256(msg.encode()).hexdigest()[:16]


async def send_action_alert(actions_taken: list[dict]) -> dict:
    """Email the operator after each action cycle with what happened,
    what it cost, and one-click pause/undo links."""
    if not actions_taken:
        return {"sent": False, "reason": "no actions"}

    status = await get_budget_status()
    pause_token = _sign_budget_action("pause")
    pause_url = f"{BASE_URL}/api/v1/budget/pause?token={pause_token}"

    total_cost = sum(a.get("cost", 0) for a in actions_taken)
    action_count = len(actions_taken)

    rows_html = ""
    rows_plain = ""
    for a in actions_taken:
        action_name = a.get("action", "unknown")
        cost = a.get("cost", 0)
        desc = a.get("description", "")[:120]
        content_id = a.get("content_id")
        reversible = a.get("reversible", True)

        undo_html = ""
        if content_id and reversible:
            undo_token = _sign_budget_action(f"undo:{content_id}")
            undo_url = f"{BASE_URL}/api/v1/budget/undo?content_id={content_id}&token={undo_token}"
            undo_html = f' <a href="{undo_url}" style="color:#ff6644;font-size:0.7rem;text-decoration:none">[undo]</a>'

        color = "#22cc88" if a.get("success") else "#ff4466"
        status_icon = "OK" if a.get("success") else "FAIL"

        rows_html += f"""
<tr>
  <td style="padding:10px;border-bottom:1px solid #1a1a2e">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <span style="color:{color};font-family:monospace;font-size:0.75rem;font-weight:600">{status_icon}</span>
        <span style="color:#e0e0f0;font-size:0.85rem;margin-left:8px">{action_name}</span>
        {undo_html}
      </div>
      <span style="color:#ffb800;font-family:monospace;font-size:0.8rem">${cost:.4f}</span>
    </div>
    <div style="color:#666;font-size:0.75rem;margin-top:4px">{desc}</div>
  </td>
</tr>"""

        undo_text = f" [undo available]" if content_id and reversible else ""
        rows_plain += f"  {status_icon} {action_name}: ${cost:.4f} — {desc}{undo_text}\n"

    daily_pct = status["daily"]["pct_used"]
    bar_color = "#22cc88" if daily_pct < 60 else "#ffb800" if daily_pct < 85 else "#ff4466"

    subject = f"FP System: {action_count} action{'s' if action_count != 1 else ''}, ${total_cost:.4f} spent — {daily_pct:.0f}% daily budget"

    plain = f"""Full Potential AI — Autonomous Action Report

{action_count} action{'s' if action_count != 1 else ''} completed. Estimated cost: ${total_cost:.4f}

{rows_plain}
Budget Status:
  Daily:   ${status['daily']['spent']:.4f} / ${status['daily']['limit']:.2f} ({daily_pct:.0f}%)
  Monthly: ${status['monthly']['spent']:.4f} / ${status['monthly']['limit']:.2f}

Pause all autonomous actions: {pause_url}
View budget: {BASE_URL}/api/v1/budget/status
"""

    html = f"""<!DOCTYPE html><html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#06060b;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<div style="max-width:600px;margin:0 auto;padding:32px 20px">

<div style="text-align:center;margin-bottom:20px">
  <a href="{BASE_URL}" style="color:#00d4ff;font-size:0.75rem;font-weight:600;letter-spacing:0.15em;text-decoration:none">FULL POTENTIAL AI</a>
  <div style="color:#666;font-size:0.65rem;margin-top:4px">AUTONOMOUS ACTION REPORT</div>
</div>

<div style="text-align:center;margin-bottom:20px">
  <span style="color:#e0e0e0;font-size:1.1rem;font-weight:600">{action_count} action{'s' if action_count != 1 else ''}</span>
  <span style="color:#666;margin:0 8px">·</span>
  <span style="color:#ffb800;font-family:monospace;font-size:1rem">${total_cost:.4f}</span>
</div>

<table style="width:100%;border-collapse:collapse;background:#0c0c14;border:1px solid #1a1a2e;border-radius:8px">
{rows_html}
</table>

<div style="margin-top:20px;padding:16px;background:#0c0c14;border:1px solid #1a1a2e;border-radius:8px">
  <div style="color:#666;font-size:0.7rem;letter-spacing:0.1em;margin-bottom:10px">BUDGET</div>
  <div style="display:flex;justify-content:space-between;margin-bottom:8px">
    <span style="color:#b0b0b0;font-size:0.85rem">Daily</span>
    <span style="color:#e0e0e0;font-family:monospace;font-size:0.85rem">${status['daily']['spent']:.4f} / ${status['daily']['limit']:.2f}</span>
  </div>
  <div style="background:#1a1a2e;border-radius:4px;height:8px;margin-bottom:12px">
    <div style="background:{bar_color};border-radius:4px;height:8px;width:{min(daily_pct, 100):.0f}%"></div>
  </div>
  <div style="display:flex;justify-content:space-between">
    <span style="color:#b0b0b0;font-size:0.85rem">Monthly</span>
    <span style="color:#e0e0e0;font-family:monospace;font-size:0.85rem">${status['monthly']['spent']:.4f} / ${status['monthly']['limit']:.2f}</span>
  </div>
</div>

<div style="margin-top:20px;text-align:center">
  <a href="{pause_url}" style="display:inline-block;padding:12px 32px;background:#ff4466;color:#fff;text-decoration:none;border-radius:6px;font-size:0.9rem;font-weight:600">Pause All Actions</a>
</div>

<div style="margin-top:12px;text-align:center">
  <a href="{BASE_URL}/api/v1/budget/status" style="color:#00d4ff;font-size:0.8rem;text-decoration:none">View full budget →</a>
</div>

<div style="margin-top:24px;text-align:center;color:#444;font-size:0.7rem">
  All actions are reversible. Click [undo] next to any action to unpublish.
  <br>Pause stops all autonomous spending immediately.
</div>

</div></body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = "Full Potential AI <noreply@fullpotential.ai>"
        msg["To"] = REVIEWER_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(plain, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("localhost", 25) as smtp:
            smtp.send_message(msg)

        logger.info(f"[BUDGET] Action alert sent: {action_count} actions, ${total_cost:.4f}")
        return {"sent": True, "actions": action_count, "cost": total_cost}
    except Exception as e:
        logger.error(f"[BUDGET] Alert email failed: {e}")
        return {"sent": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# Invoice / console actuals (reconciliation)
# ═══════════════════════════════════════════════════════════════════════════════

_GRANULARITIES = frozenset({"daily", "weekly", "monthly"})


async def upsert_cost_actual(
    granularity: str,
    period_key: str,
    provider: str,
    amount_usd: float,
    source: str = "manual",
    notes: str = "",
) -> dict[str, Any]:
    """Store or replace one billed amount for a calendar bucket (reconciliation)."""
    g = (granularity or "").strip().lower()[:16]
    if g not in _GRANULARITIES:
        raise ValueError(f"granularity must be one of {sorted(_GRANULARITIES)}")
    pk = (period_key or "").strip()[:32]
    if not pk:
        raise ValueError("period_key required")
    prov = (provider or "").strip().lower()[:32]
    if not prov:
        raise ValueError("provider required")
    now = datetime.now(timezone.utc)
    async with async_session() as session:
        row = (
            await session.execute(
                select(CostActualRow).where(
                    CostActualRow.granularity == g,
                    CostActualRow.period_key == pk,
                    CostActualRow.provider == prov,
                )
            )
        ).scalar_one_or_none()
        if row:
            row.amount_usd = float(amount_usd)
            row.source = (source or "manual")[:64]
            row.notes = (notes or "")[:4000]
            row.updated_at = now
        else:
            session.add(
                CostActualRow(
                    granularity=g,
                    period_key=pk,
                    provider=prov,
                    amount_usd=float(amount_usd),
                    source=(source or "manual")[:64],
                    notes=(notes or "")[:4000],
                    created_at=now,
                    updated_at=now,
                )
            )
        await session.commit()
    return {
        "ok": True,
        "granularity": g,
        "period_key": pk,
        "provider": prov,
        "amount_usd": round(float(amount_usd), 6),
        "source": (source or "manual")[:64],
    }


async def list_cost_actuals(limit: int = 500) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 2000))
    async with async_session() as session:
        rows = (
            (
                await session.execute(
                    select(CostActualRow).order_by(CostActualRow.updated_at.desc()).limit(limit)
                )
            )
            .scalars()
            .all()
        )
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "granularity": r.granularity,
                "period_key": r.period_key,
                "provider": r.provider,
                "amount_usd": round(float(r.amount_usd), 6),
                "source": r.source,
                "notes": r.notes or "",
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "updated_at": r.updated_at.isoformat() if r.updated_at else "",
            }
        )
    return out
