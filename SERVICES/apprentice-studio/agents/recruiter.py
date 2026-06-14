"""
Recruiter Agent — drafts and manages the talent pipeline.

Responsibilities:
  - Draft + maintain founding apprentice job post (ARTIFACTS/founding-apprentice-job-post.md).
  - Draft + maintain cohort 1 application (ARTIFACTS/cohort-1-application.md).
  - Track applicants in COHORT_1.json.
  - Run 48-hour build challenge as filter (designs the brief; humans grade).
  - Schedule final interviews with owner + founding apprentice (drafts only — does not send).

Guardrails:
  - Cannot post jobs externally without human approval.
  - Cannot email applicants without human approval.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .base import AgentReport, ProposalArtifact, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.recruiter")


class RecruiterAgent(StudioAgent):
    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.RECRUITER,
            model="claude-3-5-sonnet-20241022",
            description="Drafts roles + applications. Screens applicants. Schedules interviews.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()
        cohort = self.read_cohort()
        applicants = cohort.get("applicants", [])
        shortlist = cohort.get("shortlist", [])

        decisions: list[str] = []
        artifacts: list[ProposalArtifact] = []

        if not applicants and cohort.get("status") == "planning":
            decisions.append(
                "Confirm founding apprentice job post and authorise external posting "
                "(see ARTIFACTS/founding-apprentice-job-post.md)."
            )

        return AgentReport(
            agent=self.role,
            summary=(
                f"Recruiter idle. Applicants: {len(applicants)}, shortlist: {len(shortlist)}. "
                "Drafts ready for human review."
            ),
            decisions_needed=decisions,
            metrics={"applicants": len(applicants), "shortlist": len(shortlist)},
            proposed_artifacts=artifacts,
        )
