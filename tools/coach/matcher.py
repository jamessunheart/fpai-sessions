#!/usr/bin/env python3
"""Match stuck seekers to available human coaches."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MIN_MATCH_QUALITY = 0.6
DEFAULT_LIMIT = 3

BLOCKER_ALIASES = {
    "job": "career",
    "work": "career",
    "business": "career",
    "dating": "relationship",
    "family": "relationship",
    "art": "creative",
    "writing": "creative",
    "fitness": "health",
    "wellness": "health",
    "money": "financial",
    "finance": "financial",
}


@dataclass(frozen=True)
class CoachMatch:
    coach: dict[str, Any]
    blocker_type: str
    score: float
    ai_brief: str


def normalize_tag(value: Any) -> str:
    tag = re.sub(r"[^a-z0-9_ -]+", "", str(value or "").lower()).strip()
    tag = tag.replace("-", "_").replace(" ", "_")
    return BLOCKER_ALIASES.get(tag, tag)


def should_trigger_match(
    *,
    message_count: int,
    blocker_type: str | None,
    seeker_still_stuck: bool,
) -> bool:
    """Return True when the conversation has reached the human-match trigger."""
    return int(message_count) >= 5 and bool(normalize_tag(blocker_type)) and bool(seeker_still_stuck)


def match_coaches(
    *,
    coaches: list[dict[str, Any]],
    blocker_type: str,
    conversation_summary: str,
    limit: int = DEFAULT_LIMIT,
) -> list[CoachMatch]:
    blocker = normalize_tag(blocker_type)
    if not blocker:
        return []

    candidates: list[dict[str, Any]] = []
    for coach in coaches:
        if not bool(coach.get("active", True)):
            continue
        quality = float(coach.get("quality_score") or 0.0)
        if quality < MIN_MATCH_QUALITY:
            continue
        tags = {normalize_tag(tag) for tag in coach.get("specialty_tags") or []}
        if blocker not in tags:
            continue
        candidates.append(coach)

    candidates.sort(
        key=lambda item: (
            -float(item.get("quality_score") or 0.0),
            -int(item.get("sessions_completed") or 0),
            int(item.get("id") or 0),
        )
    )

    matches: list[CoachMatch] = []
    for coach in candidates[: max(0, int(limit))]:
        quality = float(coach.get("quality_score") or 0.0)
        sessions = int(coach.get("sessions_completed") or 0)
        score = round(quality + min(sessions, 20) / 100.0, 3)
        matches.append(
            CoachMatch(
                coach=dict(coach),
                blocker_type=blocker,
                score=score,
                ai_brief=build_ai_brief(
                    blocker_type=blocker,
                    conversation_summary=conversation_summary,
                    coach=coach,
                ),
            )
        )
    return matches


def build_ai_brief(*, blocker_type: str, conversation_summary: str, coach: dict[str, Any]) -> str:
    summary = _one_line(conversation_summary)
    coach_identifier = _one_line(coach.get("identifier") or f"coach:{coach.get('id', 'unknown')}")
    specialty = ", ".join(str(tag) for tag in coach.get("specialty_tags") or [blocker_type])
    return (
        f"Seeker blocker: {normalize_tag(blocker_type)}. "
        f"Seeker context: {summary or 'No summary provided.'} "
        f"Suggested coach: {coach_identifier}, matched for {specialty}. "
        "Share only context the seeker gave the system; avoid adding private assumptions."
    )


def matches_as_dicts(matches: list[CoachMatch]) -> list[dict[str, Any]]:
    return [
        {
            "coach": match.coach,
            "blocker_type": match.blocker_type,
            "score": match.score,
            "ai_brief": match.ai_brief,
        }
        for match in matches
    ]


def _one_line(value: Any) -> str:
    return " ".join(str(value or "").split())

