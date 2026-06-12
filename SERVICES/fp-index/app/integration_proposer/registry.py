"""Proposals registry — append-only log + mutable status file.

Each proposal exists in two places:
  - proposals.jsonl : immutable historical record (append-only)
  - proposals_status.json : current status (pending / approved / rejected / shipped / archived)

Status transitions are also logged to proposals.jsonl so we have full
provenance of every decision.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..field_sensor.registry import BRAIN_DIR, ensure_brain_dir

logger = logging.getLogger(__name__)

PROPOSALS_PATH = BRAIN_DIR / "proposals.jsonl"
STATUS_PATH = BRAIN_DIR / "proposals_status.json"

VALID_STATUSES = {"pending", "approved", "rejected", "shipped", "archived"}


def _load_status() -> dict[str, dict[str, Any]]:
    ensure_brain_dir()
    if not STATUS_PATH.exists():
        return {}
    try:
        return json.loads(STATUS_PATH.read_text())
    except json.JSONDecodeError:
        logger.warning("[PROPOSER] status file corrupt, resetting")
        return {}


def _save_status(status: dict[str, dict[str, Any]]) -> None:
    ensure_brain_dir()
    STATUS_PATH.write_text(json.dumps(status, indent=2, default=str))


def append_proposal(proposal: dict[str, Any]) -> str:
    """Append a new proposal. Returns proposal_id."""
    ensure_brain_dir()
    pid = proposal.get("proposal_id")
    if not pid:
        raise ValueError("proposal must have proposal_id")

    record = {
        "event": "created",
        "ts": datetime.now(timezone.utc).isoformat(),
        **proposal,
    }
    with PROPOSALS_PATH.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")

    status = _load_status()
    status[pid] = {
        "proposal_id": pid,
        "status": "pending",
        "created_ts": record["ts"],
        "updated_ts": record["ts"],
        "title": proposal.get("title", ""),
        "gap_id": proposal.get("source_gap_id", ""),
        "regenerative_score": proposal.get("regenerative_score"),
        "leverage": proposal.get("leverage"),
    }
    _save_status(status)
    logger.info(f"[PROPOSER] Created proposal {pid}: {proposal.get('title', '')[:80]}")
    return pid


def update_proposal_status(proposal_id: str, new_status: str, note: str = "",
                            actor: str = "human") -> dict[str, Any]:
    """Transition a proposal's status. Logs to history."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"invalid status {new_status}; must be one of {VALID_STATUSES}")

    status = _load_status()
    if proposal_id not in status:
        raise KeyError(f"proposal {proposal_id} not found")

    old_status = status[proposal_id]["status"]
    now = datetime.now(timezone.utc).isoformat()

    status[proposal_id]["status"] = new_status
    status[proposal_id]["updated_ts"] = now
    status[proposal_id].setdefault("history", []).append({
        "from": old_status, "to": new_status, "ts": now, "note": note, "actor": actor,
    })
    _save_status(status)

    with PROPOSALS_PATH.open("a") as f:
        f.write(json.dumps({
            "event": "status_change",
            "ts": now,
            "proposal_id": proposal_id,
            "from_status": old_status,
            "to_status": new_status,
            "note": note,
            "actor": actor,
        }, default=str) + "\n")

    logger.info(f"[PROPOSER] {proposal_id}: {old_status} -> {new_status}")
    return status[proposal_id]


def read_proposals() -> dict[str, dict[str, Any]]:
    """Return current status of all proposals, keyed by proposal_id."""
    return _load_status()


def pending_proposals() -> list[dict[str, Any]]:
    status = _load_status()
    out = [v for v in status.values() if v.get("status") == "pending"]
    out.sort(key=lambda x: x.get("created_ts", ""), reverse=True)
    return out


def get_proposal_full(proposal_id: str) -> Optional[dict[str, Any]]:
    """Load the full proposal (including code/plan) from proposals.jsonl."""
    if not PROPOSALS_PATH.exists():
        return None
    latest = None
    for line in PROPOSALS_PATH.read_text().strip().split("\n"):
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("proposal_id") == proposal_id and r.get("event") == "created":
            latest = r
    return latest
