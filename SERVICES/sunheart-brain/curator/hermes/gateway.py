"""Hermes channel gateway."""
from __future__ import annotations

import inspect
import logging
import os
import uuid
from dataclasses import replace
from typing import Any, Awaitable, Callable, Protocol

from .adapters.base import ChannelAdapter
from .schema import HermesMessage, HermesResponse

log = logging.getLogger("curator.hermes.gateway")


Pipeline = Callable[[HermesMessage], HermesResponse | Awaitable[HermesResponse]]


class ChannelNotRegistered(Exception):
    """Raised when a payload arrives for an unregistered channel."""


class HermesDisabled(Exception):
    """Raised when HERMES_DISABLE=1 is set."""


class UserChannelStore(Protocol):
    async def resolve(self, message: HermesMessage) -> str:
        """Return the stable universal user id for a channel identity."""


class HermesMessageLogger(Protocol):
    async def log_inbound(self, message: HermesMessage) -> None:
        """Best-effort inbound message log."""

    async def log_outbound(self, response: HermesResponse) -> None:
        """Best-effort outbound message log."""


class InMemoryUserChannelStore:
    """Small test/local identity store keyed by channel identity."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict[str, Any]] = {}

    async def resolve(self, message: HermesMessage) -> str:
        key = (message.channel, message.channel_user_id)
        row = self.rows.get(key)
        if row:
            row["last_seen"] = message.timestamp
            row["permissions"] = dict(message.permissions)
            if message.beacon_id:
                row["beacon_id"] = message.beacon_id
            return str(row["user_id"])
        user_id = message.user_id or str(uuid.uuid4())
        self.rows[key] = {
            "user_id": user_id,
            "channel": message.channel,
            "channel_user_id": message.channel_user_id,
            "beacon_id": message.beacon_id,
            "first_seen": message.timestamp,
            "last_seen": message.timestamp,
            "permissions": dict(message.permissions),
        }
        return user_id


class RecordingMessageLogger:
    """Test/local logger that records messages in memory."""

    def __init__(self) -> None:
        self.inbound: list[HermesMessage] = []
        self.outbound: list[HermesResponse] = []

    async def log_inbound(self, message: HermesMessage) -> None:
        self.inbound.append(message)

    async def log_outbound(self, response: HermesResponse) -> None:
        self.outbound.append(response)


class PostgresUserChannelStore:
    """Identity mapper backed by brain_index.user_channels."""

    async def resolve(self, message: HermesMessage) -> str:
        from psycopg.types.json import Jsonb

        from ..db import connect

        preferred_user_id = message.user_id or str(uuid.uuid4())
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.user_channels
                        (user_id, channel, channel_user_id, beacon_id, permissions)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (channel, channel_user_id) DO UPDATE
                       SET last_seen = NOW(),
                           beacon_id = COALESCE(EXCLUDED.beacon_id, user_channels.beacon_id),
                           permissions = EXCLUDED.permissions
                    RETURNING user_id
                    """,
                    (
                        preferred_user_id,
                        message.channel,
                        message.channel_user_id,
                        message.beacon_id,
                        Jsonb(message.permissions),
                    ),
                )
                row = await cur.fetchone()
                return str(row[0])


class PostgresMessageLogger:
    """Best-effort logging to the shared thread and Telegram message buffer."""

    async def log_inbound(self, message: HermesMessage) -> None:
        try:
            from ..db import connect

            async with connect() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO brain_index.thread (surface, role, text) VALUES (%s, %s, %s)",
                        (message.channel[:16], "james", message.content[:8000]),
                    )
        except Exception as exc:
            log.warning("hermes inbound thread log failed: %s", exc)

    async def log_outbound(self, response: HermesResponse) -> None:
        try:
            from ..db import connect

            async with connect() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "INSERT INTO brain_index.thread (surface, role, text) VALUES (%s, %s, %s)",
                        (response.channel[:16], "ember", response.content[:8000]),
                    )
                    if response.channel == "telegram":
                        await cur.execute(
                            """
                            INSERT INTO brain_index.tg_messages (chat_id, role, text, private_flag)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (response.channel_user_id, "bot", response.content[:8000], False),
                        )
        except Exception as exc:
            log.warning("hermes outbound log failed: %s", exc)


class HermesGateway:
    def __init__(
        self,
        *,
        identity_store: UserChannelStore | None = None,
        message_logger: HermesMessageLogger | None = None,
        pipeline: Pipeline | None = None,
    ) -> None:
        self.adapters: dict[str, ChannelAdapter] = {}
        self.identity_store = identity_store or PostgresUserChannelStore()
        self.message_logger = message_logger or PostgresMessageLogger()
        self.pipeline = pipeline or default_pipeline

    def register(self, channel: str, adapter: ChannelAdapter) -> None:
        self.adapters[channel] = adapter

    async def receive(self, raw_payload: dict, channel: str) -> HermesMessage:
        self._raise_if_disabled()
        adapter = self._adapter(channel)
        normalized = adapter.normalize(raw_payload)
        user_id = await self.identity_store.resolve(normalized)
        message = replace(normalized, user_id=user_id)
        await self.message_logger.log_inbound(message)
        return message

    async def process(self, raw_payload: dict, channel: str) -> HermesResponse:
        message = await self.receive(raw_payload, channel)
        response = self.pipeline(message)
        if inspect.isawaitable(response):
            response = await response
        if response.channel != message.channel or response.channel_user_id != message.channel_user_id:
            response = replace(
                response,
                channel=message.channel,
                channel_user_id=message.channel_user_id,
            )
        await self.message_logger.log_outbound(response)
        return response

    async def send(self, response: HermesResponse) -> None:
        self._raise_if_disabled()
        adapter = self._adapter(response.channel)
        await adapter.send(response)
        await self.message_logger.log_outbound(response)

    def _adapter(self, channel: str) -> ChannelAdapter:
        try:
            return self.adapters[channel]
        except KeyError as exc:
            raise ChannelNotRegistered(channel) from exc

    @staticmethod
    def _raise_if_disabled() -> None:
        if os.environ.get("HERMES_DISABLE") == "1":
            raise HermesDisabled("HERMES_DISABLE=1")


async def default_pipeline(message: HermesMessage) -> HermesResponse:
    """Route through the existing brain chat path without changing tgbot.py."""

    from .. import tgbot

    hits = await tgbot._search_brain(message.content)
    answer = await tgbot._synthesize_answer(
        message.content,
        hits,
        conversation_id=message.user_id,
    )
    content = tgbot._format_answer_for_telegram(answer)
    return HermesResponse(
        content=content,
        response_type="text",
        channel=message.channel,
        channel_user_id=message.channel_user_id,
    )
