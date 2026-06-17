#!/usr/bin/env python3
"""Auto-merge resolver for AI-approved doc-only build branches.

The resolver is intentionally narrow:
- source of truth is core/BUILD/REGISTRY.json;
- candidate branches must be status=done and tests_passed=true;
- every changed path must be documentation or build-loop review metadata;
- an independent AI review command must approve immediately before merge;
- dry-run is the default. Passing --execute performs the local merge only.

It never pushes, never targets main, and never deploys.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Sequence

DEFAULT_BASE = "feat/headless-build"
DOC_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".adoc"}
METADATA_PATHS = {
    "core/BUILD/REGISTRY.json",
}
METADATA_PREFIXES = (
    "core/BUILD/results/",
    "core/BUILD/reviews/",
    "core/BUILD/done/",
    "core/BUILD/SESSION_NOTES/",
)
DOC_PREFIXES = (
    "docs/",
    "core/STATE/",
)
NEVER_AUTO_PREFIXES = (
    ".github/",
    ".ssh/",
    ".env",
    "SERVICES/",
    "scripts/",
    "tools/",
    "core/BUILD/cron/",
    "core/BUILD/systemd/",
)
NEVER_AUTO_NAMES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}


class ResolverError(RuntimeError):
    """Raised for expected resolver failures."""


@dataclasses.dataclass(frozen=True)
class BuildEntry:
    build_id: str
    branch: str
    base_branch: str
    status: str
    tests_passed: bool

    @classmethod
    def from_json(cls, raw: dict[str, object], default_base: str) -> "BuildEntry":
        return cls(
            build_id=str(raw.get("id") or raw.get("slug") or raw.get("branch") or ""),
            branch=str(raw.get("branch") or ""),
            base_branch=str(raw.get("base_branch") or default_base),
            status=str(raw.get("status") or ""),
            tests_passed=bool(raw.get("tests_passed")),
        )


@dataclasses.dataclass
class CandidateResult:
    entry: BuildEntry
    action: str
    reason: str
    changed_files: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.entry.build_id,
            "branch": self.entry.branch,
            "base_branch": self.entry.base_branch,
            "action": self.action,
            "reason": self.reason,
            "changed_files": self.changed_files,
        }


def run_git(root: Path, args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise ResolverError(f"git {' '.join(args)} failed: {detail}")
    return proc


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise ResolverError("not inside a git repository")
    return Path(proc.stdout.strip())


def load_registry(path: Path, default_base: str) -> list[BuildEntry]:
    data = json.loads(path.read_text())
    return [
        BuildEntry.from_json(raw, default_base)
        for raw in data.get("active_builds", [])
        if isinstance(raw, dict)
    ]


def validate_base(base: str) -> None:
    if base in {"main", "master"}:
        raise ResolverError(f"refusing to target protected base branch: {base}")


def branch_ref(root: Path, branch: str) -> str | None:
    if not branch or branch in {"main", "master"}:
        return None
    if run_git(root, ["rev-parse", "--verify", branch], check=False).returncode == 0:
        return branch
    remote = f"origin/{branch}"
    if run_git(root, ["rev-parse", "--verify", remote], check=False).returncode == 0:
        return remote
    return None


def is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    return run_git(root, ["merge-base", "--is-ancestor", ancestor, descendant], check=False).returncode == 0


def changed_files(root: Path, base: str, branch: str) -> list[str]:
    proc = run_git(root, ["diff", "--name-only", f"{base}...{branch}"])
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def is_doc_only_path(path: str) -> bool:
    if path in METADATA_PATHS:
        return True
    if path in NEVER_AUTO_NAMES:
        return False
    if any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in NEVER_AUTO_PREFIXES):
        return False
    suffix = Path(path).suffix.lower()
    if any(path.startswith(prefix) for prefix in METADATA_PREFIXES):
        return suffix in DOC_SUFFIXES or path.endswith(".json") or path.endswith(".jsonl")
    if any(path.startswith(prefix) for prefix in DOC_PREFIXES):
        return suffix in DOC_SUFFIXES
    return False


def non_doc_paths(paths: Iterable[str]) -> list[str]:
    return [path for path in paths if not is_doc_only_path(path)]


def worktree_clean(root: Path) -> bool:
    return not run_git(root, ["status", "--porcelain"]).stdout.strip()


def review_command_ok(root: Path, command: Sequence[str], branch: str) -> tuple[bool, str]:
    if not command:
        return False, "missing review command"
    proc = subprocess.run(
        [*command, branch],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    output = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    return proc.returncode == 0, output


def merge_branch(root: Path, base: str, branch_ref_name: str, build_id: str) -> None:
    run_git(root, ["checkout", base])
    message = f"merge({build_id}): auto-merge doc-only AI-approved branch"
    try:
        run_git(root, ["merge", "--no-ff", "-m", message, branch_ref_name])
    except ResolverError:
        run_git(root, ["merge", "--abort"], check=False)
        raise


def eligible_entries(entries: Iterable[BuildEntry], base: str) -> list[BuildEntry]:
    return [
        entry
        for entry in entries
        if entry.status == "done"
        and entry.tests_passed
        and entry.base_branch == base
        and entry.branch not in {"", "main", "master", base}
    ]


def resolve(
    *,
    root: Path,
    registry: Path,
    base: str,
    review_command: Sequence[str],
    execute: bool,
    branch_filter: str | None = None,
) -> list[CandidateResult]:
    validate_base(base)
    entries = eligible_entries(load_registry(registry, base), base)
    if branch_filter:
        entries = [entry for entry in entries if entry.branch == branch_filter]

    results: list[CandidateResult] = []
    if execute and not worktree_clean(root):
        raise ResolverError("refusing to execute with a dirty worktree")

    for entry in entries:
        ref = branch_ref(root, entry.branch)
        if not ref:
            results.append(CandidateResult(entry, "skip", "branch not found", []))
            continue
        if is_ancestor(root, ref, base):
            results.append(CandidateResult(entry, "skip", "already merged", []))
            continue

        paths = changed_files(root, base, ref)
        blocked_paths = non_doc_paths(paths)
        if blocked_paths:
            results.append(
                CandidateResult(
                    entry,
                    "block",
                    "non-doc paths: " + ", ".join(blocked_paths),
                    paths,
                )
            )
            continue

        if not execute:
            results.append(CandidateResult(entry, "would_merge", "doc-only candidate", paths))
            continue

        approved, review_output = review_command_ok(root, review_command, ref)
        if not approved:
            reason = "independent AI review did not approve"
            if review_output:
                reason += f": {review_output}"
            results.append(CandidateResult(entry, "block", reason, paths))
            continue

        merge_branch(root, base, ref, entry.build_id)
        results.append(CandidateResult(entry, "merged", "doc-only and independently AI-approved", paths))

    return results


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--base", default=os.environ.get("MERGE_BASE", DEFAULT_BASE))
    parser.add_argument("--branch", help="Limit resolver to one branch.")
    parser.add_argument("--execute", action="store_true", help="Perform local merges. Default is dry-run.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument(
        "--review-command",
        nargs="+",
        default=None,
        help="Command that accepts branch as its final argument and exits 0 only on approval.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = repo_root()
    registry = args.registry or root / "core/BUILD/REGISTRY.json"
    review_command = args.review_command or [sys.executable, str(root / "tools/merge/ai_review.py")]

    try:
        results = resolve(
            root=root,
            registry=registry,
            base=args.base,
            review_command=review_command,
            execute=args.execute,
            branch_filter=args.branch,
        )
    except ResolverError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([result.as_dict() for result in results], indent=2, sort_keys=True))
    else:
        mode = "execute" if args.execute else "dry-run"
        print(f"auto-merge doc-only resolver ({mode})")
        if not results:
            print("no eligible registry entries")
        for result in results:
            print(f"{result.action}: {result.entry.branch} - {result.reason}")
            for path in result.changed_files:
                print(f"  {path}")

    if args.branch and any(result.action == "block" for result in results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
