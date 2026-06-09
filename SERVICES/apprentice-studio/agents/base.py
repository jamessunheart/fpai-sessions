"""
Studio Agent Base — shared scaffolding for the eight Apprentice Studio agents.

Each StudioAgent:
  - Has a role (one of StudioRole).
  - Reads/writes to STATE/ (PROGRAM.md, COHORT_1.json, BUDGET.json, DECISIONS.md).
  - Drafts ProposalArtifacts into ARTIFACTS/ for human review.
  - Cannot send external messages or spend money without human approval.
  - Reports status to the Studio Director.
"""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("apprentice_studio.agents")


SERVICE_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = SERVICE_ROOT / "STATE"
ARTIFACTS_DIR = SERVICE_ROOT / "ARTIFACTS"


class StudioRole(Enum):
    """The eight roles in the studio."""

    DIRECTOR = "studio_director"
    RECRUITER = "recruiter"
    CURRICULUM = "curriculum"
    BUILDER_MENTOR = "builder_mentor"
    COMMS = "comms"
    FUNDING = "funding"
    OPERATIONS = "operations"
    ARIA_COACH = "aria_coach"


@dataclass
class ProposalArtifact:
    """A draft an agent puts into ARTIFACTS/ for human review."""

    title: str
    relative_path: str  # e.g. "founding-apprentice-job-post.md"
    summary: str
    requires_human_approval: bool = True
    risk: str = "low"  # low / medium / high
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentReport:
    """A report agents bubble up to the Studio Director."""

    agent: StudioRole
    summary: str
    decisions_needed: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    proposed_artifacts: list[ProposalArtifact] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class StudioAgent(ABC):
    """Base class for Apprentice Studio agents."""

    def __init__(
        self,
        role: StudioRole,
        model: str = "claude-3-5-sonnet-20241022",
        description: str = "",
    ) -> None:
        self.role = role
        self.model = model
        self.description = description
        self.is_active = True
        self.last_run: Optional[datetime] = None
        logger.info("Studio agent ready: %s (model=%s)", role.value, model)

    # --- lifecycle ---------------------------------------------------------

    @abstractmethod
    async def heartbeat(self) -> AgentReport:
        """
        Run one cycle of this agent's responsibilities.

        Should be idempotent: heartbeat can be called many times per day.
        Emits an AgentReport for the Studio Director to aggregate.
        """

    # --- state helpers (shared across agents) ------------------------------

    def read_program(self) -> str:
        path = STATE_DIR / "PROGRAM.md"
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def read_cohort(self) -> dict[str, Any]:
        path = STATE_DIR / "COHORT_1.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def write_cohort(self, data: dict[str, Any]) -> None:
        path = STATE_DIR / "COHORT_1.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def read_budget(self) -> dict[str, Any]:
        path = STATE_DIR / "BUDGET.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def write_budget(self, data: dict[str, Any]) -> None:
        path = STATE_DIR / "BUDGET.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def append_decision_proposal(self, line: str) -> None:
        """Append a one-line decision proposal under PROGRAM.md."""
        path = STATE_DIR / "PROGRAM.md"
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        marker = "## Decisions Awaiting Human"
        if marker not in text:
            return
        before, _, after = text.partition(marker)
        if "## Active Blocks" in after:
            head, _, rest = after.partition("## Active Blocks")
            if line not in head:
                head = head.rstrip() + f"\n- [ ] {line}\n\n"
            new_text = before + marker + head + "## Active Blocks" + rest
        else:
            new_text = text + f"\n- [ ] {line}\n"
        path.write_text(new_text, encoding="utf-8")

    def write_artifact(self, relative_path: str, content: str) -> ProposalArtifact:
        """Write a draft artifact for human review."""
        path = ARTIFACTS_DIR / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return ProposalArtifact(
            title=relative_path.rsplit("/", 1)[-1].replace(".md", "").replace("-", " ").title(),
            relative_path=relative_path,
            summary=f"Draft saved to ARTIFACTS/{relative_path}",
        )

    # --- guardrails --------------------------------------------------------

    @staticmethod
    def can_send_external_message() -> bool:
        """
        External messages (email/SMS/Telegram to non-owner, social posts, etc)
        require explicit env flag AND per-message approval. Default is no.
        """
        return os.getenv("APPRENTICE_STUDIO_ALLOW_EXTERNAL", "false").lower() == "true"

    @staticmethod
    def can_spend(amount_usd: float) -> bool:
        """Agents never spend money. Operations agent flags spend; human approves."""
        return False

    def get_status(self) -> dict[str, Any]:
        return {
            "role": self.role.value,
            "model": self.model,
            "is_active": self.is_active,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "description": self.description,
        }
