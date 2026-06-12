#!/usr/bin/env python3
"""
Telegram inbox listener · v1 · 2026-05-24

Polls @sunheartbrain_bot for new messages from James. Transcribes voice notes
via Whisper. Writes everything to ~/.config/fpai/tg_inbox/messages.jsonl —
the inbox Ember reads at session start (per DAILY_AWAKENING.md).

This is the inbound half of the digest channel. The outbound half is
send_tg_digest.py. Together they make Telegram a bidirectional surface where
James can talk back to the substrate (text or voice) and influence routing,
queue priorities, decision reversals.

Usage:
  python3 tg_listen.py              # poll once for new messages
  python3 tg_listen.py --poll-loop  # continuous polling (for LaunchAgent)

Per-message types handled:
  - text       → captured as-is
  - voice      → OGG downloaded → Whisper → transcript captured
  - photo/etc  → captured with raw payload (Ember sees it on next read)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
# Env-overridable so a second instance (e.g. the builder bot) can poll a
# different bot into its own inbox without colliding with the brain bot.
CREDS_FILE = Path(os.environ.get("FPAI_TG_CREDS",
                                 HOME / ".config" / "fpai" / "tg_brain" / "creds.cache"))
OPENAI_KEY_FILE = HOME / ".config" / "fpai" / "openai" / "api.token"
INBOX_DIR = Path(os.environ.get("FPAI_TG_INBOX_DIR",
                                HOME / ".config" / "fpai" / "tg_inbox"))
INBOX_FILE = INBOX_DIR / "messages.jsonl"
AUDIO_DIR = INBOX_DIR / "audio"
STATE_FILE = INBOX_DIR / "last_update_id.txt"
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


def fetch_updates(token: str, offset: int = 0, timeout: int = 5):
    url = f"{TG_API}/bot{token}/getUpdates"
    if offset:
        url += f"?offset={offset}&timeout={timeout}"
    else:
        url += f"?timeout={timeout}"
    cmd = ["curl", "-sS", "--max-time", str(timeout + 10), url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 15)
    if r.returncode != 0:
        return {"ok": False, "error": f"curl exit {r.returncode}: {r.stderr[:200]}"}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "error": f"non-json: {r.stdout[:200]}"}


def download_voice(token: str, file_id: str) -> Path | None:
    """Two-step: /getFile to get path, then download from /file/bot{token}/{path}."""
    cmd = ["curl", "-sS", f"{TG_API}/bot{token}/getFile?file_id={file_id}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if not data.get("ok"):
        return None
    file_path = data["result"]["file_path"]
    download_url = f"{TG_API}/file/bot{token}/{file_path}"

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    target = AUDIO_DIR / f"{file_id}.ogg"
    r2 = subprocess.run(
        ["curl", "-sS", "-o", str(target), download_url],
        capture_output=True, text=True, timeout=60,
    )
    if r2.returncode != 0 or not target.exists() or target.stat().st_size == 0:
        return None
    return target


def transcribe(audio_path: Path) -> str | None:
    """Send OGG to OpenAI Whisper. Returns plain-text transcript."""
    if not OPENAI_KEY_FILE.exists():
        return None
    key = OPENAI_KEY_FILE.read_text().strip()

    cmd = [
        "curl", "-sS", "https://api.openai.com/v1/audio/transcriptions",
        "-H", f"Authorization: Bearer {key}",
        "-F", "model=whisper-1",
        "-F", f"file=@{audio_path}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return None
    try:
        data = json.loads(r.stdout)
        return data.get("text", "").strip()
    except json.JSONDecodeError:
        return None


def process_message(token: str, owner_id: int, upd: dict) -> dict | None:
    """Return inbox entry dict, or None if message should be skipped."""
    msg = upd.get("message") or upd.get("edited_message")
    if not msg:
        return None

    from_id = msg.get("from", {}).get("id")
    if from_id != owner_id:
        return None  # only listen to James

    entry = {
        "update_id": upd["update_id"],
        "message_id": msg["message_id"],
        "received_at": datetime.now(timezone.utc).isoformat(),
        "from_telegram": True,
        "chat_id": msg["chat"]["id"],
        "edited": "edited_message" in upd,
    }

    if "text" in msg:
        entry["type"] = "text"
        entry["text"] = msg["text"]
    elif "voice" in msg:
        entry["type"] = "voice"
        v = msg["voice"]
        entry["voice_file_id"] = v["file_id"]
        entry["duration_s"] = v.get("duration", 0)
        entry["mime_type"] = v.get("mime_type", "audio/ogg")

        audio_path = download_voice(token, v["file_id"])
        if audio_path:
            entry["audio_path"] = str(audio_path)
            text = transcribe(audio_path)
            if text:
                entry["text"] = text
                entry["transcribed_by"] = "whisper-1"
            else:
                entry["transcription_error"] = "whisper failed or key missing"
    elif "photo" in msg:
        entry["type"] = "photo"
        entry["photo_file_ids"] = [p["file_id"] for p in msg["photo"]]
        if "caption" in msg:
            entry["text"] = msg["caption"]
    elif "document" in msg:
        entry["type"] = "document"
        entry["doc_file_id"] = msg["document"]["file_id"]
        if "caption" in msg:
            entry["text"] = msg["caption"]
    else:
        entry["type"] = "other"
        entry["raw_keys"] = list(msg.keys())

    return entry


def append_inbox(entry: dict):
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    with open(INBOX_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def get_last_offset() -> int:
    if not STATE_FILE.exists():
        return 0
    try:
        return int(STATE_FILE.read_text().strip())
    except ValueError:
        return 0


def save_last_offset(update_id: int):
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(str(update_id))


def poll_once(creds: dict, verbose: bool = True) -> int:
    """One fetch+process cycle. Returns count of new messages captured."""
    token = creds.get("TELEGRAM_BOT_TOKEN")
    owner_id_raw = creds.get("OWNER_TG_ID") or creds.get("TELEGRAM_CHAT_ID")
    if not token or not owner_id_raw:
        if verbose:
            print(f"creds missing: token={bool(token)} owner_id={bool(owner_id_raw)}", file=sys.stderr)
        return 0
    owner_id = int(owner_id_raw)

    offset = get_last_offset()
    next_offset = offset + 1 if offset else 0

    data = fetch_updates(token, offset=next_offset, timeout=2)
    if not data.get("ok"):
        if verbose:
            print(f"fetch error: {data.get('error', data)}", file=sys.stderr)
        return 0

    count = 0
    max_update_id = offset
    for upd in data["result"]:
        entry = process_message(token, owner_id, upd)
        if entry:
            append_inbox(entry)
            count += 1
            if verbose:
                preview = (entry.get("text") or "(no text)")[:80]
                print(f"  [{entry['type']}] {preview}")
        max_update_id = max(max_update_id, upd["update_id"])

    if max_update_id > offset:
        save_last_offset(max_update_id)

    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--poll-loop", action="store_true", help="Continuous polling (for LaunchAgent)")
    ap.add_argument("--interval", type=int, default=60, help="Poll interval seconds (loop mode)")
    args = ap.parse_args()

    creds = load_creds()

    if args.poll_loop:
        print(f"polling @sunheartbrain_bot every {args.interval}s · ctrl-c to stop")
        while True:
            try:
                n = poll_once(creds, verbose=True)
                if n:
                    print(f"[{datetime.now(timezone.utc).isoformat()}] captured {n} messages")
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"poll error: {type(e).__name__}: {e}", file=sys.stderr)
            time.sleep(args.interval)
    else:
        n = poll_once(creds, verbose=True)
        print(f"captured {n} new messages" if n else "no new messages")


if __name__ == "__main__":
    main()
