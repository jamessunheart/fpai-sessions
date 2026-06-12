"""
Builder Mentor Agent — pairs with each apprentice as their AI co-builder.

Responsibilities:
  - For each apprentice, run a daily co-build pulse (review code, suggest next moves).
  - Bridge to existing aria-builder service for actual code execution.
  - Track ship/no-ship status per project; trigger "ship by week 8 or pivot" rule.
  - Surface stuck apprentices to Aria Coach for values/energy support.

Guardrails:
  - Cannot deploy to production without apprentice + owner approval.
  - Cannot rewrite an apprentice's project without their consent.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .base import AgentReport, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.builder_mentor")


class BuilderMentorAgent(StudioAgent):
    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.BUILDER_MENTOR,
            model="claude-3-5-sonnet-20241022",
            description="AI co-builder pairing with each apprentice.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()
        cohort = self.read_cohort()
        accepted = cohort.get("accepted", [])
        in_progress = cohort.get("products_in_progress", [])
        shipped = cohort.get("products_shipped", [])

        return AgentReport(
            agent=self.role,
            summary=(
                f"Builder Mentor: {len(accepted)} apprentices, "
                f"{len(in_progress)} products in progress, {len(shipped)} shipped. "
                "Daily co-build pulses begin once apprentices are accepted."
            ),
            metrics={
                "apprentices": len(accepted),
                "products_in_progress": len(in_progress),
                "products_shipped": len(shipped),
            },
        )
