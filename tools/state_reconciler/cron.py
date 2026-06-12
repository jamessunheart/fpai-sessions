#!/usr/bin/env python3
"""Scheduled drift detector for state SSOT staleness.

This entrypoint is safe to put behind cron/launchd later, but this file does
not install any schedule. It reports drift, writes the repo status artifact on
real runs, and opens one deduped human-edge gate only when a hard freshness
threshold is crossed.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.queue.build import add_gate, load_queue, open_gates_from_data
from tools.state_reconciler import status

DEFAULT_NOW = REPO_ROOT / "core" / "STATE" / "NOW.md"
DEFAULT_QUEUE = REPO_ROOT / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
DEFAULT_REPORT = REPO_ROOT / "docs" / "codex" / "STATE_STATUS.md"
NOW_STALE_GATE_ID = "state-drift-now-md-stale"

SEVERITY_ORDER = {"critical": 0, "warn": 1, "info": 2}


@dataclasses.dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    evidence: str


@dataclasses.dataclass(frozen=True)
class DriftReport:
    generated_at: str
    dry_run: bool
    findings: list[Finding]
    status_report: status.StatusReport
    gate: dict[str, Any] | None
    report_path: str | None
    schedule_snippet: str


def report(
    *,
    repo: Path | str = REPO_ROOT,
    now_path: Path | str | None = None,
    queue_path: Path | str | None = None,
    report_path: Path | str | None = None,
    dry_run: bool = True,
    now_max_age_days: int = 7,
    mirror_max_age_days: int = 1,
    today: dt.date | None = None,
) -> DriftReport:
    """Compute and optionally write a scheduled drift report."""
    repo_path = Path(repo)
    now = Path(now_path) if now_path else repo_path / "core" / "STATE" / "NOW.md"
    queue = Path(queue_path) if queue_path else repo_path / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
    output = Path(report_path) if report_path else repo_path / "docs" / "codex" / "STATE_STATUS.md"
    today_date = today or dt.datetime.now().date()
    current_status = status.summarize(repo_path)

    findings: list[Finding] = []
    findings.extend(_now_findings(now, today_date, now_max_age_days))
    findings.extend(_rung_findings(current_status))
    findings.extend(_mirror_findings(output, today_date, mirror_max_age_days))
    findings.extend(_queue_findings(queue))
    findings = sorted(findings, key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.code))

    gate: dict[str, Any] | None = None
    stale_now = next((finding for finding in findings if finding.code == "now_stale"), None)
    if stale_now and not dry_run:
        days = _age_days(now, today_date)
        gate = add_gate(
            gate_id=NOW_STALE_GATE_ID,
            stream="Game",
            question=f"NOW.md is {days} days stale - refresh the state SSOT?",
            verbs=["refresh", "hold"],
            blocking=True,
            urgent=True,
            path=queue,
        )

    written_path: str | None = None
    if output and not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(findings, current_status, gate), encoding="utf-8")
        written_path = str(output)

    return DriftReport(
        generated_at=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        dry_run=dry_run,
        findings=findings,
        status_report=current_status,
        gate=gate,
        report_path=written_path,
        schedule_snippet=schedule_snippet(repo_path),
    )


def render_markdown(
    findings: list[Finding],
    status_report: status.StatusReport,
    gate: dict[str, Any] | None = None,
) -> str:
    """Render the drift report into the existing STATE_STATUS artifact."""
    lines = [
        "# Codex State Status",
        "",
        f"- generated: `{dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()}`",
        f"- branch: `{status_report.branch}`",
        f"- dirty files: `{len(status_report.dirty_files)}`",
        f"- drift findings: `{len(findings)}`",
        f"- gate opened: `{gate['id'] if gate else 'none'}`",
        "",
        "## Drift Detector",
        "",
    ]
    if findings:
        for finding in findings:
            lines.append(f"- **{finding.severity.upper()}** `{finding.code}` - {finding.message}")
            lines.append(f"  - evidence: {finding.evidence}")
    else:
        lines.append("- No drift findings.")
    lines.extend(["", status.render_markdown(status_report).strip(), ""])
    return "\n".join(lines)


def payload(drift_report: DriftReport) -> dict[str, Any]:
    return {
        "generated_at": drift_report.generated_at,
        "dry_run": drift_report.dry_run,
        "findings": [dataclasses.asdict(finding) for finding in drift_report.findings],
        "gate": drift_report.gate,
        "report_path": drift_report.report_path,
        "schedule_snippet": drift_report.schedule_snippet,
        "status": status.report_payload(drift_report.status_report),
    }


def schedule_snippet(repo: Path | str = REPO_ROOT) -> str:
    repo_path = Path(repo)
    return "\n".join(
        [
            "# Non-installed example. James/Ember installs only after review.",
            "# Daily at 07:10 local time:",
            f"10 7 * * * cd {repo_path} && /usr/bin/env python3 -B tools/state_reconciler/cron.py --write-report",
        ]
    )


def _now_findings(now_path: Path, today: dt.date, max_age_days: int) -> list[Finding]:
    if not now_path.exists():
        return [
            Finding(
                severity="critical",
                code="now_missing",
                message="NOW.md is missing.",
                evidence=str(now_path),
            )
        ]
    updated = parse_last_updated(now_path.read_text(encoding="utf-8", errors="ignore"))
    if updated is None:
        return [
            Finding(
                severity="critical",
                code="now_unparseable",
                message="NOW.md Last Updated date could not be parsed.",
                evidence=str(now_path),
            )
        ]
    age = (today - updated).days
    if age > max_age_days:
        return [
            Finding(
                severity="critical",
                code="now_stale",
                message=f"NOW.md is {age} days old; max allowed is {max_age_days}.",
                evidence=f"Last Updated: {updated.isoformat()}",
            )
        ]
    return [
        Finding(
            severity="info",
            code="now_fresh",
            message=f"NOW.md is {age} days old.",
            evidence=f"Last Updated: {updated.isoformat()}",
        )
    ]


def _rung_findings(status_report: status.StatusReport) -> list[Finding]:
    return [
        Finding(
            severity="warn",
            code="rung_drift",
            message=drift,
            evidence="docs/codex/INTENT_BUILDSTREAM.md vs HANDOFF/artifacts",
        )
        for drift in status_report.drifts
    ]


def _mirror_findings(report_path: Path | None, today: dt.date, max_age_days: int) -> list[Finding]:
    if report_path is None:
        return []
    if not report_path.exists():
        return [
            Finding(
                severity="warn",
                code="mirror_missing",
                message="STATE_STATUS.md mirror has not been written yet.",
                evidence=str(report_path),
            )
        ]
    generated = parse_generated_at(report_path.read_text(encoding="utf-8", errors="ignore"))
    if generated is None:
        return [
            Finding(
                severity="warn",
                code="mirror_unparseable",
                message="STATE_STATUS.md generated timestamp could not be parsed.",
                evidence=str(report_path),
            )
        ]
    age = (today - generated).days
    if age > max_age_days:
        return [
            Finding(
                severity="warn",
                code="mirror_stale",
                message=f"STATE_STATUS.md is {age} days old; max preferred is {max_age_days}.",
                evidence=f"generated: {generated.isoformat()}",
            )
        ]
    return [
        Finding(
            severity="info",
            code="mirror_fresh",
            message=f"STATE_STATUS.md is {age} days old.",
            evidence=f"generated: {generated.isoformat()}",
        )
    ]


def _queue_findings(queue_path: Path) -> list[Finding]:
    try:
        data = load_queue(queue_path)
    except (OSError, ValueError) as exc:
        return [
            Finding(
                severity="warn",
                code="queue_unreadable",
                message="Human-edge queue could not be read.",
                evidence=str(exc),
            )
        ]
    open_gates = open_gates_from_data(data)
    drift_gates = [gate for gate in open_gates if gate["id"] == NOW_STALE_GATE_ID]
    return [
        Finding(
            severity="info",
            code="queue_open",
            message=f"Human-edge queue has {len(open_gates)} open gate(s).",
            evidence=f"drift gate open: {bool(drift_gates)}",
        )
    ]


def parse_last_updated(text: str) -> dt.date | None:
    match = re.search(r"Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})", text)
    if not match:
        match = re.search(r"Last Updated:\s*(\d{4}-\d{2}-\d{2})", text)
    if not match:
        return None
    return dt.date.fromisoformat(match.group(1))


def parse_generated_at(text: str) -> dt.date | None:
    match = re.search(r"generated:\s*`?(\d{4}-\d{2}-\d{2})", text)
    if not match:
        return None
    return dt.date.fromisoformat(match.group(1))


def _age_days(path: Path, today: dt.date) -> int:
    updated = parse_last_updated(path.read_text(encoding="utf-8", errors="ignore"))
    if updated is None:
        return -1
    return (today - updated).days


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the scheduled state drift detector.")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--now", type=Path, default=None)
    parser.add_argument("--queue", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--now-max-age-days", type=int, default=7)
    parser.add_argument("--mirror-max-age-days", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="write nothing and open no gates")
    parser.add_argument("--write-report", action="store_true", help="write STATE_STATUS.md and open threshold gates")
    parser.add_argument("--json", action="store_true", help="print JSON payload")
    parser.add_argument("--schedule", action="store_true", help="print non-installed cron snippet")
    args = parser.parse_args(argv)

    if args.schedule:
        print(schedule_snippet(args.repo))
        return 0

    dry_run = args.dry_run or not args.write_report
    drift_report = report(
        repo=args.repo,
        now_path=args.now,
        queue_path=args.queue,
        report_path=args.report,
        dry_run=dry_run,
        now_max_age_days=args.now_max_age_days,
        mirror_max_age_days=args.mirror_max_age_days,
    )
    if args.json:
        print(json.dumps(payload(drift_report), indent=2, sort_keys=True))
    elif dry_run:
        print(render_markdown(drift_report.findings, drift_report.status_report, drift_report.gate))
    else:
        print(f"wrote {drift_report.report_path}; gate={drift_report.gate['id'] if drift_report.gate else 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
