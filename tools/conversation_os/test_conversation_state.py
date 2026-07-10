#!/usr/bin/env python3
"""Multi-Event Conversation merging + Shared State + promotion-boundary tests.

Synthetic Events only. No network. Proves merging, separation, dedup,
out-of-order convergence, replay determinism, candidate identity, evolving
intent with retained history, and the inert two-gate promotion contract.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conversation_state as cs
import promotion_boundary as pb


def ev(eid, mid, thread, subj, occurred, sender="alice@ex.invalid"):
    return {
        "event_id": eid, "occurred_at": occurred, "dedup_key": f"dk-{mid}",
        "schema_version": "1.0", "source": "test", "type": "email.received",
        "trace_id": f"tr-{eid}",
        "payload": {"message_id": mid, "thread_id": thread, "subject": subj,
                    "from": sender, "labels": ["inbound"], "thread_id_raw": thread},
    }


def build():
    # Thread T1: 3 messages, intent evolves test_signal -> scheduling -> sales_inquiry
    m1 = ev("e1", "<m1>", None,  "hello from the wire", "2026-07-10T18:00:00Z")
    m2 = ev("e2", "<m2>", "<m1>", "can we schedule a call?", "2026-07-10T18:05:00Z")
    m3 = ev("e3", "<m3>", "<m1>", "actually about pricing and a demo", "2026-07-10T18:10:00Z")
    # Unrelated message, SAME sender, different thread
    m9 = ev("e9", "<m9>", None, "unrelated: server help needed", "2026-07-10T18:07:00Z")
    dup = ev("e2b", "<m2>", "<m1>", "can we schedule a call?", "2026-07-10T18:05:00Z")  # same dedup_key
    return [m1, m2, m3, m9, dup]


def run_conversations():
    m1, m2, m3, m9, dup = build()
    ordered = [m1, m2, m3, m9, dup]
    convs = cs.reduce(ordered)

    t1 = "conv-" + __import__("hashlib").sha256(b"<m1>").hexdigest()[:12]
    t9 = "conv-" + __import__("hashlib").sha256(b"<m9>").hexdigest()[:12]

    # merging: 3 thread msgs (+dup collapsed) -> ONE conversation with 3 facts
    assert set(convs) == {t1, t9}, f"expected 2 conversations, got {set(convs)}"
    assert len(convs[t1]["observed_facts"]) == 3, "dup must not add a fact"
    assert len(convs[t1]["source_event_ids"]) == 3, "dedup by dedup_key"
    # separation: unrelated stays separate
    assert len(convs[t9]["observed_facts"]) == 1, "unrelated separate"
    assert convs[t9]["current_intent_proposal"]["proposed_intent"] == "support"
    # intent evolution WITH retained history
    hist = [h["proposed_intent"] for h in convs[t1]["interpretations"]["intent_history"]]
    assert hist == ["test_signal", "scheduling", "sales_inquiry"], hist
    assert convs[t1]["current_intent_proposal"]["proposed_intent"] == "sales_inquiry"
    assert all("source_event_id" in h for h in convs[t1]["interpretations"]["intent_history"])
    # LAYERED identity: repetition proves CHANNEL stability, NEVER human resolution
    id1 = convs[t1]["interpretations"]["identity"]
    id9 = convs[t9]["interpretations"]["identity"]
    assert id1["channel_identity_stable"] is True, "3 obs -> stable channel"
    assert id1["entity_resolved"] is False, "repetition must NOT resolve a human"
    assert id1["entity_link_proposed"] is True, "may propose a link (unverified)"
    assert id9["channel_identity_stable"] is False, "1 obs -> not stable"
    assert id9["entity_resolved"] is False
    # unresolved question retained with source id
    assert convs[t1]["unresolved_questions"][0]["source_event_id"] == "e2"

    # out-of-order convergence + replay determinism from empty
    h_ordered = cs.state_hash(convs)
    rng = random.Random(42)
    for _ in range(5):
        shuffled = ordered[:]
        rng.shuffle(shuffled)
        assert cs.state_hash(cs.reduce(shuffled)) == h_ordered, "order-independent + replay-identical"

    return convs, h_ordered, hist


def run_promotion():
    base = dict(source_event_id="e1", source_conversation_id="conv-x")
    cases = {
        # PRIVATE alone must NOT promote
        "private_but_candidate": pb.MemoryCandidate(
            "x", "candidate", "inferred", "PRIVATE", **base),
        # durable + confirmed + approved -> promoted (even though PRIVATE)
        "durable_confirmed_approved_private": pb.MemoryCandidate(
            "x", "durable", "user-confirmed", "PRIVATE", approval_actor="james", **base),
        # PUBLIC but unverified -> rejected
        "public_but_inferred": pb.MemoryCandidate(
            "x", "durable", "inferred", "PUBLIC", approval_policy="auto", **base),
        # durable + reality-proven but NO approval -> rejected
        "durable_proven_no_approval": pb.MemoryCandidate(
            "x", "durable", "reality-proven", "COUNCIL", **base),
    }
    out = {k: pb.evaluate(v) for k, v in cases.items()}
    assert out["private_but_candidate"]["result"] == "rejected"
    assert out["durable_confirmed_approved_private"]["result"] == "knowledge.promoted"
    assert out["durable_confirmed_approved_private"]["audience"] == "PRIVATE"  # travels, didn't gate
    assert out["public_but_inferred"]["result"] == "rejected"
    assert out["durable_proven_no_approval"]["result"] == "rejected"
    # audience never causes promotion on its own
    assert all(o["result"] == "rejected" or o["inert"] is True for o in out.values())
    return out


if __name__ == "__main__":
    convs, h, hist = run_conversations()
    promo = run_promotion()
    print("ALL CONVERSATION + PROMOTION TESTS PASS")
    print("shared_state_hash:", h[:16], "…")
    print("intent_evolution:", hist)
    print("promotion_results:", {k: v["result"] for k, v in promo.items()})
