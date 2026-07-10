#!/usr/bin/env python3
"""Conversation OS — shadow-only projections from an Event.

Event → identity candidate → Conversation projection → intent proposal.

STRICTLY shadow: every output is a *candidate*/*proposal* with no side effects.
NO Room creation, NO outbound, NO Brain sync, NO knowledge promotion. These are
disposable projections — rebuildable by replaying the Event stream. If a later
gate (durability + privacy, per EMAIL_ARCHITECTURE §5b) approves, only THEN does
anything persist beyond here. Not in this module.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

# Tiny, transparent intent heuristics — a PROPOSAL only, never an action.
_INTENT_RULES = [
    ("scheduling", re.compile(r"\b(meet|call|schedule|calendar|avail|time)\b", re.I)),
    ("support", re.compile(r"\b(help|issue|problem|broken|error|bug)\b", re.I)),
    ("sales_inquiry", re.compile(r"\b(price|quote|buy|demo|interested|plan)\b", re.I)),
    ("test_signal", re.compile(r"\b(test|wire|synthetic|hello)\b", re.I)),
]


def identity_candidate(event: dict[str, Any]) -> dict[str, Any]:
    """Propose an identity from the sender — CANDIDATE only, not resolved/promoted."""
    p = event["payload"]
    frm = (p.get("from") or "").strip()
    domain = p.get("sender_identity") or (frm.split("@")[-1] if "@" in frm else None)
    # stable candidate id so the same sender maps consistently (no PII stored here)
    cand_id = "id-" + hashlib.sha256((frm or domain or "unknown").encode()).hexdigest()[:12]
    return {
        "candidate_id": cand_id,
        "resolved": False,          # never auto-resolve in shadow
        "signals": {"email_domain": domain, "has_address": bool(frm)},
        "confidence": 0.4 if domain else 0.1,
        "note": "candidate only — requires resolution gate before it becomes an identity",
    }


def conversation_projection(event: dict[str, Any], identity: dict[str, Any]) -> dict[str, Any]:
    """Project a Conversation from thread/participants — a disposable view."""
    p = event["payload"]
    thread = p.get("thread_id") or event["event_id"]  # new thread if none
    conv_id = "conv-" + hashlib.sha256(str(thread).encode()).hexdigest()[:12]
    return {
        "conversation_id": conv_id,
        "thread_ref": thread,
        "participants": [identity["candidate_id"]],
        "receiving_identity": p.get("sender_identity"),
        "event_ids": [event["event_id"]],
        "state": "observed",        # not a Room — a projection
        "rebuildable_from_stream": True,
    }


def intent_proposal(event: dict[str, Any]) -> dict[str, Any]:
    """Propose an intent from subject/labels — PROPOSAL only, no routing/action."""
    p = event["payload"]
    hay = " ".join(str(p.get(k) or "") for k in ("subject",)) + " " + " ".join(p.get("labels", []))
    matched = [name for name, rx in _INTENT_RULES if rx.search(hay)]
    top = matched[0] if matched else "unclassified"
    return {
        "proposed_intent": top,
        "alternates": matched[1:],
        "confidence": 0.5 if matched else 0.15,
        "action_taken": None,       # explicitly none — shadow
        "note": "proposal only — no Intent Room, no routing, no reply",
    }


def project(event: dict[str, Any]) -> dict[str, Any]:
    ident = identity_candidate(event)
    conv = conversation_projection(event, ident)
    intent = intent_proposal(event)
    return {
        "source_event_id": event["event_id"],
        "source_trace_id": event.get("trace_id"),
        "identity_candidate": ident,
        "conversation_projection": conv,
        "intent_proposal": intent,
        "side_effects": "NONE (no room / reply / brain / promotion)",
    }
