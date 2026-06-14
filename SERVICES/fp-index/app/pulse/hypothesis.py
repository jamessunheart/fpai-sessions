"""Proposal hypothesis + outcome evaluation.

Every approved proposal must declare a pulse-metric hypothesis:
  - target_metric: which pulse path (e.g. "zen_village.passes_last_7d")
  - expected_delta: how much it should move
  - measurement_window_days: when to check
  - rationale: why we think this will happen

After the window closes, outcomes.jsonl records whether the delta
materialized. This is the learning signal: over time we see which
kinds of proposals actually move outcomes vs which were theater.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from ..field_sensor.registry import BRAIN_DIR, ensure_brain_dir
from ..integration_proposer.registry import (
    get_proposal_full,
    read_proposals,
)
from .deltas import _flat, _iter_snapshots

logger = logging.getLogger(__name__)

OUTCOMES_PATH = BRAIN_DIR / "proposal_outcomes.jsonl"


def attach_hypothesis_to_proposal(proposal_id: str, target_metric: str,
                                  expected_delta: float,
                                  measurement_window_days: int,
                                  rationale: str) -> dict[str, Any]:
    """Attach a pulse-metric hypothesis to an existing proposal.

    Writes an append-only record in the proposals log. Status is unchanged.
    """
    ensure_brain_dir()
    from ..integration_proposer.registry import PROPOSALS_PATH
    record = {
        "event": "hypothesis_attached",
        "ts": datetime.now(timezone.utc).isoformat(),
        "proposal_id": proposal_id,
        "hypothesis": {
            "target_metric": target_metric,
            "expected_delta": expected_delta,
            "measurement_window_days": measurement_window_days,
            "rationale": rationale,
            "baseline_ts": datetime.now(timezone.utc).isoformat(),
        },
    }
    with PROPOSALS_PATH.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")
    logger.info(f"[PULSE] Hypothesis attached to {proposal_id}: {target_metric} +{expected_delta}")
    return record


def _get_metric_value(pulse: dict[str, Any], metric_path: str) -> Optional[float]:
    flat = _flat(pulse)
    v = flat.get(metric_path)
    if isinstance(v, (int, float)):
        return float(v)
    return None


def evaluate_proposal_outcomes() -> list[dict[str, Any]]:
    """For every proposal with a hypothesis and a closed window, check outcomes.

    Returns list of newly-evaluated outcomes (one per proposal newly checked).
    """
    ensure_brain_dir()
    from ..integration_proposer.registry import PROPOSALS_PATH

    if not PROPOSALS_PATH.exists():
        return []

    already_evaluated = set()
    if OUTCOMES_PATH.exists():
        for line in OUTCOMES_PATH.read_text().strip().split("\n"):
            if not line:
                continue
            try:
                r = json.loads(line)
                already_evaluated.add(r.get("proposal_id"))
            except json.JSONDecodeError:
                continue

    hypotheses: dict[str, dict[str, Any]] = {}
    for line in PROPOSALS_PATH.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("event") == "hypothesis_attached":
            hypotheses[r["proposal_id"]] = r

    if not hypotheses:
        return []

    snapshots = _iter_snapshots()
    now = datetime.now(timezone.utc)

    results = []
    for pid, h in hypotheses.items():
        if pid in already_evaluated:
            continue
        hyp = h.get("hypothesis", {})
        baseline_ts = hyp.get("baseline_ts", "")
        window_days = int(hyp.get("measurement_window_days", 7))
        try:
            baseline_dt = datetime.fromisoformat(baseline_ts)
        except ValueError:
            continue
        close_dt = baseline_dt + timedelta(days=window_days)
        if now < close_dt:
            continue

        metric = hyp.get("target_metric", "")
        baseline_snap = _closest_snapshot(snapshots, baseline_dt)
        close_snap = _closest_snapshot(snapshots, close_dt)
        if not baseline_snap or not close_snap:
            continue

        baseline_val = _get_metric_value(baseline_snap, metric)
        close_val = _get_metric_value(close_snap, metric)
        if baseline_val is None or close_val is None:
            continue

        actual_delta = close_val - baseline_val
        expected_delta = float(hyp.get("expected_delta", 0))
        status = get_proposal_full(pid) or {}

        validated = False
        if expected_delta > 0:
            validated = actual_delta >= expected_delta * 0.5
        elif expected_delta < 0:
            validated = actual_delta <= expected_delta * 0.5
        else:
            validated = abs(actual_delta) < max(abs(baseline_val) * 0.05, 1)

        outcome = {
            "ts": now.isoformat(),
            "proposal_id": pid,
            "title": status.get("title", ""),
            "metric": metric,
            "baseline_value": baseline_val,
            "close_value": close_val,
            "actual_delta": actual_delta,
            "expected_delta": expected_delta,
            "validated": validated,
            "proposal_status": status.get("status", "unknown"),
        }
        with OUTCOMES_PATH.open("a") as f:
            f.write(json.dumps(outcome, default=str) + "\n")
        logger.info(f"[PULSE] Outcome: {pid} {metric} expected={expected_delta} actual={actual_delta} validated={validated}")
        results.append(outcome)

    return results


def _closest_snapshot(snapshots: list[dict[str, Any]], target: datetime) -> Optional[dict[str, Any]]:
    """Find the snapshot closest in time to target."""
    if not snapshots:
        return None
    target_iso = target.isoformat()
    best = min(snapshots, key=lambda s: abs((s.get("ts", "") > target_iso) - 0.5))
    def ts_to_dt(s):
        try:
            return datetime.fromisoformat(s.get("ts", ""))
        except ValueError:
            return datetime.max.replace(tzinfo=timezone.utc)
    best = min(snapshots, key=lambda s: abs((ts_to_dt(s) - target).total_seconds()))
    return best


def all_outcomes() -> list[dict[str, Any]]:
    if not OUTCOMES_PATH.exists():
        return []
    out = []
    for line in OUTCOMES_PATH.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
