from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable

from tools.benchmarks import DEFAULT_OPS_LEDGER, DEFAULT_SCORE_LEDGER, REPO_ROOT, append_jsonl, read_jsonl
from tools.inventory.scan_resources import DEFAULT_OUTPUT as DEFAULT_RESOURCE_INVENTORY
from tools.inventory.scan_resources import read_inventory_context
from tools.prompt_efficiency.gepa_loop import PROMPT_ID_BENCHMARK_IMPROVEMENT, render_prompt

DEFAULT_PROPOSAL_LOG = REPO_ROOT / "core" / "benchmarks" / "improvement_proposals.jsonl"
MAX_SPECS_PER_AGENT_WEEK = 2


def should_propose(score_row: dict[str, Any]) -> bool:
    return bool(score_row.get("trigger_fired")) and bool(score_row.get("trigger_metric"))


def within_rate_limit(agent: str, proposal_log: Path, *, now: dt.datetime | None = None) -> bool:
    current = now or dt.datetime.now(dt.timezone.utc)
    cutoff = current - dt.timedelta(days=7)
    recent = []
    for row in read_jsonl(proposal_log):
        if row.get("agent") != agent or not row.get("spec_queued") or row.get("spec_queued") == "dry-run":
            continue
        try:
            queued_at = dt.datetime.fromisoformat(str(row.get("queued_at")).replace("Z", "+00:00")) if row.get("queued_at") else current
        except ValueError:
            queued_at = current
        if queued_at >= cutoff:
            recent.append(row)
    return len(recent) < MAX_SPECS_PER_AGENT_WEEK


def build_prompt(
    score_row: dict[str, Any],
    *,
    blueprint_text: str = "",
    recent_context: str = "",
    resource_inventory: str = "",
) -> str:
    return render_prompt(
        PROMPT_ID_BENCHMARK_IMPROVEMENT,
        {
            "score_row": score_row,
            "blueprint_text": blueprint_text,
            "recent_context": recent_context,
            "resource_inventory": resource_inventory,
        },
    )


def collect_recent_context(agent: str, ops_ledger: Path = DEFAULT_OPS_LEDGER) -> str:
    terms = (agent.lower(),)
    selected = []
    for row in read_jsonl(ops_ledger)[-500:]:
        event = str(row.get("event") or "").lower()
        text = json.dumps(row, sort_keys=True).lower()
        if event not in {"correction", "reversed", "auto_reverted", "failed", "request_changes"}:
            continue
        if any(term in text for term in terms):
            selected.append(json.dumps(row, sort_keys=True))
    return "\n".join(selected[-12:])


def draft_with_claude(prompt: str) -> str:
    cmd = shlex.split(os.environ.get("BENCHMARKS_CLAUDE_CMD", "claude -p --effort low"))
    completed = subprocess.run(
        cmd,
        input=prompt,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"claude proposal failed: {completed.stderr.strip()[:500]}")
    return completed.stdout.strip()


def queue_with_curator(spec_markdown: str) -> str:
    if os.environ.get("BENCHMARKS_QUEUE_LIVE") != "1":
        return "dry-run"
    from curator.decisions import queue_build  # type: ignore

    return str(queue_build(spec_markdown))


def propose_for_score(
    score_row: dict[str, Any],
    *,
    blueprint_dir: Path = REPO_ROOT / "docs" / "blueprints",
    proposal_log: Path = DEFAULT_PROPOSAL_LOG,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    claude_runner: Callable[[str], str] | None = None,
    queue_build: Callable[[str], str] | None = None,
    now: dt.datetime | None = None,
    resource_inventory_path: Path = DEFAULT_RESOURCE_INVENTORY,
) -> dict[str, Any] | None:
    if not should_propose(score_row):
        return None
    agent = str(score_row.get("agent") or "unknown")
    if not within_rate_limit(agent, proposal_log, now=now):
        return None
    blueprint_path = blueprint_dir / f"{agent}.md"
    blueprint = blueprint_path.read_text(encoding="utf-8", errors="replace") if blueprint_path.exists() else ""
    recent_context = str(score_row.get("recent_context") or collect_recent_context(agent, ops_ledger))
    resource_inventory = read_inventory_context(resource_inventory_path, limit=24_000)
    prompt = build_prompt(
        score_row,
        blueprint_text=blueprint,
        recent_context=recent_context,
        resource_inventory=resource_inventory,
    )
    runner = claude_runner or (draft_with_claude if os.environ.get("BENCHMARKS_PROPOSE_LIVE") == "1" else None)
    spec_markdown = runner(prompt) if runner else prompt
    queued = (queue_build or queue_with_curator)(spec_markdown)
    row = {
        "queued_at": (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agent": agent,
        "trigger_metric": score_row.get("trigger_metric"),
        "value": score_row.get("primary_metric"),
        "spec_queued": queued,
        "reasoning": score_row.get("trigger_reason") or "",
    }
    append_jsonl(proposal_log, row)
    return row


def propose_from_ledger(
    score_ledger: Path = DEFAULT_SCORE_LEDGER,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    proposals: list[dict[str, Any]] = []
    for row in read_jsonl(score_ledger):
        proposal = propose_for_score(row, **kwargs)
        if proposal:
            proposals.append(proposal)
    return proposals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score-ledger", type=Path, default=DEFAULT_SCORE_LEDGER)
    parser.add_argument("--proposal-log", type=Path, default=DEFAULT_PROPOSAL_LOG)
    args = parser.parse_args(argv)
    proposals = propose_from_ledger(args.score_ledger, proposal_log=args.proposal_log)
    print(json.dumps({"proposals": proposals}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
