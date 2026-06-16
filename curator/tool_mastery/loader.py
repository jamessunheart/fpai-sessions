"""Load compact tool mastery context for prompt injection."""

from __future__ import annotations

import os
import re
from pathlib import Path

SECTION_NAMES = ("Optimal use patterns", "Anti-patterns")
TOOL_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def repo_root() -> Path:
    override = os.environ.get("TOOL_MASTERY_REPO_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2]


def mastery_card_path(tool_name: str) -> Path | None:
    if not TOOL_RE.match(tool_name):
        return None
    return repo_root() / "docs" / "tool_mastery" / f"{tool_name}.md"


def _extract_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}[^\n]*\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return " ".join(match.group(1).strip().split())


def _truncate_words(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    words = text.split()
    if len(words) <= max_tokens:
        return text
    return " ".join(words[:max_tokens]).rstrip() + " ..."


def get_mastery_context(tool_name: str, max_tokens: int = 300) -> str:
    """Return compact mastery context for a known tool, or empty string."""
    path = mastery_card_path(tool_name)
    if path is None or not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = []
    for heading in SECTION_NAMES:
        body = _extract_section(text, heading)
        if body:
            sections.append((heading, body))
    if not sections:
        return ""
    per_section = max(8, max_tokens // len(sections))
    chunks = [f"{heading}: {_truncate_words(body, per_section)}" for heading, body in sections]
    body = _truncate_words(" ".join(chunks), max_tokens)
    return f"[{tool_name} mastery] {body}"


def inject_mastery(prompt: str, tool_name: str) -> str:
    """Prepend mastery context unless disabled or no card exists."""
    if os.environ.get("TOOL_MASTERY_DISABLE") == "1":
        return prompt
    context = get_mastery_context(tool_name)
    if not context:
        return prompt
    return f"{context}\n\n{prompt}"
