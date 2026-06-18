#!/usr/bin/env python3
"""Track Forge-discovered upstream contribution opportunities."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.forge.security_gate import assert_public

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG = REPO_ROOT / "core" / "STATE" / "UPSTREAM_CONTRIBUTIONS.md"

CONTRIBUTE_RE = re.compile(
    r"^\s*(?:[-*]\s*)?CONTRIBUTE:\s*(?P<project>[^-]+?)\s*[-:]\s*(?P<gap>.+?)(?:\s*[-:]\s*PR complexity:\s*(?P<complexity>low|med|medium|high))?\s*$",
    re.I,
)


@dataclass(frozen=True)
class Opportunity:
    project: str
    gap: str
    complexity: str = "unknown"
    status: str = "draft"

    def as_dict(self) -> dict[str, str]:
        return {
            "project": self.project,
            "gap": self.gap,
            "complexity": self.complexity,
            "status": self.status,
        }


def parse_opportunities(text: str) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for line in text.splitlines():
        match = CONTRIBUTE_RE.match(line)
        if not match:
            continue
        project = " ".join(match.group("project").split())
        gap = " ".join(match.group("gap").split())
        complexity = (match.group("complexity") or "unknown").lower().replace("medium", "med")
        if "pr complexity" in gap.lower():
            gap = re.split(r"\s*[-:]\s*PR complexity:", gap, flags=re.I)[0].strip()
        public = assert_public(f"{project}: {gap}")
        if public.blocked:
            continue
        opportunities.append(Opportunity(project=project, gap=gap, complexity=complexity))
    return opportunities


def draft_pr_description(opportunity: Opportunity) -> str:
    return (
        f"## Summary\n\n"
        f"Address a small integration gap noticed while using {opportunity.project} inside FPOS.\n\n"
        f"## Gap\n\n{opportunity.gap}\n\n"
        "## Proposed change\n\n"
        "- Keep the patch minimal and upstream-shaped.\n"
        "- Add or update tests/docs that prove the integration edge.\n"
        "- Avoid FPOS-private context, credentials, contact data, and internal decision logs.\n\n"
        "## Review gate\n\n"
        "Council review required before any external submission.\n"
    )


def render_log(opportunities: list[Opportunity], *, current: dt.datetime | None = None) -> str:
    now = current or dt.datetime.now(dt.timezone.utc)
    lines = [
        "# Upstream Contributions",
        "",
        f"Updated: {now.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        "",
        "This public-edge tracker records contribution opportunities only. External PR submission remains a James/Council gate.",
        "",
        "| Project | Gap | Complexity | Status |",
        "|---|---|---|---|",
    ]
    for item in opportunities:
        lines.append(f"| {item.project} | {item.gap} | {item.complexity} | {item.status} |")
    if not opportunities:
        lines.append("| none yet | waiting for Forge scans | unknown | draft |")
    lines.extend(["", "## Draft PR Descriptions", ""])
    for item in opportunities:
        lines.append(f"### {item.project}")
        lines.append("")
        lines.append(draft_pr_description(item).strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def update_log_from_text(text: str, *, output: Path = DEFAULT_LOG, current: dt.datetime | None = None) -> dict[str, Any]:
    opportunities = parse_opportunities(text)
    rendered = render_log(opportunities, current=current)
    gate = assert_public(rendered)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(gate.sanitized, encoding="utf-8")
    return {"output": str(output), "count": len(opportunities), "opportunities": [item.as_dict() for item in opportunities]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract CONTRIBUTEs from Forge scan text.")
    parser.add_argument("--input", type=Path, help="Scan report or FRONTIER_LOG path")
    parser.add_argument("--output", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    text = args.input.read_text(encoding="utf-8", errors="replace") if args.input else ""
    result = update_log_from_text(text, output=args.output)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"tracked {result['count']} opportunities in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

