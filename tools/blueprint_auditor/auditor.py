#!/usr/bin/env python3
"""Blueprint Weakness Auditor.

Reads living module blueprints and produces review-gated improvement signals.
It does not edit blueprints, queue specs, deploy, or call external services.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BLUEPRINT_DIR = REPO_ROOT / "docs" / "blueprints"
DEFAULT_REPORT = REPO_ROOT / "core" / "BUILD" / "signals" / "blueprint_weakness_report.md"
DEFAULT_PROPOSALS = REPO_ROOT / "core" / "BUILD" / "signals" / "blueprint_weakness_proposals.jsonl"
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))

REQUIRED_SECTIONS = (
    "Identity",
    "What it does",
    "How it works",
    "Quality standard",
    "Current behavior (verified)",
    "Known gaps",
    "Integration map",
    "Improvement history",
    "Test coverage",
)

MEASURABLE_RE = re.compile(
    r"(\d+|percent|%|within|every|daily|hour|minute|pass|fail|zero|at least|no more than)",
    re.IGNORECASE,
)
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
EMPTY_MARKERS = {"", "none", "n/a", "todo", "tbd", "unknown", "- none", "- todo", "- tbd"}


@dataclasses.dataclass(frozen=True)
class Weakness:
    module: str
    severity: int
    kind: str
    title: str
    evidence: str
    proposed_fix: str

    def proposal(self) -> dict[str, object]:
        title = f"Close blueprint gap: {self.module} {self.kind.replace('_', ' ')}"
        proposed_fix = self.proposed_fix.rstrip(".")
        spec = (
            f"Audit docs/blueprints/{self.module}.md and close this weakness: {self.title}. "
            f"Evidence: {self.evidence}. Proposed fix: {proposed_fix}. "
            "Keep changes review-gated; update tests or proof references if behavior changes."
        )
        return {
            "source": "blueprint_weakness_auditor",
            "module": self.module,
            "severity": self.severity,
            "kind": self.kind,
            "title": title[:96],
            "spec": spec,
            "route": "codex",
            "safe_auto": False,
            "needs_review": True,
        }


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def parse_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections.setdefault(current, []).append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def is_empty(body: str) -> bool:
    cleaned = compact(re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)).lower()
    return cleaned in EMPTY_MARKERS


def blueprint_files(blueprint_dir: Path) -> list[Path]:
    if not blueprint_dir.exists():
        return []
    return sorted(
        path for path in blueprint_dir.glob("*.md")
        if path.name != "_TEMPLATE.md" and not path.name.startswith(".")
    )


def audit_blueprint(path: Path) -> list[Weakness]:
    module = path.stem
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = parse_sections(text)
    weaknesses: list[Weakness] = []

    for section in REQUIRED_SECTIONS:
        if section not in sections:
            weaknesses.append(Weakness(
                module,
                5,
                "missing_section",
                f"Missing `{section}` section",
                f"{path.name} lacks the required section heading",
                f"Add `## {section}` using current repo evidence, or mark an explicit unknown with owner and date.",
            ))

    quality = sections.get("Quality standard", "")
    if quality and not MEASURABLE_RE.search(quality):
        weaknesses.append(Weakness(
            module,
            4,
            "vague_quality_standard",
            "Quality standard is not measurable",
            compact(quality)[:220],
            "Rewrite the standard with an observable threshold, cadence, pass/fail condition, or dated proof target.",
        ))

    current = sections.get("Current behavior (verified)", "")
    if current and not DATE_RE.search(current):
        weaknesses.append(Weakness(
            module,
            3,
            "undated_current_behavior",
            "Current behavior has no verification date",
            compact(current)[:220],
            "Add the latest verified date and the command, smoke test, ops-ledger row, or result file that proved it.",
        ))
    if current and re.search(r"\b(should|intended|planned|will)\b", current, re.IGNORECASE):
        weaknesses.append(Weakness(
            module,
            3,
            "aspirational_current_behavior",
            "Current behavior includes aspirational language",
            compact(current)[:220],
            "Separate verified facts from planned behavior and move unverified claims to Known gaps.",
        ))

    known_gaps = sections.get("Known gaps", "")
    if known_gaps and is_empty(known_gaps):
        weaknesses.append(Weakness(
            module,
            2,
            "empty_known_gaps",
            "Known gaps are empty",
            "No active gap, limitation, or explicit `no known gaps as of DATE` entry found",
            "Add at least one dated limitation or a dated proof-backed `no known gaps` statement.",
        ))

    integration = sections.get("Integration map", "")
    for label in ("Depends on", "Used by", "DB tables", "Kill switch"):
        if integration and label.lower() not in integration.lower():
            weaknesses.append(Weakness(
                module,
                3,
                "integration_map_incomplete",
                f"Integration map missing `{label}`",
                compact(integration)[:220],
                f"Add `{label}` with concrete paths, modules, tables, env vars, or `none known as of DATE`.",
            ))

    tests = sections.get("Test coverage", "")
    if tests and not re.search(r"\b(test|unittest|pytest|smoke|py_compile|bash -n)\b", tests, re.IGNORECASE):
        weaknesses.append(Weakness(
            module,
            4,
            "test_coverage_vague",
            "Test coverage does not name concrete tests",
            compact(tests)[:220],
            "Name the exact test files/commands and what remains untested.",
        ))
    if tests and "not tested" not in tests.lower() and "untested" not in tests.lower():
        weaknesses.append(Weakness(
            module,
            2,
            "missing_test_gap",
            "Test coverage does not state remaining untested behavior",
            compact(tests)[:220],
            "Add an explicit untested/residual-risk line so future builds know where proof is weak.",
        ))

    history = sections.get("Improvement history", "")
    if history and not DATE_RE.search(history):
        weaknesses.append(Weakness(
            module,
            3,
            "history_undated",
            "Improvement history has no dated entries",
            compact(history)[:220],
            "Add dated entries in `YYYY-MM-DD | dNNN | change | why it mattered` format.",
        ))

    return weaknesses


def select_top(weaknesses: Iterable[Weakness], limit: int) -> list[Weakness]:
    return sorted(weaknesses, key=lambda w: (w.severity, w.module, w.kind), reverse=True)[:limit]


def render_report(weaknesses: list[Weakness], *, blueprint_dir: Path, generated_at: str) -> str:
    by_module: dict[str, list[Weakness]] = {}
    for weakness in weaknesses:
        by_module.setdefault(weakness.module, []).append(weakness)
    lines = [
        "# Blueprint Weakness Auditor Report",
        "",
        f"**Generated:** {generated_at}",
        f"**Blueprint dir:** `{blueprint_dir}`",
        "**Mode:** deterministic local audit; no network, installs, deploys, or automatic queue writes.",
        "",
        "## Summary",
        "",
        f"- Blueprints with findings: {len(by_module)}",
        f"- Total findings: {len(weaknesses)}",
        "",
        "## Top Findings",
        "",
    ]
    for weakness in select_top(weaknesses, 12):
        lines.extend(
            [
                f"### {weakness.module} · {weakness.kind} · severity {weakness.severity}",
                f"- **Issue:** {weakness.title}",
                f"- **Evidence:** {weakness.evidence}",
                f"- **Proposed fix:** {weakness.proposed_fix}",
                "",
            ]
        )
    if not weaknesses:
        lines.append("No blueprint weaknesses found by the deterministic checks.")
        lines.append("")
    lines.extend(["## Module Counts", "", "| Module | Findings | Max severity |", "|---|---:|---:|"])
    for module, rows in sorted(by_module.items()):
        lines.append(f"| {module} | {len(rows)} | {max(row.severity for row in rows)} |")
    lines.append("")
    return "\n".join(lines)


def write_jsonl(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def append_ops(ledger: Path, *, finding_count: int, report: Path, proposals: Path) -> bool:
    row = {
        "ts": utc_now(),
        "loop": "blueprint_weakness_auditor",
        "event": "proposed" if finding_count else "ran",
        "detail": f"blueprint audit found {finding_count} weaknesses",
        "cost": "$0",
        "artifact": str(report),
        "next": f"review {proposals}" if finding_count else "",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return True
    except OSError:
        return False


def run(
    *,
    blueprint_dir: Path = DEFAULT_BLUEPRINT_DIR,
    report_path: Path = DEFAULT_REPORT,
    proposals_path: Path = DEFAULT_PROPOSALS,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    max_proposals: int = 8,
    no_ledger: bool = False,
) -> dict[str, object]:
    weaknesses: list[Weakness] = []
    for path in blueprint_files(blueprint_dir):
        weaknesses.extend(audit_blueprint(path))
    generated_at = utc_now()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(weaknesses, blueprint_dir=blueprint_dir, generated_at=generated_at), encoding="utf-8")
    proposals = [weakness.proposal() for weakness in select_top(weaknesses, max_proposals)]
    write_jsonl(proposals_path, proposals)
    ledger_written = False if no_ledger else append_ops(
        ops_ledger,
        finding_count=len(weaknesses),
        report=report_path,
        proposals=proposals_path,
    )
    return {
        "blueprints": len(blueprint_files(blueprint_dir)),
        "findings": len(weaknesses),
        "proposals": len(proposals),
        "report": str(report_path),
        "proposal_file": str(proposals_path),
        "ledger_written": ledger_written,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit module blueprints for weak contracts.")
    parser.add_argument("--blueprints", type=Path, default=DEFAULT_BLUEPRINT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--proposals", type=Path, default=DEFAULT_PROPOSALS)
    parser.add_argument("--ops-ledger", type=Path, default=DEFAULT_OPS_LEDGER)
    parser.add_argument("--max-proposals", type=int, default=8)
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    summary = run(
        blueprint_dir=args.blueprints,
        report_path=args.report,
        proposals_path=args.proposals,
        ops_ledger=args.ops_ledger,
        max_proposals=args.max_proposals,
        no_ledger=args.no_ledger,
    )
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"blueprint-auditor: findings={summary['findings']} proposals={summary['proposals']}")
        print(f"report: {summary['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
