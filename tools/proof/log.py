#!/usr/bin/env python3
"""Auto-proof — one command that records a ship to both proof logs.

Rung 1 of the self-standing ladder (Bar 4). See docs/codex/AI_PROTOCOLS.md.

Enforces the Buildstream Law: a build is valid only if it unlocks the next
adjacent, nameable downstream intent. If it unlocks nothing adjacent, it must
be labeled honestly as `maintenance`, `decoration`, or `drift`. Vague unlocks
("improves the system", "supports Heaven on Earth", etc.) are rejected.

Every row carries: Intent solved · Unlocks next · Proof · Next move.

Usage:
    python3 tools/proof/log.py \
        --summary "what shipped (the intent solved)" \
        --unlocks "the next adjacent intent this opens" \
        --next "the immediate next move" \
        [--stream Game] [--actor "AI(Ember)"] [--tested "py_compile + live"] \
        [--files "tools/proof/log.py"] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

HOME = Path.home()
VAULT = Path(
    os.environ.get(
        "FPAI_VAULT",
        HOME
        / "Library"
        / "Mobile Documents"
        / "iCloud~md~obsidian"
        / "Documents"
        / "FPOS"
        / "Full Potential OS",
    )
)
VAULT_PROOF = VAULT / "00_MEMORY" / "PROOF LOG.md"
LOCAL_PROOF = HOME / ".claude" / "memory-global" / "PROOF_LOG.md"

# Honest non-unlock labels — valid when a build genuinely opens nothing adjacent.
HONEST_LABELS = {"maintenance", "decoration", "drift"}

# Vague unlocks that dodge the Buildstream Law — rejected.
VAGUE_PHRASES = (
    "improves the system",
    "improve the system",
    "supports the system",
    "support the system",
    "better system",
    "improves things",
    "makes things better",
    "general improvement",
    "supports heaven",
    "heaven on earth",
    "helps the system",
    "improves coherence",
    "good for the system",
)


def stamp(now: dt.datetime) -> str:
    """`YYYY-MM-DD HH:MM TZ` in local time (e.g. 2026-06-06 18:12 EEST)."""
    tz = now.strftime("%Z") or "local"
    return f"{now:%Y-%m-%d %H:%M} {tz}"


def validate_unlocks(unlocks: str) -> str | None:
    """Return an error string if the unlock violates the Buildstream Law, else None."""
    u = unlocks.strip()
    low = u.lower()
    if low in HONEST_LABELS:
        return None  # honest non-unlock — allowed
    if len(u) < 12:
        return (
            f"Unlock too vague/short: {u!r}. Name the NEXT practical intent it opens, "
            f"or label it honestly as one of: {', '.join(sorted(HONEST_LABELS))}."
        )
    for phrase in VAGUE_PHRASES:
        if phrase in low:
            return (
                f"Vague unlock rejected ({phrase!r}). The Buildstream Law requires the "
                f"NEXT adjacent, nameable intent — not a distant aspiration. "
                f"Or label it: {', '.join(sorted(HONEST_LABELS))}."
            )
    return None


def build_row(args: argparse.Namespace, now: dt.datetime) -> str:
    proof = args.tested.strip() if args.tested else "(see files)"
    if args.files:
        proof = f"{proof} · Files: {args.files.strip()}" if args.tested else f"Files: {args.files.strip()}"
    return (
        f"- {stamp(now)} · [{args.stream}]"
        f" · Intent solved: {args.summary.strip()}"
        f" · Unlocks next: {args.unlocks.strip()}"
        f" · Proof: {proof}"
        f" · Next move: {args.next.strip()}"
        f" · {args.actor}"
    )


def already_logged(path: Path, row: str) -> bool:
    if not path.exists():
        return False
    try:
        return row in path.read_text(encoding="utf-8")
    except OSError:
        return False


def insert_after_header(text: str, row: str) -> str:
    """Prepend the row right after the first `---` separator (newest on top)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "---":
            j = i + 1
            if j < len(lines) and lines[j].strip() == "":
                j += 1
            lines.insert(j, row)
            return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    return row + "\n" + text


def write_proof(path: Path, row: str, dry: bool) -> str:
    if already_logged(path, row):
        return f"skip (already present): {path}"
    if dry:
        return f"would write → {path}"
    if not path.exists():
        return f"MISSING target (not written): {path}"
    text = path.read_text(encoding="utf-8")
    path.write_text(insert_after_header(text, row), encoding="utf-8")
    return f"wrote → {path}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Record a ship to both proof logs (Buildstream Law enforced).")
    ap.add_argument("--summary", required=True, help="the intent solved / what shipped")
    ap.add_argument("--unlocks", required=True, help="the NEXT adjacent nameable intent this opens (or: maintenance/decoration/drift)")
    ap.add_argument("--next", required=True, help="the immediate next move")
    ap.add_argument("--stream", default="Game", help="Sunheart stream (default Game)")
    ap.add_argument("--actor", default="AI(Ember)", help="who shipped it")
    ap.add_argument("--tested", default="", help="proof / verification done")
    ap.add_argument("--files", default="", help="files changed")
    ap.add_argument("--dry-run", action="store_true", help="print, write nothing")
    args = ap.parse_args(argv)

    err = validate_unlocks(args.unlocks)
    if err:
        print(f"BUILDSTREAM LAW: {err}", file=sys.stderr)
        return 2

    now = dt.datetime.now().astimezone()
    row = build_row(args, now)

    print(row)
    print("---")
    for target in (VAULT_PROOF, LOCAL_PROOF):
        print(write_proof(target, row, args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
