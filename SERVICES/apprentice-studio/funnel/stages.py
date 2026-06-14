"""
Funnel stages, decisions, and candidate model.

Stages are linear with explicit transitions. A candidate has exactly one stage
at any moment. Every transition is logged in candidate.history.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class Stage(Enum):
    """The seven stages of the funnel."""

    SOURCED = "sourced"                    # Outbound prospect, not yet contacted
    CONTACTED = "contacted"                # Outbound message sent
    APPLIED = "applied"                    # Inbound application received
    SCREENED = "screened"                  # Auto-screener has scored
    CHALLENGE_SENT = "challenge_sent"      # 48-hour build challenge brief sent
    CHALLENGE_GRADED = "challenge_graded"  # Build submission evaluated
    INTERVIEWED = "interviewed"            # Final conversation done
    OFFER_SENT = "offer_sent"              # Offer letter out
    HIRED = "hired"                        # Signed
    DECLINED = "declined"                  # Rejected at any stage (terminal)
    WITHDRAWN = "withdrawn"                # Candidate withdrew (terminal)

    @classmethod
    def active_stages(cls) -> list["Stage"]:
        return [
            cls.SOURCED,
            cls.CONTACTED,
            cls.APPLIED,
            cls.SCREENED,
            cls.CHALLENGE_SENT,
            cls.CHALLENGE_GRADED,
            cls.INTERVIEWED,
            cls.OFFER_SENT,
        ]

    @classmethod
    def terminal_stages(cls) -> list["Stage"]:
        return [cls.HIRED, cls.DECLINED, cls.WITHDRAWN]


class Decision(Enum):
    """Decision an agent or human can take on a candidate."""

    ADVANCE = "advance"
    DECLINE = "decline"
    HOLD = "hold"
    REQUEST_MORE_INFO = "request_more_info"


@dataclass
class HistoryEntry:
    timestamp: str
    stage_from: str
    stage_to: str
    decision: Optional[str]
    by: str  # "human" or agent name
    note: Optional[str] = None


@dataclass
class Candidate:
    """One person in the funnel."""

    id: str
    name: str
    email: str
    stage: Stage = Stage.APPLIED
    source: str = "inbound"  # "inbound" / "outbound" / "referral:<who>"

    # Raw application data (free-form dict — kept verbatim)
    application: dict[str, Any] = field(default_factory=dict)

    # Scores (each stage adds its own)
    screening_score: Optional[float] = None       # 0-1
    screening_rationale: str = ""
    challenge_score: Optional[float] = None       # 0-1
    challenge_rationale: str = ""
    interview_score: Optional[float] = None       # 0-1
    interview_rationale: str = ""

    # Flags / signal
    flags: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)

    # Lifecycle
    history: list[HistoryEntry] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    @staticmethod
    def make_id(email: str, name: str) -> str:
        seed = f"{email.strip().lower()}|{name.strip().lower()}"
        return hashlib.sha256(seed.encode()).hexdigest()[:12]

    def transition(
        self,
        to: Stage,
        decision: Optional[Decision] = None,
        by: str = "human",
        note: Optional[str] = None,
    ) -> None:
        entry = HistoryEntry(
            timestamp=datetime.now().isoformat(),
            stage_from=self.stage.value,
            stage_to=to.value,
            decision=decision.value if decision else None,
            by=by,
            note=note,
        )
        self.history.append(entry)
        self.stage = to
        self.last_updated = entry.timestamp

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "stage": self.stage.value,
            "source": self.source,
            "application": self.application,
            "screening_score": self.screening_score,
            "screening_rationale": self.screening_rationale,
            "challenge_score": self.challenge_score,
            "challenge_rationale": self.challenge_rationale,
            "interview_score": self.interview_score,
            "interview_rationale": self.interview_rationale,
            "flags": self.flags,
            "strengths": self.strengths,
            "concerns": self.concerns,
            "history": [h.__dict__ for h in self.history],
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Candidate":
        history = [HistoryEntry(**h) for h in data.get("history", [])]
        return cls(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            stage=Stage(data.get("stage", "applied")),
            source=data.get("source", "inbound"),
            application=data.get("application", {}),
            screening_score=data.get("screening_score"),
            screening_rationale=data.get("screening_rationale", ""),
            challenge_score=data.get("challenge_score"),
            challenge_rationale=data.get("challenge_rationale", ""),
            interview_score=data.get("interview_score"),
            interview_rationale=data.get("interview_rationale", ""),
            flags=data.get("flags", []),
            strengths=data.get("strengths", []),
            concerns=data.get("concerns", []),
            history=history,
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_updated=data.get("last_updated", datetime.now().isoformat()),
        )


# Stage transitions map: which decisions advance from which stage to which.
TRANSITIONS: dict[Stage, dict[Decision, Stage]] = {
    Stage.SOURCED: {
        Decision.ADVANCE: Stage.CONTACTED,
        Decision.DECLINE: Stage.DECLINED,
    },
    Stage.CONTACTED: {
        Decision.ADVANCE: Stage.APPLIED,  # responded + applied
        Decision.DECLINE: Stage.DECLINED,
    },
    Stage.APPLIED: {
        Decision.ADVANCE: Stage.SCREENED,
        Decision.DECLINE: Stage.DECLINED,
    },
    Stage.SCREENED: {
        Decision.ADVANCE: Stage.CHALLENGE_SENT,
        Decision.DECLINE: Stage.DECLINED,
        Decision.HOLD: Stage.SCREENED,
    },
    Stage.CHALLENGE_SENT: {
        Decision.ADVANCE: Stage.CHALLENGE_GRADED,
        Decision.DECLINE: Stage.DECLINED,
    },
    Stage.CHALLENGE_GRADED: {
        Decision.ADVANCE: Stage.INTERVIEWED,
        Decision.DECLINE: Stage.DECLINED,
    },
    Stage.INTERVIEWED: {
        Decision.ADVANCE: Stage.OFFER_SENT,
        Decision.DECLINE: Stage.DECLINED,
    },
    Stage.OFFER_SENT: {
        Decision.ADVANCE: Stage.HIRED,
        Decision.DECLINE: Stage.WITHDRAWN,
    },
}


def next_stage(current: Stage, decision: Decision) -> Optional[Stage]:
    """Return the next stage given a decision, or None if invalid."""
    return TRANSITIONS.get(current, {}).get(decision)
