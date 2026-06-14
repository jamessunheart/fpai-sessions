"""
Studio Director — orchestrates the seven other agents.

Responsibilities:
  - Daily heartbeat: aggregate reports, update PROGRAM.md health section.
  - Weekly review: full program review with metrics + recommendations.
  - Escalation: if a block exceeds 24h, escalate to human via aria-bridge.
  - Decision routing: pulls "Decisions Awaiting Human" from each agent into PROGRAM.md.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Iterable

from .base import AgentReport, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.studio_director")


class StudioDirectorAgent(StudioAgent):
    """The orchestrator agent."""

    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.DIRECTOR,
            model="claude-3-5-sonnet-20241022",
            description="Orchestrates the studio. Daily pulse, weekly review, escalations.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()
        return AgentReport(
            agent=self.role,
            summary="Studio Director pulse: agents idle, awaiting first cycle.",
            metrics={"phase": "0 — Founding Apprentice Search"},
        )

    async def aggregate(self, reports: Iterable[AgentReport]) -> AgentReport:
        """Aggregate other agents' reports into a single director-level report."""
        decisions_needed: list[str] = []
        blocks: list[str] = []
        artifacts: list = []
        summaries: list[str] = []

        for r in reports:
            summaries.append(f"- {r.agent.value}: {r.summary}")
            decisions_needed.extend(r.decisions_needed)
            blocks.extend(r.blocks)
            artifacts.extend(r.proposed_artifacts)

        for d in decisions_needed:
            self.append_decision_proposal(d)

        return AgentReport(
            agent=self.role,
            summary="Aggregated cycle:\n" + "\n".join(summaries),
            decisions_needed=decisions_needed,
            blocks=blocks,
            proposed_artifacts=artifacts,
        )

    async def weekly_review(self, reports: Iterable[AgentReport]) -> str:
        """Render a weekly review summary suitable for Telegram + NOW.md."""
        cohort = self.read_cohort()
        budget = self.read_budget()
        spent = budget.get("spent_to_date", 0)
        total = budget.get("pilot_budget_total", 0)
        pct = (spent / total * 100) if total else 0

        lines = [
            "# Apprentice Studio — Weekly Review",
            f"_{datetime.now().strftime('%Y-%m-%d')}_",
            "",
            "## Phase",
            cohort.get("status", "planning"),
            "",
            "## Spend",
            f"${spent:,.0f} / ${total:,.0f} ({pct:.1f}%)",
            "",
            "## Reports",
        ]
        for r in reports:
            lines.append(f"### {r.agent.value}")
            lines.append(r.summary)
            if r.decisions_needed:
                lines.append("**Decisions needed:**")
                lines.extend(f"- {d}" for d in r.decisions_needed)
            if r.blocks:
                lines.append("**Blocks:**")
                lines.extend(f"- {b}" for b in r.blocks)
            lines.append("")
        return "\n".join(lines)
