#!/usr/bin/env python3
"""Conversation OS — multi-Event Conversation merging + evolving Shared State.

Pure, order-independent reducer: fold a stream of Events into Conversations,
each with a Shared State that distinguishes observed facts from model
interpretations. Deterministic — replaying the same Events in any order yields
identical Shared State (proven by a content hash).

Guarantees:
  - related Events (same thread) merge into ONE Conversation
  - unrelated Events (different thread) stay SEPARATE, even from the same sender
  - duplicate Events add no state (dedup by dedup_key)
  - out-of-order delivery converges (fold is sorted by occurred_at, event_id)
  - identity stays a CANDIDATE unless evidence resolves it
  - intent can evolve WITHOUT rewriting history (append-only intent_history)
  - every interpretation retains its source Event IDs
Shadow-only: no Rooms, replies, Brain writes, or external actions.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from shadow_projections import intent_proposal
import identity_layers


def _thread_key(event: dict[str, Any]) -> str:
    """Canonical conversation key: thread root ref, else this message's own id."""
    p = event["payload"]
    return str(p.get("thread_id") or p.get("message_id") or event["event_id"])


def _empty_state(conv_id: str, thread_key: str) -> dict[str, Any]:
    return {
        "conversation_id": conv_id,
        "thread_key": thread_key,
        "observed_facts": [],          # immutable, one per Event
        "interpretations": {           # model-derived, revisable, source-linked
            "identity": None,          # LAYERED — repetition never resolves a human
            "intent_history": [],      # append-only; never silently rewritten
        },
        "decisions": [],
        "commitments": [],
        "unresolved_questions": [],
        "current_intent_proposal": None,
        "confidence": 0.0,
        "last_meaningful_change": None,
        "source_event_ids": [],
    }


def reduce(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fold Events → {conversation_id: SharedState}. Order-independent + dedup."""
    # dedup by dedup_key — keep a DETERMINISTIC representative (min occurred_at,
    # then min event_id) so a duplicate delivered in any order yields identical
    # state. Then sort for a deterministic fold.
    by_key: dict[str, dict[str, Any]] = {}
    for e in events:
        k = e.get("dedup_key") or e["event_id"]
        cur = by_key.get(k)
        rank = (str(e.get("occurred_at") or ""), e["event_id"])
        if cur is None or rank < (str(cur.get("occurred_at") or ""), cur["event_id"]):
            by_key[k] = e
    uniq = sorted(by_key.values(), key=lambda e: (str(e.get("occurred_at") or ""), e["event_id"]))

    convs: dict[str, dict[str, Any]] = {}
    for e in uniq:
        tkey = _thread_key(e)
        conv_id = "conv-" + hashlib.sha256(tkey.encode()).hexdigest()[:12]
        st = convs.setdefault(conv_id, _empty_state(conv_id, tkey))
        p = e["payload"]

        # observed fact (immutable)
        st["observed_facts"].append({
            "event_id": e["event_id"],
            "occurred_at": e.get("occurred_at"),
            "from_domain": (p.get("from") or "").split("@")[-1] or None,
            "subject": p.get("subject"),
        })
        st["source_event_ids"].append(e["event_id"])

        # LAYERED identity — repetition advances channel stability ONLY, never
        # human/entity resolution. No deterministic evidence here -> stays unresolved.
        channel_addr = (p.get("from") or "").strip()
        st["interpretations"]["identity"] = identity_layers.assess(
            channel_addr, observation_count=len(st["source_event_ids"]))

        # intent proposal — append to history only when it changes (history never rewritten)
        prop = intent_proposal(e)
        prop["source_event_id"] = e["event_id"]
        prev = st["current_intent_proposal"]
        if prev is None or prop["proposed_intent"] != prev["proposed_intent"]:
            st["interpretations"]["intent_history"].append({
                "proposed_intent": prop["proposed_intent"],
                "confidence": prop["confidence"],
                "source_event_id": e["event_id"],
                "at": e.get("occurred_at"),
            })
            st["last_meaningful_change"] = e.get("occurred_at")
        st["current_intent_proposal"] = prop
        st["confidence"] = prop["confidence"]

        # unresolved question heuristic (retains source Event id)
        subj = (p.get("subject") or "")
        if subj.strip().endswith("?"):
            st["unresolved_questions"].append({"q": subj, "source_event_id": e["event_id"]})

    return convs


def state_hash(convs: dict[str, dict[str, Any]]) -> str:
    """Content hash of Shared State — identical iff the reduction is identical."""
    return hashlib.sha256(json.dumps(convs, sort_keys=True).encode()).hexdigest()
