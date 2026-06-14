#!/usr/bin/env python3
"""
Validate that every open mission declares its Constitution alignment.

Usage:
    python mission_constitution_check.py
The script exits with code 1 if any mission is missing the expected fields.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPEN_DIR = ROOT / "missions" / "open"

EXPECTED_SNIPPETS = {
    "**Constitution Principle:**": "missing Constitution Principle",
    "**Regenerative Impact:**": "missing Regenerative Impact",
}


def main() -> None:
    if not OPEN_DIR.exists():
        print(f"[WARN] Missions directory not found: {OPEN_DIR}")
        sys.exit(0)

    missing: list[str] = []
    for mission in sorted(OPEN_DIR.glob("M*.md")):
        text = mission.read_text()
        for snippet, label in EXPECTED_SNIPPETS.items():
            if snippet not in text:
                missing.append(f"{mission.relative_to(ROOT)} → {label}")

    if missing:
        print("Constitution alignment check failed:")
        for item in missing:
            print(f"  - {item}")
        sys.exit(1)

    print(f"Checked {len(list(OPEN_DIR.glob('M*.md')))} missions — all declare Constitution alignment.")


if __name__ == "__main__":
    main()

