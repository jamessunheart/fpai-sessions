#!/usr/bin/env python3
"""CORA credit accounting for human coach sessions.

This module is intentionally side-effect free by default. Callers pass fixture
dicts or DB-shaped rows in, and receive updated copies plus ledger entries out.
Live persistence and fiat payout execution remain separate James/Ember-gated
work.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

TEXT_ASYNC_CREDITS = 25
VOICE_VIDEO_CREDITS = 75
HIGH_RATING_BONUS = 15
OUTCOME_BONUS = 50
FIAT_ACTIVE_COACH_GATE = 20
FIAT_RATE_USD_PER_CREDIT = 0.50

CREDIT_TIERS: tuple[tuple[int, str], ...] = (
    (25, "1 month priority AI access"),
    (50, "early feature access"),
    (100, "Zen Village / Camp Zen early-bird rate"),
    (200, "co-creator status review"),
    (500, "affiliate tier eligibility"),
)


@dataclass(frozen=True)
class FiatPhase:
    phase: int
    active_coaches_required: int
    active_coaches: int
    conversion_allowed: bool
    usd_per_credit: float
    reason: str


def session_base_credits(session_type: str) -> int:
    kind = _clean(session_type)
    if kind == "text_async":
        return TEXT_ASYNC_CREDITS
    if kind in {"voice", "video"}:
        return VOICE_VIDEO_CREDITS
    raise ValueError(f"unknown session_type: {session_type!r}")


def calculate_session_credits(
    *,
    session_type: str,
    seeker_rating: int | None = None,
    outcome_achieved: bool | None = False,
) -> int:
    credits = session_base_credits(session_type)
    if seeker_rating is not None and int(seeker_rating) >= 4:
        credits += HIGH_RATING_BONUS
    if bool(outcome_achieved):
        credits += OUTCOME_BONUS
    return credits


def fiat_phase(active_coaches: int) -> FiatPhase:
    count = max(0, int(active_coaches))
    allowed = count >= FIAT_ACTIVE_COACH_GATE
    return FiatPhase(
        phase=2 if allowed else 1,
        active_coaches_required=FIAT_ACTIVE_COACH_GATE,
        active_coaches=count,
        conversion_allowed=allowed,
        usd_per_credit=FIAT_RATE_USD_PER_CREDIT if allowed else 0.0,
        reason="20+ active coaches reached" if allowed else "credits only until 20 active coaches",
    )


def available_unlocks(cora_credits: int) -> list[dict[str, Any]]:
    balance = max(0, int(cora_credits))
    return [
        {"threshold": threshold, "unlock": unlock}
        for threshold, unlock in CREDIT_TIERS
        if balance >= threshold
    ]


def award_session_credits(
    *,
    coach: dict[str, Any],
    session: dict[str, Any],
    active_coaches: int = 0,
    awarded_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    """Award credits once for a completed session.

    Returns ``(coach_copy, session_copy, ledger_entry_or_none)``. When the
    session already has ``coach_credits_awarded`` set, no additional credits are
    added and the ledger entry is ``None``.
    """
    coach_copy = dict(coach)
    session_copy = dict(session)

    already_awarded = int(session_copy.get("coach_credits_awarded") or 0)
    if already_awarded > 0:
        return coach_copy, session_copy, None

    if not bool(session_copy.get("completed")):
        raise ValueError("cannot award coach credits before session is completed")

    credits = calculate_session_credits(
        session_type=str(session_copy.get("session_type") or ""),
        seeker_rating=session_copy.get("seeker_rating"),
        outcome_achieved=session_copy.get("outcome_achieved"),
    )
    coach_copy["cora_credits"] = int(coach_copy.get("cora_credits") or 0) + credits
    coach_copy["sessions_completed"] = int(coach_copy.get("sessions_completed") or 0) + 1
    session_copy["coach_credits_awarded"] = credits

    phase = fiat_phase(active_coaches)
    if phase.conversion_allowed:
        session_copy["fiat_conversion_rate"] = phase.usd_per_credit
        session_copy["fiat_equivalent_usd"] = round(credits * phase.usd_per_credit, 2)
    else:
        session_copy["fiat_conversion_rate"] = 0.0
        session_copy["fiat_equivalent_usd"] = 0.0

    ledger_entry = {
        "event": "coach_credit_award",
        "awarded_at": awarded_at or datetime.now(timezone.utc).isoformat(),
        "coach_id": coach_copy.get("id"),
        "session_id": session_copy.get("id"),
        "credits": credits,
        "session_type": session_copy.get("session_type"),
        "seeker_rating": session_copy.get("seeker_rating"),
        "outcome_achieved": bool(session_copy.get("outcome_achieved")),
        "fiat_phase": phase.phase,
        "fiat_conversion_allowed": phase.conversion_allowed,
        "fiat_equivalent_usd": session_copy["fiat_equivalent_usd"],
    }
    return coach_copy, session_copy, ledger_entry


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())

