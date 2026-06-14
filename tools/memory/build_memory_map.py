#!/usr/bin/env python3
"""The Cartographer v0 — compile ALL memory files into one complete, compact map.

Problem this solves (James, 2026-06-12): MEMORY.md is 43KB and only partially
auto-loads; 244 memory files exist but retrieval was passive — the Camp Zen
revenue plan sat invisible while strategy was rebuilt from scratch.
"Memories lost are our biggest cost."

Output: memory/MEMORY_MAP.md — one line per memory, grouped by type.
Complete coverage guaranteed (every .md gets a line, frontmatter or not).
Consumed by .claude/hooks/memory-recall.sh (auto-recall on every prompt)
and readable by any session as the full index.

Spec lineage: spec_the_cartographer_internal_index.md (Tier-0 indexer).
"""
import os
import re
import sys
from datetime import datetime, timezone

MEM_DIR = os.path.expanduser(
    "~/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory"
)
MAP_PATH = os.path.join(MEM_DIR, "MEMORY_MAP.md")

SKIP_FILES = {"MEMORY.md", "MEMORY_MAP.md"}
SKIP_DIRS = {"observations", "background_log"}  # high-volume logs, not recall targets

TYPE_ORDER = ["feedback", "project", "reference", "spec", "identity", "session", "other"]


def parse_frontmatter(text):
    """Extract name/description/type from YAML frontmatter without pyyaml."""
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                m = re.match(r"^\s*(name|description|type)\s*:\s*(.+?)\s*$", line)
                if m:
                    meta[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return meta


def first_heading(text):
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def classify(relpath, fname, meta):
    t = meta.get("type", "")
    if t in ("feedback", "project", "reference", "spec"):
        return t
    if relpath.startswith("identity/sessions"):
        return "session"
    if relpath.startswith("identity"):
        return "identity"
    for prefix in ("feedback", "project", "reference", "spec", "architecture"):
        if fname.startswith(prefix):
            return prefix if prefix != "architecture" else "reference"
    return "other"


def main():
    entries = {}  # type -> list of (name, description, relpath)
    count = 0
    for root, dirs, files in os.walk(MEM_DIR):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in sorted(files):
            if not fname.endswith(".md") or fname in SKIP_FILES:
                continue
            path = os.path.join(root, fname)
            relpath = os.path.relpath(path, MEM_DIR)
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    text = f.read(8000)  # head is enough for meta
            except OSError:
                continue
            meta = parse_frontmatter(text)
            name = meta.get("name") or os.path.splitext(fname)[0]
            desc = meta.get("description") or first_heading(text) or "(no description)"
            desc = re.sub(r"\s+", " ", desc)[:240]
            kind = classify(relpath, fname, meta)
            entries.setdefault(kind, []).append((name, desc, relpath))
            count += 1

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
    lines = [
        "# MEMORY MAP — complete index (auto-generated, do not hand-edit)",
        f"# Generated {now} by tools/memory/build_memory_map.py · {count} memories",
        "# One line per memory: TYPE | name | description | path",
        "# Full coverage: every memory file is here. Grep this, not your assumptions.",
        "",
    ]
    for kind in TYPE_ORDER:
        if kind not in entries:
            continue
        lines.append(f"## {kind.upper()} ({len(entries[kind])})")
        for name, desc, relpath in sorted(entries[kind]):
            lines.append(f"{kind} | {name} | {desc} | {relpath}")
        lines.append("")

    with open(MAP_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"MEMORY_MAP.md written: {count} memories, {len(lines)} lines")


if __name__ == "__main__":
    sys.exit(main())
