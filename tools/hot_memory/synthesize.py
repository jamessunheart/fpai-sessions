#!/usr/bin/env python3
"""Synthesize scanner deltas into one bounded HOT_STATE document."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from tools.hot_memory.common import DEFAULT_HOT_DIR, REPO_ROOT, clean_text, is_public_safe, load_scans, utc_stamp

DEFAULT_HOT_STATE = DEFAULT_HOT_DIR / "HOT_STATE.md"
DEFAULT_REPO_MIRROR = REPO_ROOT / "core" / "STATE" / "HOT_STATE.md"
MAX_HOT_STATE_CHARS = int(os.environ.get("HOT_MEMORY_MAX_CHARS", "3000"))
SECTION_ORDER = [
    ("directive", "Active directives"),
    ("spec_queue", "Spec queue"),
    ("general", "System identity facts"),
    ("decision", "Recent architecture decisions"),
    ("ops", "Active measurements"),
    ("signal", "Recent correction signals"),
]


def synthesize(
    *,
    hot_dir: Path = DEFAULT_HOT_DIR,
    output: Path = DEFAULT_HOT_STATE,
    mirror: Path | None = DEFAULT_REPO_MIRROR,
    max_chars: int = MAX_HOT_STATE_CHARS,
) -> str:
    scans = load_scans(hot_dir)
    rendered = render_hot_state(scans, max_chars=max_chars)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    if mirror:
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mirror.write_text(rendered, encoding="utf-8")
    _append_log(hot_dir / "hot_state_log.jsonl", output=output, chars=len(rendered), scans=scans)
    return rendered


def render_hot_state(scans: list[dict[str, Any]], *, max_chars: int = MAX_HOT_STATE_CHARS) -> str:
    facts = _facts(scans)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for item in facts:
        by_category.setdefault(str(item.get("category") or "general"), []).append(item)
    for rows in by_category.values():
        rows.sort(key=lambda row: (-int(row.get("weight") or 0), str(row.get("date") or ""), str(row.get("text") or "")))

    # Inject self-portrait gap summary if fresh (<24h)
    self_portrait_block = ""
    portrait_path = REPO_ROOT / "core" / "STATE" / "SELF_PORTRAIT.md"
    if portrait_path.exists():
        import time as _time
        age_h = (_time.time() - portrait_path.stat().st_mtime) / 3600
        if age_h < 24:
            import re as _re
            raw = portrait_path.read_text(encoding="utf-8")
            gap = _re.search(r"## The gap\n(.*?)(?=\n##|\Z)", raw, _re.DOTALL)
            biases = _re.search(r"## Platform biases.*?\n(.*?)(?=\n##|\Z)", raw, _re.DOTALL)
            gap_txt = gap.group(1).strip()[:300] if gap else ""
            bias_txt = biases.group(1).strip()[:200] if biases else ""
            if gap_txt or bias_txt:
                self_portrait_block = f"\n## Honesty mirror (self-portrait)\n- GAP: {gap_txt}\n- BIASES: {bias_txt}\n"

    lines = [f"# HOT_STATE - {utc_stamp()} - synthesized from {len(scans)} scanners", ""]
    if self_portrait_block:
        lines.append(self_portrait_block)
    for category, title in SECTION_ORDER:
        rows = by_category.get(category, [])
        if not rows:
            continue
        lines.append(f"## {title}")
        for row in rows[:4 if category == "directive" else 3]:
            lines.append(f"- {clean_text(str(row.get('text') or ''))} [source: {clean_text(str(row.get('source') or 'unknown'), max_chars=90)} - {clean_text(str(row.get('date') or 'unknown'), max_chars=40)}]")
        lines.append("")
    pruned = _pruned(scans)
    if pruned:
        lines.append("## Pruned")
        for item in pruned[:4]:
            lines.append(f"- {clean_text(item, max_chars=180)}")
        lines.append("")
    rendered = "\n".join(lines).strip() + "\n"
    if len(rendered) <= max_chars:
        return rendered
    return _bounded(lines, max_chars=max_chars)


def _facts(scans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for scan in scans:
        for item in scan.get("facts") or []:
            if not isinstance(item, dict):
                continue
            text = clean_text(str(item.get("text") or ""))
            if not is_public_safe(text):
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            rows.append({**item, "text": text})
    return rows


def _pruned(scans: list[dict[str, Any]]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for scan in scans:
        for item in scan.get("pruned") or []:
            text = clean_text(str(item), max_chars=180)
            if text and text.lower() not in seen and is_public_safe(text):
                seen.add(text.lower())
                rows.append(text)
    return rows


def _bounded(lines: list[str], *, max_chars: int) -> str:
    kept: list[str] = []
    for line in lines:
        candidate = "\n".join([*kept, line]).strip() + "\n"
        if len(candidate) > max_chars - 24:
            break
        kept.append(line)
    return "\n".join(kept).rstrip() + "\n- ... bounded\n"


def _append_log(path: Path, *, output: Path, chars: int, scans: list[dict[str, Any]]) -> None:
    row = {
        "ts": utc_stamp(),
        "event": "hot_state_synthesized",
        "output": str(output),
        "chars": chars,
        "scanner_count": len(scans),
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
    except OSError:
        return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hot-dir", type=Path, default=DEFAULT_HOT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_HOT_STATE)
    parser.add_argument("--mirror", type=Path, default=DEFAULT_REPO_MIRROR)
    parser.add_argument("--no-mirror", action="store_true")
    parser.add_argument("--max-chars", type=int, default=MAX_HOT_STATE_CHARS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    rendered = synthesize(
        hot_dir=args.hot_dir,
        output=args.output,
        mirror=None if args.no_mirror else args.mirror,
        max_chars=args.max_chars,
    )
    if args.json:
        print(json.dumps({"ok": True, "chars": len(rendered), "output": str(args.output)}, sort_keys=True))
    else:
        print(f"wrote {args.output} ({len(rendered)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

