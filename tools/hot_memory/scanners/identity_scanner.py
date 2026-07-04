#!/usr/bin/env python3
"""Scan identity and NOW mirrors into public-safe hot-memory facts."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

from tools.hot_memory.common import DEFAULT_HOT_DIR, REPO_ROOT, compact_facts, fact, file_date, write_scan

KEY_FILES = (
    "core/STATE/NOW.md",
    "core/STATE/NORTH_STAR.md",
    "core/STATE/AI_GOALS.md",
    "core/STATE/identity/ALIGNMENT.md",
    "core/STATE/identity/DAILY_AWAKENING.md",
    "core/STATE/identity/STORY.md",
)

# Live memory paths (prefer newer file when both exist)
_LIVE_MEMORY_CANDIDATES = [
    Path.home() / ".claude/projects/-opt-fpai-build-FPAI_Cockpit/memory/identity",
    Path.home() / ".claude/projects/-opt-fpai-build-FPAI-Cockpit/memory/identity",
    Path.home() / ".claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity",
]


def _live_identity_dir() -> Path | None:
    for p in _LIVE_MEMORY_CANDIDATES:
        if p.is_dir():
            return p
    return None


def _best_path(repo_root: Path, rel: str) -> Path:
    """Return the newest copy of an identity file between live memory and repo mirror."""
    repo_path = repo_root / rel
    live_dir = _live_identity_dir()
    if live_dir and "identity/" in rel:
        filename = Path(rel).name
        live_path = live_dir / filename
        if live_path.exists():
            repo_mtime = repo_path.stat().st_mtime if repo_path.exists() else 0
            if live_path.stat().st_mtime > repo_mtime:
                return live_path
    return repo_path


def collect(repo_root: Path = REPO_ROOT):
    facts = []
    for rel in KEY_FILES:
        path = _best_path(repo_root, rel)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in _candidate_lines(text):
            facts.append(fact(line, rel, file_date(path), weight=_weight(line), category="directive"))
    return compact_facts(facts, limit=12)


def _current_section(text: str) -> str:
    """Identity files (ALIGNMENT.md, STORY.md) stack dated snapshots newest-first;
    everything below the first 'archived' marker is history. Without this cut the
    scanner surfaced archived numbers (awareness 41.3%) into HOT_STATE as ACTIVE
    directives — the most-trusted surface amplifying the stalest data (2026-07-03).
    Same rule as tools/governance/metric_coherence.current_section."""
    out = []
    for line in text.splitlines():
        if "archived" in line.lower():
            break
        out.append(line)
    return "\n".join(out)


def _candidate_lines(text: str) -> list[str]:
    lines = []
    for raw in _current_section(text).splitlines():
        line = re.sub(r"^[#>\-\s*`|]+", "", raw).strip()
        if not line or len(line) < 20:
            continue
        lower = line.lower()
        if any(token in lower for token in ("100%", "directive", "priority", "north star", "decision filter", "self-sustaining", "sovereignty", "james carries only")):
            lines.append(line)
        if len(lines) >= 4:
            break
    return lines


def _weight(line: str) -> int:
    lower = line.lower()
    if "100%" in lower or "directive" in lower:
        return 10
    if "priority" in lower or "north star" in lower:
        return 9
    return 7


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    args = parser.parse_args(argv)
    payload = write_scan("identity", collect(args.repo_root), hot_dir=args.hot_dir)
    print(payload["changed"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

