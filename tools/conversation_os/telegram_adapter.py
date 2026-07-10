#!/usr/bin/env python3
"""Conversation OS — Telegram One Chat activation (shadow, reversible).

Reads the EXISTING live inbox (~/.config/fpai/tg_inbox/messages.jsonl, written by
tg_listen.py) into the proven spine. Does NOT touch the live bot, its cursor, or
send anything. Uses its OWN cursor so it never disturbs tg_listen. Disable flag
and full rollback (delete cursor + store) supported.

Pipeline (observe + propose ONLY):
  message -> canonical Event -> Conversation projection -> intent -> disposition.
No Rooms are created live, no replies sent, no Brain writes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from shadow_adapter import normalize_telegram, append_event, replay, Event
import conversation_state as cs
import intent_disposition as idsp
import identity_layers as il
from dataclasses import asdict

INBOX = Path.home() / ".config" / "fpai" / "tg_inbox" / "messages.jsonl"
CONVOS_DIR = Path.home() / ".config" / "fpai" / "conversation_os"
CURSOR = CONVOS_DIR / "tg_cursor.txt"        # OUR cursor — not tg_listen's
STORE = CONVOS_DIR / "telegram_events.jsonl"
DISABLE = CONVOS_DIR / ".tg_disabled"

# Authenticated channel ownership → deterministic identity (NOT repetition-based).
# James's own authenticated One Chat. chat_id is an authenticated account.
AUTHENTICATED_CHATS = {"8514069423": "James"}


def _disabled() -> bool:
    return os.environ.get("CONVOS_TG_DISABLED") == "1" or DISABLE.exists()


def _read_cursor() -> int:
    try:
        return int(CURSOR.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def ingest_new() -> list[dict[str, Any]]:
    """Read only messages newer than our cursor; ingest to our store. Idempotent."""
    if _disabled() or not INBOX.exists():
        return []
    CONVOS_DIR.mkdir(parents=True, exist_ok=True)
    cursor = _read_cursor()
    max_seen = cursor
    new_events = []
    for line in INBOX.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        uid = int(rec.get("update_id") or 0)
        if uid <= cursor:
            continue
        max_seen = max(max_seen, uid)
        ev = normalize_telegram(rec, tenant_id="james")
        written, _ = append_event(ev, STORE)
        if written:
            new_events.append(asdict(ev))
    if max_seen > cursor:
        CURSOR.write_text(str(max_seen))
    return new_events


def identity_for(event: dict[str, Any]) -> dict[str, Any]:
    """Resolve identity via authenticated channel ownership when available."""
    chat = str(event["payload"].get("from") or "")
    if chat in AUTHENTICATED_CHATS:
        ev = il.DeterministicEvidence(authenticated_ownership=True)
        layered = il.assess(f"telegram:{chat}", observation_count=1, evidence=ev)
        layered["resolved_entity"] = AUTHENTICATED_CHATS[chat]
        return layered
    return il.assess(f"telegram:{chat}", observation_count=1)


def process() -> dict[str, Any]:
    """Full shadow pass over ALL ingested Telegram Events. Observe + propose only."""
    ingest_new()
    events = replay(STORE)
    convs = cs.reduce(events)
    proposals = []
    for conv_id, st in convs.items():
        intent = (st.get("current_intent_proposal") or {}).get("proposed_intent", "unclassified")
        # map an intent into disposition signals (shadow heuristic; deterministic)
        text = (st["observed_facts"][-1]["subject"] or "") if st["observed_facts"] else ""
        sig = _signals_from(intent, text, st)
        disp = idsp.dispose(sig)
        proposals.append({"conversation_id": conv_id, "intent": intent,
                          "disposition": disp["disposition"], "creates_room": disp["creates_room"],
                          "kernel_rule": disp["kernel_rule"],
                          "source_event_ids": st["source_event_ids"]})
    return {"conversations": convs, "proposals": proposals, "event_count": len(events)}


def _signals_from(intent: str, text: str, st: dict[str, Any]) -> dict[str, Any]:
    t = (text or "").lower()
    multistep = any(w in t for w in ("project", "launch", "build", "plan", "campaign", "objective"))
    return {
        "is_notification": intent in ("test_signal",) and len(st["observed_facts"]) == 1 and "test" in t,
        "is_question": t.strip().endswith("?"),
        "is_scheduling": intent == "scheduling",
        "objective_multistep": multistep,
        "ambiguous": intent == "unclassified" and not multistep and not t.strip().endswith("?"),
        "source_event_ids": st["source_event_ids"],
        # new-Room evidence is NOT auto-satisfied — requires explicit objective framing
        "meaningful_objective": multistep, "bounded_scope": False,
        "identifiable_participants": True, "next_coordination_need": multistep,
        "proposed_completion_condition": False, "no_strong_existing_room_match": True,
        "authority_or_review": False,
    }
