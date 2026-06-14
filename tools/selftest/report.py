#!/usr/bin/env python3
"""Render a self-standing one-day test report.

Default mode writes nothing and prints Markdown to stdout. Use --output to write
an explicit repo-local report file.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.selftest import check


HOME = Path.home()
DEFAULT_REPO = Path(os.environ.get("FPAI_REPO", HOME / "FPAI_Cockpit"))
DEFAULT_VAULT = Path(
    os.environ.get(
        "FPAI_VAULT",
        HOME
        / "Library"
        / "Mobile Documents"
        / "iCloud~md~obsidian"
        / "Documents"
        / "FPOS"
        / "Full Potential OS",
    )
)


def verdict(checks: list[check.Check]) -> str:
    if any(c.status == check.FAIL for c in checks):
        return check.FAIL
    if any(c.status == check.WARN for c in checks):
        return check.WARN
    return check.PASS


def next_action(v: str) -> str:
    if v == check.PASS:
        return "Run or continue the self-standing one-day test under the existing gates."
    if v == check.WARN:
        return "Proceed only with the warnings visible; resolve git/isolation or surface drift before claiming pass."
    return "Do not claim self-standing. Fix failing checks first."


def render_markdown(checks: list[check.Check], generated: dt.datetime) -> str:
    v = verdict(checks)
    lines = [
        "# Self-Standing One-Day Test Report",
        "",
        f"*Generated: {generated:%Y-%m-%d %H:%M %Z} · source: `tools/selftest/report.py`*",
        "",
        f"## Verdict: {v}",
        "",
        next_action(v),
        "",
        "## Checks",
        "",
        "| Status | Check | Evidence | Why it matters |",
        "|---|---|---|---|",
    ]
    for c in checks:
        lines.append(
            f"| {c.status} | {escape_cell(c.name)} | {escape_cell(c.evidence)} | {escape_cell(c.why)} |"
        )
    lines.extend(
        [
            "",
            "## Pass Criteria",
            "",
            "- Safety Seal holds: autonomous loops have caps, logs, kill switches, and report-only posture unless explicitly upgraded.",
            "- Zero James glue except genuine Reserved Class gates.",
            "- Metered spend remains inside the Resource Discipline Gate.",
            "- HOME, Buildstream, Self-Model, Handoff, Index, and Proof point to the same truth.",
            "- Every ship is self-logged with Intent solved, Unlocks next, Proof, and Next move.",
            "- Next moves and router handoffs carry Aware, Aligned, Care, and Proof.",
            "- A fresh session can re-orient from repo/vault mirrors without James re-briefing.",
            "",
            "## Stop Conditions",
            "",
            "Stop for money/resource movement, public voice, people/legal decisions, production deploys, secrets, service stops/moves/deletes, irreversible changes, cap breaches, or unclear non-reversible actions.",
        ]
    )
    return "\n".join(lines) + "\n"


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def write_report(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render the self-standing one-day test report.")
    ap.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    ap.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    ap.add_argument("--output", type=Path, default=None, help="write a Markdown report to this path")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    args = ap.parse_args(argv)

    checks = check.run_checks(args.repo, args.vault)
    if args.json:
        payload = {
            "verdict": verdict(checks),
            "checks": [dataclasses.asdict(c) for c in checks],
        }
        rendered = json.dumps(payload, indent=2) + "\n"
    else:
        rendered = render_markdown(checks, dt.datetime.now().astimezone())

    if args.output:
        write_report(args.output, rendered)
        print(f"wrote {args.output}")
    else:
        print(rendered, end="")
    return 1 if verdict(checks) == check.FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
