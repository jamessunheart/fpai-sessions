#!/usr/bin/env python3
"""
Ember Dashboard build · core/STATE/DASHBOARD.md → SERVICES/dashboard-page/dashboard.json

Parses the canonical markdown source-of-truth (with YAML frontmatter + YAML-ish
list-of-dicts inside sections) and emits a clean JSON blob the static page consumes.

Design constraint: zero new dependencies. Uses stdlib only (yaml-via-tolerant-parser).
This script is invoked:
  - by Ember each time she writes DASHBOARD.md (Edit hook · post-write)
  - manually: `python3 infra/scripts/dashboard_build.py`
  - by deploy script before rsync to remote
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "core" / "STATE" / "DASHBOARD.md"
OUT = REPO / "SERVICES" / "dashboard-page" / "dashboard.json"


# ─────────────────────────────────────────────────────────────
# Minimal YAML-ish parser (no PyYAML dep · handles our schema)
# ─────────────────────────────────────────────────────────────

def _strip_quotes(v: str) -> str:
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    return v


def _coerce(v: str):
    """Coerce string to int/float/bool/None/str."""
    s = _strip_quotes(v).strip()
    if s == "" or s.lower() in ("null", "~"):
        return None
    if s.lower() == "true":
        return True
    if s.lower() == "false":
        return False
    # int
    if re.fullmatch(r"-?\d+", s):
        try:
            return int(s)
        except ValueError:
            pass
    # float
    if re.fullmatch(r"-?\d+\.\d+", s):
        try:
            return float(s)
        except ValueError:
            pass
    return s


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Pull --- ... --- block from top of file."""
    fm = {}
    body = text
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if m:
        raw, body = m.group(1), m.group(2)
        for line in raw.splitlines():
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            k, _, v = line.partition(":")
            fm[k.strip()] = _coerce(v)
    return fm, body


