"""Telegram bot — send cycle summaries, receive steering messages."""

import json
import os
import requests
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
LAST_UPDATE_FILE = BASE / "telegram" / ".last_update_id"


def _token():
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


def _chat_id():
    return os.environ.get("TELEGRAM_CHAT_ID", "")


def send_message(text, parse_mode="Markdown"):
    """Send a message to Sunheart via Telegram."""
    token = _token()
    chat_id = _chat_id()
    if not token or not chat_id:
        raise Exception("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    # Telegram has a 4096 char limit per message
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]

    for chunk in chunks:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": parse_mode,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            # Retry without parse_mode (markdown can fail on special chars)
            resp2 = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
                timeout=30,
            )
            if resp2.status_code != 200:
                raise Exception(f"Telegram send failed: {resp2.text[:200]}")


def get_new_messages():
    """Poll for new messages from Sunheart. Returns list of {timestamp, message}."""
    token = _token()
    chat_id = _chat_id()
    if not token:
        return []

    last_id = 0
    if LAST_UPDATE_FILE.exists():
        try:
            last_id = int(LAST_UPDATE_FILE.read_text().strip())
        except Exception:
            pass

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": last_id + 1, "timeout": 5},
            timeout=15,
        )
        data = resp.json()
    except Exception:
        return []

    messages = []
    max_id = last_id

    for update in data.get("result", []):
        uid = update.get("update_id", 0)
        if uid > max_id:
            max_id = uid

        msg = update.get("message", {})
        from_id = str(msg.get("from", {}).get("id", ""))
        text = msg.get("text", "")

        # Only accept messages from Sunheart
        if from_id == chat_id and text:
            # Skip bot commands that aren't steering
            if text.startswith("/") and not text.startswith("/steer"):
                continue
            messages.append({
                "timestamp": msg.get("date", 0),
                "message": text.lstrip("/steer").strip() if text.startswith("/steer") else text,
            })

    if max_id > last_id:
        LAST_UPDATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAST_UPDATE_FILE.write_text(str(max_id))

    return messages
