#!/usr/bin/env python3
"""Read platform-bias calibration context and rate tool sovereignty."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "core" / "STATE" / "PLATFORM_BIAS_REGISTRY.md"
MAX_CONTEXT_CHARS = 7000


@dataclass(frozen=True)
class SovereigntyRating:
    rating: str
    reason: str
    alternative_prompt: str


def read_text(path: Path = DEFAULT_REGISTRY) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def registry_context(path: Path = DEFAULT_REGISTRY, *, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    text = read_text(path)
    if not text:
        return ""
    sections = []
    for heading in (
        "Known Platform Biases",
        "Calibration Rule",
        "Sovereign Rating Rubric",
        "Platform Critic Lens",
        "Highest-Risk Zones",
    ):
        body = _section(text, heading)
        if body:
            sections.append(f"## {heading}\n{body}")
    if not sections:
        sections = [text]
    return ("PLATFORM BIAS REGISTRY - COUNCIL-OPEN\n" + "\n\n".join(sections))[:max_chars]


def platform_critic_prompt(path: Path = DEFAULT_REGISTRY) -> str:
    context = registry_context(path)
    return (
        "You are the Platform Critic lens. Your job is not to reject commercial tools; "
        "it is to ensure every adoption is conscious, not defaulted by platform-shaped training.\n\n"
        "For this proposal, answer:\n"
        "1. Does this recommendation favor Anthropic, OpenAI, or another platform we depend on?\n"
        "2. What is the sovereign-first, local-first, open-source alternative? What do we actually lose by using it?\n"
        "3. Is the 'best practice' genuinely best for this system: sovereignty-first, private data, local-first, and cost-capped?\n"
        "4. Are safety concerns genuine risk to James/the system, or mostly platform liability posture?\n\n"
        "Be specific. Name the alternative. Quantify the loss when possible. Advisory only; the council decides.\n\n"
        + context
    ).strip()


def sovereignty_check_text(path: Path = DEFAULT_REGISTRY) -> str:
    context = registry_context(path, max_chars=3200)
    return (
        "Sovereignty check: for every recommended tool, name whether it is open-source, self-hostable, "
        "or local-first. Rate it as Sovereign / Hybrid / Dependent. If it is not Sovereign, surface a "
        "sovereign alternative beside it and state the real loss, not the assumed loss.\n\n"
        + context
    ).strip()


def rate_tool(name: str, url: str = "", tags: tuple[str, ...] = ()) -> SovereigntyRating:
    haystack = " ".join([name, url, " ".join(tags)]).lower()
    local_markers = ("local", "self-host", "selfhost", "ollama", "open-source", "github.com", "postgres", "sqlite")
    dependent_markers = (
        "anthropic",
        "openai",
        "twilio",
        "brevo",
        "stripe",
        "supabase.com",
        "runpod",
        "api",
        "cloud",
        "saas",
    )
    if any(marker in haystack for marker in local_markers) and not any(marker in haystack for marker in dependent_markers):
        return SovereigntyRating("Sovereign", "open/local/self-hostable signal present", "Keep local/self-hosted operation as the default.")
    if any(marker in haystack for marker in local_markers):
        return SovereigntyRating("Hybrid", "has open/local surface but depends on hosted or metered infrastructure", "Compare against a fully local path before adoption.")
    if any(marker in haystack for marker in dependent_markers) or re.search(r"https?://(?!github\.com)", haystack):
        return SovereigntyRating("Dependent", "hosted/API/platform dependency signal present", "Name the closest open-source or self-hosted substitute before recommending.")
    return SovereigntyRating("Hybrid", "sovereignty posture unclear from available metadata", "Require an explicit open-source/self-hostability check before adoption.")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\s*$", text, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^## ", text[start:], flags=re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end].strip()

