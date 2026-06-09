#!/usr/bin/env python3
"""Drive the next safe results-bearing move from the Intent Buildstream."""
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
DEFAULT_BUILDSTREAM = REPO_ROOT / "docs" / "codex" / "INTENT_BUILDSTREAM.md"
DEFAULT_RESULTS_LANE = REPO_ROOT / "docs" / "codex" / "RESULTS_LANE.md"
DEFAULT_QUEUE = REPO_ROOT / "core" / "STATE" / "HUMAN_EDGE_QUEUE.json"
DEFAULT_CONSEQUENCE_LEDGER = REPO_ROOT / "core" / "STATE" / "RESULTS_DRAFTS" / "consequence.jsonl"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.queue.build import add_gate  # noqa: E402


RESULT_KINDS = {"revenue", "donation", "funding", "enrollment"}
HUMAN_EDGE_WORDS = (
    "approve",
    "approval",
    "bless",
    "send",
    "outbound",
    "named lead",
    "move money",
    "transfer",
    "positioning call",
    "price",
    "public",
    "deploy",
    "secret",
)


@dataclasses.dataclass(frozen=True)
class Opportunity:
    ident: str
    title: str
    weight: float
    status: str
    results: tuple[str, ...]
    next_move: str
    tier: str
    verbs: tuple[str, ...]
    stream: str


@dataclasses.dataclass(frozen=True)
class EngineResult:
    action: str
    opportunity: Opportunity | None
    move: str
    target: str | None
    consequence: dict[str, Any] | None = None

    def summary(self) -> str:
        if self.opportunity is None:
            return "No READY results-bearing opportunity found."
        return (
            f"{self.opportunity.ident}: {self.move} -> {self.action}"
            + (f" ({self.target})" if self.target else "")
        )


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "results-opportunity"


