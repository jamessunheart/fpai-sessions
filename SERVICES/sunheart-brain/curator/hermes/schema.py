"""Channel-agnostic Hermes message schema."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


DEFAULT_PERMISSIONS = {
    "memory": True,
    "marketing": False,
    "human_followup": False,
}


@dataclass
class HermesMessage:
    user_id: str
    channel: str
    channel_user_id: str
    message_type: str
    content: str
    beacon_id: str | None
    timestamp: str
    raw: dict[str, Any]
    permissions: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HermesResponse:
    content: str
    response_type: str
    channel: str
    channel_user_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_permissions(raw: dict[str, Any] | None) -> dict[str, bool]:
    permissions = dict(DEFAULT_PERMISSIONS)
    for key, value in (raw or {}).items():
        if key in permissions:
            permissions[key] = bool(value)
    return permissions
