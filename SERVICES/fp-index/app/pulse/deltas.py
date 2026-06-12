"""Compute deltas between pulse snapshots. This is what proves compounding."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ..field_sensor.registry import BRAIN_DIR

PULSE_SNAPSHOTS = BRAIN_DIR / "pulse_snapshots.jsonl"


def _iter_snapshots() -> list[dict[str, Any]]:
    if not PULSE_SNAPSHOTS.exists():
        return []
    out = []
    for line in PULSE_SNAPSHOTS.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return sorted(out, key=lambda x: x.get("ts", ""))


def pulse_history(limit: int = 20) -> list[dict[str, Any]]:
    snaps = _iter_snapshots()
    return snaps[-limit:]


def _flat(d: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flat(v, key))
        else:
            out[key] = v
    return out


def weekly_deltas() -> dict[str, Any]:
    """Return a flattened delta between the two most recent snapshots."""
    snaps = _iter_snapshots()
    if len(snaps) < 2:
        return {
            "status": "insufficient_snapshots",
            "snapshots_so_far": len(snaps),
            "message": "Need at least 2 weekly snapshots to compute compounding delta.",
        }

    prior = snaps[-2]
    latest = snaps[-1]

    prior_flat = _flat(prior)
    latest_flat = _flat(latest)

    deltas: dict[str, Any] = {}
    for key in sorted(set(prior_flat) | set(latest_flat)):
        p = prior_flat.get(key)
        l = latest_flat.get(key)
        if isinstance(p, (int, float)) and isinstance(l, (int, float)):
            deltas[key] = {"prior": p, "latest": l, "delta": l - p,
                           "pct": ((l - p) / p * 100) if p else None}

    return {
        "status": "ok",
        "prior_ts": prior.get("ts"),
        "latest_ts": latest.get("ts"),
        "deltas": deltas,
    }


def summary_line(pulse: Optional[dict[str, Any]] = None) -> str:
    """One-line human summary of current pulse. For logs or dashboards."""
    if pulse is None:
        snaps = _iter_snapshots()
        if not snaps:
            return "pulse: no snapshots yet"
        pulse = snaps[-1]
    zv = pulse.get("zen_village", {})
    sys = pulse.get("system", {})
    reach = pulse.get("reach", {})
    props = sys.get("proposals", {})
    return (
        f"pulse: passes={zv.get('passes_total', 0)} "
        f"bookings={zv.get('bookings_total', 0)} "
        f"rev=${zv.get('zen_pass_revenue_total', 0) + zv.get('bookings_revenue_total', 0):.0f} "
        f"subs={reach.get('email_subscribers_total', 0)} "
        f"proposals={props.get('approved', 0)}/{props.get('total', 0)} "
        f"probe={sys.get('probe_pass_rate_latest', 0) or 0:.0%}"
    )
