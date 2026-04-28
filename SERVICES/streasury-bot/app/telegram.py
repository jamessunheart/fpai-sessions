"""app/telegram.py — minimal HTTP client for the Telegram Bot API.

Outbound helpers are no-ops if the token is missing so tests / dry-runs don't
explode. Owner-side auth lives in tgbot.py (whitelist).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

log = logging.getLogger("streasury.telegram")

API_BASE = "https://api.telegram.org"


def enabled() -> bool:
    return bool(settings.telegram_bot_token)


def _url(method: str) -> str:
    return f"{API_BASE}/bot{settings.telegram_bot_token}/{method}"


def esc(s: str) -> str:
    """Escape characters meaningful in Telegram HTML mode."""
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


async def send(
    chat_id: int | str,
    text: str,
    *,
    parse_mode: str = "HTML",
    reply_markup: dict | None = None,
    reply_to: int | None = None,
) -> dict | None:
    if not enabled():
        return None
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(_url("sendMessage"), json=payload)
            if r.status_code != 200:
                log.warning("sendMessage %s: %s", r.status_code, r.text[:200])
                return None
            return r.json().get("result")
    except Exception as e:
        log.warning("send error: %s", e)
        return None


async def edit_message(chat_id: int | str, message_id: int, text: str, *, parse_mode: str = "HTML",
                       reply_markup: dict | None = None) -> bool:
    if not enabled():
        return False
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(_url("editMessageText"), json=payload)
            return r.status_code == 200
    except Exception as e:
        log.warning("edit error: %s", e)
        return False


async def answer_callback(callback_id: str, text: str = "", *, alert: bool = False) -> bool:
    if not enabled():
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(_url("answerCallbackQuery"), json={
                "callback_query_id": callback_id,
                "text": text,
                "show_alert": alert,
            })
            return r.status_code == 200
    except Exception as e:
        log.warning("answer_callback error: %s", e)
        return False


async def get_file_path(file_id: str) -> str | None:
    if not enabled():
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(_url("getFile"), params={"file_id": file_id})
            r.raise_for_status()
            return r.json()["result"]["file_path"]
    except Exception as e:
        log.warning("getFile error: %s", e)
        return None


async def download_file(file_id: str) -> bytes | None:
    """Resolve file_id → bytes. Used by photo and voice handlers."""
    path = await get_file_path(file_id)
    if not path:
        return None
    url = f"{API_BASE}/file/bot{settings.telegram_bot_token}/{path}"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.content
    except Exception as e:
        log.warning("download_file error: %s", e)
        return None
