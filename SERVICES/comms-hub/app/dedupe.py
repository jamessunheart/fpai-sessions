from __future__ import annotations

import hashlib
import json

from .models import MessageInput


def dedupe_key(message: MessageInput) -> str:
    payload = {
        "source": message.source,
        "audience": message.audience,
        "priority": message.priority,
        "topic": message.topic,
        "body": message.body.strip(),
        "attachments": [attachment.model_dump() for attachment in message.attachments],
        "metadata": message.metadata,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()

