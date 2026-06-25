"""Local web adapter for Hermes."""
from __future__ import annotations

from datetime import datetime, timezone

from ..schema import HermesMessage, HermesResponse, normalize_permissions
from .base import ChannelAdapter


class WebAdapter(ChannelAdapter):
    channel = "web"

    def __init__(self) -> None:
        self.sent: list[HermesResponse] = []

    def normalize(self, raw: dict) -> HermesMessage:
        content = str(raw.get("content") or raw.get("text") or "").strip()
        channel_user_id = str(raw.get("channel_user_id") or raw.get("user_id") or "").strip()
        if not channel_user_id:
            raise ValueError("web payload missing user_id or channel_user_id")
        return HermesMessage(
            user_id=str(raw.get("user_id") or ""),
            channel=self.channel,
            channel_user_id=channel_user_id,
            message_type=str(raw.get("message_type") or "text"),
            content=content,
            beacon_id=raw.get("beacon_id"),
            timestamp=str(raw.get("timestamp") or datetime.now(timezone.utc).isoformat()),
            raw=raw,
            permissions=normalize_permissions(raw.get("permissions")),
        )

    async def send(self, response: HermesResponse) -> None:
        self.sent.append(response)

    def health_check(self) -> bool:
        return True
