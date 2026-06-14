"""
Comms Agent — owns the studio's public voice (drafts only).

Responsibilities:
  - Maintain manifesto (ARTIFACTS/manifesto.md).
  - Draft weekly public posts ("here's what we built and learned this week").
  - Plan demo day (livestream, agenda, invite list — drafts).
  - Draft alumni newsletter quarterly.
  - Maintain studio site outline (ARTIFACTS/studio-site-outline.md).

Guardrails:
  - Cannot publish anything externally without human approval.
  - All drafts go to ARTIFACTS/ for review.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .base import AgentReport, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.comms")


class CommsAgent(StudioAgent):
    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.COMMS,
            model="claude-3-5-sonnet-20241022",
            description="Drafts manifesto, public posts, demo day plan, alumni comms.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()

        return AgentReport(
            agent=self.role,
            summary=(
                "Comms: manifesto + studio site outline drafted. "
                "Weekly post generator activates once cohort 1 begins."
            ),
            decisions_needed=[
                "Approve public manifesto (ARTIFACTS/manifesto.md)",
                "Approve studio site outline (ARTIFACTS/studio-site-outline.md)",
            ],
            metrics={"public_posts_published": 0},
        )
