#!/usr/bin/env python3
"""Rollback a build worktree to the last known good ref when verification fails.

This guard is intentionally local:
- it runs one explicit verification command;
- it never pushes, merges, deploys, or touches services;
- on failure, it resets only the current git worktree to a known-good ref;
- every decision is written to JSON and Markdown reports for James/Ember review.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Sequence

DEFAULT_KNOWN_GOOD = "feat/headless-build"
DEFAULT_REPORT_DIR = Path("core/BUILD/reports/auto_revert")
PROTECTED_BRANCHES = {"main", "master"}


class AutoRevertError(RuntimeError):
    """Expected operator-facing failure."""


@dataclasses.dataclass
class CheckResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def output_tail(self) -> str:
        combined = "\n".join(part for part in (self.stdout, self.stderr) if part)
        lines = [line.rstrip() for line in combined.splitlines() if line.strip()]
        return "\n".join(lines[-40:])


@dataclasses.dataclass
class AutoRevertReport:
    status: str
    branch: str
    known_good_ref: str
    known_good_sha: str
    failed_head_sha: str
    check_command: list[str]
    check_returncode: int
    changed_files_before_revert: list[str]
    rollback_performed: bool
    report_id: str
    failed_backup_ref: str
    failed_diff_path: str
    post_revert_head_sha: str
    post_revert_clean: bool
    output_tail: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return dataclasses.asdict(self)


def run_git(root: Path, args: Sequence[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise AutoRevertError(f"git {' '.join(args)} failed: {detail}")
    return proc


def repo_root(start: Path | None = None) -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AutoRevertError("not inside a git repository")
    return Path(proc.stdout.strip())


def current_branch(root: Path) -> str:
    return run_git(root, ["branch", "--show-current"]).stdout.strip() or "DETACHED"


def rev_parse(root: Path, ref: str) -> str:
    return run_git(root, ["rev-parse", "--verify", ref]).stdout.strip()


def worktree_changes(root: Path) -> list[str]:
    proc = run_git(root, ["status", "--porcelain"])
    changes: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changes.append(path.strip())
    return sorted(changes)


def run_check(root: Path, command: Sequence[str]) -> CheckResult:
    if not command:
        raise AutoRevertError("missing check command")
    proc = subprocess.run(
        list(command),
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return CheckResult(list(command), proc.returncode, proc.stdout, proc.stderr)


def reset_to_known_good(root: Path, known_good_ref: str, *, clean_untracked: bool) -> None:
    run_git(root, ["reset", "--hard", known_good_ref])
    if clean_untracked:
        run_git(root, ["clean", "-fd"])


def preserve_failed_head(root: Path, report_id: str, failed_head_sha: str) -> str:
    backup_ref = f"refs/fpai-auto-revert/{report_id}"
    run_git(root, ["update-ref", backup_ref, failed_head_sha])
    return backup_ref


def write_failed_diff(root: Path, report_dir: Path, report_id: str, known_good_sha: str, backup_ref: str) -> Path:
    out_dir = report_dir if report_dir.is_absolute() else root / report_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    diff_path = out_dir / f"{report_id}.failed.diff"
    proc = run_git(root, ["diff", "--binary", known_good_sha, backup_ref], check=False)
    diff_path.write_text(proc.stdout, encoding="utf-8")
    return diff_path


def append_ops_ledger(path: Path, report: AutoRevertReport) -> None:
    row = {
        "ts": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "auto_revert",
        "event": "reversed" if report.rollback_performed else report.status,
        "detail": report.reason,
        "cost": "$0",
        "artifact": str(path),
        "next": "James/Ember review auto-revert report before rebuilding",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
        "known_good_ref": report.known_good_ref,
        "failed_head_sha": report.failed_head_sha,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_reports(root: Path, report_dir: Path, report: AutoRevertReport) -> tuple[Path, Path]:
    out_dir = report_dir if report_dir.is_absolute() else root / report_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{report.report_id}.json"
    md_path = out_dir / f"{report.report_id}.md"
    json_path.write_text(json.dumps(report.as_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    (out_dir / "latest.json").write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
    (out_dir / "latest.md").write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    return json_path, md_path


def render_markdown(report: AutoRevertReport) -> str:
    changed = "\n".join(f"- `{path}`" for path in report.changed_files_before_revert) or "- none"
    output = report.output_tail or "(no output)"
    command = " ".join(report.check_command)
    return f"""# Auto-Revert Report

- Status: {report.status}
- Reason: {report.reason}
- Branch: `{report.branch}`
- Known good: `{report.known_good_ref}` (`{report.known_good_sha}`)
- Failed head: `{report.failed_head_sha}`
- Failed backup ref: `{report.failed_backup_ref or 'n/a'}`
- Failed diff: `{report.failed_diff_path or 'n/a'}`
- Check: `{command}` exited `{report.check_returncode}`
- Rollback performed: `{str(report.rollback_performed).lower()}`
- Post-revert HEAD: `{report.post_revert_head_sha or 'n/a'}`
- Post-revert clean: `{str(report.post_revert_clean).lower()}`

## Changed Files Before Revert
{changed}

## Check Output Tail
```text
{output}
```

