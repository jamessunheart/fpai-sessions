#!/usr/bin/env python3
"""Scan identity and NOW mirrors into public-safe hot-memory facts."""
from __future__ import annotations

import argparse
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


def collect(repo_root: Path = REPO_ROOT):
    facts = []
    for rel in KEY_FILES:
        path = repo_root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for line in _candidate_lines(text):
            facts.append(fact(line, rel, file_date(path), weight=_weight(line), category="directive"))
    return compact_facts(facts, limit=12)


def _candidate_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
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

