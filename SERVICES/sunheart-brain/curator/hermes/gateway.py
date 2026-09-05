"""Hermes channel gateway and legacy probe-send compatibility helper.

The synchronous send_message helper remains standalone-loadable for the d054
probe and payment activation callers. The class gateway is available when this
module is imported as part of curator.hermes.
"""
from __future__ import annotations

import inspect
import json
import logging
import os
import urllib.parse
import urllib.request
import uuid
from dataclasses import replace
from typing import Any, Awaitable, Callable, Protocol

if __package__:
    from .adapters.base import ChannelAdapter
    from .schema import HermesMessage, HermesResponse
else:
    # Existing callers load this file by path under a non-package module name.
    # They use only send_message; do not mutate sys.path just to satisfy type
    # imports for the separate class gateway.
    ChannelAdapter = HermesMessage = HermesResponse = Any


log = logging.getLogger("curator.hermes.gateway")

Pipeline = Callable[[HermesMessage], HermesResponse | Awaitable[HermesResponse]]

SERVER_DEFAULT_PERMISSIONS = {
    "memory": True,
    "marketing": False,
    "human_followup": False,
}


def _server_permissions() -> dict[str, bool]:
    """Return permissions chosen by the server, never by an inbound payload."""

    return dict(SERVER_DEFAULT_PERMISSIONS)


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


class ChannelNotRegistered(Exception):
    """Raised when a payload arrives for an unregistered channel."""


class HermesDisabled(Exception):
    """Raised when HERMES_DISABLE=1 is set."""


class UserChannelStore(Protocol):
    async def resolve(self, message: HermesMessage) -> str:
        """Return the stable, server-resolved user id for a channel identity."""


class HermesMessageLogger(Protocol):
    async def log_inbound(self, message: HermesMessage) -> None:
        """Best-effort inbound message log."""

    async def log_outbound(
        self,
        response: HermesResponse,
        *,
        user_id: str | None = None,
    ) -> None:
        """Best-effort outbound message log for a resolved user."""


class InMemoryUserChannelStore:
    """Small test/local identity store keyed by channel identity."""

    def __init__(self) -> None:
        self.rows: dict[tuple[str, str], dict[str, Any]] = {}

    async def resolve(self, message: HermesMessage) -> str:
        key = (message.channel, message.channel_user_id)
        row = self.rows.get(key)
        if row:
            row["last_seen"] = message.timestamp
            if message.beacon_id:
                row["beacon_id"] = message.beacon_id
            return str(row["user_id"])
        user_id = str(uuid.uuid4())
        self.rows[key] = {
            "user_id": user_id,
            "channel": message.channel,
            "channel_user_id": message.channel_user_id,
            "beacon_id": message.beacon_id,
            "first_seen": message.timestamp,
            "last_seen": message.timestamp,
            "permissions": _server_permissions(),
        }
        return user_id


class RecordingMessageLogger:
    """Test/local logger that records messages in memory."""

    def __init__(self) -> None:
        self.inbound: list[HermesMessage] = []
        self.outbound: list[HermesResponse] = []
        self.outbound_user_ids: list[str | None] = []

    async def log_inbound(self, message: HermesMessage) -> None:
        self.inbound.append(message)

    async def log_outbound(
        self,
        response: HermesResponse,
        *,
        user_id: str | None = None,
    ) -> None:
        self.outbound.append(response)
        self.outbound_user_ids.append(user_id)


class PostgresUserChannelStore:
    """Identity mapper backed by brain_index.user_channels."""

    async def resolve(self, message: HermesMessage) -> str:
        from psycopg.types.json import Jsonb

        from ..db import connect

        server_user_id = str(uuid.uuid4())
        async with connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO brain_index.user_channels
                        (user_id, channel, channel_user_id, beacon_id, permissions)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (channel, channel_user_id) DO UPDATE
                       SET last_seen = NOW(),
                           beacon_id = COALESCE(EXCLUDED.beacon_id, user_channels.beacon_id)
                    RETURNING user_id
                    """,
                    (
                        server_user_id,
                        message.channel,
                        message.channel_user_id,
                        message.beacon_id,
                        Jsonb(_server_permissions()),
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
                        """
                        INSERT INTO brain_index.thread (user_id, surface, role, text)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (message.user_id, message.channel[:16], "user", message.content[:8000]),
                    )
        except Exception as exc:
            log.warning("hermes inbound thread log failed: %s", exc)

    async def log_outbound(
        self,
        response: HermesResponse,
        *,
        user_id: str | None = None,
    ) -> None:
        try:
            from ..db import connect

            async with connect() as conn:
                async with conn.cursor() as cur:
                    if user_id:
                        await cur.execute(
                            """
                            INSERT INTO brain_index.thread (user_id, surface, role, text)
                            VALUES (%s, %s, %s, %s)
                            """,
                            (user_id, response.channel[:16], "assistant", response.content[:8000]),
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
        self._runtime_injected = identity_store is not None and message_logger is not None
        self._pipeline_injected = pipeline is not None
        self.identity_store = identity_store or PostgresUserChannelStore()
        self.message_logger = message_logger or PostgresMessageLogger()
        self.pipeline = pipeline or default_pipeline

    def register(self, channel: str, adapter: ChannelAdapter) -> None:
        self.adapters[channel] = adapter

    async def receive(
        self,
        raw_payload: dict,
        channel: str,
        *,
        trusted_channel_user_id: str | None = None,
    ) -> HermesMessage:
        self._raise_if_disabled()
        adapter = self._adapter(channel)
        channel_user_id = str(trusted_channel_user_id or "").strip()
        if not channel_user_id:
            raise HermesDisabled("Hermes receive requires server-resolved channel identity")

        untrusted = adapter.normalize(raw_payload)
        normalized = replace(
            untrusted,
            user_id="",
            channel_user_id=channel_user_id,
            permissions=_server_permissions(),
        )
        user_id = await self.identity_store.resolve(normalized)
        message = replace(normalized, user_id=user_id)
        await self.message_logger.log_inbound(message)
        return message

    async def process(
        self,
        raw_payload: dict,
        channel: str,
        *,
        trusted_channel_user_id: str | None = None,
    ) -> HermesResponse:
        self._raise_if_disabled()
        if not self._pipeline_injected:
            raise HermesDisabled("Hermes default pipeline is inert; inject a bounded pipeline")
        message = await self.receive(
            raw_payload,
            channel,
            trusted_channel_user_id=trusted_channel_user_id,
        )
        response = self.pipeline(message)
        if inspect.isawaitable(response):
            response = await response
        if response.channel != message.channel or response.channel_user_id != message.channel_user_id:
            response = replace(
                response,
                channel=message.channel,
                channel_user_id=message.channel_user_id,
            )
        await self.message_logger.log_outbound(response, user_id=message.user_id)
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

    def _raise_if_disabled(self) -> None:
        if os.environ.get("HERMES_DISABLE") == "1":
            raise HermesDisabled("HERMES_DISABLE=1")
        if not self._runtime_injected:
            raise HermesDisabled("Hermes default runtime is inert; inject reviewed local components")


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
