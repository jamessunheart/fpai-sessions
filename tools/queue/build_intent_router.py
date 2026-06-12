#!/usr/bin/env python3
"""Build-intent router — James speaks intent, the system builds (Ember-as-builder).

Companion to verb_router.py. The verb router handles SHORT exact verbs (gate answers).
This router handles messages that start with `build:` — James's plain-language build
requests from Telegram. It does NOT build directly; it captures the intent into
core/BUILD/intents/ so Ember can draft a spec → run Codex → review → reply.

Pattern (Ember-as-builder, per James 2026-06-11):
  James (Telegram):  "build: a daily report that emails me the treasury balance"
        → this router writes core/BUILD/intents/<id>-<slug>.md  (status: open)
        → Ember picks it up, drafts core/BUILD/specs/NNN-<slug>.md
        → run_codex.sh builds it in an isolated worktree
        → Ember reviews, replies in-thread: "built, tests green, merge? ⚡"

Fail-safes (Rung 0 doctrine):
- only messages whose normalized text starts with the `build:` trigger are captured
- own cursor (separate from verb_router) so the two lanes never collide
- capture only — NOTHING is built, merged, or sent from here; Reserved-Class preserved
- idempotent: an update_id at/below the cursor is never re-captured
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

INBOX = Path(os.environ.get("FPAI_TG_INBOX",
                            Path.home() / ".config/fpai/tg_inbox/messages.jsonl"))
CURSOR = Path(os.environ.get("FPAI_BUILD_INTENT_CURSOR",
                             Path.home() / ".config/fpai/tg_inbox/build_intent_cursor.txt"))
INTENTS_DIR = Path(os.environ.get("FPAI_BUILD_INTENTS_DIR",
                                  REPO_ROOT / "core" / "BUILD" / "intents"))
TRIGGER = "build:"


def _slug(text: str, n: int = 6) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:n]) or "intent"


def capture(inbox: Path | str = INBOX,
            cursor_path: Path | str = CURSOR,
            intents_dir: Path | str = INTENTS_DIR) -> list[dict]:
    """Scan new inbox messages; capture `build:` intents. Return what was captured."""
    inbox, cursor_path, intents_dir = Path(inbox), Path(cursor_path), Path(intents_dir)
    if not inbox.exists():
        return []
    last_id = int(cursor_path.read_text().strip()) if cursor_path.exists() else 0
    captured: list[dict] = []
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
        raw = str(msg.get("text", "")).strip()
        if not raw.lower().startswith(TRIGGER):
            continue
        intent = raw[len(TRIGGER):].strip()
        if not intent:
            continue
        when = dt.datetime.now().isoformat(timespec="seconds")
        path = intents_dir / f"{uid}-{_slug(intent)}.md"
        intents_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            "status: open\n"
            "source: telegram\n"
            f"update_id: {uid}\n"
            f"received: {when}\n"
            "---\n\n"
            f"{intent}\n",
            encoding="utf-8",
        )
        captured.append({"update_id": uid, "intent": intent, "file": str(path), "at": when})
    if max_id > last_id:
        cursor_path.parent.mkdir(parents=True, exist_ok=True)
        cursor_path.write_text(str(max_id))
    return captured


def main() -> int:
    got = capture()
    print(f"build_intent_router: captured={len(got)}")
    for g in got:
        print(f"  + {Path(g['file']).name}: {g['intent'][:70]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
