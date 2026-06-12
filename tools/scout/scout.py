#!/usr/bin/env python3
"""World Scout / Capability Scout.

Local-first upgrade sequencer for FPAI. It ranks known ecosystem candidates
against a focus phrase, assigns build/fork/API/ignore verdicts, and writes a
SCOUT REPORT with one recommended next upgrade.

No network. No installs. Web/research findings can be added later as data.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = Path(__file__).resolve().parent / "SCOUT_REPORT.md"
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "how",
    "it",
    "make",
    "of",
    "or",
    "the",
    "to",
    "up",
}


@dataclasses.dataclass(frozen=True)
class Candidate:
    name: str
    category: str
    summary: str
    fit: str
    verdict: str
    integration_cost: int
    leverage: int
    maturity: int
    focus_tags: tuple[str, ...]
    next_step: str
    caution: str
    source: str

    @property
    def base_score(self) -> int:
        return self.leverage + self.maturity - self.integration_cost


SEEDS: tuple[Candidate, ...] = (
    Candidate(
        name="Service Registry / World Map",
        category="system clarity",
        summary="A canonical local registry of services, status, owner, URLs, deploy target, cost, and kill condition.",
        fit="Directly answers the current system problem: the substrate cannot optimize what it cannot see.",
        verdict="build",
        integration_cost=1,
        leverage=10,
        maturity=8,
        focus_tags=("services", "registry", "clarity", "cleanup", "map", "world", "focus"),
        next_step="Generate a read-only service inventory from SERVICES/* metadata, then manually classify live/paused/archive.",
        caution="Avoid broad automated edits; produce a report first, then route cleanup specs.",
        source="local need; existing SERVICES/INDEX.md is stale",
    ),
    Candidate(
        name="Microsoft Conductor",
        category="agent orchestration",
        summary="Agent coordination pattern for multi-agent workflows and durable orchestration.",
        fit="Useful once FPAI has a clean service map and knows which workflows deserve orchestration.",
        verdict="fork",
        integration_cost=6,
        leverage=8,
        maturity=7,
        focus_tags=("agents", "orchestration", "workflow", "subagent", "coordination"),
        next_step="Prototype one narrow orchestration loop after the service registry exists.",
        caution="Premature orchestration would amplify current repo sprawl.",
        source="approved scout target from docs/codex/README.md",
    ),
    Candidate(
        name="Obsidian Agent Skills",
        category="second brain",
        summary="Skill-style workflows attached to an Obsidian vault and reused by agents.",
        fit="Strong fit for FPOS because James already uses the vault as visible memory.",
        verdict="fork",
        integration_cost=4,
        leverage=7,
        maturity=7,
        focus_tags=("obsidian", "vault", "memory", "skills", "second brain"),
        next_step="Fork the pattern into one repo-local skill for scout reports and proof logs.",
        caution="Do not let skill proliferation become another unindexed surface.",
        source="approved scout target from docs/codex/README.md",
    ),
    Candidate(
        name="LiteLLM / OpenRouter-style Model Router",
        category="model routing",
        summary="A thin routing layer for model choice, budgets, caps, and provider fallback.",
        fit="Good fit after cost meter is trustworthy; lets expensive calls route by task class.",
        verdict="API",
        integration_cost=5,
        leverage=8,
        maturity=8,
        focus_tags=("model", "router", "cost", "budget", "llm", "spend"),
        next_step="Add a read-only routing recommendation report before using any paid provider.",
        caution="Requires secrets and spend controls; never auto-wire providers from scout output.",
        source="known ecosystem pattern",
    ),
    Candidate(
        name="Graphiti / Temporal Knowledge Graph",
        category="knowledge graph",
        summary="Episodic memory graph pattern for entities, events, and time-aware relationships.",
        fit="High long-term fit for FPOS memory, but only after current canonical surfaces are clean.",
        verdict="fork",
        integration_cost=7,
        leverage=8,
        maturity=6,
        focus_tags=("memory", "knowledge", "graph", "timeline", "context"),
        next_step="Run a tiny proof on one source: qb questions or service registry history.",
        caution="Knowledge graphs become noise if source-of-truth boundaries are unclear.",
        source="known ecosystem pattern",
    ),
    Candidate(
        name="n8n",
        category="workflow automation",
        summary="Workflow automation engine with many connectors and human-readable flows.",
        fit="Useful for boring repeatable tasks after routing and permission boundaries are firm.",
        verdict="API",
        integration_cost=4,
        leverage=6,
        maturity=9,
        focus_tags=("workflow", "automation", "connector", "ops"),
        next_step="Use as an external automation option only for one approved, reversible workflow.",
        caution="Can create hidden background automation; keep manual until trusted.",
        source="known ecosystem tool",
    ),
    Candidate(
        name="Dify / Flowise",
        category="agent app builder",
        summary="Visual LLM app builders for chat, retrieval, and tool workflows.",
        fit="Helpful for prototypes, less helpful for this repo's need for canonical clarity.",
        verdict="ignore",
        integration_cost=5,
        leverage=4,
        maturity=8,
        focus_tags=("prototype", "chat", "builder", "workflow"),
        next_step="Ignore for now; revisit only if a user-facing AI app needs rapid prototyping.",
        caution="Adds another admin surface before the current ones are mapped.",
        source="known ecosystem tool",
    ),
    Candidate(
        name="Actual Budget",
        category="financial dashboard",
        summary="Local-first finance tracking and budgeting system.",
        fit="Potential fit for treasury visibility, but not the current clarity bottleneck.",
        verdict="API",
        integration_cost=5,
        leverage=5,
        maturity=8,
        focus_tags=("finance", "budget", "dashboard", "treasury"),
        next_step="Evaluate after financial consolidation hub spec is active.",
        caution="Do not import sensitive financial data during scout phase.",
        source="known ecosystem tool",
    ),
    Candidate(
        name="Open WebUI",
        category="AI interface",
        summary="Local AI chat UI and model interaction surface.",
        fit="Not the current need; FPAI already has too many surfaces competing for attention.",
        verdict="ignore",
        integration_cost=4,
        leverage=3,
        maturity=8,
        focus_tags=("chat", "ui", "model", "interface"),
        next_step="Ignore until there is a clear user group and one required model surface.",
        caution="Likely increases interface sprawl.",
        source="known ecosystem tool",
    ),
)


def words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOPWORDS}


def score_candidate(candidate: Candidate, focus_terms: set[str]) -> tuple[int, list[str]]:
    tag_hits = sorted(focus_terms.intersection(candidate.focus_tags))
    text = " ".join(
        [
            candidate.name,
            candidate.category,
            candidate.summary,
            candidate.fit,
            " ".join(candidate.focus_tags),
        ]
    )
    text_hits = sorted(focus_terms.intersection(words(text)))
    hits = sorted(set(tag_hits + text_hits))
    focus_bonus = min(6, len(hits) * 2)
    verdict_bonus = {"build": 3, "fork": 2, "API": 1, "ignore": -3}.get(candidate.verdict, 0)
    return candidate.base_score + focus_bonus + verdict_bonus, hits


def choose_recommendation(scored: list[dict]) -> dict:
    viable = [row for row in scored if row["verdict"] != "ignore"]
    return max(viable or scored, key=lambda row: (row["score"], -row["integration_cost"], row["name"]))


def render_report(focus: str, scored: list[dict], recommendation: dict) -> str:
    today = dt.date.today().isoformat()
    lines = [
        "# SCOUT REPORT",
        "",
        f"**Date:** {today}",
        f"**Focus:** {focus}",
        "**Mode:** local deterministic seed scan; no network; no installs; no external spend.",
        "",
        "## One Recommended Next Upgrade",
        "",
        f"**{recommendation['name']}** -> **{recommendation['verdict']}**",
        "",
        f"**Why:** {recommendation['fit']}",
        f"**Next step:** {recommendation['next_step']}",
        f"**Caution:** {recommendation['caution']}",
        "",
        "## Scored Intent",
        "",
        f"- **Intent:** {recommendation['name']}",
        f"- **Verdict:** {recommendation['verdict']}",
        f"- **Score:** {recommendation['score']}",
        f"- **Route:** Codex spec before implementation; James approves consequential changes.",
        f"- **Definition of done:** {recommendation['next_step']}",
        "",
        "## Candidates",
        "",
        "| Score | Candidate | Category | Verdict | Cost | Hits |",
        "|---:|---|---|---|---:|---|",
    ]
    for row in scored:
        hits = ", ".join(row["hits"]) if row["hits"] else "-"
        lines.append(
            f"| {row['score']} | {row['name']} | {row['category']} | {row['verdict']} | "
            f"{row['integration_cost']} | {hits} |"
        )
    lines.extend(["", "## Candidate Notes", ""])
    for row in scored:
        lines.extend(
            [
                f"### {row['name']}",
                f"- **Summary:** {row['summary']}",
                f"- **Fit:** {row['fit']}",
                f"- **Next step:** {row['next_step']}",
                f"- **Caution:** {row['caution']}",
                f"- **Source:** {row['source']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def run(focus: str, output: Path) -> dict:
    focus_terms = words(focus)
    scored: list[dict] = []
    for candidate in SEEDS:
        score, hits = score_candidate(candidate, focus_terms)
        row = dataclasses.asdict(candidate)
        row["score"] = score
        row["hits"] = hits
        scored.append(row)
    scored.sort(key=lambda row: (row["score"], -row["maturity"], row["integration_cost"]), reverse=True)
    recommendation = choose_recommendation(scored)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(focus, scored, recommendation), encoding="utf-8")
    return {
        "focus": focus,
        "output": str(output),
        "candidate_count": len(scored),
        "recommended": recommendation["name"],
        "verdict": recommendation["verdict"],
        "score": recommendation["score"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank upgrade candidates and write SCOUT REPORT.")
    parser.add_argument("focus", help="What the scout should optimize for.")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT, help="Report path.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    summary = run(args.focus, args.output)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"wrote {summary['output']}")
        print(f"recommended: {summary['recommended']} ({summary['verdict']}, score {summary['score']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
