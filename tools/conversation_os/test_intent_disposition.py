#!/usr/bin/env python3
"""Shadow proof set for the Intent Disposition Gate + layered identity.

Deterministic. No network, no side effects. Covers the 8 required disposition
scenarios, replay/order-independence, and the identity-resolution correction.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import intent_disposition as idsp
import identity_layers as il

FULL_ROOM = {k: True for k in idsp.NEW_ROOM_EVIDENCE}

SCENARIOS = {
    # 1 newsletter/notification -> archive
    "newsletter": (dict(is_notification=True, source_event_ids=["n1"]), "ignore_or_archive"),
    # 2 simple factual question -> action candidate (NOT room)
    "factual_question": (dict(is_question=True, source_event_ids=["q1"]), "create_action_candidate"),
    # 3 scheduling request -> action candidate, not room
    "scheduling": (dict(is_scheduling=True, source_event_ids=["s1"]), "create_action_candidate"),
    # 4 belongs to existing objective -> attach
    "existing_objective": (dict(matches_existing_room="conv-abc", source_event_ids=["a1"]),
                           "attach_to_existing_room"),
    # 5 new multi-step objective w/ full evidence -> propose room
    "new_objective": ({**FULL_ROOM, "objective_multistep": True, "source_event_ids": ["r1"]},
                      "propose_new_room"),
    # 6 ambiguous -> clarification
    "ambiguous": (dict(ambiguous=True, source_event_ids=["c1"]), "needs_clarification"),
    # 7 conflicting -> human review
    "conflicting": (dict(conflicting_intents=True, source_event_ids=["h1"]), "human_review"),
    # extra: room-worthy but no authority -> human review
    "room_no_authority": ({**FULL_ROOM, "authority_or_review": False,
                           "objective_multistep": True, "source_event_ids": ["r2"]}, "human_review"),
}


def run_dispositions():
    out = {}
    for name, (sig, expected) in SCENARIOS.items():
        d = idsp.dispose(sig)
        assert d["disposition"] == expected, f"{name}: {d['disposition']} != {expected}"
        assert d["side_effects"] == "NONE"
        assert d["source_event_ids"] == sig["source_event_ids"], "retains source Event IDs"
        assert d["kernel_rule"], "records the rule that fired"
        out[name] = d
    # only ONE scenario proposes a Room
    rooms = [n for n, d in out.items() if d["creates_room"]]
    assert rooms == ["new_objective"], rooms

    # kernel overrides a wrong model recommendation, records it
    ov = idsp.dispose(dict(is_notification=True, source_event_ids=["x"]),
                      recommended="propose_new_room")
    assert ov["disposition"] == "ignore_or_archive" and ov["kernel_overrode"] is True

    # 8 replay / order-independence: dict-driven disposition is pure -> identical
    import json
    a = json.dumps({n: idsp.dispose(s) for n, (s, _) in SCENARIOS.items()}, sort_keys=True)
    b = json.dumps({n: idsp.dispose(s) for n, (s, _) in reversed(list(SCENARIOS.items()))},
                   sort_keys=True)
    assert a == b, "disposition is order-independent / replay-identical"
    return out, rooms


def run_identity():
    # repetition -> stable channel, NEVER resolved
    rep = il.assess("alice@ex.invalid", observation_count=5)
    assert rep["channel_identity_stable"] is True
    assert rep["entity_resolved"] is False, "repetition must never resolve a human"
    assert rep["entity_link_proposed"] is True
    # deterministic evidence -> resolves
    ev = il.assess("alice@ex.invalid", observation_count=1,
                   evidence=il.DeterministicEvidence(explicit_human_confirmation=True))
    assert ev["entity_resolved"] is True
    assert "explicit_human_confirmation" in ev["resolving_evidence"]
    # cross-channel: 2 verified channels alone only PROPOSES; needs explicit linkage
    cc = il.assess("alice@ex.invalid", 1,
                   evidence=il.DeterministicEvidence(
                       verified_contact_match=True,
                       verified_channels=frozenset({"email", "telegram"}),
                       explicit_channel_linkage=True))
    assert cc["cross_channel_link_verified"] is True
    return rep, ev, cc


if __name__ == "__main__":
    out, rooms = run_dispositions()
    rep, ev, cc = run_identity()
    print("ALL DISPOSITION + IDENTITY-LAYER TESTS PASS")
    print("dispositions:", {n: d["disposition"] for n, d in out.items()})
    print("proposes_room:", rooms)
    print("identity: repetition_resolved =", rep["entity_resolved"],
          "| evidence_resolved =", ev["entity_resolved"],
          "| cross_channel =", cc["cross_channel_link_verified"])
