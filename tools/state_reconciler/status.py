#!/usr/bin/env python3
"""Render a repo-side current-truth status report.

This helper notices drift between the Intent Buildstream, HANDOFF, and built
artifacts. It does not execute work, edit the vault, or change routing state.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BUILDSTREAM = REPO_ROOT / "docs" / "codex" / "INTENT_BUILDSTREAM.md"
DEFAULT_HANDOFF = REPO_ROOT / "docs" / "codex" / "HANDOFF.md"
DEFAULT_REPORT = REPO_ROOT / "docs" / "codex" / "STATE_STATUS.md"

RUNG_NAMES = {
    0: "Reserved-Class boundary",
    1: "Apprentice execution tier",
    2: "Self-directing loop",
    3: "Auto-spec drafting",
    4: "Apprentice-built hubs",
}


@dataclasses.dataclass(frozen=True)
class RungReport:
    rung: int
    intent_id: str
    name: str
    buildstream_status: str
    actual_state: str
    evidence: list[str]
    drift: str | None


@dataclasses.dataclass(frozen=True)
class StatusReport:
    generated_at: str
    branch: str
    dirty_files: list[str]
    rungs: list[RungReport]
    drifts: list[str]
    next_unlock: str
    mirror_guidance: list[str]


def summarize(
    repo: Path | str = REPO_ROOT,
    buildstream_path: Path | str | None = None,
    handoff_path: Path | str | None = None,
) -> StatusReport:
    repo_path = Path(repo)
    buildstream = Path(buildstream_path) if buildstream_path else repo_path / "docs" / "codex" / "INTENT_BUILDSTREAM.md"
    handoff = Path(handoff_path) if handoff_path else repo_path / "docs" / "codex" / "HANDOFF.md"
    buildstream_text = _read(buildstream)
    handoff_text = _read(handoff)
    stream_rungs = _parse_rungs(buildstream_text)
    branch, dirty = _git_state(repo_path)

    built = _built_map(repo_path, handoff_text)
    artifacts = _artifact_map(repo_path, handoff_text)
    reports: list[RungReport] = []
    for rung in range(5):
        row = stream_rungs.get(rung, {})
        actual = _actual_state(rung, built, artifacts)
        evidence = _evidence(rung, repo_path, handoff_text)
        drift = _drift_for(rung, row.get("status", "missing"), actual, built)
        reports.append(
            RungReport(
                rung=rung,
                intent_id=str(row.get("id") or f"rung{rung}"),
                name=RUNG_NAMES[rung],
                buildstream_status=str(row.get("status") or "missing"),
                actual_state=actual,
                evidence=evidence,
                drift=drift,
            )
        )

    drifts = [report.drift for report in reports if report.drift]
    return StatusReport(
        generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        branch=branch,
        dirty_files=dirty,
        rungs=reports,
        drifts=drifts,
        next_unlock=_next_unlock(reports, repo_path),
        mirror_guidance=[
            "Mirror this repo artifact into the Full Potential OS vault after review.",
            "Suggested vault note: [[CODEX STATE STATUS]] or the current FPOS cockpit/status surface.",
            "Treat the mirror as observation only; it is not approval to build, send, deploy, move money, or edit doctrine.",
        ],
    )


def render_markdown(report: StatusReport) -> str:
    lines = [
        "# Codex State Status",
        "",
        f"- generated: `{report.generated_at}`",
        f"- branch: `{report.branch}`",
        f"- dirty files: `{len(report.dirty_files)}`",
        "",
        "## Rung Truth",
        "",
        "| Rung | Buildstream | Actual | Evidence | Drift |",
        "|---|---|---|---|---|",
    ]
    for rung in report.rungs:
        evidence = "<br>".join(f"`{item}`" for item in rung.evidence) if rung.evidence else "none"
        drift = rung.drift or ""
        lines.append(
            f"| Rung {rung.rung}: {rung.name} | `{rung.buildstream_status}` | "
            f"`{rung.actual_state}` | {evidence} | {drift} |"
        )

    lines.extend(["", "## Drift", ""])
    if report.drifts:
        lines.extend(f"- {drift}" for drift in report.drifts)
    else:
        lines.append("- No ladder drift detected.")

    lines.extend(
        [
            "",
            "## Next Unlock",
            "",
            report.next_unlock,
            "",
            "## Dirty Worktree",
            "",
        ]
    )
    if report.dirty_files:
        lines.extend(f"- `{item}`" for item in report.dirty_files)
    else:
        lines.append("- clean")

    lines.extend(["", "## Vault Mirror", ""])
    lines.extend(f"- {item}" for item in report.mirror_guidance)
    lines.extend(
        [
            "",
            "## Suggested HANDOFF Note",
            "",
            "```markdown",
            "### State status mirror",
            f"- Current branch: `{report.branch}`",
            f"- Next valid unlock: {report.next_unlock}",
            f"- Drift count: `{len(report.drifts)}`",
            "- Mirror source: `docs/codex/STATE_STATUS.md`",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_report(report: StatusReport, path: Path | str = DEFAULT_REPORT) -> Path:
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(report), encoding="utf-8")
    return report_path


def report_payload(report: StatusReport) -> dict[str, Any]:
    return {
        "generated_at": report.generated_at,
        "branch": report.branch,
        "dirty_files": report.dirty_files,
        "drifts": report.drifts,
        "next_unlock": report.next_unlock,
        "mirror_guidance": report.mirror_guidance,
        "rungs": [dataclasses.asdict(rung) for rung in report.rungs],
    }


def _parse_rungs(text: str) -> dict[int, dict[str, Any]]:
    rows: dict[int, dict[str, Any]] = {}
    for line in text.splitlines():
        match = re.match(r"^- Rung\s+(\d+)\s+\|\s+(.+)$", line.strip())
        if not match:
            continue
        rung = int(match.group(1))
        row = _parse_pipe_segments(match.group(2))
        row["rung"] = rung
        rows[rung] = row
    return rows


def _parse_pipe_segments(text: str) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for segment in [part.strip() for part in text.split("|")]:
        if ":" not in segment:
            continue
        key, value = segment.split(":", 1)
        row[key.strip().lower().replace("-", "_")] = value.strip()
    return row


def _built_map(repo: Path, handoff_text: str) -> dict[int, bool]:
    return {
        0: (repo / "tools" / "reserved" / "classify.py").exists()
        and "SPEC_reserved-class-boundary" in handoff_text,
        1: (repo / "tools" / "apprentice" / "run.py").exists()
        and "SPEC_apprentice-execution-tier" in handoff_text,
        2: (repo / "tools" / "loop" / "direct.py").exists()
        and "SPEC_self-directing-loop" in handoff_text,
        3: "SPEC_auto-spec-drafting ·" in handoff_text,
        4: False,
    }


def _artifact_map(repo: Path, handoff_text: str) -> dict[int, bool]:
    del handoff_text
    return {
        0: False,
        1: False,
        2: False,
        3: (repo / "tools" / "spec" / "draft.py").exists()
        or bool(list((repo / "docs" / "codex" / "specs").glob("SPEC_*.draft.md"))),
        4: False,
    }


def _actual_state(rung: int, built: dict[int, bool], artifacts: dict[int, bool]) -> str:
    if built.get(rung):
        return "built"
    if artifacts.get(rung):
        return "artifact-present-unlogged"
    if rung == 0:
        return "ready"
    if built.get(rung - 1):
        return "ready"
    return f"blocked-on-rung{rung - 1}"


def _evidence(rung: int, repo: Path, handoff_text: str) -> list[str]:
    checks = {
        0: [("tools/reserved/classify.py", "SPEC_reserved-class-boundary")],
        1: [("tools/apprentice/run.py", "SPEC_apprentice-execution-tier")],
        2: [("tools/loop/direct.py", "SPEC_self-directing-loop")],
        3: [
            ("docs/codex/specs/SPEC_auto-spec-drafting.md", "SPEC_auto-spec-drafting"),
            ("tools/spec/draft.py", "SPEC_auto-spec-drafting"),
            ("tools/spec/test_draft.py", "SPEC_auto-spec-drafting"),
        ],
        4: [],
    }
    evidence: list[str] = []
    for rel_path, marker in checks.get(rung, []):
        if (repo / rel_path).exists():
            evidence.append(rel_path)
        if marker in handoff_text:
            evidence.append(f"HANDOFF:{marker}")
    if rung == 3:
        draft_dir = repo / "docs" / "codex" / "specs"
        evidence.extend(str(path.relative_to(repo)) for path in sorted(draft_dir.glob("SPEC_*.draft.md")))
    return _dedupe(evidence)


def _drift_for(rung: int, buildstream_status: str, actual: str, built: dict[int, bool]) -> str | None:
    status = buildstream_status.lower()
    if actual == "built" and status not in {"done", "built"}:
        return f"Buildstream still says `{buildstream_status}`, but Rung {rung} appears built."
    if actual == "artifact-present-unlogged":
        return f"Rung {rung} has repo artifacts, but no HANDOFF completion marker was found."
    prereq_match = re.search(r"blocked-on-rung(\d+)", status)
    if prereq_match and built.get(int(prereq_match.group(1))):
        return (
            f"Buildstream says Rung {rung} is `{buildstream_status}`, "
            f"but that prerequisite appears built."
        )
    return None


def _next_unlock(reports: list[RungReport], repo: Path) -> str:
    for report in reports:
        if report.actual_state == "artifact-present-unlogged":
            return (
                f"Review/log Rung {report.rung}: {report.name} artifacts before advancing the ladder."
            )
    for report in reports:
        if report.actual_state == "ready":
            if report.rung == 3 and (repo / "docs" / "codex" / "specs" / "SPEC_auto-spec-drafting.md").exists():
                return "Build/review `SPEC_auto-spec-drafting`; Rung 2 is built, so Rung 3 is the next adjacent unlock."
            return f"Advance Rung {report.rung}: {report.name}."
    return "No ready ladder rung found; reconcile manually before granting more autonomy."


def _git_state(repo: Path) -> tuple[str, list[str]]:
    branch = "unknown"
    dirty: list[str] = []
    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip()
        status_result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if status_result.returncode == 0:
            dirty = [line.rstrip() for line in status_result.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        pass
    return branch, dirty


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a current-state truth report.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--buildstream", type=Path, default=None)
    parser.add_argument("--handoff", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None, help="optional Markdown report path")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    args = parser.parse_args(argv)

    report = summarize(args.repo, args.buildstream, args.handoff)
    if args.report:
        path = write_report(report, args.report)
        if args.json:
            payload = report_payload(report)
            payload["report_path"] = str(path)
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"wrote {path}")
    elif args.json:
        print(json.dumps(report_payload(report), indent=2, sort_keys=True))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
