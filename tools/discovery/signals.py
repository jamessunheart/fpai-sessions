"""Seeker-language signals for public contact discovery scoring."""
from __future__ import annotations

import re

SEEKER_SIGNALS = [
    "full potential",
    "stuck",
    "unfulfilled",
    "plateaued",
    "what am I doing",
    "what's next",
    "what is next",
    "more than this",
    "conscious",
    "consciousness",
    "awakening",
    "purpose",
    "clarity",
    "direction",
    "next level",
    "seeking growth",
    "right container",
    "what's possible",
    "what is possible",
]

GENERIC_PERSONAL_GROWTH_SIGNALS = [
    "personalgrowth",
    "personal growth",
    "#personalgrowth",
]


def _normalized(text: str) -> str:
    return " ".join(str(text or "").lower().replace("#", " ").split())


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def count_matches(text: str, signals: list[str] | tuple[str, ...]) -> int:
    normalized = _normalized(text)
    compact = _compact(text)
    count = 0
    for signal in signals:
        needle = _normalized(signal)
        if not needle:
            continue
        if " " in needle or "'" in needle:
            count += int(needle in normalized)
        else:
            count += int(_compact(needle) in compact)
    return count


def seeker_match_count(text: str) -> int:
    return count_matches(text, SEEKER_SIGNALS)


def generic_personal_growth_count(text: str) -> int:
    return count_matches(text, GENERIC_PERSONAL_GROWTH_SIGNALS)
