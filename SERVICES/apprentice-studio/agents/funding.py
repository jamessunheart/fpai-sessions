"""
Funding Agent — researches and tracks funding leads.

Responsibilities:
  - Maintain ARTIFACTS/funding-leads.md with active leads + status.
  - Research grants, sponsors, aligned angels weekly.
  - Draft pitches per lead.
  - Track API credit partnerships (OpenAI, Anthropic, Google) — these are cheap wins.

Funding strategy (in order):
  1. Cohort 1 ships first; revenue is proof.
  2. API credit partnerships next.
  3. Aligned angels who care about consciousness tech.
  4. Government grants last (slow).

Guardrails:
  - Cannot contact funders without human approval.
  - Pitches go to ARTIFACTS/ for review.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .base import AgentReport, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.funding")


class FundingAgent(StudioAgent):
    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.FUNDING,
            model="claude-3-5-sonnet-20241022",
            description="Researches funding leads, drafts pitches, tracks pipeline.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()

        return AgentReport(
            agent=self.role,
            summary=(
                "Funding: 5 initial leads researched (see ARTIFACTS/funding-leads.md). "
                "Holding outreach until cohort 1 has shipped product (per strategy)."
            ),
            decisions_needed=[
                "Approve API credit partnership outreach to Anthropic + OpenAI now (low-risk, high-value).",
            ],
            metrics={"leads_tracked": 5, "pitches_sent": 0},
        )
