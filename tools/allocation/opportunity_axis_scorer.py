#!/usr/bin/env python3
"""Advisory scorer for Opportunity Portfolio axes.

The Opportunity Engine stays deterministic: it only computes scores from axes.
This helper fills missing axes by asking Claude for the REQUIRED_DOMINO_AXES,
validates/clamps the answer, writes the axes back to the portfolio, and logs
the advisory scoring event.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from tools.allocation import opportunity_engine


DEFAULT_LOG = Path.home() / ".config/fpai/allocation/opportunity_axis_scores.jsonl"
Runner = Callable[[list[str]], subprocess.CompletedProcess[str]]


class AxisScoringError(RuntimeError):
    pass


def score_missing_axes(
    ledger: Path | str = opportunity_engine.DEFAULT_LEDGER,
    *,
    log_path: Path | str = DEFAULT_LOG,
    rescore_all: bool = False,
    dry_run: bool = False,
    runner: Runner | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    stamp = now or opportunity_engine.utc_now()
    path = Path(ledger)
    portfolio = opportunity_engine.load_portfolio(path)
    rows = portfolio.get("opportunities", [])
    if not isinstance(rows, list):
        raise AxisScoringError("portfolio opportunities must be a list")

    completed = 0
    skipped = 0
    errors: list[dict[str, str]] = []
    events: list[dict[str, Any]] = []
    command_runner = runner or _run_claude

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            skipped += 1
            continue
        normalized = opportunity_engine.normalize_axes(row.get("axes"))
        missing = [axis for axis in opportunity_engine.REQUIRED_DOMINO_AXES if normalized.get(axis) is None]
        if not rescore_all and not missing:
            skipped += 1
            continue
        try:
            axes = _score_one(row, command_runner)
        except Exception as exc:
            errors.append({"id": str(row.get("id") or index), "error": str(exc)})
            continue
        merged_axes = dict(row.get("axes") or {})
        merged_axes.update(axes)
        row["axes"] = opportunity_engine.normalize_axes(merged_axes)
        row["axis_score_basis"] = {
            "source": "claude_advisory_axis_scorer",
            "scored_at": stamp,
            "axes": list(opportunity_engine.REQUIRED_DOMINO_AXES),
        }
        row["updated_at"] = stamp
        completed += 1
        events.append(
            {
                "schema": "fpai_opportunity_axis_score_v1",
                "ts": stamp,
                "ledger": str(path),
                "opportunity_id": row.get("id"),
                "opportunity_title": row.get("title"),
                "rescore_all": rescore_all,
                "dry_run": dry_run,
                "axes": row["axes"],
            }
        )

    if not dry_run and completed:
        _write_portfolio(portfolio, path, stamp)
        _append_log(log_path, events)

    view = opportunity_engine.ranked(portfolio)
    return {
        "schema": "fpai_opportunity_axis_scorer_result_v1",
        "ts": stamp,
        "ledger": str(path),
        "log_path": str(log_path),
        "dry_run": dry_run,
        "rescore_all": rescore_all,
        "scored": completed,
        "skipped": skipped,
        "errors": errors,
        "all_scores_present": all(row.get("next_domino_score") is not None for row in view.get("all", [])),
        "next_domino": [
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "next_domino_score": row.get("next_domino_score"),
                "allocation_score": row.get("allocation_score"),
            }
            for row in view.get("next_domino", [])[:3]
        ],
    }


def _score_one(row: dict[str, Any], runner: Runner) -> dict[str, float]:
    prompt = _build_prompt(row)
    result = runner(["claude", "-p", prompt])
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise AxisScoringError(f"claude failed with exit {result.returncode}: {stderr[:300]}")
    payload = _extract_json(result.stdout or "")
    axes_raw = payload.get("axes") if isinstance(payload.get("axes"), dict) else payload
    axes = opportunity_engine.normalize_axes(axes_raw)
    missing = [axis for axis in opportunity_engine.REQUIRED_DOMINO_AXES if axes.get(axis) is None]
    if missing:
        raise AxisScoringError(f"claude response missing axes: {', '.join(missing)}")
    return {axis: axes[axis] for axis in opportunity_engine.REQUIRED_DOMINO_AXES}


def _build_prompt(row: dict[str, Any]) -> str:
    safe_row = {
        "id": row.get("id"),
        "title": row.get("title"),
        "description": row.get("description") or row.get("summary") or "",
        "questions": row.get("questions") or {},
        "spot": row.get("spot") or {},
        "topple": row.get("topple") or {},
    }
    return (
        "Score this opportunity for the FPAI Opportunity Engine.\n"
        "Return ONLY compact JSON with key 'axes'. Each required axis must be a number from 0 to 10.\n"
        "Axis meaning: pain=severity, market=buyer/reach, compounding=future optionality, "
        "difficulty=implementation drag where 10 is hardest, time_to_revenue=delay where 10 is slowest, "
        "time_to_first_dollar=delay where 10 is slowest, path_to_recurring=recurring revenue strength, "
        "constraint=current bottleneck pressure, leverage=cascade unlocked, proof_speed=how fast proof appears, "
        "topple_reversibility=how reversible/safe the first action is.\n"
        f"Required axes: {', '.join(opportunity_engine.REQUIRED_DOMINO_AXES)}.\n"
        "Opportunity JSON:\n"
        f"{json.dumps(safe_row, sort_keys=True)}"
    )


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AxisScoringError("claude response did not contain JSON") from None
        parsed = json.loads(stripped[start : end + 1])
    if not isinstance(parsed, dict):
        raise AxisScoringError("claude response JSON must be an object")
    return parsed


def _run_claude(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, timeout=90, check=False)


def _append_log(path: Path | str, events: list[dict[str, Any]]) -> None:
    if not events:
        return
    log = Path(path)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, sort_keys=True) + "\n")


def _write_portfolio(portfolio: dict[str, Any], path: Path, stamp: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = dict(portfolio)
    out["updated_at"] = stamp
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score missing Opportunity Portfolio axes with claude -p.")
    parser.add_argument("--ledger", type=Path, default=opportunity_engine.DEFAULT_LEDGER)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--rescore-all", action="store_true", help="Re-score rows even when all required axes already exist.")
    parser.add_argument("--dry-run", action="store_true", help="Call Claude and show result without writing the ledger/log.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = score_missing_axes(args.ledger, log_path=args.log, rescore_all=args.rescore_all, dry_run=args.dry_run)
    except AxisScoringError as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else _format_result(result))
    return 1 if result["errors"] else 0


def _format_result(result: dict[str, Any]) -> str:
    domino = result.get("next_domino") or []
    top = domino[0] if domino else {}
    return (
        f"scored={result.get('scored')} skipped={result.get('skipped')} errors={len(result.get('errors') or [])} "
        f"all_scores_present={result.get('all_scores_present')} "
        f"next_domino={top.get('title', 'none')} ({top.get('next_domino_score', 'blank')})"
    )


if __name__ == "__main__":
    raise SystemExit(main())
