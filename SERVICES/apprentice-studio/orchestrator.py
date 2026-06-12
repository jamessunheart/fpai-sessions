"""
Studio Orchestrator — coordinates the eight agents, runs cycles, escalates blocks.

Mirrors the aria-command orchestrator pattern but specialised for program ops
rather than code/deploy/trade tasks.

Usage:
    orch = StudioOrchestrator()
    await orch.run_cycle()           # single cycle, all agents heartbeat
    await orch.run_weekly_review()   # full review, returns markdown
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from agents import (
    AriaCoachAgent,
    BuilderMentorAgent,
    CommsAgent,
    CurriculumAgent,
    FundingAgent,
    OperationsAgent,
    RecruiterAgent,
    StudioAgent,
    StudioDirectorAgent,
)
from agents.base import STATE_DIR, AgentReport

logger = logging.getLogger("apprentice_studio.orchestrator")


class StudioOrchestrator:
    """Coordinates Apprentice Studio agents."""

    def __init__(self) -> None:
        self.director = StudioDirectorAgent()
        self.specialised: list[StudioAgent] = [
            RecruiterAgent(),
            CurriculumAgent(),
            BuilderMentorAgent(),
            CommsAgent(),
            FundingAgent(),
            OperationsAgent(),
            AriaCoachAgent(),
        ]
        self._last_cycle: Optional[datetime] = None
        self._last_weekly_review: Optional[datetime] = None
        logger.info(
            "StudioOrchestrator ready: %d specialised agents + director", len(self.specialised)
        )

    @property
    def all_agents(self) -> list[StudioAgent]:
        return [self.director, *self.specialised]

    async def run_cycle(self) -> AgentReport:
        """Run one heartbeat cycle across all agents and aggregate via the director."""
        reports = await asyncio.gather(*[a.heartbeat() for a in self.specialised])
        aggregated = await self.director.aggregate(reports)
        self._last_cycle = datetime.now()
        return aggregated

    async def run_weekly_review(self) -> str:
        """Run a full weekly review. Returns markdown."""
        reports = await asyncio.gather(*[a.heartbeat() for a in self.specialised])
        await self.director.aggregate(reports)  # also updates PROGRAM.md decisions
        markdown = await self.director.weekly_review(reports)
        self._last_weekly_review = datetime.now()

        archive_dir = STATE_DIR.parent / "ARTIFACTS" / "weekly-reviews"
        archive_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d")
        (archive_dir / f"{stamp}.md").write_text(markdown, encoding="utf-8")

        return markdown

    def status(self) -> dict:
        return {
            "last_cycle": self._last_cycle.isoformat() if self._last_cycle else None,
            "last_weekly_review": (
                self._last_weekly_review.isoformat() if self._last_weekly_review else None
            ),
            "agents": [a.get_status() for a in self.all_agents],
        }


_orchestrator: Optional[StudioOrchestrator] = None


def get_orchestrator() -> StudioOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = StudioOrchestrator()
    return _orchestrator
