"""Read + summarize probe results. Compute compounding deltas over time."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from ..field_sensor.registry import BRAIN_DIR

RESULTS_PATH = BRAIN_DIR / "probe_results.jsonl"


def _iter_results() -> list[dict[str, Any]]:
    if not RESULTS_PATH.exists():
        return []
    out = []
    for line in RESULTS_PATH.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _group_by_run(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    runs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in results:
        runs[r.get("run_id", "unknown")].append(r)
    return runs


def _summarize_run(run_id: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    avg = sum(r.get("score", 0.0) for r in results) / total if total else 0.0
    ts = min((r.get("ts", "") for r in results), default="")
    return {
        "run_id": run_id,
        "ts": ts,
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "avg_score": avg,
    }


def latest_run_summary() -> Optional[dict[str, Any]]:
    results = _iter_results()
    if not results:
        return None
    runs = _group_by_run(results)
    latest_id = max(runs.keys(), key=lambda k: min((r.get("ts", "") for r in runs[k]), default=""))
    summary = _summarize_run(latest_id, runs[latest_id])
    per_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in runs[latest_id]:
        per_cat[r.get("category", "unknown")].append(r)
    summary["per_category"] = {
        cat: {
            "total": len(rs),
            "passed": sum(1 for r in rs if r.get("passed")),
            "avg_score": sum(r.get("score", 0.0) for r in rs) / len(rs) if rs else 0.0,
        }
        for cat, rs in per_cat.items()
    }
    summary["per_probe"] = [
        {"probe_id": r.get("probe_id"), "score": r.get("score"), "passed": r.get("passed")}
        for r in sorted(runs[latest_id], key=lambda x: x.get("probe_id", ""))
    ]
    return summary


def results_since(days: int) -> list[dict[str, Any]]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    all_r = _iter_results()
    return [r for r in all_r if r.get("ts", "") >= cutoff]


def compounding_delta(baseline_days: int = 30, recent_days: int = 7) -> dict[str, Any]:
    """Compare most-recent window to the earliest baseline window.

    True compounding means pass rate on the UNCHANGED probe subset is rising.
    """
    all_r = _iter_results()
    if not all_r:
        return {"status": "no_data"}

    runs = _group_by_run(all_r)
    run_summaries = sorted(
        [_summarize_run(rid, rs) for rid, rs in runs.items()],
        key=lambda s: s["ts"],
    )
    if len(run_summaries) < 2:
        return {
            "status": "insufficient_runs",
            "runs_so_far": len(run_summaries),
            "message": "Need at least 2 runs (ideally weeks apart) to measure delta.",
        }

    baseline = run_summaries[0]
    latest = run_summaries[-1]

    baseline_probes = {r["probe_id"]: r for r in runs[baseline["run_id"]]}
    latest_probes = {r["probe_id"]: r for r in runs[latest["run_id"]]}
    common = sorted(set(baseline_probes) & set(latest_probes))

    common_baseline_passed = sum(1 for p in common if baseline_probes[p].get("passed"))
    common_latest_passed = sum(1 for p in common if latest_probes[p].get("passed"))
    common_n = len(common)

    per_probe_delta = []
    for pid in common:
        b = baseline_probes[pid]
        l = latest_probes[pid]
        per_probe_delta.append({
            "probe_id": pid,
            "baseline_score": b.get("score", 0.0),
            "latest_score": l.get("score", 0.0),
            "delta": l.get("score", 0.0) - b.get("score", 0.0),
            "baseline_passed": b.get("passed", False),
            "latest_passed": l.get("passed", False),
        })

    return {
        "status": "ok",
        "baseline_run": baseline,
        "latest_run": latest,
        "common_probes": common_n,
        "baseline_pass_rate_on_common": common_baseline_passed / common_n if common_n else 0.0,
        "latest_pass_rate_on_common": common_latest_passed / common_n if common_n else 0.0,
        "pass_rate_delta": (common_latest_passed - common_baseline_passed) / common_n if common_n else 0.0,
        "per_probe_delta": per_probe_delta,
    }


def all_runs_summary() -> list[dict[str, Any]]:
    runs = _group_by_run(_iter_results())
    return sorted(
        [_summarize_run(rid, rs) for rid, rs in runs.items()],
        key=lambda s: s["ts"],
    )
