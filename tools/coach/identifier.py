#!/usr/bin/env python3
"""Identify potential coaches from completed probe conversations."""
from __future__ import annotations

import json
import re
import subprocess
from typing import Any, Callable

from tools.coach.matcher import normalize_tag

MIN_COACH_QUALITY = 0.7
DOMAIN_KEYWORDS = {
    "career": ("career", "job", "work", "business", "founder", "promotion", "interview"),
    "relationship": ("relationship", "partner", "dating", "marriage", "family", "breakup"),
    "creative": ("creative", "writing", "art", "music", "film", "book", "creator"),
    "health": ("health", "fitness", "body", "nutrition", "healing", "wellness", "sleep"),
    "financial": ("financial", "finance", "money", "debt", "income", "investing", "budget"),
}
EXPERTISE_CUES = re.compile(
    r"\b(i (worked|got|made|built|recovered|healed|navigated|solved|learned|created)|"
    r"what helped me|my process|i can help|i have helped|after i)\b",
    re.I,
)


def identify_potential_coach(
    *,
    probe_session: dict[str, Any],
    conversation: list[dict[str, Any]] | list[str],
    tag_extractor: Callable[[str], list[str]] | None = None,
) -> dict[str, Any] | None:
    """Return a pending coach row when a high-quality probe shows expertise."""
    quality_score = float(probe_session.get("quality_score") or 0.0)
    if quality_score < MIN_COACH_QUALITY:
        return None

    transcript = transcript_text(conversation)
    if not demonstrates_domain_expertise(transcript):
        return None

    tags = extract_specialty_tags(transcript, tag_extractor=tag_extractor)
    if not tags:
        return None

    return make_pending_coach(
        identifier=str(probe_session.get("identifier") or probe_session.get("handle") or ""),
        platform=str(probe_session.get("platform") or "unknown"),
        specialty_tags=tags,
        quality_score=quality_score,
        recruited_from_probe_id=str(probe_session.get("probe_id") or probe_session.get("id") or ""),
    )


def make_pending_coach(
    *,
    identifier: str,
    platform: str,
    specialty_tags: list[str],
    quality_score: float,
    recruited_from_probe_id: str,
) -> dict[str, Any]:
    return {
        "identifier": identifier,
        "platform": platform,
        "specialty_tags": sorted({normalize_tag(tag) for tag in specialty_tags if normalize_tag(tag)}),
        "quality_score": float(quality_score),
        "sessions_completed": 0,
        "cora_credits": 0,
        "fiat_earned": 0.0,
        "active": False,
        "recruited_from_probe_id": recruited_from_probe_id,
    }


def demonstrates_domain_expertise(transcript: str) -> bool:
    text = _clean(transcript)
    if not text:
        return False
    return bool(EXPERTISE_CUES.search(text)) and bool(_heuristic_tags(text))


def extract_specialty_tags(
    transcript: str,
    *,
    tag_extractor: Callable[[str], list[str]] | None = None,
    runner: Callable[..., Any] = subprocess.run,
) -> list[str]:
    if tag_extractor is not None:
        return _normalize_tags(tag_extractor(transcript))

    heuristic = _heuristic_tags(transcript)
    if heuristic:
        return heuristic

    prompt = (
        "Extract 1-3 challenge specialty tags from this conversation. "
        "Use only these labels when supported: career, relationship, creative, health, financial. "
        "Return JSON list only.\n\n"
        f"{transcript[:4000]}"
    )
    try:
        result = runner(
            ["claude", "-p", "--effort", "low", prompt],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except Exception:
        return []
    if getattr(result, "returncode", 1) != 0:
        return []
    try:
        parsed = json.loads(getattr(result, "stdout", "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return _normalize_tags(parsed)


def compose_invitation(coach: dict[str, Any]) -> str:
    tags = ", ".join(coach.get("specialty_tags") or ["this"])
    return (
        f"You've clearly worked through {tags}. Would you be open to helping others doing the same? "
        "You'd earn CORA credits that unlock more of what this system can do for you."
    )


def transcript_text(conversation: list[dict[str, Any]] | list[str]) -> str:
    parts: list[str] = []
    for item in conversation:
        if isinstance(item, dict):
            role = item.get("role") or item.get("speaker") or "unknown"
            text = item.get("content") or item.get("text") or ""
            parts.append(f"{role}: {text}")
        else:
            parts.append(str(item))
    return "\n".join(parts)


def _heuristic_tags(transcript: str) -> list[str]:
    text = _clean(transcript)
    tags: list[str] = []
    for tag, keywords in DOMAIN_KEYWORDS.items():
        if any(re.search(rf"\b{re.escape(keyword)}\b", text, re.I) for keyword in keywords):
            tags.append(tag)
    return tags


def _normalize_tags(tags: list[Any]) -> list[str]:
    return sorted({normalize_tag(tag) for tag in tags if normalize_tag(tag) in DOMAIN_KEYWORDS})


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())

