#!/usr/bin/env python3
"""Render public benchmark leaderboard artifacts from per-agent score ledgers."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from tools.benchmarks import DEFAULT_SCORE_LEDGER, read_jsonl
from tools.forge.security_gate import assert_public

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PUBLIC_DIR = REPO_ROOT / "benchmarks"


def summarize_scores(rows: list[dict[str, Any]], *, min_points: int = 3) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        agent = str(row.get("agent") or "").strip()
        if agent:
            grouped[agent].append(row)
    agents: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for agent, values in sorted(grouped.items()):
        values = sorted(values, key=lambda item: str(item.get("run_date") or ""))
        if len(values) < min_points:
            skipped.append({"agent": agent, "points": len(values), "reason": "fewer_than_min_points"})
            continue
        latest = values[-1]
        first = values[0]
        latest_metric = _metric(latest.get("primary_metric"))
        first_metric = _metric(first.get("primary_metric"))
        agents.append(
            {
                "agent": agent,
                "points": len(values),
                "latest_date": latest.get("run_date") or "",
                "primary_metric": latest_metric,
                "delta_from_first": round(latest_metric - first_metric, 4),
                "sovereign_run": "qualified" if latest_metric > 0 else "observed",
            }
        )
    return {"agents": agents, "skipped": skipped, "min_points": min_points}


def render_leaderboard(summary: dict[str, Any], *, current: dt.datetime | None = None) -> str:
    now = current or dt.datetime.now(dt.timezone.utc)
    lines = [
        "# FPOS Public Benchmark Leaderboard",
        "",
        f"Updated: {now.date().isoformat()}",
        "",
        "Gate: agents publish only after at least 3 scored data points.",
        "",
        "| Agent | Data points | Latest date | Primary metric | Delta from first | Sovereign run |",
        "|---|---:|---|---:|---:|---|",
    ]
    for item in summary.get("agents", []):
        lines.append(
            f"| {item['agent']} | {item['points']} | {item['latest_date']} | {item['primary_metric']:.4f} | {item['delta_from_first']:.4f} | {item['sovereign_run']} |"
        )
    if not summary.get("agents"):
        lines.append("| pending | 0 | - | 0.0000 | 0.0000 | waiting for 3 data points |")
    return "\n".join(lines).rstrip() + "\n"


def write_public_benchmarks(
    *,
    score_ledger: Path = DEFAULT_SCORE_LEDGER,
    public_dir: Path = DEFAULT_PUBLIC_DIR,
    min_points: int = 3,
    current: dt.datetime | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(score_ledger)
    summary = summarize_scores(rows, min_points=min_points)
    leaderboard = render_leaderboard(summary, current=current)
    gate = assert_public(leaderboard)
    public_dir.mkdir(parents=True, exist_ok=True)
    (public_dir / "leaderboard.md").write_text(gate.sanitized, encoding="utf-8")
    results_dir = public_dir / "results"
    results_dir.mkdir(exist_ok=True)
    run_date = (current or dt.datetime.now(dt.timezone.utc)).date().isoformat()
    (results_dir / f"{run_date}.md").write_text(gate.sanitized, encoding="utf-8")
    return {"leaderboard": str(public_dir / "leaderboard.md"), "agents_published": len(summary["agents"]), "skipped": summary["skipped"]}


def _metric(value: Any) -> float:
    if isinstance(value, dict):
        values = [float(item) for item in value.values() if isinstance(item, (int, float))]
        return round(sum(values) / len(values), 4) if values else 0.0
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return 0.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render public benchmark leaderboard.")
    parser.add_argument("--score-ledger", type=Path, default=DEFAULT_SCORE_LEDGER)
    parser.add_argument("--public-dir", type=Path, default=DEFAULT_PUBLIC_DIR)
    parser.add_argument("--min-points", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = write_public_benchmarks(score_ledger=args.score_ledger, public_dir=args.public_dir, min_points=args.min_points)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"wrote {result['leaderboard']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

