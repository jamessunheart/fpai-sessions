#!/usr/bin/env python3
"""Shadow Room lifecycle proof set — 14 scenarios + replay determinism.

Synthetic Events only. No side effects. Proves Event-driven transitions,
actor/source retention, idempotency, proof-gated completion, invalid-transition
rejection, inert closure whitelist, and byte-identical replay.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import room_lifecycle as rl
import intent_disposition as idsp
import identity_layers as il

_seq = 0


def e(etype, t, actor="system", **payload):
    global _seq
    _seq += 1
    eid = f"re{_seq}"
    payload.setdefault("room_key", "K1")
    return {"event_id": eid, "type": etype, "actor": actor,
            "occurred_at": t, "dedup_key": f"dk-{etype}-{t}", "payload": payload}


def full_lifecycle():
    return [
        e("propose_room", "2026-07-10T18:00:00Z", objective="ship X (multi-step)",
          owner_candidates=["ownerA"], completion_condition="X deployed + verified"),
        e("request_approval", "2026-07-10T18:01:00Z"),
        e("approve", "2026-07-10T18:02:00Z", actor="james"),
        e("attach_conversation_event", "2026-07-10T18:03:00Z"),
        e("add_action_candidate", "2026-07-10T18:04:00Z", action="do step 1"),
        e("blocker_raised", "2026-07-10T18:05:00Z", blocker="waiting on dep"),
        e("blocker_cleared", "2026-07-10T18:06:00Z"),
        e("claim_completion", "2026-07-10T18:07:00Z"),
        e("attach_proof", "2026-07-10T18:08:00Z", proof_valid=False),           # insufficient
        e("attach_proof", "2026-07-10T18:09:00Z", proof_valid=True, outcome="X live"),
        e("close", "2026-07-10T18:10:00Z", actor="james", learning_candidates=[
            {"class": "verified_decision", "text": "chose approach A"},
            {"class": "model_interpretation", "text": "seemed urgent"},   # ineligible
        ]),
    ]


def run():
    evs = full_lifecycle()

    # 1 proposed
    assert rl.reduce_room(evs[:1])["state"] == "proposed"
    # 2 missing authority -> awaiting_approval
    assert rl.reduce_room(evs[:2])["state"] == "awaiting_approval"
    # 3 approved -> active
    assert rl.reduce_room(evs[:3])["state"] == "active"
    # 4 related conversation event attached
    r4 = rl.reduce_room(evs[:4])
    assert r4["state"] == "active" and len(r4["observed_events"]) == 1
    # 5 action candidate tracked WITHOUT a new Room (disposition-level)
    d5 = idsp.dispose(dict(is_scheduling=True, source_event_ids=["s"]))
    assert d5["disposition"] == "create_action_candidate" and d5["creates_room"] is False
    # 6 blocker -> blocked
    assert rl.reduce_room(evs[:6])["state"] == "blocked"
    # 7 cleared -> active
    assert rl.reduce_room(evs[:7])["state"] == "active"
    # 8 completion claimed w/o valid proof -> stays completion_proposed
    r8 = rl.reduce_room(evs[:9])   # includes the INVALID proof
    assert r8["state"] == "completion_proposed", r8["state"]
    assert any("insufficient" in x["reason"] for x in r8["rejected_transitions"])
    # 9 valid proof -> completed
    assert rl.reduce_room(evs[:10])["state"] == "completed"
    # 10 closure records outcome + filtered learning candidates
    r10 = rl.reduce_room(evs)
    assert r10["state"] == "closed"
    assert r10["verified_outcome"] == "X live"
    lc = r10["learning_candidates"]
    assert [c["class"] for c in lc] == ["verified_decision"], "ineligible class filtered"
    assert lc[0]["written_to_brain"] is False and "approval" in lc[0]["pending_gates"]
    # 11 duplicate + out-of-order -> deterministic
    base_hash = rl.room_hash(rl.reduce_room(evs))
    rng = random.Random(7)
    for _ in range(5):
        shuffled = evs + [evs[3], evs[6]]  # inject duplicates
        rng.shuffle(shuffled)
        assert rl.room_hash(rl.reduce_room(shuffled)) == base_hash, "dup/out-of-order deterministic"
    # 12 invalid transition -> rejected + audited, state unchanged
    bad = [evs[0], e("claim_completion", "2026-07-10T18:00:30Z")]  # claim while proposed
    r12 = rl.reduce_room(bad)
    assert r12["state"] == "proposed"
    assert any("invalid/skipped" in x["reason"] for x in r12["rejected_transitions"])
    # 13 rejected proposal never becomes active
    rej = [evs[0], e("reject", "2026-07-10T18:00:30Z", actor="james"),
           e("approve", "2026-07-10T18:00:40Z", actor="james")]
    r13 = rl.reduce_room(rej)
    assert r13["state"] == "rejected", r13["state"]
    # 14 replay from empty identical
    assert rl.room_hash(rl.reduce_room(list(reversed(evs)))) == base_hash

    # identity cross-channel refinement: 2 verified channels alone != verified link
    two = il.assess("a@x.invalid", 1, evidence=il.DeterministicEvidence(
        verified_contact_match=True, verified_channels=frozenset({"email", "telegram"})))
    assert two["cross_channel_link_proposed"] is True
    assert two["cross_channel_link_verified"] is False, "2 channels != same human without linkage"
    linked = il.assess("a@x.invalid", 1, evidence=il.DeterministicEvidence(
        verified_contact_match=True, verified_channels=frozenset({"email", "telegram"}),
        explicit_channel_linkage=True))
    assert linked["cross_channel_link_verified"] is True

    print("ALL ROOM-LIFECYCLE + IDENTITY-CROSS-CHANNEL TESTS PASS")
    print("final state:", r10["state"], "| outcome:", r10["verified_outcome"])
    print("learning_candidates:", [c["class"] for c in lc], "| written_to_brain:", lc[0]["written_to_brain"])
    print("room_hash:", base_hash[:16], "…")


if __name__ == "__main__":
    run()
