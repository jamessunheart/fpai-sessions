#!/usr/bin/env python3
"""
/scene capture · v1 · 2026-05-30 · smallest working version

A CONSUMER of the existing tg_inbox (messages.jsonl), NOT a second Telegram
poller. tg_listen.py already captures every message James sends; this script
just watches that stream for `/scene ...` and does two things:

  1. Appends the scene/intention to the vault   → SCENES.md (readable memory)
  2. Replies in Telegram so James sees it landed → "🎬 Scene captured"

Why a consumer, not a poller: two scripts calling getUpdates would fight over
Telegram's update offset and drop messages. One poller (tg_listen), many
readers. This is a reader.

Usage:
  python3 scene_capture.py          # process any new /scene messages once
  python3 scene_capture.py --dry    # show what it would do, no writes/sends
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
CREDS_FILE = HOME / ".config" / "fpai" / "tg_brain" / "creds.cache"
INBOX_FILE = HOME / ".config" / "fpai" / "tg_inbox" / "messages.jsonl"
STATE_FILE = HOME / ".config" / "fpai" / "tg_inbox" / "scene_last_update_id.txt"

# The vault — visible memory for James, humans, and AI.
VAULT = HOME / "Library" / "Mobile Documents" / "iCloud~md~obsidian" / "Documents" / "FPOS" / "Full Potential OS"
SCENES_FILE = VAULT / "00_MEMORY" / "SCENES.md"

TG_API = "https://api.telegram.org"


def load_creds() -> dict:
    creds = {}
    if not CREDS_FILE.exists():
        return creds
    for line in CREDS_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        creds[k.strip()] = v.strip().strip('"').strip("'")
    return creds


def send_message(token: str, chat_id: int, text: str) -> bool:
    url = f"{TG_API}/bot{token}/sendMessage"
    cmd = [
        "curl", "-sS", url,
        "--data-urlencode", f"chat_id={chat_id}",
        "--data-urlencode", f"text={text}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    try:
        return json.loads(r.stdout).get("ok", False)
    except json.JSONDecodeError:
        return False


def get_last_id() -> int:
    if not STATE_FILE.exists():
        return 0
    try:
        return int(STATE_FILE.read_text().strip())
    except ValueError:
        return 0


def save_last_id(update_id: int):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(str(update_id))


def parse_scene(text: str) -> str | None:
    """Return the scene body if text is a /scene command, else None."""
    stripped = text.strip()
    low = stripped.lower()
    if low == "/scene" or low.startswith("/scene@"):
        return ""  # bare command, no body
    if low.startswith("/scene ") or low.startswith("/scene\n"):
        return stripped[len("/scene"):].strip()
    return None


def append_scene(body: str, when: str):
    SCENES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SCENES_FILE.exists():
        SCENES_FILE.write_text(
            "# SCENES\n\n"
            "*Captured intentions from `/scene` in @sunheartbrain_bot. "
            "Newest on top. One scene per entry.*\n\n"
            "---\n\n"
        )
    existing = SCENES_FILE.read_text()
    # Insert new entry right after the `---` separator (newest on top).
    marker = "---\n\n"
    idx = existing.find(marker)
    entry = f"### {when}\n\n{body}\n\n---\n\n"
    if idx == -1:
        SCENES_FILE.write_text(existing + "\n" + entry)
    else:
        cut = idx + len(marker)
        SCENES_FILE.write_text(existing[:cut] + entry + existing[cut:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="Show actions, no writes/sends")
    args = ap.parse_args()

    creds = load_creds()
    token = creds.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("creds missing TELEGRAM_BOT_TOKEN", file=sys.stderr)
        return 1

    if not INBOX_FILE.exists():
        print("no inbox yet — nothing to do")
        return 0

    last_id = get_last_id()
    max_id = last_id
    captured = 0

    for line in INBOX_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        uid = entry.get("update_id", 0)
        if uid <= last_id:
            continue
        if entry.get("type") != "text" or "text" not in entry:
            max_id = max(max_id, uid)
            continue

        body = parse_scene(entry["text"])
        if body is None:
            max_id = max(max_id, uid)
            continue  # not a /scene command

        chat_id = entry.get("chat_id")
        when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        if body == "":
            # Bare /scene — prompt for the content, don't save an empty scene.
            reply = "🎬 What's the scene? Send:  /scene <your intention or moment>"
            if args.dry:
                print(f"[dry] would prompt (bare /scene), uid={uid}")
            elif chat_id:
                send_message(token, chat_id, reply)
            max_id = max(max_id, uid)
            continue

        if args.dry:
            print(f"[dry] would capture uid={uid}: {body[:60]!r}")
        else:
            append_scene(body, when)
            if chat_id:
                preview = body if len(body) <= 60 else body[:57] + "..."
                send_message(token, chat_id, f"🎬 Scene captured → {preview}")
        captured += 1
        max_id = max(max_id, uid)

    if not args.dry and max_id > last_id:
        save_last_id(max_id)

    print(f"captured {captured} scene(s)" if captured else "no new scenes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
