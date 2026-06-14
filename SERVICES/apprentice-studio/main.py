"""
Apprentice Studio — service entrypoint.

Runs:
  - FastAPI for status + manual cycle triggers (read-only-ish for human review).
  - APScheduler for the proactive cadence (daily pulse, weekly review).

This service intentionally cannot send external messages or spend money.
Drafts go to ARTIFACTS/. Decisions go to STATE/PROGRAM.md.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from funnel import get_funnel
from funnel.screener import screen as screen_candidate
from orchestrator import get_orchestrator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("apprentice_studio.main")


# ---- Proactive triggers --------------------------------------------------

async def daily_pulse() -> None:
    """Daily 7am cycle. Emits an aggregated report into PROGRAM.md."""
    logger.info("Daily pulse running...")
    orch = get_orchestrator()
    report = await orch.run_cycle()
    logger.info(
        "Daily pulse complete. Decisions needed: %d, blocks: %d",
        len(report.decisions_needed),
        len(report.blocks),
    )


async def weekly_review() -> None:
    """Weekly Monday review. Writes to ARTIFACTS/weekly-reviews/."""
    logger.info("Weekly review running...")
    orch = get_orchestrator()
    markdown = await orch.run_weekly_review()
    logger.info("Weekly review complete. %d chars.", len(markdown))


# ---- FastAPI app ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    tz = os.getenv("APPRENTICE_STUDIO_TZ", "America/Denver")

    scheduler.add_job(
        daily_pulse,
        CronTrigger.from_crontab("0 7 * * *", timezone=tz),
        id="daily_pulse",
        replace_existing=True,
    )
    scheduler.add_job(
        weekly_review,
        CronTrigger.from_crontab("0 8 * * 1", timezone=tz),
        id="weekly_review",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (timezone=%s)", tz)

    asyncio.create_task(_initial_cycle())

    try:
        yield
    finally:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


async def _initial_cycle() -> None:
    """On boot, run one cycle so PROGRAM.md is fresh from the start."""
    await asyncio.sleep(1)
    try:
        await daily_pulse()
    except Exception:
        logger.exception("Initial cycle failed")


app = FastAPI(
    title="Apprentice Studio",
    description="AI-native studio for training builders and shipping products. AI holds it down.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
async def root() -> dict:
    return {
        "service": "apprentice-studio",
        "version": "0.1.0",
        "phase": "0 — Founding Apprentice Search",
        "now": datetime.now().isoformat(),
    }


@app.get("/status")
async def status() -> dict:
    return get_orchestrator().status()


@app.post("/cycle")
async def trigger_cycle() -> dict:
    """Manually trigger a cycle (idempotent). Useful for testing / on-demand pulse."""
    report = await get_orchestrator().run_cycle()
    return {
        "ran_at": datetime.now().isoformat(),
        "summary": report.summary,
        "decisions_needed": report.decisions_needed,
        "blocks": report.blocks,
    }


@app.post("/weekly-review")
async def trigger_weekly_review() -> dict:
    markdown = await get_orchestrator().run_weekly_review()
    return {"ran_at": datetime.now().isoformat(), "markdown": markdown}


# --- Funnel endpoints -----------------------------------------------------

class ApplicationIn(BaseModel):
    """Public application form payload. Mirrors ARTIFACTS/cohort-1-application.md."""

    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Best email")
    location: str = Field("", description="City / country")
    availability: str = Field("", description="Available full-time 10 weeks?")
    shipped_thing: str = Field("", description="Link + paragraph on one shipped thing")
    ai_workflow: str = Field("", description="Default AI workflow")
    ai_collaborator_story: str = Field("", description="A project where AI was your collaborator")
    what_to_build: str = Field("", description="What you'd want to build during the 10 weeks")
    lens_fit: str = Field("", description="Three-lenses fit (regen / sovereignty / consciousness)")
    why_this: str = Field("", description="Why this and not a normal job")
    equity_ok: str = Field("", description="OK with the 70/20/10 split? yes/no/discuss")
    other: str = Field("", description="Anything else")
    source: str = Field("inbound", description="Where they came from")


@app.post("/apply", status_code=201)
async def apply(payload: ApplicationIn) -> dict:
    """Public endpoint: receive an application. Stores + auto-screens."""
    funnel = get_funnel()
    application = payload.model_dump(exclude={"name", "email", "source"})
    cand = funnel.add_application(
        name=payload.name,
        email=str(payload.email),
        application=application,
        source=payload.source or "inbound",
    )
    result = screen_candidate(cand)
    funnel.save()
    return {
        "id": cand.id,
        "stage": cand.stage.value,
        "screening_score": result.score,
        "message": "Application received. We respond within 7 days.",
    }


@app.get("/funnel/status")
async def funnel_status() -> dict:
    """Funnel snapshot. Read-only."""
    funnel = get_funnel()
    needs = funnel.needs_action()
    return {
        "summary": funnel.funnel_summary(),
        "needs_action": [
            {
                "id": c.id,
                "name": c.name,
                "stage": c.stage.value,
                "best_score": max(
                    c.challenge_score or 0, c.screening_score or 0, c.interview_score or 0
                ),
            }
            for c in needs[:25]
        ],
        "total_candidates": len(funnel.candidates),
    }


@app.get("/funnel/candidate/{candidate_id}")
async def funnel_candidate(candidate_id: str) -> dict:
    funnel = get_funnel()
    cand = funnel.get(candidate_id)
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return cand.to_dict()


def cli() -> None:
    """Run the service via uvicorn from the command line."""
    import uvicorn

    host = os.getenv("APPRENTICE_STUDIO_HOST", "127.0.0.1")
    port = int(os.getenv("APPRENTICE_STUDIO_PORT", "8090"))
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    cli()
