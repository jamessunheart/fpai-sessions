#!/usr/bin/env python3
"""Conversation OS — Intent Disposition Gate (deterministic, shadow-only).

Each intent proposal gets a disposition. The MODEL may *recommend* one; the
KERNEL validates against deterministic rules and records the rule + evidence
that fired. No live Room creation, replies, Brain writes, or promotion.

A new Room is expensive — it requires strong evidence. A simple message,
question, receipt, notification, or one-step action must NOT become a Room.
"""
from __future__ import annotations

from typing import Any

DISPOSITIONS = (
    "observe_only", "needs_clarification", "create_action_candidate",
    "attach_to_existing_room", "propose_new_room", "ignore_or_archive",
    "human_review",
)

# All seven must hold to propose a new Room.
NEW_ROOM_EVIDENCE = (
    "meaningful_objective", "bounded_scope", "identifiable_participants",
    "next_coordination_need", "proposed_completion_condition",
    "no_strong_existing_room_match", "authority_or_review",
)


def _new_room_ready(sig: dict[str, Any]) -> tuple[bool, list[str]]:
    missing = [k for k in NEW_ROOM_EVIDENCE if not sig.get(k)]
    return (not missing, missing)


def dispose(signals: dict[str, Any], *, recommended: str | None = None) -> dict[str, Any]:
    """Deterministic disposition. `signals` are extracted facts; `recommended`
    is the model's suggestion (validated, may be overridden). Records rule+evidence."""
    # Ordered rules — FIRST match wins. Each returns (disposition, rule, evidence).
    disp = rule = None
    evidence: dict[str, Any] = {}

    if signals.get("is_bulk") or signals.get("is_notification"):
        disp, rule = "ignore_or_archive", "bulk/notification -> archive"
        evidence = {"is_bulk": signals.get("is_bulk"), "is_notification": signals.get("is_notification")}
    elif signals.get("conflicting_intents"):
        disp, rule = "human_review", "conflicting intent signals -> human review"
        evidence = {"conflicting_intents": True}
    elif signals.get("ambiguous"):
        disp, rule = "needs_clarification", "ambiguous intent -> clarify"
        evidence = {"ambiguous": True}
    elif signals.get("matches_existing_room"):
        disp, rule = "attach_to_existing_room", "matches existing objective -> attach"
        evidence = {"room_id": signals.get("matches_existing_room")}
    elif signals.get("objective_multistep"):
        ready, missing = _new_room_ready(signals)
        if ready:
            disp, rule = "propose_new_room", "multi-step objective + full room evidence -> propose room"
            evidence = {"new_room_evidence": {k: signals.get(k) for k in NEW_ROOM_EVIDENCE}}
        elif missing == ["authority_or_review"]:
            disp, rule = "human_review", "room-worthy but lacks authority -> human review"
            evidence = {"missing": missing}
        else:
            disp, rule = "needs_clarification", "multi-step but insufficient room evidence -> clarify"
            evidence = {"missing": missing}
    elif signals.get("is_scheduling") or signals.get("is_single_step_action") or signals.get("is_question"):
        disp, rule = "create_action_candidate", "actionable single step/question -> action candidate (NOT room)"
        evidence = {k: signals.get(k) for k in ("is_scheduling", "is_single_step_action", "is_question")}
    else:
        disp, rule = "observe_only", "no actionable/coordination signal -> observe"
        evidence = {}

    result = {
        "disposition": disp,
        "kernel_rule": rule,
        "evidence": evidence,
        "creates_room": disp == "propose_new_room",  # PROPOSAL only, never live
        "side_effects": "NONE",
        "source_event_ids": signals.get("source_event_ids", []),
    }
    if recommended is not None and recommended != disp:
        result["model_recommended"] = recommended
        result["kernel_overrode"] = True
        result["override_reason"] = f"kernel rule '{rule}' outranks model suggestion '{recommended}'"
    elif recommended is not None:
        result["model_recommended"] = recommended
        result["kernel_overrode"] = False
    return result
