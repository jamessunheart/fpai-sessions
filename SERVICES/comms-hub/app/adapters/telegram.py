from __future__ import annotations

import json
from typing import Any
from urllib import parse, request

from ..config import Settings
from ..models import Attachment, DeliveryResult, MessageInput, MessageRecord
from ..security import chat_allowed
from ..store import JsonlStore


def adapter_state(settings: Settings) -> dict[str, Any]:
    return {
        "enabled": settings.tg_enabled,
        "poll_enabled": settings.tg_poll_enabled,
        "send_enabled": settings.tg_send_enabled,
        "token_present": bool(settings.telegram_bot_token),
        "allowed_chat_ids_count": len(settings.telegram_allowed_chat_ids),
    }


def send_message(message: MessageRecord, settings: Settings, chat_id: str | None = None) -> DeliveryResult:
    if not settings.tg_enabled:
        return DeliveryResult(status="blocked", detail="COMMS_HUB_TG_ENABLED=0")
    if not settings.tg_send_enabled:
        return DeliveryResult(status="blocked", detail="COMMS_HUB_TG_SEND_ENABLED=0")
    if not settings.telegram_bot_token:
        return DeliveryResult(status="blocked", detail="TELEGRAM_BOT_TOKEN missing")
    target_chat = chat_id or str(message.metadata.get("telegram_chat_id", ""))
    if not chat_allowed(target_chat, settings.telegram_allowed_chat_ids):
        return DeliveryResult(status="blocked", detail="telegram chat not allowlisted")
    if settings.dry_run:
        return DeliveryResult(status="dry_run", detail=f"would send telegram message to {target_chat}")
    response = telegram_api_request(settings, "sendMessage", {"chat_id": target_chat, "text": message.body})
    if response.get("ok"):
        return DeliveryResult(status="delivered", detail=f"telegram sent to {target_chat}")
    return DeliveryResult(status="failed", detail="telegram send failed")


def process_update(update: dict[str, Any], settings: Settings, store: JsonlStore) -> MessageRecord | None:
    update_id = int(update.get("update_id", 0))
    state = store.load_state()
    last_update_id = int(state.get("telegram_last_update_id", 0) or 0)
    if update_id <= last_update_id:
        return None

    message = update.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    if not chat_allowed(chat_id, settings.telegram_allowed_chat_ids):
        state["telegram_last_update_id"] = update_id
        store.save_state(state)
        return None

    text = message.get("text") or ""
    audience = "system"
    metadata: dict[str, Any] = {"telegram_update_id": update_id, "telegram_chat_id": chat_id}
    if text.startswith("/builder"):
        audience = "builder"
        parts = text.split(maxsplit=2)
        if len(parts) >= 2 and not parts[1].startswith("/"):
            metadata["builder_id"] = parts[1]
    elif text.startswith("/system"):
        audience = "system"

    attachments: list[Attachment] = []
    if "voice" in message:
        voice = message["voice"]
        attachments.append(Attachment(type="voice", file_id=voice.get("file_id"), duration=voice.get("duration")))
        if not text:
            text = "[voice message]"

    record = store.append_inbox(MessageInput(
        source="telegram",
        audience=audience,  # type: ignore[arg-type]
        priority="normal",
        topic="telegram",
        body=text,
        attachments=attachments,
        metadata=metadata,
    ))
    state = store.load_state()
    state["telegram_last_update_id"] = update_id
    store.save_state(state)
    return record


def poll_updates(settings: Settings, store: JsonlStore, updates: list[dict[str, Any]] | None = None) -> list[MessageRecord]:
    if not (settings.enabled and settings.tg_enabled and settings.tg_poll_enabled):
        return []
    if updates is None:
        if not settings.telegram_bot_token:
            return []
        state = store.load_state()
        last_update_id = int(state.get("telegram_last_update_id", 0) or 0)
        response = telegram_api_request(settings, "getUpdates", {"offset": last_update_id + 1, "timeout": 0})
        updates = response.get("result", []) if response.get("ok") else []
    records: list[MessageRecord] = []
    for update in updates:
        record = process_update(update, settings, store)
        if record is not None:
            records.append(record)
    return records


def telegram_api_request(settings: Settings, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/{method}"
    body = parse.urlencode(payload).encode("utf-8")
    req = request.Request(url, data=body, method="POST")
    try:
        with request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception:
        return {"ok": False}
