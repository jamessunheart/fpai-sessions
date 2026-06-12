#!/usr/bin/env python3
"""Generate docs/status/INDEX.md from available status files."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATUS_DIR = ROOT / "docs" / "status"
OUTPUT_FILE = STATUS_DIR / "INDEX.md"

SKIP = {"INDEX.md"}


def extract_title(path: Path) -> str:
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            return line.lstrip("# ").strip()
    return path.stem


def main() -> None:
    entries = []
    for md in sorted(STATUS_DIR.glob("*.md")):
        if md.name in SKIP:
            continue
        title = extract_title(md)
        rel = md.relative_to(ROOT)
        entries.append((title, rel.as_posix()))

    lines = [
        "# Status Index",
        "",
        "Automatically generated list of status and health reports.",
        "",
    ]
    for title, rel in entries:
        lines.append(f"- [{title}]({rel})")

    OUTPUT_FILE.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