def parse_yaml_block(block: str):
    """
    Parse a block that is either:
      - flat key: value pairs (one per line)
      - list of dicts starting with `- key: value` (each item is one record)
    Returns either a dict or a list-of-dicts.
    """
    lines = [l for l in block.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        return None

    # Detect list of dicts: any top-level line starts with "- "
    is_list = any(re.match(r"^\s*-\s+\S", l) for l in lines)

    if is_list:
        records: list[dict] = []
        current: dict | None = None
        # Determine indent of the "- " marker
        for raw in lines:
            stripped = raw.lstrip()
            indent = len(raw) - len(stripped)
            if stripped.startswith("- "):
                # Start new record
                if current is not None:
                    records.append(current)
                current = {}
                # Inline key on same line
                rest = stripped[2:].strip()
                if rest and ":" in rest:
                    k, _, v = rest.partition(":")
                    current[k.strip()] = _coerce(v)
            else:
                # Continuation line: belongs to current record
                if current is None:
                    continue
                if ":" in stripped:
                    k, _, v = stripped.partition(":")
                    current[k.strip()] = _coerce(v)
        if current is not None:
            records.append(current)
        return records
    else:
        out = {}
        for line in lines:
            stripped = line.lstrip()
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                out[k.strip()] = _coerce(v)
        return out


def parse_sections(body: str) -> dict:
    """
    Split body into sections by markdown headings.
    Returns nested dict matching the schema in DASHBOARD.md.
    """
    # Find all H1/H2 sections
    # Schema:
    #   # vision · prose
    #   # mission · prose
    #   # values · prose
    #   # intent · prose
    #   # trust_tier · prose
    #   # progress
    #     ## old_world (list of dicts)
    #     ## new_world (list of dicts)
    #   # counts
    #     today: ... cumulative: ... pre_activation: ... (yaml-style nested)
    #   # five_p (list of dicts)
    #   # latest_narrator (yaml-style flat)
    #   # latest_journal (yaml-style flat)
    #   # footer (yaml-style flat)
    #   # header (yaml-style flat, optional)

    sections: dict = {}

    # Strategy: walk lines, track current H1 + H2, accumulate content
    current_h1 = None
    current_h2 = None
    buf: list[str] = []

    def flush():
        if current_h1 is None:
            return
        content = "\n".join(buf).strip()
        if current_h2:
            # Ensure parent is a dict; if it was set to a string (empty H1 then H2),
            # promote to dict.
            existing = sections.get(current_h1)
            if not isinstance(existing, dict):
                sections[current_h1] = {}
            sections[current_h1][current_h2] = content
        else:
            # Only set if not already promoted to a dict by a previous H2
            if current_h1 not in sections or not isinstance(sections.get(current_h1), dict):
                sections[current_h1] = content

    for line in body.splitlines():
        m1 = re.match(r"^#\s+(.+?)\s*$", line)
        m2 = re.match(r"^##\s+(.+?)\s*$", line)
        if m1:
            flush()
            current_h1 = m1.group(1).strip().lower().replace(" ", "_")
            current_h2 = None
            buf = []
        elif m2:
            flush()
            current_h2 = m2.group(1).strip().lower().replace(" ", "_")
            buf = []
        else:
            buf.append(line)
    flush()
    return sections


def parse_counts_block(text: str) -> dict:
    """
    counts block has 3 nested keys (today, cumulative, pre_activation), each a list of dicts.
    """
    out: dict[str, list] = {"today": [], "cumulative": [], "pre_activation": []}
    if not text:
        return out

    # Split by top-level key labels
    current_key = None
    current_buf: list[str] = []

    def flush_counts():
        nonlocal current_buf
        if current_key is None or not current_buf:
            return
        parsed = parse_yaml_block("\n".join(current_buf))
        if isinstance(parsed, list):
            out[current_key] = parsed

    for line in text.splitlines():
        m = re.match(r"^(today|cumulative|pre_activation)\s*:\s*$", line.strip())
        if m:
            flush_counts()
            current_key = m.group(1)
            current_buf = []
        else:
            if current_key is not None:
                current_buf.append(line)
    flush_counts()
    return out


def parse_prose_section(text: str) -> str:
    """A pure-prose section: strip blank lines, return single paragraph."""
    if not text:
        return ""
    # Drop frontmatter-style key:value lines if any slipped in
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return " ".join(lines).strip()


def parse_flat_block(text: str) -> dict:
    """A flat key: value YAML-like block."""
    parsed = parse_yaml_block(text or "")
    return parsed if isinstance(parsed, dict) else {}


# ─────────────────────────────────────────────────────────────
# Main build
# ─────────────────────────────────────────────────────────────

def build():
    if not SRC.exists():
        sys.stderr.write(f"[dashboard_build] source missing: {SRC}\n")
        sys.exit(1)

    text = SRC.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    secs = parse_sections(body)

    # Progress bars
    old_world_raw = secs.get("progress", {}).get("old_world", "") if isinstance(secs.get("progress"), dict) else ""
    new_world_raw = secs.get("progress", {}).get("new_world", "") if isinstance(secs.get("progress"), dict) else ""
    old_world = parse_yaml_block(old_world_raw) or []
    new_world = parse_yaml_block(new_world_raw) or []
    if not isinstance(old_world, list):
        old_world = []
    if not isinstance(new_world, list):
        new_world = []

    # Compute group weights as sum
    def sum_w(items):
        return sum((it.get("weight") or 0) for it in items if isinstance(it, dict))

    old_w = sum_w(old_world)
    new_w = sum_w(new_world)

    # Counts
    counts = parse_counts_block(secs.get("counts", "") if isinstance(secs.get("counts"), str) else "")

    # 5-P
    fivep_raw = secs.get("five_p", "")
    five_p = parse_yaml_block(fivep_raw) if fivep_raw else []
    if not isinstance(five_p, list):
        five_p = []

    # Latest narrator + journal + footer
    latest_narrator = parse_flat_block(secs.get("latest_narrator", ""))
    latest_journal = parse_flat_block(secs.get("latest_journal", ""))
    footer = parse_flat_block(secs.get("footer", ""))

    # Prose sections
    vision = parse_prose_section(secs.get("vision", ""))
    mission = parse_prose_section(secs.get("mission", ""))
    values = parse_prose_section(secs.get("values", ""))
    intent = parse_prose_section(secs.get("intent", ""))
    trust_tier_text = parse_prose_section(secs.get("trust_tier", ""))

    # Assemble
    out = {
        "_schema_version": fm.get("schema_version", 1),
        "_mtime": int(SRC.stat().st_mtime),
        "_built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "last_updated": fm.get("last_updated"),
        "session_id": fm.get("session_id"),
        "session_name": fm.get("session_name"),
        "trust_tier": fm.get("trust_tier"),
        "trust_tier_text": trust_tier_text,
        "sunheart_score": fm.get("sunheart_score"),
        "vision": vision,
        "mission": mission,
        "values": values,
        "intent": intent,
        "progress": {
            "old_world": old_world,
            "new_world": new_world,
            "old_world_weight": old_w,
            "new_world_weight": new_w,
        },
        "counts": counts,
        "five_p": five_p,
        "latest_narrator": latest_narrator or None,
        "latest_journal": latest_journal or None,
        "footer": footer,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[dashboard_build] OK · {SRC.name} → {OUT.relative_to(REPO)} · {len(old_world)}+{len(new_world)} bars · mtime {out['_mtime']}")


if __name__ == "__main__":
    build()
