#!/usr/bin/env python3
"""Command-line utilities for mission lifecycle management."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from generate_mission_feed import (
    STATUS_DIRS,
    build_feed,
    find_missions_root,
    find_repo_root,
    parse_mission_file,
)


def update_field(lines: list[str], field: str, new_value: str) -> list[str]:
    needle = f"**{field}:**"
    for idx, line in enumerate(lines):
        if needle in line:
            prefix = line.split(needle, 1)[0]
            lines[idx] = f"{prefix}{needle} {new_value}"
            return lines
    # Insert near the top (after title metadata block)
    insertion = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("##"):
            insertion = idx
            break
    insertion = insertion or len(lines)
    lines.insert(insertion, f"- **{field}:** {new_value}")
    return lines


def save_lines(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n")


def find_mission_file(missions_root: Path, mission_id: str) -> Tuple[Path, str]:
    mission_id = mission_id.upper()
    for folder, label in STATUS_DIRS:
        directory = missions_root / folder
        if not directory.exists():
            continue
        for candidate in directory.glob(f"{mission_id}*.md"):
            return candidate, folder
    raise FileNotFoundError(f"Mission {mission_id} not found in {missions_root}")


def git_commit(repo_root: Path, message: str, target_paths: list[Path]) -> None:
    rel_paths = [str(path.relative_to(repo_root)) for path in target_paths]
    subprocess.run(["git", "add", "-A"] + rel_paths, check=True, cwd=repo_root)
    subprocess.run(["git", "commit", "-m", message], check=True, cwd=repo_root)


def list_missions(missions_root: Path) -> None:
    feed = build_feed(missions_root)
    print(f"{'ID':<6} {'Status':<12} {'Priority':<8} {'Owner':<15} Title")
    print("-" * 80)
    for entry in feed:
        if entry["status"] != "OPEN":
            continue
        print(
            f"{entry['id']:<6} {entry['status']:<12} {entry['priority'] or '-':<8} "
            f"{(entry['owner'] or 'UNASSIGNED'):<15} {entry['title']}"
        )


def claim_mission(missions_root: Path, repo_root: Path, mission_id: str, owner: str) -> None:
    path, folder = find_mission_file(missions_root, mission_id)
    if folder != "open":
        raise ValueError(f"Mission {mission_id} is not in open/. Found in {folder}.")
    lines = path.read_text().splitlines()
    lines = update_field(lines, "Owner", owner)
    lines = update_field(lines, "Status", "IN-PROGRESS")
    save_lines(path, lines)

    target = missions_root / "in-progress" / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(path, target)

    git_commit(repo_root, f"chore(missions): claim {mission_id} for {owner}", [missions_root])
    print(f"Mission {mission_id} claimed by {owner}.")


def close_mission(missions_root: Path, repo_root: Path, mission_id: str, notes: Optional[str]) -> None:
    path, _ = find_mission_file(missions_root, mission_id)
    lines = path.read_text().splitlines()
    lines = update_field(lines, "Status", "DONE")
    if notes:
        lines = update_field(lines, "Notes", notes)
    save_lines(path, lines)

    target = missions_root / "done" / path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(path, target)

    git_commit(repo_root, f"chore(missions): close {mission_id}", [missions_root])
    print(f"Mission {mission_id} closed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mission management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List open missions")

    claim_parser = subparsers.add_parser("claim", help="Claim a mission")
    claim_parser.add_argument("mission_id")
    claim_parser.add_argument("owner")

    close_parser = subparsers.add_parser("close", help="Close a mission")
    close_parser.add_argument("mission_id")
    close_parser.add_argument("--notes")

    args = parser.parse_args()
    missions_root = find_missions_root()
    repo_root = find_repo_root()

    if args.command == "list":
        list_missions(missions_root)
    elif args.command == "claim":
        claim_mission(missions_root, repo_root, args.mission_id, args.owner)
    elif args.command == "close":
        close_mission(missions_root, repo_root, args.mission_id, args.notes)


if __name__ == "__main__":
    main()