def parse_metadata(line: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in line.split("|"):
        part = part.strip().lstrip("-").strip()
        if ":" not in part:
            fields.setdefault("title", part.strip())
            continue
        key, value = part.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def opportunity_from_meta(meta: dict[str, str], fallback_title: str) -> Opportunity | None:
    raw_results = meta.get("results", "")
    results = tuple(r.strip().lower() for r in re.split(r"[,/ ]+", raw_results) if r.strip())
    if not any(r in RESULT_KINDS for r in results):
        return None
    status = meta.get("status", "").lower()
    if status != "ready":
        return None
    title = meta.get("title") or fallback_title
    ident = meta.get("id") or slugify(title)
    next_move = meta.get("next") or meta.get("move") or title
    tier = classify_tier(meta.get("tier", ""), next_move)
    verbs = tuple(v.strip() for v in meta.get("verbs", "").split(",") if v.strip()) or (
        "approve",
        "revise",
        "checkpoint",
    )
    stream = meta.get("stream") or stream_for_results(results)
    try:
        weight = float(meta.get("weight", meta.get("value", "0")))
    except ValueError:
        weight = 0.0
    return Opportunity(
        ident=ident,
        title=title,
        weight=weight,
        status=status,
        results=results,
        next_move=next_move,
        tier=tier,
        verbs=verbs,
        stream=stream,
    )


def stream_for_results(results: tuple[str, ...]) -> str:
    if "enrollment" in results:
        return "Zen"
    if "funding" in results or "donation" in results or "revenue" in results:
        return "Ventures"
    return "Game"


def classify_tier(explicit: str, move: str) -> str:
    tier = explicit.strip().lower()
    if tier in {"ai", "ai-doable", "draft", "reversible"}:
        return "ai"
    if tier in {"human", "human-edge", "james", "gate"}:
        return "human"
    lowered = move.lower()
    if any(word in lowered for word in HUMAN_EDGE_WORDS):
        return "human"
    return "ai"


def parse_opportunities(text: str) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    current_heading = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_heading = line.lstrip("#").strip()
            continue
        if "results:" not in line.lower():
            continue
        meta = parse_metadata(line)
        opportunity = opportunity_from_meta(meta, current_heading)
        if opportunity:
            opportunities.append(opportunity)
    return opportunities


def choose_opportunity(opportunities: list[Opportunity]) -> Opportunity | None:
    if not opportunities:
        return None
    return sorted(opportunities, key=lambda item: (-item.weight, item.ident))[0]


def render_draft(opportunity: Opportunity) -> str:
    return (
        f"### {utc_now()} · {opportunity.ident}\n"
        f"- status: awaiting James review\n"
        f"- results: {', '.join(opportunity.results)}\n"
        f"- weight: {opportunity.weight:g}\n"
        f"- opportunity: {opportunity.title}\n"
        f"- next move: {opportunity.next_move}\n"
        f"- staged artifact: Draft/prep only. Nothing has been sent, deployed, or moved.\n"
        f"- review verbs: approve / revise / checkpoint\n\n"
        "#### Draft\n"
        f"{draft_body(opportunity)}\n"
    )


def draft_body(opportunity: Opportunity) -> str:
    title = opportunity.title.rstrip(".")
    move = opportunity.next_move.rstrip(".")
    return (
        f"Prepare `{move}` for `{title}`.\n\n"
        "- Hook: name the result this creates.\n"
        "- Offer: one concrete next step, reversible and reviewable.\n"
        "- Proof: record reply, dollar, signup, or no-response after James approves any send.\n"
    )


def append_results_lane(opportunity: Opportunity, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
    else:
        existing = "# RESULTS LANE\n\n*Review lane for AI-staged results moves. Nothing here has been sent.*\n\n"
    path.write_text(existing.rstrip() + "\n\n" + render_draft(opportunity), encoding="utf-8")


def write_human_gate(opportunity: Opportunity, queue_path: Path) -> dict[str, Any]:
    question = f"Approve next results move for {opportunity.title}: {opportunity.next_move}?"
    return add_gate(
        gate_id=f"results-{slugify(opportunity.ident)}",
        stream=opportunity.stream,
        question=question,
        verbs=list(opportunity.verbs),
        blocking=True,
        urgent=False,
        path=queue_path,
    )


def record_consequence(
    opportunity_id: str,
    outcome: str,
    detail: str,
    ledger_path: Path,
    dry_run: bool = False,
) -> dict[str, Any]:
    row = {
        "ts": utc_now(),
        "opportunity_id": opportunity_id,
        "outcome": outcome,
        "realized": outcome in {"reply", "dollar", "signup"},
        "detail": detail,
    }
    if not dry_run:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def run_engine(
    *,
    buildstream_path: Path = DEFAULT_BUILDSTREAM,
    results_lane_path: Path = DEFAULT_RESULTS_LANE,
    queue_path: Path = DEFAULT_QUEUE,
    consequence_ledger_path: Path = DEFAULT_CONSEQUENCE_LEDGER,
    dry_run: bool = False,
) -> EngineResult:
    text = buildstream_path.read_text(encoding="utf-8", errors="ignore")
    opportunity = choose_opportunity(parse_opportunities(text))
    if opportunity is None:
        return EngineResult(action="none", opportunity=None, move="", target=None)
    if opportunity.tier == "human":
        if dry_run:
            target = str(queue_path)
        else:
            gate = write_human_gate(opportunity, queue_path)
            target = f"{queue_path}#{gate['id']}"
        return EngineResult(action="human-gated", opportunity=opportunity, move=opportunity.next_move, target=target)
    if not dry_run:
        append_results_lane(opportunity, results_lane_path)
    return EngineResult(action="ai-staged", opportunity=opportunity, move=opportunity.next_move, target=str(results_lane_path))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Advance the highest-weighted results-bearing opportunity safely.")
    ap.add_argument("--buildstream", type=Path, default=DEFAULT_BUILDSTREAM)
    ap.add_argument("--results-lane", type=Path, default=DEFAULT_RESULTS_LANE)
    ap.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--consequence-ledger", type=Path, default=DEFAULT_CONSEQUENCE_LEDGER)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--record-consequence", metavar="OPPORTUNITY_ID")
    ap.add_argument("--outcome", choices=["reply", "dollar", "signup", "none"], default="none")
    ap.add_argument("--detail", default="")
    args = ap.parse_args(argv)

    if args.record_consequence:
        row = record_consequence(
            args.record_consequence,
            args.outcome,
            args.detail,
            args.consequence_ledger,
            dry_run=args.dry_run,
        )
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))
        return 0

    result = run_engine(
        buildstream_path=args.buildstream,
        results_lane_path=args.results_lane,
        queue_path=args.queue_json,
        consequence_ledger_path=args.consequence_ledger,
        dry_run=args.dry_run,
    )
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

