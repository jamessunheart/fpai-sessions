#!/usr/bin/env python3
"""Verb router — James's word is the signature (Standing Policy P3).

Reads new Telegram-inbox messages and matches each against the open
human-edge gates' verbs. An exact, unambiguous verb answers its gate;
anything else is left alone. Answering a gate only RECORDS the decision —
execution still walks the Reserved-Class path.

Fail-safes (Rung 0 doctrine):
- exact match only (whole message, case-insensitive, trimmed)
- a verb matching >1 open gate is ambiguous → skipped, logged, never guessed
- cursor file prevents double-processing; an answered gate can't re-answer
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.queue.build import answer_gate, load_queue, open_gates_from_data

INBOX = Path(os.environ.get("FPAI_TG_INBOX",
                            Path.home() / ".config/fpai/tg_inbox/messages.jsonl"))
CURSOR = Path(os.environ.get("FPAI_VERB_CURSOR",
                             Path.home() / ".config/fpai/tg_inbox/verb_router_cursor.txt"))
LOG = Path(os.environ.get("FPAI_VERB_LOG",
                          Path.home() / ".config/fpai/tg_inbox/verb_router_log.jsonl"))


def _read_cursor() -> int:
    try:
        return int(CURSOR.read_text().strip())
    except (OSError, ValueError):
        return 0


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split()).strip("\"'`“”.!")


def route(queue_path: Path | str | None = None,
          inbox: Path | str = INBOX,
          cursor_path: Path | str = CURSOR,
          log_path: Path | str = LOG) -> list[dict]:
    """Process new inbox messages; return the actions taken (answered/ambiguous)."""
    inbox, cursor_path, log_path = Path(inbox), Path(cursor_path), Path(log_path)
    if not inbox.exists():
        return []
    last_id = int(cursor_path.read_text().strip()) if cursor_path.exists() else 0
    actions: list[dict] = []
    max_id = last_id
    for line in inbox.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        uid = int(msg.get("update_id", 0))
        if uid <= last_id:
            continue
        max_id = max(max_id, uid)
        text = _normalize(str(msg.get("text", "")))
        if not text or len(text) > 60:  # verbs are short; long messages are conversation
            continue
        # match against gates fresh each message — an answer may close a gate mid-batch
        gates = open_gates_from_data(load_queue(queue_path))
        hits = [g for g in gates if text in {_normalize(v) for v in g["verbs"]}]
        if len(hits) == 1:
            gate = hits[0]
            verb = next(v for v in gate["verbs"] if _normalize(v) == text)
            answer_gate(gate["id"], verb, queue_path)
            actions.append({"action": "answered", "gate": gate["id"], "verb": verb,
                            "update_id": uid, "at": dt.datetime.now().isoformat(timespec="seconds")})
        elif len(hits) > 1:
            actions.append({"action": "ambiguous", "verb": text,
                            "gates": [g["id"] for g in hits], "update_id": uid,
                            "at": dt.datetime.now().isoformat(timespec="seconds")})
    if max_id > last_id:
        cursor_path.parent.mkdir(parents=True, exist_ok=True)
        cursor_path.write_text(str(max_id))
    if actions:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as fh:
            for a in actions:
                fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    return actions


def main() -> int:
    actions = route()
    answered = [a for a in actions if a["action"] == "answered"]
    ambiguous = [a for a in actions if a["action"] == "ambiguous"]
    print(f"verb_router: answered={len(answered)} ambiguous={len(ambiguous)}")
    for a in answered:
        print(f"  ✓ {a['gate']} ← \"{a['verb']}\"")
    for a in ambiguous:
        print(f"  ⚠ \"{a['verb']}\" matches {len(a['gates'])} gates — left for James to disambiguate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
