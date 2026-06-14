"""
Aria Coach Agent — values, energy, alignment 1:1s with each apprentice.

Responsibilities:
  - Daily check-in with each apprentice (3-5 questions, conversational).
  - Surface energy/alignment issues to the Studio Director.
  - Aggregate apprentice voice into the weekly review.
  - Bridge to the existing aria-bridge soul/consciousness layer.

This agent is not about productivity. It's the human-flourishing pulse of the studio.

Guardrails:
  - Apprentice 1:1 transcripts are private. Only aggregated themes go to the Director.
  - Cannot share apprentice details with anyone but that apprentice + the human owner.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .base import AgentReport, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.aria_coach")


class AriaCoachAgent(StudioAgent):
    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.ARIA_COACH,
            model="claude-3-5-sonnet-20241022",
            description="1:1 coaching for each apprentice on values, energy, alignment.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()
        cohort = self.read_cohort()
        accepted = cohort.get("accepted", [])

        return AgentReport(
            agent=self.role,
            summary=(
                f"Aria Coach standing by for {len(accepted)} apprentices. "
                "Daily 1:1 check-ins begin once apprentices are onboarded."
            ),
            metrics={"active_coachees": len(accepted)},
        )
