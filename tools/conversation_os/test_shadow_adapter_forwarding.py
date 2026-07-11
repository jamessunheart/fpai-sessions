#!/usr/bin/env python3
"""Forwarding-safe recipient identity: Gmail auto-forward must NOT overwrite the
original recipient with the forwarding box (James, 2026-07-11)."""
from shadow_adapter import normalize_email


def test_forwarded_preserves_original_recipient():
    p = normalize_email({
        "from": "rayaan@x.com",
        "to": "james.rick.stinson@gmail.com",       # who they actually emailed
        "delivered_to": "james@fullpotential.ai",   # system inbox (forwarding box)
        "subject": "candidates", "message_id": "<a@x>",
    }).payload
    assert p["original_recipient"] == "james.rick.stinson@gmail.com"
    assert p["arrived_via"] == "james@fullpotential.ai"
    assert p["was_forwarded"] is True
    assert p["reply_as_identity"] == "james.rick.stinson@gmail.com"


def test_direct_mail_has_no_forward_chain():
    p = normalize_email({
        "from": "ana@y.com", "to": "james@fullpotential.ai",
        "subject": "invoice", "message_id": "<b@y>",
    }).payload
    assert p["original_recipient"] == "james@fullpotential.ai"
    assert p["arrived_via"] is None
    assert p["was_forwarded"] is False


if __name__ == "__main__":
    test_forwarded_preserves_original_recipient()
    test_direct_mail_has_no_forward_chain()
    print("PASS forwarding-safe recipient identity")
