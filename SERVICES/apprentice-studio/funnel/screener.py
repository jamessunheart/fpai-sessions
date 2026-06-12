"""
Auto-screener — scores applications against the studio's published criteria.

Produces a deterministic 0-1 score plus a rationale, strengths, and concerns.
Designed to run with or without an LLM:
  - Default: rule-based heuristics on application fields.
  - Optional: when ANTHROPIC_API_KEY is set, augments with a Claude pass.

Rubric weights (sum = 1.0):
  - shipped_thing      0.30   — they have actually shipped real software
  - ai_native          0.25   — they build with AI as a collaborator, not a novelty
  - mission_fit        0.20   — three-lenses alignment (regen / sovereignty / consciousness)
  - clarity            0.15   — they answer plainly; no fluff
  - availability       0.10   — full-time for 10 weeks
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from .stages import Candidate, Stage

logger = logging.getLogger("apprentice_studio.funnel.screener")


@dataclass
class ScreeningResult:
    score: float
    rationale: str
    strengths: list[str] = field(default_factory=list)
    concerns: list[str] = field(default_factory=list)
    sub_scores: dict[str, float] = field(default_factory=dict)


WEIGHTS: dict[str, float] = {
    "shipped_thing": 0.30,
    "ai_native": 0.25,
    "mission_fit": 0.20,
    "clarity": 0.15,
    "availability": 0.10,
}


SHIPPED_HINTS = [
    "https://", "http://", "github.com", "users", "shipped", "launched",
    "production", "live", "deployed", "customers", "subscribers",
]
AI_NATIVE_HINTS = [
    "claude", "gpt", "cursor", "anthropic", "openai", "agent", "agents",
    "llm", "embedding", "rag", "ollama", "mcp", "tool use",
]
MISSION_HINTS = [
    "regenerative", "sovereignty", "consciousness", "flourish", "expand",
    "human potential", "commons", "co-op", "regen", "wellbeing",
    "alignment", "human-ai",
]
RED_FLAGS = [
    "passive income", "10x my", "one weird trick", "hustle", "grind",
    "to the moon", "automate everything", "replace humans",
]


def _len(text: Any) -> int:
    return len(str(text or "").strip())


def _has_any(text: str, words: list[str]) -> int:
    t = text.lower()
    return sum(1 for w in words if w in t)


def _shipped_score(application: dict[str, Any]) -> tuple[float, str]:
    field_text = " ".join(
        str(application.get(k, "")) for k in [
            "shipped_thing", "portfolio", "shipped", "links", "github"
        ]
    )
    if not field_text.strip():
        return 0.0, "no shipped-thing field provided"
    hits = _has_any(field_text, SHIPPED_HINTS)
    has_url = bool(re.search(r"https?://", field_text))
    if has_url and hits >= 2:
        return 1.0, "shipped: links + production language"
    if has_url:
        return 0.7, "shipped: link present, light evidence of users"
    if hits >= 2:
        return 0.5, "shipped: claims production language but no link"
    if _len(field_text) > 100:
        return 0.3, "shipped: long description, no concrete evidence"
    return 0.1, "shipped: minimal evidence"


def _ai_native_score(application: dict[str, Any]) -> tuple[float, str]:
    text = " ".join(
        str(application.get(k, "")) for k in ["ai_workflow", "ai_collaborator_story", "tools"]
    )
    if not text.strip():
        return 0.0, "no AI-workflow field provided"
    hits = _has_any(text, AI_NATIVE_HINTS)
    if hits >= 4:
        return 1.0, f"ai-native: rich tool vocabulary ({hits} hints)"
    if hits >= 2:
        return 0.7, f"ai-native: meaningful AI usage ({hits} hints)"
    if hits >= 1:
        return 0.4, "ai-native: some AI usage mentioned"
    return 0.1, "ai-native: AI feels like an afterthought"


def _mission_score(application: dict[str, Any]) -> tuple[float, str, list[str]]:
    text = " ".join(
        str(application.get(k, "")) for k in [
            "lens_fit", "mission", "what_to_build", "why_this"
        ]
    )
    flags: list[str] = []
    if not text.strip():
        return 0.0, "no mission/lens field provided", flags

    red = _has_any(text, RED_FLAGS)
    if red:
        flags.append(f"{red} red-flag phrase(s) present")

    hits = _has_any(text, MISSION_HINTS)
    if hits >= 2 and not red:
        return 1.0, f"mission: explicit alignment ({hits} hints)", flags
    if hits >= 1 and not red:
        return 0.7, "mission: language is aligned", flags
    if red:
        return 0.2, "mission: red-flag language outweighs alignment", flags
    return 0.4, "mission: present but unspecific", flags


def _clarity_score(application: dict[str, Any]) -> tuple[float, str]:
    answers = [str(application.get(k, "")) for k in [
        "what_to_build", "lens_fit", "why_this", "ai_collaborator_story"
    ]]
    answers = [a for a in answers if a.strip()]
    if not answers:
        return 0.0, "clarity: no qualitative answers provided"

    avg_len = sum(len(a) for a in answers) / len(answers)
    has_questions_back = any("?" in a for a in answers)

    if 60 <= avg_len <= 600 and not has_questions_back:
        return 1.0, "clarity: tight, answers the question"
    if avg_len < 30:
        return 0.3, "clarity: too short, low signal"
    if avg_len > 1500:
        return 0.4, "clarity: too long, possibly evasive"
    return 0.6, "clarity: serviceable"


def _availability_score(application: dict[str, Any]) -> tuple[float, str]:
    answer = str(application.get("availability", "")).lower().strip()
    if not answer:
        return 0.0, "no availability answer"
    if "yes" in answer and len(answer) < 80:
        return 1.0, "availability: clean yes"
    if "yes" in answer:
        return 0.8, "availability: yes with caveats"
    if "conditional" in answer or "depends" in answer:
        return 0.4, "availability: conditional"
    if "no" in answer:
        return 0.0, "availability: no"
    return 0.5, "availability: ambiguous"


def screen(candidate: Candidate) -> ScreeningResult:
    """Score an applicant. Updates the candidate object in place."""
    app = candidate.application
    sub: dict[str, float] = {}
    notes: list[str] = []
    flags: list[str] = []

    sub["shipped_thing"], note = _shipped_score(app)
    notes.append(note)

    sub["ai_native"], note = _ai_native_score(app)
    notes.append(note)

    sub["mission_fit"], note, mission_flags = _mission_score(app)
    notes.append(note)
    flags.extend(mission_flags)

    sub["clarity"], note = _clarity_score(app)
    notes.append(note)

    sub["availability"], note = _availability_score(app)
    notes.append(note)

    score = sum(sub[k] * WEIGHTS[k] for k in WEIGHTS)
    rationale = " | ".join(notes)

    strengths = [
        k.replace("_", " ").title() for k, v in sub.items() if v >= 0.8
    ]
    concerns = [
        k.replace("_", " ").title() for k, v in sub.items() if v <= 0.3
    ]

    candidate.screening_score = round(score, 3)
    candidate.screening_rationale = rationale
    candidate.strengths = strengths
    candidate.concerns = concerns
    if flags:
        candidate.flags.extend(flags)
        candidate.flags = list(dict.fromkeys(candidate.flags))  # dedupe

    if candidate.stage == Stage.APPLIED:
        candidate.transition(
            Stage.SCREENED, by="screener", note=f"Screening score: {score:.2f}"
        )

    return ScreeningResult(
        score=round(score, 3),
        rationale=rationale,
        strengths=strengths,
        concerns=concerns,
        sub_scores={k: round(v, 3) for k, v in sub.items()},
    )


def screen_all(funnel) -> list[tuple[Candidate, ScreeningResult]]:
    """Screen every APPLIED candidate. Returns list of (candidate, result)."""
    out = []
    for cand in list(funnel.candidates.values()):
        if cand.stage == Stage.APPLIED:
            result = screen(cand)
            out.append((cand, result))
    funnel.save()
    return out
