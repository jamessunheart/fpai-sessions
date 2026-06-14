#!/usr/bin/env python3
"""Generate docs/status/overnight-report.md from core intent + missions data."""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT / "core" / "architecture" / "STATE" / "NOW.md"
ACTIONS_DIR = ROOT / "core" / "architecture" / "ACTIONS" / "fast-load"
MISSIONS_FILE = ROOT / "orchestration" / "missions" / "missions.md"
OUTPUT_FILE = ROOT / "docs" / "status" / "overnight-report.md"


def read_state_excerpt(lines: int = 40) -> str:
    text = STATE_FILE.read_text().strip().splitlines()
    excerpt = text[:lines]
    return "\n".join(excerpt).strip()


def list_actions() -> List[str]:
    scripts = []
    if ACTIONS_DIR.exists():
        for item in sorted(ACTIONS_DIR.iterdir()):
            if item.is_file():
                scripts.append(item.name)
    return scripts


def parse_missions() -> List[dict]:
    rows: List[dict] = []
    lines = MISSIONS_FILE.read_text().splitlines()
    table_started = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| Mission"):
            table_started = True
            continue
        if table_started:
            if not stripped.startswith("|"):
                break
            if stripped.startswith("| ---"):
                continue
            parts = [cell.strip() for cell in line.split("|")[1:-1]]
            if len(parts) != 5:
                continue
            mission, priority, role, files, deliverable = parts
            rows.append({
                "mission": mission,
                "priority": priority,
                "role": role,
                "files": files,
                "deliverable": deliverable,
            })
    return rows


def main() -> None:
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    state_excerpt = read_state_excerpt()
    actions = list_actions()
    missions = [m for m in parse_missions() if m["priority"] in {"P0", "P1"}]

    lines = [
        "# Overnight Intent Snapshot",
        "",
        f"Generated: {timestamp}",
        "",
        "## Intent – STATE/NOW.md",
        state_excerpt,
        "",
        "## Fast-Load Actions",
    ]
    if actions:
        lines += ["- " + name for name in actions]
    else:
        lines.append("_No fast-load scripts found._")

    lines += ["", "## Priority Missions (P0–P1)"]
    if missions:
        lines.append("| Mission | Priority | Role | Files | Expected Deliverable |")
        lines.append("| --- | --- | --- | --- | --- |")
        lines += [f"| {m['mission']} | {m['priority']} | {m['role']} | {m['files']} | {m['deliverable']} |" for m in missions]
    else:
        lines.append("_No active P0–P1 missions._")

    OUTPUT_FILE.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
