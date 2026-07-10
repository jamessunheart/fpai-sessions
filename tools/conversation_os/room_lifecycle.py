#!/usr/bin/env python3
"""Conversation OS — shadow Room lifecycle (state machine, proof-gated closure).

SHADOW ONLY. No real rooms, messages, replies, Brain writes, or external actions.
A Room is a deterministic fold over immutable Events. Every transition names its
responsible actor/policy, retains source Event IDs, is idempotent, replays
identically, and rejects invalid/skipped transitions (audited).

States: proposed · awaiting_approval · active · blocked · completion_proposed ·
completed · closed · rejected.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

STATES = ("proposed", "awaiting_approval", "active", "blocked",
          "completion_proposed", "completed", "closed", "rejected")
TERMINAL = {"closed", "rejected"}

# (from_state, event_type) -> to_state. None = uninstantiated Room.
TRANSITIONS: dict[tuple[str | None, str], str] = {
    (None, "propose_room"): "proposed",
    ("proposed", "request_approval"): "awaiting_approval",
    ("proposed", "approve"): "active",
    ("proposed", "reject"): "rejected",
    ("awaiting_approval", "approve"): "active",
    ("awaiting_approval", "reject"): "rejected",
    ("active", "blocker_raised"): "blocked",
    ("blocked", "blocker_cleared"): "active",
    ("active", "claim_completion"): "completion_proposed",
    ("completion_proposed", "attach_proof_valid"): "completed",
    ("completed", "close"): "closed",
}
# self-loops: valid, do NOT change state, but record activity
SELF_LOOPS: set[tuple[str, str]] = {
    ("active", "attach_conversation_event"),
    ("active", "add_action_candidate"),
    ("completion_proposed", "attach_proof_invalid"),  # insufficient proof: stays
    ("completion_proposed", "claim_completion"),       # re-claim: stays
}

# ---- Durable-knowledge whitelist (INERT policy; nothing writes to Brain) ----
ELIGIBLE_PRE_OUTCOME = {
    "user_confirmed_preference", "explicit_correction",
    "verified_identity_fact", "standing_policy_decision",
}
ELIGIBLE_AT_CLOSURE = ELIGIBLE_PRE_OUTCOME | {
    "verified_decision", "reality_proven_outcome",
    "operating_lesson", "superseding_correction",
}
INELIGIBLE = {
    "model_interpretation", "intent_proposal", "inferred_preference",
    "unverified_third_party", "situational_state", "routing_confidence",
    "unresolved_question",
}


def _event_type(e: dict[str, Any]) -> str:
    t = e["type"]
    if t == "attach_proof":
        return "attach_proof_valid" if e.get("payload", {}).get("proof_valid") else "attach_proof_invalid"
    return t


def _empty_room(room_id: str) -> dict[str, Any]:
    return {
        "room_id": room_id, "state": None,
        # truth layers (kept distinct)
        "objective": None, "owner_candidates": [], "participants": [],
        "observed_events": [], "shared_state_ref": None,
        "decisions": [], "commitments": [], "actions": [], "blockers": [],
        "completion_condition": None, "submitted_proof": None,
        "verified_outcome": None, "learning_candidates": [],
        # audit
        "transitions": [], "rejected_transitions": [], "source_event_ids": [],
    }


def nominate_learning(items: list[dict[str, Any]], *, at_closure: bool) -> list[dict[str, Any]]:
    """INERT: filter candidate knowledge by the durable whitelist. Nothing persists.
    Each survivor still must pass durability/privacy/approval gates downstream."""
    eligible = ELIGIBLE_AT_CLOSURE if at_closure else ELIGIBLE_PRE_OUTCOME
    out = []
    for it in items:
        cls = it.get("class")
        if cls in eligible and cls not in INELIGIBLE:
            out.append({**it, "eligible": True,
                        "pending_gates": ["durability_truth", "privacy_audience", "approval"],
                        "written_to_brain": False})
    return out


def _apply(room: dict[str, Any], e: dict[str, Any]) -> None:
    etype = _event_type(e)
    cur = room["state"]
    actor = e.get("actor") or e.get("policy") or "unspecified"
    eid = e["event_id"]
    p = e.get("payload", {})

    def record(to):
        room["transitions"].append({"from": cur, "to": to, "event_type": etype,
                                     "actor": actor, "source_event_id": eid})
        room["source_event_ids"].append(eid)

    # valid state transition
    if (cur, etype) in TRANSITIONS:
        to = TRANSITIONS[(cur, etype)]
        room["state"] = to
        record(to)
        if etype == "propose_room":
            room["objective"] = p.get("objective")
            room["owner_candidates"] = p.get("owner_candidates", [])
            room["completion_condition"] = p.get("completion_condition")
        elif etype == "blocker_raised":
            room["blockers"].append({"blocker": p.get("blocker"), "source_event_id": eid})
        elif etype == "blocker_cleared":
            for b in room["blockers"]:
                b.setdefault("cleared_by", eid)
        elif etype == "claim_completion":
            room["decisions"].append({"claim": "completion", "source_event_id": eid})
        elif etype == "attach_proof_valid":
            room["submitted_proof"] = {"proof": p.get("proof"), "source_event_id": eid}
            room["verified_outcome"] = p.get("outcome") or "verified"
        elif etype == "close":
            cands = p.get("learning_candidates", [])
            room["learning_candidates"] = nominate_learning(cands, at_closure=True)
        return

    # valid self-loop (no state change) — records activity
    if (cur, etype) in SELF_LOOPS:
        room["source_event_ids"].append(eid)
        if etype == "attach_conversation_event":
            room["observed_events"].append(eid)
        elif etype == "add_action_candidate":
            room["actions"].append({"action": p.get("action"), "source_event_id": eid})
        elif etype == "attach_proof_invalid":
            room["rejected_transitions"].append(
                {"from": cur, "event_type": etype, "reason": "insufficient proof",
                 "source_event_id": eid})
        return

    # invalid / skipped transition -> rejected + audited, state unchanged
    room["rejected_transitions"].append(
        {"from": cur, "event_type": etype, "reason": "invalid/skipped transition",
         "actor": actor, "source_event_id": eid})


def reduce_room(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Deterministic fold. Dedup by dedup_key; sort by (occurred_at, event_id)."""
    by_key: dict[str, dict[str, Any]] = {}
    for e in events:
        k = e.get("dedup_key") or e["event_id"]
        cur = by_key.get(k)
        rank = (str(e.get("occurred_at") or ""), e["event_id"])
        if cur is None or rank < (str(cur.get("occurred_at") or ""), cur["event_id"]):
            by_key[k] = e
    uniq = sorted(by_key.values(), key=lambda e: (str(e.get("occurred_at") or ""), e["event_id"]))
    room_id = "room-" + hashlib.sha256(
        (uniq[0]["payload"].get("room_key", uniq[0]["event_id"]) if uniq else "empty").encode()
    ).hexdigest()[:12]
    room = _empty_room(room_id)
    for e in uniq:
        _apply(room, e)
    return room


def room_hash(room: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(room, sort_keys=True).encode()).hexdigest()
