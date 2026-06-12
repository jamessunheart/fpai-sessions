"""
Zen Village — Telegram send helper.

Uses TELEGRAM_BOT_TOKEN from /etc/zen-village/telegram-notify.env. Bypasses
the broken `fp-index/api/v1/brain/notify` URL that previously returned
{sent:false}; we hit api.telegram.org directly.

Public API:
  send_to_admins(text)        - notify everyone in ZV_TG_ADMIN_IDS
  send_to_chat(chat_id, text) - notify a specific chat / user
  send_to_pulse(text, topic)  - post to the Village Pulse supergroup
                                in the right Topic (thread_id resolved
                                from ZV_TG_PULSE_TOPIC_<TOPIC> env)
  send_to_accounting(text)    - notify ZV_TG_ACCOUNTING_IDS
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, Optional

logger = logging.getLogger("zen_village.telegram")

_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
_ADMIN_IDS = [s.strip() for s in (os.environ.get("ZV_TG_ADMIN_IDS") or "").split(",") if s.strip()]
_ACCOUNTING_IDS = [s.strip() for s in (os.environ.get("ZV_TG_ACCOUNTING_IDS") or "").split(",") if s.strip()]
_PULSE_CHAT_ID = (os.environ.get("ZV_TG_PULSE_CHAT_ID") or "").strip()
_NOTIFY_LABEL = (os.environ.get("ZV_NOTIFY_LABEL") or "Zen Village").strip()

TOPICS = {
    "bookings": (os.environ.get("ZV_TG_PULSE_TOPIC_BOOKINGS") or "").strip(),
    "financials": (os.environ.get("ZV_TG_PULSE_TOPIC_FINANCIALS") or "").strip(),
    "workers": (os.environ.get("ZV_TG_PULSE_TOPIC_WORKERS") or "").strip(),
    "general": (os.environ.get("ZV_TG_PULSE_TOPIC_GENERAL") or "").strip(),
}


def _api(method: str, payload: dict) -> dict:
    if not _BOT_TOKEN:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
    url = f"https://api.telegram.org/bot{_BOT_TOKEN}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            body = r.read().decode("utf-8")
            return json.loads(body) if body else {"ok": False}
    except Exception as e:
        logger.warning("telegram %s failed: %s", method, e)
        return {"ok": False, "error": str(e)}


def send_to_chat(
    chat_id: str | int,
    text: str,
    parse_mode: str = "HTML",
    thread_id: Optional[int | str] = None,
    disable_preview: bool = True,
    reply_markup: Optional[dict] = None,
) -> dict:
    """Send text to a single chat (user, group, or channel)."""
    if not chat_id:
        return {"ok": False, "error": "no chat_id"}
    payload = {
        "chat_id": str(chat_id),
        "text": text[:4000],
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview,
    }
    if thread_id:
        payload["message_thread_id"] = int(thread_id)
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _api("sendMessage", payload)


_NOTIFY_KEYS_FILE = Path(
    os.environ.get("ZV_NOTIFY_KEYS_FILE",
                   "/opt/fpai/apps/zen-village/data/notify_keys.json")
)


def _short_token(submission_key: str) -> str:
    """Stable 8-char token for a submission_key. Telegram callback_data ≤ 64 bytes."""
    return hashlib.sha1(submission_key.encode()).hexdigest()[:10]


def remember_submission_key(submission_key: str) -> str:
    """Persist short_token → full submission_key mapping for callback handling."""
    if not submission_key:
        return ""
    tok = _short_token(submission_key)
    try:
        d = {}
        if _NOTIFY_KEYS_FILE.exists():
            d = json.loads(_NOTIFY_KEYS_FILE.read_text())
        d[tok] = submission_key
        # Cap size to last 5000 entries
        if len(d) > 5000:
            d = dict(list(d.items())[-5000:])
        _NOTIFY_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = _NOTIFY_KEYS_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False))
        tmp.replace(_NOTIFY_KEYS_FILE)
    except Exception as e:
        logger.warning("notify_keys persist failed: %s", e)
    return tok


def resolve_submission_key(token: str) -> str:
    if not token:
        return ""
    try:
        if _NOTIFY_KEYS_FILE.exists():
            return (json.loads(_NOTIFY_KEYS_FILE.read_text()) or {}).get(token, "")
    except Exception:
        pass
    return ""


def submission_action_keyboard(submission_key: str) -> dict:
    """InlineKeyboardMarkup: one-tap status updates + open dashboard."""
    tok = remember_submission_key(submission_key)
    return {
        "inline_keyboard": [[
            {"text": "✓ Contacted", "callback_data": f"sub:contact:{tok}"},
            {"text": "📁 Archive", "callback_data": f"sub:close:{tok}"},
            {"text": "🌐 Open", "url": "https://zenvillagecr.com/admin/submissions"},
        ]],
    }


def send_to_many(chat_ids: Iterable[str | int], text: str, **kw) -> list[dict]:
    return [send_to_chat(cid, text, **kw) for cid in chat_ids if cid]


def send_to_admins(text: str, **kw) -> list[dict]:
    return send_to_many(_ADMIN_IDS, text, **kw)


def send_to_accounting(text: str, **kw) -> list[dict]:
    return send_to_many(_ACCOUNTING_IDS, text, **kw)


def send_to_pulse(text: str, topic: str = "general", **kw) -> dict:
    """Post into Village Pulse supergroup, into the right Topic thread."""
    if not _PULSE_CHAT_ID:
        return {"ok": False, "error": "ZV_TG_PULSE_CHAT_ID not configured"}
    thread = TOPICS.get(topic.lower(), "")
    return send_to_chat(_PULSE_CHAT_ID, text, thread_id=thread or None, **kw)


def is_admin(telegram_id: str | int) -> bool:
    return str(telegram_id) in _ADMIN_IDS


def admin_ids() -> list[str]:
    return list(_ADMIN_IDS)


def label() -> str:
    return _NOTIFY_LABEL


def configured() -> dict:
    """Diagnostic: which chats are wired."""
    return {
        "bot_token_set": bool(_BOT_TOKEN),
        "admin_ids_count": len(_ADMIN_IDS),
        "accounting_ids_count": len(_ACCOUNTING_IDS),
        "pulse_chat_id_set": bool(_PULSE_CHAT_ID),
        "topics_configured": {k: bool(v) for k, v in TOPICS.items()},
        "label": _NOTIFY_LABEL,
    }
