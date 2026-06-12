"""
Operations Agent — budget, logistics, contracts, IP.

Responsibilities:
  - Track BUDGET.json: spend vs plan, flag overruns.
  - Plan retreats (kickoff + demo): venue research, food, travel, schedule.
  - Maintain apprentice agreement template (covers IP split, default license back to FPAI).
  - Maintain cohort onboarding checklist.

Guardrails:
  - Cannot spend money. Flags any spend above $0; human approves.
  - Cannot sign contracts.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .base import AgentReport, StudioAgent, StudioRole

logger = logging.getLogger("apprentice_studio.operations")


class OperationsAgent(StudioAgent):
    def __init__(self) -> None:
        super().__init__(
            role=StudioRole.OPERATIONS,
            model="claude-3-5-sonnet-20241022",
            description="Budget, retreat logistics, contracts, IP templates.",
        )

    async def heartbeat(self) -> AgentReport:
        self.last_run = datetime.now()
        budget = self.read_budget()
        total = budget.get("pilot_budget_total", 0)
        spent = budget.get("spent_to_date", 0)
        pending = budget.get("pending_approvals", [])

        decisions: list[str] = []
        if total and not spent:
            decisions.append(
                f"Approve $150k pilot budget allocation (see STATE/BUDGET.json — categories already split)."
            )

        return AgentReport(
            agent=self.role,
            summary=(
                f"Operations: budget ${spent:,.0f}/${total:,.0f}. "
                f"{len(pending)} pending approvals. Retreat venue research begins on cohort approval."
            ),
            decisions_needed=decisions,
            metrics={"budget_spent": spent, "budget_total": total, "pending_approvals": len(pending)},
        )
