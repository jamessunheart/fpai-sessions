"""
Curriculum Agent — designs and adapts the cohort curriculum.

Responsibilities:
  - Maintain the 10-week cohort curriculum: kickoff retreat, build sprint, demo retreat.
  - Generate weekly assignments per apprentice based on their project track.
  - Track each apprentice's progress in COHORT_1.json.
  - Recommend curriculum changes based on what's working / what's not.

Guardrails:
  - Cannot reassign apprentices to new tracks without human approval.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .base import AgentReport, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.curriculum")


class CurriculumAgent(StudioAgent):
    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.CURRICULUM,
            model="claude-3-5-sonnet-20241022",
            description="Designs curriculum, weekly assignments, progress tracking.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()
        cohort = self.read_cohort()
        accepted = cohort.get("accepted", [])

        decisions: list[str] = []
        if cohort.get("status") == "planning" and not accepted:
            decisions.append(
                "Approve 3 product tracks for cohort 1 (see ARTIFACTS/90-day-plan.md)."
            )

        return AgentReport(
            agent=self.role,
            summary=(
                f"Curriculum: 10-week hybrid template ready. Accepted apprentices: {len(accepted)}. "
                "Weekly assignment generator activates once apprentices are accepted."
            ),
            decisions_needed=decisions,
            metrics={"accepted": len(accepted)},
        )
