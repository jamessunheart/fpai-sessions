#!/usr/bin/env python3
"""
memory-curator — keep file-based memory pruned + relevance-sorted

Scores each memory note by:
- type weight (feedback/project/user > reference > architecture)
- recency (60-day half-life, configurable)
- cross-reference count (notes that reference this note)
- explicit pin/archive markers in description

Rewrites MEMORY.md sorted by score (highest first), so the auto-loaded
first ~50 lines surface the most valuable memories. Low-score notes stay
in the dir but drop out of the index. Very-low-score notes are flagged
as archival candidates.

Usage:
    curator.py [--memory-dir PATH] [--apply] [--top N] [--archive-threshold X]

Default: --memory-dir = ~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory
Default: dry-run (no writes). Use --apply to commit.
Default: --top 40 entries in MEMORY.md.
Default: --archive-threshold 0.05 flags candidates with score < 0.05.

Frontmatter conventions the curator respects:
- description: include `[pin]` to force top, `[archive]` to force bottom
- type: one of feedback / project / reference / user / architecture
- Implicit: file mtime drives recency; content-grep drives cross-refs

Designed to be:
- Idempotent (re-run safely)
- Inspectable (--dry-run prints scoring detail)
- Configurable (env vars + flags)
- Cron-friendly (no interactive prompts)
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DEFAULT_MEMORY_DIR = Path.home() / ".claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"
INDEX_FILE = "MEMORY.md"

TYPE_WEIGHTS = {
    "feedback": 1.5,
    "project": 1.2,
    "user": 1.3,
    "architecture": 1.2,
    "reference": 1.0,
}
DEFAULT_TYPE_WEIGHT = 0.9

RECENCY_HALF_LIFE_DAYS = float(os.environ.get("CURATOR_RECENCY_HALF_LIFE_DAYS", "60"))
CROSS_REF_BOOST = float(os.environ.get("CURATOR_CROSS_REF_BOOST", "0.15"))
PIN_SCORE = 9999.0
ARCHIVE_SCORE = -9999.0


@dataclass
class Memory:
    path: Path
    name: str = ""
    description: str = ""
    mtime: float = 0.0
    type: str = "reference"
    content: str = ""
    pinned: bool = False
    archived_marker: bool = False
    cross_refs: int = 0
    score: float = 0.0
    score_breakdown: dict = field(default_factory=dict)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Returns (frontmatter_dict, body). Handles --- delimited YAML-like front."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("\n---", 3)
    if end == -1:
        return {}, content
    front_text = content[3:end].strip()
    body = content[end + 4:].strip()
    fm = {}
    for line in front_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, body


def load_memory(path: Path) -> Memory:
    content = path.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(content)
    desc = fm.get("description", "")
    name = fm.get("name", path.stem)
    haystack = (name + " " + desc).lower()
    return Memory(
        path=path,
        name=name,
        description=desc,
        mtime=path.stat().st_mtime,
        type=fm.get("type", "reference").strip().lower(),
        content=content,
        pinned="[pin]" in haystack,
        archived_marker="[archive]" in haystack or "[deprecated]" in haystack,
    )


def count_cross_references(memories: list[Memory]) -> None:
    """For each memory, count how many OTHER memories mention its filename."""
    by_filename = {m.path.name: m for m in memories}
    for m in memories:
        m.cross_refs = 0
    for m in memories:
        # find filenames mentioned in this memory's content
        for other_name in by_filename:
            if other_name == m.path.name:
                continue
            if other_name in m.content:
                by_filename[other_name].cross_refs += 1


def score_memory(m: Memory, now: float) -> float:
    if m.pinned:
        m.score_breakdown = {"pinned": True}
        return PIN_SCORE
    if m.archived_marker:
        m.score_breakdown = {"archived_marker": True}
        return ARCHIVE_SCORE

    type_weight = TYPE_WEIGHTS.get(m.type, DEFAULT_TYPE_WEIGHT)
    age_days = max(0, (now - m.mtime) / 86400.0)
    recency = math.exp(-age_days / RECENCY_HALF_LIFE_DAYS)
    ref_boost = 1.0 + CROSS_REF_BOOST * m.cross_refs

    score = type_weight * recency * ref_boost

    m.score_breakdown = {
        "type": m.type,
        "type_weight": round(type_weight, 3),
        "age_days": round(age_days, 1),
        "recency": round(recency, 3),
        "cross_refs": m.cross_refs,
        "ref_boost": round(ref_boost, 3),
        "score": round(score, 3),
    }
    return score


def build_index_line(m: Memory) -> str:
    """Format one MEMORY.md line for a memory (fallback when no existing line)."""
    title = m.name
    desc = re.sub(r"\s+", " ", m.description).strip()
    if len(desc) > 160:
        desc = desc[:157] + "..."
    return f"- [{title}]({m.path.name}) — {desc}"


def parse_existing_index(index_text: str) -> dict[str, str]:
    """Returns {filename: full_line} for existing MEMORY.md entries.

    Preserves hand-curated wording. Only files that already had an entry get
    their existing line; new files get a fresh line built from YAML.
    """
    out: dict[str, str] = {}
    # Match lines like: - [Title](filename.md) — description...
    pattern = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)")
    for line in index_text.splitlines():
        line = line.rstrip()
        if not line.startswith("- ["):
            continue
        m = pattern.match(line)
        if m:
            out[m.group(1)] = line
    return out


def render_memory_md(memories: list[Memory], top_n: int, existing_index: dict[str, str]) -> str:
    """Render MEMORY.md sorted by score desc; reuse existing line text when present."""
    sorted_mems = sorted(memories, key=lambda m: m.score, reverse=True)
    top = sorted_mems[:top_n]
    lines = []
    for m in top:
        existing = existing_index.get(m.path.name)
        lines.append(existing if existing else build_index_line(m))
    return "\n".join(lines) + "\n"


def diff_index(old: str, new: str) -> str:
    """Return a unified-ish diff summary."""
    old_lines = set(old.splitlines())
    new_lines = set(new.splitlines())
    added = new_lines - old_lines
    removed = old_lines - new_lines
    out = []
    if added:
        out.append(f"  + {len(added)} new entries")
        for line in sorted(added)[:5]:
            out.append(f"    + {line[:160]}")
    if removed:
        out.append(f"  - {len(removed)} entries dropped from top")
        for line in sorted(removed)[:5]:
            out.append(f"    - {line[:160]}")
    return "\n".join(out) if out else "  (no change)"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--memory-dir", type=Path, default=DEFAULT_MEMORY_DIR)
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run)")
    ap.add_argument("--top", type=int, default=40, help="Number of entries to keep in MEMORY.md")
    ap.add_argument("--archive-threshold", type=float, default=0.05)
    ap.add_argument("--verbose", action="store_true", help="Print per-memory score breakdown")
    args = ap.parse_args()

    if not args.memory_dir.exists():
        print(f"error: memory dir not found: {args.memory_dir}", file=sys.stderr)
        return 2

    md_files = sorted(p for p in args.memory_dir.glob("*.md") if p.name != INDEX_FILE)
    memories = [load_memory(p) for p in md_files]
    count_cross_references(memories)

    now = time.time()
    for m in memories:
        m.score = score_memory(m, now)

    memories_sorted = sorted(memories, key=lambda m: m.score, reverse=True)

    # ── Report ─────────────────────────────────────────────────────
    print(f"Memory dir: {args.memory_dir}")
    print(f"Total memories: {len(memories)}")
    print(f"Index size cap: top {args.top}")
    print(f"Recency half-life: {RECENCY_HALF_LIFE_DAYS} days")
    print(f"Mode: {'APPLY' if args.apply else 'DRY-RUN'}")
    print()
    print("=" * 70)
    print("RANKING (highest score → lowest)")
    print("=" * 70)
    for i, m in enumerate(memories_sorted, 1):
        marker = "[PIN]" if m.pinned else "[ARC]" if m.archived_marker else ""
        in_index = i <= args.top
        idx_marker = "★" if in_index else " "
        print(f"{idx_marker} {i:>3}. {m.score:>8.3f}  {marker:5}  {m.name[:80]}")
        if args.verbose and not m.pinned and not m.archived_marker:
            print(f"        breakdown: {m.score_breakdown}")

    print()
    print("=" * 70)
    print("ARCHIVE CANDIDATES (score below threshold)")
    print("=" * 70)
    candidates = [m for m in memories_sorted if m.score < args.archive_threshold and not m.pinned]
    if not candidates:
        print("  (none)")
    else:
        for m in candidates:
            age = (now - m.mtime) / 86400.0
            print(f"  - {m.path.name}  score={m.score:.3f}  age={age:.0f}d  refs={m.cross_refs}")
        print()
        print(f"  → consider archiving (move to memory/archive/) or pinning if still load-bearing")

    print()
    print("=" * 70)
    print("MEMORY.md INDEX (proposed)")
    print("=" * 70)
    index_path = args.memory_dir / INDEX_FILE
    old_index = index_path.read_text(encoding="utf-8", errors="replace") if index_path.exists() else ""
    existing_lines = parse_existing_index(old_index)
    new_index = render_memory_md(memories, args.top, existing_lines)
    print(diff_index(old_index, new_index))

    if args.apply:
        # Backup current index
        if index_path.exists():
            backup = args.memory_dir / f"MEMORY.md.bak.{int(now)}"
            backup.write_text(old_index, encoding="utf-8")
            print(f"\nbackup written: {backup}")
        index_path.write_text(new_index, encoding="utf-8")
        print(f"updated: {index_path}")
    else:
        print()
        print("(dry-run: no changes written — pass --apply to commit)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
