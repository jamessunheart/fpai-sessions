from __future__ import annotations

import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:sk|xoxb|ghp)_[A-Za-z0-9_=-]{16,}\b"),
    re.compile(r"(?i)(token|secret|password|api[_-]?key)\s*=\s*[^ \n]+"),
]


def redact_text(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def redact_obj(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_obj(item) for item in value]
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if key.lower() in {"token", "secret", "password", "api_key", "bot_token"}:
                clean[key] = "[REDACTED]"
            else:
                clean[key] = redact_obj(item)
        return clean
    return value


def chat_allowed(chat_id: str | int | None, allowed_chat_ids: set[str]) -> bool:
    if not chat_id:
        return False
    return str(chat_id) in allowed_chat_ids

