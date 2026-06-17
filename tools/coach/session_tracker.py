#!/usr/bin/env python3
"""Track coach sessions, award credits, and produce learning-signal rows."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from tools.coach.credit_ledger import award_session_credits


def new_session(
    *,
    session_id: int,
    seeker_identifier: str,
    coach_id: int,
    blocker_type: str,
    session_type: str,
    ai_brief: str,
    matched_at: str | None = None,
) -> dict[str, Any]:
    return {
        "id": int(session_id),
        "seeker_identifier": seeker_identifier,
        "coach_id": int(coach_id),
        "matched_at": matched_at or datetime.now(timezone.utc).isoformat(),
        "blocker_type": blocker_type,
        "session_type": session_type,
        "completed": False,
        "seeker_rating": None,
        "coach_credits_awarded": 0,
        "outcome_achieved": False,
        "ai_brief": ai_brief,
    }


def complete_session(
    *,
    session: dict[str, Any],
    coach: dict[str, Any],
    seeker_rating: int,
    outcome_achieved: bool = False,
    active_coaches: int = 0,
    completed_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    rating = int(seeker_rating)
    if rating < 1 or rating > 5:
        raise ValueError("seeker_rating must be between 1 and 5")

    session_copy = dict(session)
    session_copy["completed"] = True
    session_copy["completed_at"] = completed_at or datetime.now(timezone.utc).isoformat()
    session_copy["seeker_rating"] = rating
    session_copy["outcome_achieved"] = bool(outcome_achieved)
    return award_session_credits(coach=coach, session=session_copy, active_coaches=active_coaches)


def learning_signal(
    *,
    session: dict[str, Any],
    coach_notes: str = "",
    intervention_summary: str = "",
) -> dict[str, Any]:
    """Return a correction-shaped positive example for later routing learning."""
    return {
        "source": "coach_session",
        "signal": "successful_human_intervention" if _successful(session) else "human_intervention",
        "blocker_type": session.get("blocker_type"),
        "session_id": session.get("id"),
        "coach_id": session.get("coach_id"),
        "seeker_rating": session.get("seeker_rating"),
        "outcome_achieved": bool(session.get("outcome_achieved")),
        "prompt": session.get("ai_brief") or "",
        "preferred": {
            "text": _one_line(intervention_summary or coach_notes or "Human coach helped seeker move through the blocker.")
        },
        "metadata": {
            "session_type": session.get("session_type"),
            "coach_credits_awarded": int(session.get("coach_credits_awarded") or 0),
        },
    }


def _successful(session: dict[str, Any]) -> bool:
    rating = session.get("seeker_rating")
    return (rating is not None and int(rating) >= 4) or bool(session.get("outcome_achieved"))


def _one_line(value: Any) -> str:
    return " ".join(str(value or "").split())

