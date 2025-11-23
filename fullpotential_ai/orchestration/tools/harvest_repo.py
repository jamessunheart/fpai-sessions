#!/usr/bin/env python3
"""
Automate harvesting code from external repositories via git subtree.

Steps performed:
1. Add/fetch a temporary remote.
2. Run `git subtree add --prefix ... --squash`.
3. Drop the temporary remote.
4. Commit any pending changes (if subtree did not create one).
5. Push the updated main branch.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Sequence

REMOTE_NAME = "temp_harvest"
PLACEHOLDER_FILES = {".gitkeep", ".keep"}


class HarvestError(RuntimeError):
    """Raised when the harvest workflow cannot proceed safely."""


def find_repo_root() -> Path:
    script_path = Path(__file__).resolve()
    for ancestor in [script_path, *script_path.parents]:
        if (ancestor / ".git").is_dir():
            return ancestor
    raise HarvestError("Unable to locate repository root (.git not found).")


def run_git(args: Sequence[str], repo_root: Path, capture_output: bool = True) -> str:
    cmd = ["git", *args]
    if capture_output:
        result = subprocess.run(
            cmd,
            cwd=repo_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        return result.stdout.strip()
    subprocess.run(cmd, cwd=repo_root, check=True)
    return ""


def ensure_clean_worktree(repo_root: Path) -> None:
    status = run_git(["status", "--porcelain"], repo_root)
    if status:
        raise HarvestError("Working tree has uncommitted changes. Commit or stash them before harvesting.")


def ensure_on_main(repo_root: Path) -> None:
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if branch != "main":
        raise HarvestError(f"Current branch is '{branch}'. Checkout 'main' before running the harvester.")


def ensure_remote_slot_available(repo_root: Path) -> None:
    remotes = run_git(["remote"], repo_root).splitlines()
    if REMOTE_NAME in remotes:
        raise HarvestError(f"Remote '{REMOTE_NAME}' already exists. Remove it manually or choose a different name.")


def is_effectively_empty(path: Path) -> bool:
    for child in path.iterdir():
        if child.is_file() and child.name in PLACEHOLDER_FILES:
            continue
        return False
    return True


def ensure_safe_prefix(repo_root: Path, requested_prefix: str) -> str:
    cleaned = requested_prefix.strip()
    if not cleaned:
        raise HarvestError("Target path (--path) must be provided.")

    path_obj = Path(cleaned)
    if path_obj.is_absolute():
        raise HarvestError("Target path must be relative to the repo root.")

    resolved = (repo_root / path_obj).resolve()
    try:
        relative = resolved.relative_to(repo_root)
    except ValueError as exc:
        raise HarvestError("Target path escapes the repository root. Refusing to continue.") from exc

    if resolved.exists():
        if not resolved.is_dir():
            raise HarvestError(f"Target path '{relative}' already exists and is not a directory.")
        if not is_effectively_empty(resolved):
            raise HarvestError(f"Target directory '{relative}' is not empty. Choose an empty/non-existent path.")

    return relative.as_posix()


def add_remote(repo_root: Path, url: str) -> None:
    print(f"Adding temporary remote '{REMOTE_NAME}' for {url}...")
    run_git(["remote", "add", "-f", REMOTE_NAME, url], repo_root, capture_output=False)


def remove_remote(repo_root: Path) -> None:
    print(f"Removing temporary remote '{REMOTE_NAME}'...")
    run_git(["remote", "remove", REMOTE_NAME], repo_root, capture_output=False)


def run_subtree_add(repo_root: Path, prefix: str, branch: str, commit_message: str) -> None:
    print(f"Running git subtree add into '{prefix}' from {REMOTE_NAME}/{branch}...")
    run_git(
        ["subtree", "add", "--prefix", prefix, REMOTE_NAME, branch, "--squash", "--message", commit_message],
        repo_root,
        capture_output=False,
    )


def commit_if_needed(repo_root: Path, prefix: str, commit_message: str) -> bool:
    status = run_git(["status", "--porcelain"], repo_root)
    if not status:
        print("No pending changes to commit; git subtree already created the merge commit.")
        return False

    print("Staging harvested files for commit...")
    run_git(["add", "--all", prefix], repo_root, capture_output=False)
    print(f"Committing harvested code with message: {commit_message}")
    run_git(["commit", "-m", commit_message], repo_root, capture_output=False)
    return True


def push_main(repo_root: Path) -> None:
    print("Pushing 'main' to origin...")
    run_git(["push", "origin", "main"], repo_root, capture_output=False)


def harvest(url: str, branch: str, target_path: str) -> None:
    repo_root = find_repo_root()
    ensure_clean_worktree(repo_root)
    ensure_on_main(repo_root)
    ensure_remote_slot_available(repo_root)
    prefix = ensure_safe_prefix(repo_root, target_path)
    commit_message = f"harvest: merged {url} into {prefix}"

    remote_added = False
    try:
        add_remote(repo_root, url)
        remote_added = True
        run_subtree_add(repo_root, prefix, branch, commit_message)
    finally:
        if remote_added:
            try:
                remove_remote(repo_root)
            except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
                raise HarvestError(f"Failed to remove temporary remote '{REMOTE_NAME}': {exc}") from exc

    commit_if_needed(repo_root, prefix, commit_message)
    push_main(repo_root)
    print("Harvest complete.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harvest external repos via git subtree.")
    parser.add_argument("--url", required=True, help="Git URL of the repository to harvest.")
    parser.add_argument("--branch", default="main", help="Branch to harvest from the remote repository.")
    parser.add_argument("--path", required=True, help="Target directory (relative to repo root) for the subtree.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        harvest(args.url, args.branch, args.path)
    except HarvestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(
            f"Command '{' '.join(exc.cmd)}' failed with exit code {exc.returncode}.",
            file=sys.stderr,
        )
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()

