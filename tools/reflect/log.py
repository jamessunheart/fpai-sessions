#!/usr/bin/env python3
"""Reflections — log the system's thinking about itself, and surface it.

A running wall (newest-on-top) of reflections on self / system / process / doctrine.
Appends to vault `00_MEMORY/REFLECTIONS LOG.md`, then regenerates the live
"Latest reflections" + "By category" blocks inside `00_MEMORY/SYSTEM SELF-MODEL.md`
so they're never buried.

Usage:
    python3 tools/reflect/log.py --who Ember --category self \
        --insight "PageRank measures what the system is about, not what runs it." [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
from pathlib import Path

HOME = Path.home()
VAULT = Path(
    os.environ.get(
        "FPAI_VAULT",
        HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian"
        / "Documents" / "FPOS" / "Full Potential OS",
    )
)
LOG = VAULT / "00_MEMORY" / "REFLECTIONS LOG.md"
SELFMODEL = VAULT / "00_MEMORY" / "SYSTEM SELF-MODEL.md"

R_START = "<!-- REFLECT:START -->"
R_END = "<!-- REFLECT:END -->"
LATEST_N = 12
CATEGORIES = ("self", "system", "process", "doctrine")
CAT_ICON = {"core": "⭐", "self": "🪞", "system": "🏗️", "process": "🔄", "doctrine": "📐"}


def stamp(now: dt.datetime) -> str:
    return f"{now:%Y-%m-%d %H:%M} {now.strftime('%Z') or 'local'}"


def prepend_entry(text: str, row: str) -> str:
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.strip() == "---":
            j = i + 1
            if j < len(lines) and lines[j].strip() == "":
                j += 1
            lines.insert(j, row)
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return text + "\n" + row + "\n"


def parse_entries() -> list[tuple[str, str, str, str]]:
    """Return [(stamp, who, category, insight)] newest-first from the log."""
    if not LOG.exists():
        return []
    out = []
    for ln in LOG.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- (.+?) · (.+?) · \[(.+?)\] · (.+)$", ln)
        if m:
            out.append((m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4).strip()))
    return out


def render_block(entries: list[tuple[str, str, str, str]]) -> str:
    """Three tiers, mirroring the Index of Indexes: Core (curated) → Weighted (computed) → Recent (dated)."""
    # ⭐ Core — promoted durable self-truths (category 'core')
    core = [(s, who, ins) for s, who, c, ins in entries if c == "core"]
    core_str = (
        "\n".join(f"- ⭐ {ins}  _({who})_" for s, who, ins in core)
        if core else "_none promoted yet — log with `--category core` to pin a durable truth_"
    )

    # 📊 Weighted — non-core categories ranked by volume (where learning concentrates) + drill-down
    ranked = []
    for cat in CATEGORIES:
        rows = [(s, who, ins) for s, who, c, ins in entries if c == cat]
        if rows:
            ranked.append((cat, rows))
    ranked.sort(key=lambda x: len(x[1]), reverse=True)
    weighted = "\n".join(
        f"- {CAT_ICON[cat]} **{cat}** · {len(rows)} {'▓' * min(len(rows), 12)}"
        for cat, rows in ranked
    ) or "_none yet_"
    toggles = "\n\n".join(
        f"> [!note]- {CAT_ICON[cat]} {cat} · {len(rows)}\n"
        + "\n".join(f"> - `{s[:10]}` · {who} — {ins}" for s, who, ins in rows)
        for cat, rows in ranked
    )

    # 🪞 Recent — dated wall, newest first
    recent = "\n".join(
        f"- `{s}` · **{who}** · {CAT_ICON.get(cat, '·')} {cat} — {ins}"
        for s, who, cat, ins in entries[:LATEST_N]
    ) or "_none yet_"

    return f"""{R_START}
### ⭐ Core insights  *(promoted — durable self-truths the system operates by)*

{core_str}

### 📊 By weight  *(where the system's learning concentrates)*

{weighted}

{toggles}

### 🪞 Recent reflections  *(dated wall — newest first · full log [[REFLECTIONS LOG]])*

{recent}
{R_END}"""


def inject_selfmodel(block: str, dry: bool) -> str:
    if not SELFMODEL.exists():
        return f"skip (missing): {SELFMODEL}"
    text = SELFMODEL.read_text(encoding="utf-8")
    if R_START in text and R_END in text:
        new = re.sub(re.escape(R_START) + r".*?" + re.escape(R_END), lambda _: block, text, count=1, flags=re.DOTALL)
    else:
        # insert just after the first H1
        lines = text.splitlines()
        for i, ln in enumerate(lines):
            if ln.startswith("# "):
                lines.insert(i + 1, "\n" + block + "\n")
                break
        new = "\n".join(lines)
    if dry:
        return f"would update → {SELFMODEL}"
    if new != text:
        SELFMODEL.write_text(new, encoding="utf-8")
        return f"surfaced → {SELFMODEL}"
    return f"unchanged → {SELFMODEL}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Log a system self-reflection + surface it.")
    ap.add_argument("--insight", help="the reflection (one line; not needed with --resurface)")
    ap.add_argument("--who", default="Ember", help="who/what logged it (Ember/Codex/James/GPT/…)")
    ap.add_argument("--category", default="system", help="self | system | process | doctrine")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resurface", action="store_true", help="just regenerate the Self-Model block, don't log")
    args = ap.parse_args(argv)

    if not args.resurface and not args.insight:
        ap.error("--insight is required unless --resurface is given")

    now = dt.datetime.now().astimezone()
    if not args.resurface:
        row = f"- {stamp(now)} · {args.who} · [{args.category}] · {args.insight.strip()}"
        if LOG.exists():
            text = LOG.read_text(encoding="utf-8")
            if row in text:
                print(f"skip (already present): {LOG}")
            elif args.dry_run:
                print(row)
                print(f"would write → {LOG}")
            else:
                LOG.write_text(prepend_entry(text, row), encoding="utf-8")
                print(f"logged → {LOG}")
        else:
            print(f"MISSING log file: {LOG}")
            return 1

    block = render_block(parse_entries())
    print(inject_selfmodel(block, args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
