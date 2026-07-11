#!/usr/bin/env python3
"""Tests for the 6-layer unified digest — layer mapping, cross-channel dedup, invariants."""
from digest import build_digest, render_telegram, LAYERS

SAMPLE = [
    # same person, two channels, same thread -> must collapse to ONE row
    {"person": "Rayaan", "channel": "whatsapp", "thread_key": "eng-recruit",
     "context": "Engineer recruitment", "disposition": "human_review",
     "source_ref": "wa:msg-1", "urgency": "high"},
    {"person": "Rayaan", "channel": "email", "thread_key": "eng-recruit",
     "context": "Engineer recruitment", "disposition": "human_review",
     "source_ref": "gmail:thr-9"},
    # drafted reply -> Ready to Approve
    {"person": "Ana", "channel": "email", "thread_key": "invoice-may",
     "context": "May invoice", "disposition": "create_action_candidate",
     "draft_reply": "Paid — receipt attached.", "source_ref": "gmail:thr-3"},
    # single-step actionable, no draft -> AI Can Handle
    {"person": "Booking", "channel": "email", "thread_key": "cal-hold",
     "disposition": "create_action_candidate", "source_ref": "gmail:thr-4"},
    # awaiting other -> Waiting on Others
    {"person": "Vendor", "channel": "email", "thread_key": "quote",
     "disposition": "observe_only", "signals": {"awaiting_other": True},
     "source_ref": "gmail:thr-5"},
    # bulk/notification -> FYI
    {"person": "Newsletter", "channel": "email", "thread_key": "weekly",
     "disposition": "ignore_or_archive", "source_ref": "gmail:thr-6"},
    # attached to a room -> Active Objectives
    {"person": "James", "channel": "email", "thread_key": "mailsac",
     "disposition": "attach_to_existing_room", "room_id": "room-d315e6011119",
     "source_ref": "gmail:thr-7"},
]


def test_layers_and_dedup():
    d = build_digest(SAMPLE)
    # Rayaan collapsed across whatsapp+email into ONE Needs-James row
    nj = d["layers"]["needs_james"]
    assert len(nj) == 1, nj
    assert set(nj[0]["channels"]) == {"whatsapp", "email"}
    assert len(nj[0]["sources"]) == 2
    assert nj[0]["urgency"] == "high"  # high urgency preserved from either channel

    assert d["counts"]["ready_to_approve"] == 1     # Ana (drafted)
    assert d["counts"]["ai_can_handle"] == 1        # Booking
    assert d["counts"]["waiting_on_others"] == 1    # Vendor
    assert d["counts"]["fyi"] == 1                  # Newsletter
    assert d["counts"]["active_objectives"] == 1    # James/room
    assert d["total"] == 6                          # 7 items -> 6 rows after dedup


def test_invariants_never_send_or_promote():
    d = build_digest(SAMPLE)
    assert d["outbound_sent"] == 0
    assert d["brain_writes"] == 0


def test_render_is_deterministic():
    a = render_telegram(build_digest(SAMPLE))
    b = render_telegram(build_digest(list(reversed(SAMPLE))))
    assert a == b, "digest render must be order-independent"


def test_empty():
    d = build_digest([])
    assert d["total"] == 0
    assert all(d["counts"][L] == 0 for L in LAYERS)


if __name__ == "__main__":
    for fn in [test_layers_and_dedup, test_invariants_never_send_or_promote,
               test_render_is_deterministic, test_empty]:
        fn(); print("PASS", fn.__name__)
    print("\n--- sample render ---")
    print(render_telegram(build_digest(SAMPLE)))
