#!/usr/bin/env python3
"""
Generate a machine-readable mission feed plus an opportunities board.

The script works both inside the repo and on the live server. Override
MISSIONS_ROOT or MISSION_FEED_PATHS env vars to customize locations.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

STATUS_DIRS = [
    ("open", "OPEN"),
    ("in-progress", "IN_PROGRESS"),
    ("done", "DONE"),
]


def find_repo_root() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / ".git").exists():
            return ancestor
    return Path(__file__).resolve().parents[-1]


def find_missions_root() -> Path:
    env = os.environ.get("MISSIONS_ROOT")
    if env:
        return Path(env).expanduser()

    candidates = []
    script_path = Path(__file__).resolve()
    for ancestor in script_path.parents:
        candidate = ancestor / "missions"
        if candidate.exists() and candidate.is_dir():
            candidates.append(candidate)
        candidate = ancestor / "orchestration" / "missions"
        if candidate.exists() and candidate.is_dir():
            candidates.append(candidate)
    if candidates:
        return candidates[0]
    raise FileNotFoundError("Unable to locate missions directory. Set MISSIONS_ROOT.")


def find_output_paths() -> List[Path]:
    env = os.environ.get("MISSION_FEED_PATHS")
    if env:
        return [Path(p).expanduser() for p in env.split(",") if p.strip()]

    paths: List[Path] = []
    script_path = Path(__file__).resolve()
    for ancestor in script_path.parents:
        candidate = ancestor / "docs" / "status" / "missions.json"
        if candidate.parent.exists():
            paths.append(candidate)
    # Deduplicate while preserving order
    unique: List[Path] = []
    for path in paths:
        if path not in unique:
            unique.append(path)
    if not unique:
        default = find_repo_root() / "docs" / "status" / "missions.json"
        default.parent.mkdir(parents=True, exist_ok=True)
        unique.append(default)
    return unique


def read_lines(path: Path) -> List[str]:
    return path.read_text().splitlines()


def extract_field(lines: Iterable[str], label: str) -> Optional[str]:
    needle = f"**{label}:**"
    for line in lines:
        if needle in line:
            after = line.split(needle, 1)[1].strip()
            return after.replace("_", " ").strip(" -")
    return None


def normalize_owner(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    lowered = value.lower()
    if any(token in lowered for token in ("ready for owner input", "tbd", "available", "unassigned", "none")):
        return None
    return value


def extract_principle(line: Optional[str]) -> Optional[str]:
    if not line:
        return None
    if "**" in line:
        parts = line.split("**")
        if len(parts) >= 3:
            return parts[1].strip()
    return line


def parse_mission_file(path: Path, status_label: str) -> Dict[str, Optional[str]]:
    lines = read_lines(path)
    metadata = {
        "id": path.stem.split("_")[0],
        "title": lines[0].lstrip("# ").strip() if lines else path.stem,
        "status": status_label,
        "priority": extract_field(lines, "Priority"),
        "owner": normalize_owner(extract_field(lines, "Owner")),
        "status_text": extract_field(lines, "Status"),
        "principle": extract_principle(extract_field(lines, "Constitution Principle")),
        "regenerative_impact": extract_field(lines, "Regenerative Impact"),
        "path": str(path),
    }
    return metadata


def build_feed(missions_root: Path) -> List[Dict[str, Optional[str]]]:
    feed: List[Dict[str, Optional[str]]] = []
    for folder, label in STATUS_DIRS:
        directory = missions_root / folder
        if not directory.exists():
            continue
        for mission_file in sorted(directory.glob("M*.md")):
            feed.append(parse_mission_file(mission_file, label))
    return sorted(feed, key=lambda item: item["id"] or "")


def write_json(feed: List[Dict[str, Optional[str]]], output_paths: List[Path]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "missions": feed,
    }
    for path in output_paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2))


def write_opportunities(feed: List[Dict[str, Optional[str]]], output_paths: List[Path]) -> None:
    rows = [
        "| ID | Title | Priority | Principle |",
        "| --- | --- | --- | --- |",
    ]
    for mission in feed:
        if mission["status"] != "OPEN" or mission["owner"]:
            continue
        rows.append(
            f"| {mission['id']} | {mission['title']} | {mission['priority'] or '-'} | {mission['principle'] or '-'} |"
        )
    content = [
        "# Mission Opportunities",
        f"_Updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')}_",
        "",
    ]
    content.extend(rows if len(rows) > 2 else ["No unassigned missions at the moment."])
    for path in output_paths:
        opp_path = path.parent / "OPPORTUNITIES.md"
        opp_path.write_text("\n".join(content) + "\n")


def main() -> None:
    missions_root = find_missions_root()
    feed = build_feed(missions_root)
    output_paths = find_output_paths()
    write_json(feed, output_paths)
    write_opportunities(feed, output_paths)


if __name__ == "__main__":
    main()

