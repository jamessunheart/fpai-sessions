#!/usr/bin/env python3
"""Read-only cruft reaper report.

This scanner produces cleanup candidates only. It never deletes files, stops
services, edits .gitignore, or untracks anything.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = REPO_ROOT / "docs" / "codex" / "REAPER_REPORT.md"

ARTIFACT_NAMES = {
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "logs",
    "node_modules",
    "overnight-logs",
    "venv",
}
ARTIFACT_SUFFIXES = (".log", ".pyc", ".pyo")


@dataclasses.dataclass(frozen=True)
class Candidate:
    path: str
    kind: str
    reason: str
    evidence: str
    suggested_action: str
    size_bytes: int = 0
    stale_days: int = 0
    score: float = 0.0


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def run_git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def git_tracked_files(repo: Path) -> list[str]:
    output = run_git(repo, ["ls-files", "-z"])
    return [part for part in output.split("\0") if part]


def last_commit_days(repo: Path, rel_path: str, now: dt.datetime | None = None) -> int:
    now = now or utc_now()
    try:
        output = run_git(repo, ["log", "-1", "--format=%ct", "--", rel_path]).strip()
    except subprocess.CalledProcessError:
        return 0
    if not output:
        return 0
    committed = dt.datetime.fromtimestamp(int(output), tz=dt.timezone.utc)
    return max(0, (now - committed).days)


def artifact_root(path: str) -> str | None:
    parts = Path(path).parts
    for index, part in enumerate(parts):
        if part in ARTIFACT_NAMES:
            return str(Path(*parts[: index + 1]))
    if path.endswith(ARTIFACT_SUFFIXES):
        return path
    return None


def tracked_artifact_candidates(repo: Path, files: list[str], now: dt.datetime | None = None) -> list[Candidate]:
    grouped: dict[str, int] = {}
    for path in files:
        root = artifact_root(path)
        if root:
            grouped[root] = grouped.get(root, 0) + 1

    candidates: list[Candidate] = []
    for root, count in grouped.items():
        size = path_size_bytes(repo / root)
        stale = last_commit_days(repo, root, now)
        candidates.append(
            candidate(
                path=root,
                kind="tracked-artifact",
                reason="tracked-artifact",
                evidence=f"{count} tracked artifact file(s); last commit age {stale}d; size {format_bytes(size)}",
                suggested_action="untrack after James approval; add ignore rule separately",
                size_bytes=size,
                stale_days=stale,
            )
        )
    return candidates


def oversized_path_candidates(repo: Path, threshold_bytes: int, roots: list[str] | None = None) -> list[Candidate]:
    roots = roots or top_level_paths(repo)
    candidates: list[Candidate] = []
    for rel_path in roots:
        abs_path = repo / rel_path
        if not abs_path.exists():
            continue
        size = path_size_bytes(abs_path)
        if size < threshold_bytes:
            continue
        stale = last_commit_days(repo, rel_path)
        candidates.append(
            candidate(
                path=rel_path,
                kind="oversized-path",
                reason="size",
                evidence=f"{format_bytes(size)} >= threshold {format_bytes(threshold_bytes)}; last commit age {stale}d",
                suggested_action="review for archive/untrack split after James approval",
                size_bytes=size,
                stale_days=stale,
            )
        )
    return candidates


def stale_service_candidates(
    repo: Path,
    units: list[dict[str, str]],
    stale_days: int,
    now: dt.datetime | None = None,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    for unit in units:
        state = str(unit.get("state", "")).lower()
        if state not in {"enabled", "running"}:
            continue
        rel_path = service_repo_path(repo, unit)
        if not rel_path:
            continue
        age = last_commit_days(repo, rel_path, now)
        if age < stale_days:
            continue
        candidates.append(
            candidate(
                path=rel_path,
                kind="frozen-service",
                reason="zero-commit-90d",
                evidence=f"systemd unit {unit.get('name')} is {state}; last commit age {age}d",
                suggested_action="candidate stop/archive only after James approval",
                size_bytes=path_size_bytes(repo / rel_path),
                stale_days=age,
            )
        )
    return candidates


def service_repo_path(repo: Path, unit: dict[str, str]) -> str | None:
    raw_path = unit.get("path") or unit.get("repo_path") or ""
    if raw_path:
        path = Path(raw_path)
        if path.is_absolute():
            try:
                return str(path.relative_to(repo))
            except ValueError:
                return None
        return str(path)

    name = unit.get("name", "")
    if not name:
        return None
    for service_file in repo.rglob("*.service"):
        if service_file.name == name:
            return str(service_file.parent.relative_to(repo))
    return None


def discover_systemd_units() -> tuple[list[dict[str, str]], str]:
    systemctl = shutil_which("systemctl")
    if not systemctl:
        return [], "systemctl unavailable on this host"
    units: list[dict[str, str]] = []
    try:
        running = subprocess.run(
            [systemctl, "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        enabled = subprocess.run(
            [systemctl, "list-unit-files", "--type=service", "--state=enabled", "--no-legend", "--no-pager"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        return [], f"systemctl failed: {exc}"
    if running.returncode == 0:
        for line in running.stdout.splitlines():
            parts = line.split()
            if parts and parts[0].endswith(".service"):
                units.append({"name": parts[0], "state": "running"})
    if enabled.returncode == 0:
        for line in enabled.stdout.splitlines():
            parts = line.split()
            if parts and parts[0].endswith(".service"):
                units.append({"name": parts[0], "state": "enabled"})
    note = "systemd scan ok" if units else "systemd scan found no running/enabled repo-mapped units"
    return units, note


def shutil_which(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate_path = Path(directory) / name
        if candidate_path.exists() and os.access(candidate_path, os.X_OK):
            return str(candidate_path)
    return None


def top_level_paths(repo: Path) -> list[str]:
    ignored = {".git"}
    return sorted(path.name for path in repo.iterdir() if path.name not in ignored)


def path_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [directory for directory in dirs if directory != ".git"]
        for name in files:
            file_path = Path(root) / name
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


def candidate(
    *,
    path: str,
    kind: str,
    reason: str,
    evidence: str,
    suggested_action: str,
    size_bytes: int = 0,
    stale_days: int = 0,
) -> Candidate:
    size_mb = size_bytes / (1024 * 1024)
    staleness_factor = 1 + (stale_days / 90 if stale_days else 0)
    score = round(max(size_mb, 0.1) * staleness_factor, 2)
    return Candidate(path, kind, reason, evidence, suggested_action, size_bytes, stale_days, score)


def dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    best: dict[tuple[str, str], Candidate] = {}
    for item in candidates:
        key = (item.path, item.kind)
        if key not in best or item.score > best[key].score:
            best[key] = item
    return sorted(best.values(), key=lambda item: (-item.score, item.path, item.kind))


def gitignore_suggestions(candidates: list[Candidate]) -> list[str]:
    suggestions = set()
    for item in candidates:
        if item.kind != "tracked-artifact":
            continue
        root = artifact_root(item.path) or item.path
        name = Path(root).name
        if name in ARTIFACT_NAMES:
            suggestions.add(f"{name}/")
        elif root.endswith(ARTIFACT_SUFFIXES):
            suggestions.add(f"*{Path(root).suffix}")
    return sorted(suggestions)


def build_report(
    *,
    repo: Path = REPO_ROOT,
    output: Path = DEFAULT_REPORT,
    size_threshold_mb: int = 512,
    stale_days: int = 90,
    systemd_units: list[dict[str, str]] | None = None,
    dry_run: bool = False,
) -> str:
    """Build and write the read-only report. ``dry_run`` is report-only too."""
    repo = Path(repo)
    files = git_tracked_files(repo)
    units_note = "systemd units supplied by caller"
    units = systemd_units
    if units is None:
        units, units_note = discover_systemd_units()
    threshold = size_threshold_mb * 1024 * 1024
    artifact_candidates = tracked_artifact_candidates(repo, files)
    size_roots = sorted(set(top_level_paths(repo)) | {item.path for item in artifact_candidates})
    candidates = dedupe_candidates(
        [
            *stale_service_candidates(repo, units, stale_days),
            *artifact_candidates,
            *oversized_path_candidates(repo, threshold, size_roots),
        ]
    )
    report = render_report(
        candidates=candidates,
        repo=repo,
        threshold_bytes=threshold,
        stale_days=stale_days,
        units_note=units_note,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return report


def render_report(
    *,
    candidates: list[Candidate],
    repo: Path,
    threshold_bytes: int,
    stale_days: int,
    units_note: str,
) -> str:
    generated = utc_now().isoformat(timespec="seconds")
    lines = [
        "# Cruft Reaper Report",
        "",
        f"*Generated: `{generated}` · repo: `{repo}`*",
        "",
        "🔴 **REPORT ONLY. James approves any deletion, stop, archive, untrack, or .gitignore edit.**",
        "",
        "## Scan Settings",
        "",
        f"- stale service threshold: `{stale_days}d`",
        f"- oversized path threshold: `{format_bytes(threshold_bytes)}`",
        f"- systemd evidence: {units_note}",
        "",
        "## Ranked Kill-List Candidates",
        "",
    ]
    if not candidates:
        lines.append("_No candidates found by this report._")
    else:
        lines.extend(
            [
                "| Rank | Candidate | Reason | Evidence | Suggested action | Score |",
                "|---:|---|---|---|---|---:|",
            ]
        )
        for rank, item in enumerate(candidates, start=1):
            lines.append(
                "| {rank} | `{path}` | `{reason}` | {evidence} | {action} | {score:g} |".format(
                    rank=rank,
                    path=item.path,
                    reason=item.reason,
                    evidence=escape_table(item.evidence),
                    action=escape_table(item.suggested_action),
                    score=item.score,
                )
            )
    suggestions = gitignore_suggestions(candidates)
    lines.extend(["", "## .gitignore Suggestions", ""])
    if suggestions:
        lines.append("```gitignore")
        lines.extend(suggestions)
        lines.append("```")
        lines.append("")
        lines.append("_Suggestion only. This report did not edit `.gitignore`._")
    else:
        lines.append("_No tracked artifact ignore suggestions found._")
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- No files were deleted.",
            "- No services were stopped or disabled.",
            "- No files were untracked.",
            "- No `.gitignore` changes were applied.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} GB"


def load_units(path: Path | None) -> list[dict[str, str]] | None:
    if not path:
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a read-only cruft reaper report.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--size-threshold-mb", type=int, default=512)
    parser.add_argument("--stale-days", type=int, default=90)
    parser.add_argument("--systemd-units-json", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="same behavior; report-only by design")
    args = parser.parse_args(argv)
    report = build_report(
        repo=args.repo,
        output=args.output,
        size_threshold_mb=args.size_threshold_mb,
        stale_days=args.stale_days,
        systemd_units=load_units(args.systemd_units_json),
        dry_run=args.dry_run,
    )
    print(f"wrote {args.output}")
    print(f"{candidate_row_count(report)} candidate row(s)")
    return 0


def candidate_row_count(report: str) -> int:
    return sum(1 for line in report.splitlines() if line.startswith("| ") and "| `" in line)


if __name__ == "__main__":
    raise SystemExit(main())
