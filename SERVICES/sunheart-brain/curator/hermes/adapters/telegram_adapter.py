"""Telegram adapter for Hermes."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import httpx

from ..schema import HermesMessage, HermesResponse, normalize_permissions
from .base import ChannelAdapter


VOICE_PLACEHOLDER = "[voice message: transcription pending]"
IMAGE_PLACEHOLDER = "[image message]"
FILE_PLACEHOLDER = "[file message]"


class TelegramAdapter(ChannelAdapter):
    channel = "telegram"

    def normalize(self, raw: dict) -> HermesMessage:
        msg = raw.get("message") or raw.get("edited_message") or {}
        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            raise ValueError("telegram payload missing message.chat.id")

        text = (msg.get("text") or msg.get("caption") or "").strip()
        message_type = self._message_type(msg, text)
        content = self._content_for(msg, text, message_type)
        beacon_id = self._beacon_id(text)
        timestamp = self._timestamp(msg.get("date"))

        return HermesMessage(
            user_id="",
            channel=self.channel,
            channel_user_id=str(chat_id),
            message_type=message_type,
            content=content,
            beacon_id=beacon_id,
            timestamp=timestamp,
            raw=raw,
            permissions=normalize_permissions(raw.get("permissions")),
        )

    async def send(self, response: HermesResponse) -> None:
        from ... import telegram

        await telegram.send(response.content)

    def health_check(self) -> bool:
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            return False
        if os.environ.get("HERMES_TELEGRAM_HEALTH_NETWORK") != "1":
            return True
        try:
            with httpx.Client(timeout=5) as client:
                res = client.get(f"https://api.telegram.org/bot{token}/getMe")
            return res.status_code == 200 and bool((res.json().get("result") or {}).get("id"))
        except Exception:
            return False

    @staticmethod
    def _message_type(msg: dict[str, Any], text: str) -> str:
        if text.startswith("/"):
            return "command"
        if msg.get("voice") or msg.get("audio"):
            return "voice"
        if msg.get("photo"):
            return "image"
        if msg.get("document"):
            return "file"
        return "text"

    @staticmethod
    def _content_for(msg: dict[str, Any], text: str, message_type: str) -> str:
        if text:
            return text
        if message_type == "voice":
            return VOICE_PLACEHOLDER
        if message_type == "image":
            return IMAGE_PLACEHOLDER
        if message_type == "file":
            return FILE_PLACEHOLDER
        return ""

    @staticmethod
    def _beacon_id(text: str) -> str | None:
        if not text.startswith("/start"):
            return None
        parts = text.split(maxsplit=1)
        return parts[1].strip() if len(parts) == 2 and parts[1].strip() else None

    @staticmethod
    def _timestamp(unix_seconds: Any) -> str:
        if isinstance(unix_seconds, (int, float)):
            return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).isoformat()
        return datetime.now(timezone.utc).isoformat()
