"""Generate and refresh mastery cards from tool documentation."""

from __future__ import annotations

import os
import re
import subprocess
import urllib.request
from pathlib import Path

from .loader import mastery_card_path, repo_root

AUTO_TAG = "[AUTO-GENERATED]"
REQUIRED_SECTIONS = (
    "What it does best",
    "Optimal use patterns (concrete, with examples)",
    "Anti-patterns (what silently degrades it)",
    "Effort/parameter settings for this system",
    "Key constraints and hard limits",
    "How to detect it's not performing well",
    "Last updated + source",
)


def _read_source(source_url_or_text: str) -> str:
    src = source_url_or_text.strip()
    if src.startswith(("http://", "https://")):
        with urllib.request.urlopen(src, timeout=20) as response:
            return response.read().decode("utf-8", errors="replace")
    return source_url_or_text


def _claude_bin() -> str:
    return os.environ.get("CLAUDE_BIN") or os.path.expanduser("~/.local/bin/claude")


def _run_claude(prompt: str) -> str:
    result = subprocess.run(
        [_claude_bin(), "-p", "--effort", "high", prompt],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=240,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"claude exited {result.returncode}")
    return result.stdout.strip()


def _has_heading(text: str, heading: str) -> bool:
    return f"## {heading}" in text


def _normalize_card(tool_name: str, generated: str, source_label: str) -> str:
    body = generated.strip()
    if body.startswith("# "):
        body = "\n".join(body.splitlines()[1:]).strip()
    parts = [AUTO_TAG, f"# {tool_name} Mastery Card", ""]
    parts.append(body)
    for section in REQUIRED_SECTIONS:
        if not _has_heading(body, section):
            parts.extend(["", f"## {section}", "Not extracted."])
    if "## Last updated + source" not in body:
        parts[-1] = f"Generated from: {source_label}"
    return "\n".join(parts).rstrip() + "\n"


def _source_from_card(text: str) -> str:
    match = re.search(r"^## Last updated \+ source\s*$([\s\S]*?)(?=^##\s+|\Z)", text, re.MULTILINE)
    if not match:
        return text
    source = match.group(1).strip()
    if source.lower().startswith("generated from:"):
        source = source.split(":", 1)[1].strip()
    return source or text


def learn_tool(tool_name: str, source_url_or_text: str, force: bool = False) -> str:
    """Create or refresh a mastery card. Existing cards are skipped unless forced."""
    path = mastery_card_path(tool_name)
    if path is None:
        raise ValueError(f"invalid tool_name: {tool_name!r}")
    if path.exists() and not force:
        return str(path)

    source_text = _read_source(source_url_or_text)
    prompt = (
        "Read this tool documentation and extract a mastery card. Goal: help an AI system use this "
        "tool at its full potential. Format: ## What it does best / ## Optimal use patterns "
        "(concrete examples) / ## Anti-patterns / ## Effort/parameter settings for this system / "
        "## Key constraints and hard limits / ## How to detect it's not performing well / "
        "## Last updated + source. Be specific and opinionated - no generic advice. "
        f"Tool: {tool_name}. Source: {source_text[:50000]}"
    )
    generated = _run_claude(prompt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_normalize_card(tool_name, generated, source_url_or_text[:200]), encoding="utf-8")
    return str(path)


def _log_refresh(count: int) -> None:
    ops = repo_root() / "tools" / "build_loop" / "ops_log.py"
    if not ops.exists():
        return
    try:
        subprocess.run(
            ["python3", str(ops), "tool_mastery", "mastery_refreshed", f"tools={count}", "$0", "", ""],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        return


def refresh_all() -> list[str]:
    """Refresh only cards still marked auto-generated."""
    cards_dir = repo_root() / "docs" / "tool_mastery"
    if not cards_dir.exists():
        _log_refresh(0)
        return []
    refreshed: list[str] = []
    for path in sorted(cards_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if AUTO_TAG not in text:
            continue
        refreshed.append(learn_tool(path.stem, _source_from_card(text), force=True))
    _log_refresh(len(refreshed))
    return refreshed
