#!/usr/bin/env python3
"""Conversation OS — the 6-layer unified digest (SHADOW / read-only render).

Consumes canonical Conversation items (each already folded from immutable Events
and passed through `intent_disposition.dispose`) and buckets them into the six
James-facing layers. Pure function: no I/O, no sending, no Brain writes.

Layers (James, 2026-07-11), in scan-priority order:
  1. Needs James        — judgment / relationship / personal voice required
  2. Ready to Approve   — a reply is drafted, awaiting his approval to send
  3. AI Can Handle      — low-risk prep that can be readied without sending
  4. Waiting on Others  — our commitments / unanswered asks / follow-ups
  5. FYI                — useful info, no action
  6. Active Objectives  — messages attached to an existing Intent Room

Cross-channel dedup: items sharing (person, thread_key) collapse to one row that
lists every channel it arrived on. Every row keeps a source identifier so James
can jump to the original message.
"""
from __future__ import annotations

from typing import Any

LAYERS = (
    "needs_james", "ready_to_approve", "ai_can_handle",
    "waiting_on_others", "fyi", "active_objectives",
)
LAYER_TITLES = {
    "needs_james": "Needs James",
    "ready_to_approve": "Ready to Approve",
    "ai_can_handle": "AI Can Handle",
    "waiting_on_others": "Waiting on Others",
    "fyi": "FYI",
    "active_objectives": "Active Objectives",
}


def _layer_for(item: dict[str, Any]) -> str:
    """Deterministic disposition -> layer mapping. Kernel signals win; an item
    already attached to a Room is an Active Objective regardless of disposition."""
    disp = item.get("disposition")
    sig = item.get("signals", {})

    if disp in ("attach_to_existing_room", "propose_new_room") or item.get("room_id"):
        return "active_objectives"
    if item.get("draft_reply"):            # an outbound draft exists -> approve gate
        return "ready_to_approve"
    if disp in ("human_review", "needs_clarification"):
        return "needs_james"
    if sig.get("awaiting_other") or sig.get("is_commitment") or sig.get("is_followup"):
        return "waiting_on_others"
    if disp == "create_action_candidate":
        return "ai_can_handle"
    # observe_only / ignore_or_archive / anything else -> informational
    return "fyi"


def _dedup_key(item: dict[str, Any]) -> str:
    person = (item.get("person") or item.get("from") or "unknown").strip().lower()
    thread = (item.get("thread_key") or item.get("subject") or item.get("conversation_id") or "").strip().lower()
    return f"{person}::{thread}"


_URG_RANK = {"high": 0, "normal": 1, "low": 2}


def build_digest(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold Conversation items into the 6 layers with cross-channel dedup.
    Fully order-independent: layer escalates to the most James-demanding, urgency
    to the highest, and channels/sources are sorted before render."""
    merged: dict[str, dict[str, Any]] = {}
    for it in items:
        k = _dedup_key(it)
        row = merged.get(k)
        chan = it.get("channel") or "unknown"
        src = it.get("source_ref") or it.get("message_id") or it.get("conversation_id") or "?"
        if row is None:
            merged[k] = {
                "person": it.get("person") or it.get("from") or "unknown",
                "context": it.get("context") or it.get("subject") or "",
                "channels": {chan},
                "layer": _layer_for(it),
                "sources": {src},
                "urgency": it.get("urgency", "normal"),
                "draft_reply": it.get("draft_reply"),
                "room_id": it.get("room_id"),
            }
        else:
            row["channels"].add(chan)
            row["sources"].add(src)
            row["context"] = row["context"] or (it.get("context") or it.get("subject") or "")
            row["draft_reply"] = row["draft_reply"] or it.get("draft_reply")
            row["room_id"] = row["room_id"] or it.get("room_id")
            # escalate layer to the more James-demanding of the two (lower index wins)
            if LAYERS.index(_layer_for(it)) < LAYERS.index(row["layer"]):
                row["layer"] = _layer_for(it)
            # escalate urgency to the highest seen
            if _URG_RANK.get(it.get("urgency", "normal"), 1) < _URG_RANK.get(row["urgency"], 1):
                row["urgency"] = it.get("urgency", "normal")

    layers: dict[str, list[dict[str, Any]]] = {L: [] for L in LAYERS}
    for row in merged.values():
        row["channels"] = sorted(row["channels"])
        row["sources"] = sorted(row["sources"])
        layers[row["layer"]].append(row)
    for L in LAYERS:
        layers[L].sort(key=lambda r: (str(r["person"]).lower(), str(r["sources"][0])))

    return {
        "layers": layers,
        "counts": {L: len(layers[L]) for L in LAYERS},
        "total": len(merged),
        "outbound_sent": 0,          # invariant: digest NEVER sends
        "brain_writes": 0,           # invariant: digest NEVER promotes
    }


def render_telegram(digest: dict[str, Any]) -> str:
    """Compact Telegram-friendly text. Skips empty layers. Source id per row."""
    URG = {"high": "🔴", "normal": "", "low": ""}
    out: list[str] = ["📥 *Unified Comms Digest* (shadow · read-only)"]
    for L in LAYERS:
        rows = digest["layers"][L]
        if not rows:
            continue
        out.append(f"\n*{LAYER_TITLES[L]}* ({len(rows)})")
        for r in rows:
            chans = "/".join(r["channels"])
            urg = URG.get(r.get("urgency", "normal"), "")
            ctx = f" — {r['context']}" if r["context"] else ""
            out.append(f"  {urg}• {r['person']} [{chans}]{ctx}  ⟨{r['sources'][0]}⟩")
    if digest["total"] == 0:
        out.append("\n_(no messages in window)_")
    out.append(f"\n_sent this run: {digest['outbound_sent']} · brain writes: {digest['brain_writes']}_")
    return "\n".join(out)


if __name__ == "__main__":  # pragma: no cover
    import json, sys
    items = json.load(sys.stdin)
    d = build_digest(items)
    print(render_telegram(d))
    print("\n" + json.dumps(d["counts"]))