## Next
James/Ember should review this report, inspect `{report.failed_backup_ref or report.failed_head_sha}` or the failed diff artifact if needed, and rebuild from `{report.known_good_ref}`.
"""


def make_report_id() -> str:
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%S%fZ")
    return f"auto-revert-{stamp}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def guard_build(
    *,
    root: Path,
    known_good_ref: str,
    check_command: Sequence[str],
    report_dir: Path,
    execute: bool,
    allow_dirty: bool,
    ops_ledger: Path | None = None,
) -> AutoRevertReport:
    branch = current_branch(root)
    if branch in PROTECTED_BRANCHES:
        raise AutoRevertError(f"refusing to run auto-revert on protected branch: {branch}")

    known_good_sha = rev_parse(root, known_good_ref)
    failed_head_sha = rev_parse(root, "HEAD")
    report_id = make_report_id()
    dirty_before_check = worktree_changes(root)
    if dirty_before_check and not allow_dirty:
        raise AutoRevertError("worktree has uncommitted changes; pass --allow-dirty only for isolated build worktrees")

    check = run_check(root, check_command)
    changed_before_revert = worktree_changes(root)

    if check.ok:
        report = AutoRevertReport(
            status="ok",
            branch=branch,
            known_good_ref=known_good_ref,
            known_good_sha=known_good_sha,
            failed_head_sha=failed_head_sha,
            check_command=check.command,
            check_returncode=check.returncode,
            changed_files_before_revert=changed_before_revert,
            rollback_performed=False,
            report_id=report_id,
            failed_backup_ref="",
            failed_diff_path="",
            post_revert_head_sha="",
            post_revert_clean=False,
            output_tail=check.output_tail,
            reason="verification passed; no rollback needed",
        )
    elif execute:
        backup_ref = preserve_failed_head(root, report_id, failed_head_sha)
        reset_to_known_good(root, known_good_ref, clean_untracked=allow_dirty)
        post_revert_head_sha = rev_parse(root, "HEAD")
        post_revert_clean = not worktree_changes(root)
        failed_diff_path = write_failed_diff(root, report_dir, report_id, known_good_sha, backup_ref)
        verified = post_revert_head_sha == known_good_sha and post_revert_clean
        report = AutoRevertReport(
            status="reverted" if verified else "revert_failed",
            branch=branch,
            known_good_ref=known_good_ref,
            known_good_sha=known_good_sha,
            failed_head_sha=failed_head_sha,
            check_command=check.command,
            check_returncode=check.returncode,
            changed_files_before_revert=changed_before_revert,
            rollback_performed=verified,
            report_id=report_id,
            failed_backup_ref=backup_ref,
            failed_diff_path=str(failed_diff_path),
            post_revert_head_sha=post_revert_head_sha,
            post_revert_clean=post_revert_clean,
            output_tail=check.output_tail,
            reason=(
                "verification failed; worktree reset to known good ref"
                if verified
                else "verification failed; attempted rollback did not verify cleanly"
            ),
        )
    else:
        backup_ref = preserve_failed_head(root, report_id, failed_head_sha)
        failed_diff_path = write_failed_diff(root, report_dir, report_id, known_good_sha, backup_ref)
        report = AutoRevertReport(
            status="would_revert",
            branch=branch,
            known_good_ref=known_good_ref,
            known_good_sha=known_good_sha,
            failed_head_sha=failed_head_sha,
            check_command=check.command,
            check_returncode=check.returncode,
            changed_files_before_revert=changed_before_revert,
            rollback_performed=False,
            report_id=report_id,
            failed_backup_ref=backup_ref,
            failed_diff_path=str(failed_diff_path),
            post_revert_head_sha="",
            post_revert_clean=False,
            output_tail=check.output_tail,
            reason="verification failed; dry-run mode did not reset worktree",
        )

    json_path, _md_path = write_reports(root, report_dir, report)
    if ops_ledger is not None:
        append_ops_ledger(ops_ledger, report)
    return report


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, help="git worktree to guard; defaults to current directory")
    parser.add_argument("--known-good", default=DEFAULT_KNOWN_GOOD, help="ref to reset to when verification fails")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--execute", action="store_true", help="perform git reset --hard on failed verification")
    parser.add_argument(
        "--fail-after-revert",
        action="store_true",
        help="return the check command's failing exit code even after rollback succeeds",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="allow uncommitted build output to be discarded; use only in isolated build worktrees",
    )
    parser.add_argument("--ops-ledger", type=Path, help="optional JSONL ops ledger to append to")
    parser.add_argument("check_command", nargs=argparse.REMAINDER, help="verification command, usually after --")
    args = parser.parse_args(argv)
    if args.check_command and args.check_command[0] == "--":
        args.check_command = args.check_command[1:]
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        root = repo_root(args.repo_root or Path.cwd())
        report = guard_build(
            root=root,
            known_good_ref=args.known_good,
            check_command=args.check_command,
            report_dir=args.report_dir,
            execute=args.execute,
            allow_dirty=args.allow_dirty,
            ops_ledger=args.ops_ledger,
        )
    except AutoRevertError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    print(f"{report.status}: {report.reason}")
    if report.rollback_performed:
        print(f"reset to {report.known_good_ref} ({report.known_good_sha})")
    print(f"report: {args.report_dir / (report.report_id + '.md')}")
    if report.rollback_performed and args.fail_after_revert:
        return report.check_returncode or 1
    return 0 if report.check_returncode == 0 or report.rollback_performed else 1


if __name__ == "__main__":
    raise SystemExit(main())
