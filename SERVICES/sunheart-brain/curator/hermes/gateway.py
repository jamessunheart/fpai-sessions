"""Minimal Hermes gateway for channel-agnostic probe sends.

Only Telegram is implemented in d054. Other platforms fail closed until their
reviewed adapters exist.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from typing import Any


def send_message(*, platform: str, handle: str, text: str) -> bool:
    if platform != "telegram":
        return False
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or not handle or not text:
        return False
    payload: dict[str, Any] = {"chat_id": handle, "text": text}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception:
        return False
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        return False
    return bool(result.get("ok"))
