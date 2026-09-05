#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util as _ilu
import os
import sys
import unittest
import urllib.parse
from pathlib import Path
from types import ModuleType
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
CURATOR_ROOT = ROOT / "SERVICES" / "sunheart-brain"
if str(CURATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(CURATOR_ROOT))

from curator.hermes.adapters.base import ChannelAdapter
from curator.hermes.adapters.telegram_adapter import TelegramAdapter
from curator.hermes.adapters.web_adapter import WebAdapter
from curator.hermes.gateway import (
    ChannelNotRegistered,
    HermesDisabled,
    HermesGateway,
    InMemoryUserChannelStore,
    PostgresMessageLogger,
    PostgresUserChannelStore,
    RecordingMessageLogger,
    SERVER_DEFAULT_PERMISSIONS,
)
from curator.hermes.schema import HermesMessage, HermesResponse


class DummyAdapter(ChannelAdapter):
    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.sent: list[HermesResponse] = []

    def normalize(self, raw: dict) -> HermesMessage:
        raise AssertionError("not used in send routing test")

    async def send(self, response: HermesResponse) -> None:
        self.sent.append(response)

    def health_check(self) -> bool:
        return True


class FakeAsyncCursor:
    def __init__(self, row: tuple | None = None) -> None:
        self.row = row
        self.executed: list[tuple[str, tuple]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    async def execute(self, sql: str, params: tuple = ()) -> None:
        self.executed.append((sql, params))

    async def fetchone(self):
        return self.row


class FakeAsyncConnection:
    def __init__(self, row: tuple | None = None) -> None:
        self.cursor_instance = FakeAsyncCursor(row)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_exc):
        return False

    def cursor(self) -> FakeAsyncCursor:
        return self.cursor_instance


def fake_db_module(connection: FakeAsyncConnection) -> ModuleType:
    module = ModuleType("curator.db")
    module.connect = lambda: connection
    return module


class HermesGatewayTest(unittest.TestCase):
    def test_telegram_update_normalizes_to_message(self) -> None:
        msg = TelegramAdapter().normalize(
            {
                "update_id": 123,
                "message": {
                    "message_id": 456,
                    "date": 1_700_000_000,
                    "chat": {"id": 999},
                    "text": "/start beacon-42",
                },
            }
        )

        self.assertEqual(msg.channel, "telegram")
        self.assertEqual(msg.channel_user_id, "999")
        self.assertEqual(msg.message_type, "command")
        self.assertEqual(msg.content, "/start beacon-42")
        self.assertEqual(msg.beacon_id, "beacon-42")
        self.assertTrue(msg.permissions["memory"])

    def test_web_post_normalizes_to_message(self) -> None:
        msg = WebAdapter().normalize(
            {
                "user_id": "user-1",
                "content": "What changed today?",
                "permissions": {"marketing": True},
            }
        )

        self.assertEqual(msg.channel, "web")
        self.assertEqual(msg.channel_user_id, "user-1")
        self.assertEqual(msg.user_id, "user-1")
        self.assertEqual(msg.content, "What changed today?")
        self.assertTrue(msg.permissions["marketing"])

    def test_gateway_process_maps_users_and_uses_same_pipeline_for_telegram_and_web(self) -> None:
        async def run() -> tuple[
            HermesGateway,
            InMemoryUserChannelStore,
            RecordingMessageLogger,
            list[HermesMessage],
        ]:
            store = InMemoryUserChannelStore()
            logger = RecordingMessageLogger()
            calls: list[HermesMessage] = []

            async def pipeline(message: HermesMessage) -> HermesResponse:
                calls.append(message)
                return HermesResponse(
                    content=f"echo: {message.content}",
                    response_type="text",
                    channel=message.channel,
                    channel_user_id=message.channel_user_id,
                )

            gateway = HermesGateway(identity_store=store, message_logger=logger, pipeline=pipeline)
            gateway.register("telegram", TelegramAdapter())
            gateway.register("web", WebAdapter())

            telegram_response = await gateway.process(
                {
                    "message": {
                        "message_id": 1,
                        "chat": {"id": 12345},
                        "text": "hello from telegram",
                    },
                },
                "telegram",
                trusted_channel_user_id="authenticated-telegram-12345",
            )
            web_response = await gateway.process(
                {
                    "user_id": "web-user-1",
                    "content": "hello from web",
                },
                "web",
                trusted_channel_user_id="authenticated-web-user-1",
            )

            self.assertEqual(telegram_response.content, "echo: hello from telegram")
            self.assertEqual(web_response.content, "echo: hello from web")
            self.assertEqual(len(logger.inbound), 2)
            self.assertEqual(len(logger.outbound), 2)
            return gateway, store, logger, calls

        _gateway, store, logger, calls = asyncio.run(run())
        self.assertEqual([call.channel for call in calls], ["telegram", "web"])
        self.assertEqual(calls[0].content, "hello from telegram")
        self.assertEqual(calls[1].content, "hello from web")
        self.assertIn(("telegram", "authenticated-telegram-12345"), store.rows)
        self.assertIn(("web", "authenticated-web-user-1"), store.rows)
        self.assertNotIn(("web", "web-user-1"), store.rows)
        self.assertTrue(store.rows[("telegram", "authenticated-telegram-12345")]["user_id"])
        web_user_id = store.rows[("web", "authenticated-web-user-1")]["user_id"]
        self.assertNotEqual(web_user_id, "web-user-1")
        self.assertEqual(calls[1].user_id, web_user_id)
        self.assertEqual(calls[1].permissions, SERVER_DEFAULT_PERMISSIONS)
        self.assertEqual(logger.outbound_user_ids, [calls[0].user_id, calls[1].user_id])

    def test_gateway_uses_trusted_identity_and_ignores_payload_permissions(self) -> None:
        async def run() -> tuple[HermesMessage, HermesMessage, HermesMessage, InMemoryUserChannelStore]:
            store = InMemoryUserChannelStore()
            gateway = HermesGateway(identity_store=store, message_logger=RecordingMessageLogger())
            gateway.register("web", WebAdapter())
            first = await gateway.receive(
                {
                    "user_id": "claimed-universal-user",
                    "channel_user_id": "browser-session-1",
                    "content": "hello",
                    "permissions": {
                        "memory": False,
                        "marketing": True,
                        "human_followup": True,
                    },
                },
                "web",
                trusted_channel_user_id="authenticated-browser-1",
            )
            second = await gateway.receive(
                {
                    "user_id": "different-claim",
                    "channel_user_id": "browser-session-1",
                    "content": "again",
                    "permissions": {"marketing": True},
                },
                "web",
                trusted_channel_user_id="authenticated-browser-1",
            )
            spoof = await gateway.receive(
                {
                    "user_id": "claimed-universal-user",
                    "channel_user_id": "browser-session-1",
                    "content": "spoof attempt",
                    "permissions": {"marketing": True},
                },
                "web",
                trusted_channel_user_id="authenticated-browser-2",
            )
            return first, second, spoof, store

        first, second, spoof, store = asyncio.run(run())
        row = store.rows[("web", "authenticated-browser-1")]
        self.assertNotEqual(first.user_id, "claimed-universal-user")
        self.assertEqual(second.user_id, first.user_id)
        self.assertNotEqual(spoof.user_id, first.user_id)
        self.assertEqual(first.channel_user_id, "authenticated-browser-1")
        self.assertEqual(spoof.channel_user_id, "authenticated-browser-2")
        self.assertNotIn(("web", "browser-session-1"), store.rows)
        self.assertEqual(first.permissions, SERVER_DEFAULT_PERMISSIONS)
        self.assertEqual(second.permissions, SERVER_DEFAULT_PERMISSIONS)
        self.assertEqual(spoof.permissions, SERVER_DEFAULT_PERMISSIONS)
        self.assertEqual(row["permissions"], SERVER_DEFAULT_PERMISSIONS)

    def test_injected_gateway_requires_trusted_channel_identity(self) -> None:
        gateway = HermesGateway(
            identity_store=InMemoryUserChannelStore(),
            message_logger=RecordingMessageLogger(),
        )
        gateway.register("web", WebAdapter())

        with self.assertRaisesRegex(HermesDisabled, "server-resolved channel identity"):
            asyncio.run(
                gateway.receive(
                    {"user_id": "caller-selected", "content": "hi"},
                    "web",
                )
            )

    def test_default_gateway_runtime_is_inert(self) -> None:
        gateway = HermesGateway()
        gateway.register("web", WebAdapter())

        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HermesDisabled):
                asyncio.run(gateway.receive({"user_id": "u1", "content": "hi"}, "web"))

    def test_process_requires_an_explicit_bounded_pipeline(self) -> None:
        logger = RecordingMessageLogger()
        gateway = HermesGateway(
            identity_store=InMemoryUserChannelStore(),
            message_logger=logger,
        )
        gateway.register("web", WebAdapter())

        with self.assertRaises(HermesDisabled):
            asyncio.run(gateway.process({"user_id": "u1", "content": "hi"}, "web"))
        self.assertEqual(logger.inbound, [])
        self.assertEqual(logger.outbound, [])

    def test_postgres_identity_is_server_generated_and_permissions_do_not_update(self) -> None:
        connection = FakeAsyncConnection(("resolved-server-user",))
        fake_psycopg = ModuleType("psycopg")
        fake_types = ModuleType("psycopg.types")
        fake_json = ModuleType("psycopg.types.json")
        fake_json.Jsonb = lambda value: value
        fake_types.json = fake_json
        fake_psycopg.types = fake_types
        modules = {
            "curator.db": fake_db_module(connection),
            "psycopg": fake_psycopg,
            "psycopg.types": fake_types,
            "psycopg.types.json": fake_json,
        }
        message = HermesMessage(
            user_id="caller-claimed-user",
            channel="web",
            channel_user_id="browser-session-2",
            message_type="text",
            content="hello",
            beacon_id=None,
            timestamp="2026-09-03T00:00:00+00:00",
            raw={},
            permissions={"memory": False, "marketing": True, "human_followup": True},
        )

        with mock.patch.dict(sys.modules, modules):
            resolved = asyncio.run(PostgresUserChannelStore().resolve(message))

        self.assertEqual(resolved, "resolved-server-user")
        sql, params = connection.cursor_instance.executed[0]
        self.assertNotEqual(params[0], "caller-claimed-user")
        self.assertEqual(params[4], SERVER_DEFAULT_PERMISSIONS)
        self.assertNotIn("permissions = EXCLUDED.permissions", sql)

    def test_message_logger_uses_resolved_user_and_generic_roles(self) -> None:
        connection = FakeAsyncConnection()
        message = HermesMessage(
            user_id="resolved-user-3",
            channel="web",
            channel_user_id="browser-session-3",
            message_type="text",
            content="hello",
            beacon_id=None,
            timestamp="2026-09-03T00:00:00+00:00",
            raw={},
            permissions=SERVER_DEFAULT_PERMISSIONS,
        )
        response = HermesResponse(
            content="reply",
            response_type="text",
            channel="web",
            channel_user_id="browser-session-3",
        )
        logger = PostgresMessageLogger()

        with mock.patch.dict(sys.modules, {"curator.db": fake_db_module(connection)}):
            asyncio.run(logger.log_inbound(message))
            asyncio.run(logger.log_outbound(response, user_id=message.user_id))

        inbound_sql, inbound_params = connection.cursor_instance.executed[0]
        outbound_sql, outbound_params = connection.cursor_instance.executed[1]
        self.assertIn("(user_id, surface, role, text)", " ".join(inbound_sql.split()))
        self.assertEqual(inbound_params, ("resolved-user-3", "web", "user", "hello"))
        self.assertIn("(user_id, surface, role, text)", " ".join(outbound_sql.split()))
        self.assertEqual(outbound_params, ("resolved-user-3", "web", "assistant", "reply"))
        self.assertNotIn("james", inbound_params + outbound_params)

        no_identity_connection = FakeAsyncConnection()
        with mock.patch.dict(sys.modules, {"curator.db": fake_db_module(no_identity_connection)}):
            asyncio.run(PostgresMessageLogger().log_outbound(response))
        self.assertEqual(no_identity_connection.cursor_instance.executed, [])

    def test_standalone_loader_preserves_legacy_probe_send(self) -> None:
        gateway_path = CURATOR_ROOT / "curator" / "hermes" / "gateway.py"
        spec = _ilu.spec_from_file_location("fpai_test_standalone_hermes_gateway", gateway_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        gateway = _ilu.module_from_spec(spec)
        spec.loader.exec_module(gateway)

        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": true}'
        with (
            mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}),
            mock.patch.object(gateway.urllib.request, "urlopen", return_value=response) as urlopen,
        ):
            sent = gateway.send_message(platform="telegram", handle="12345", text="hello")

        self.assertTrue(sent)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(
            urllib.parse.parse_qs(request.data.decode("utf-8")),
            {"chat_id": ["12345"], "text": ["hello"]},
        )
        self.assertEqual(urlopen.call_args.kwargs, {"timeout": 15})

        with mock.patch.object(gateway.urllib.request, "urlopen") as urlopen:
            self.assertFalse(gateway.send_message(platform="sms", handle="12345", text="hello"))
        urlopen.assert_not_called()

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch.object(gateway.urllib.request, "urlopen") as urlopen,
        ):
            self.assertFalse(gateway.send_message(platform="telegram", handle="12345", text="hello"))
        urlopen.assert_not_called()

        with (
            mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}),
            mock.patch.object(gateway.urllib.request, "urlopen", side_effect=OSError("offline")),
        ):
            self.assertFalse(gateway.send_message(platform="telegram", handle="12345", text="hello"))

        for body in (b"not-json", b'{"ok": false}'):
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = body
            with (
                mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}),
                mock.patch.object(gateway.urllib.request, "urlopen", return_value=response),
            ):
                self.assertFalse(gateway.send_message(platform="telegram", handle="12345", text="hello"))

    def test_send_routes_to_correct_adapter(self) -> None:
        async def run() -> DummyAdapter:
            adapter = DummyAdapter("sms")
            gateway = HermesGateway(identity_store=InMemoryUserChannelStore(), message_logger=RecordingMessageLogger())
            gateway.register("sms", adapter)
            await gateway.send(
                HermesResponse(
                    content="reply",
                    response_type="text",
                    channel="sms",
                    channel_user_id="+15551234567",
                )
            )
            return adapter

        adapter = asyncio.run(run())
        self.assertEqual(len(adapter.sent), 1)
        self.assertEqual(adapter.sent[0].channel_user_id, "+15551234567")

    def test_unknown_channel_raises_channel_not_registered(self) -> None:
        async def run() -> None:
            gateway = HermesGateway(identity_store=InMemoryUserChannelStore(), message_logger=RecordingMessageLogger())
            await gateway.receive({"content": "hi"}, "instagram")

        with self.assertRaises(ChannelNotRegistered):
            asyncio.run(run())

    def test_kill_switch_disables_gateway(self) -> None:
        async def run() -> None:
            gateway = HermesGateway(identity_store=InMemoryUserChannelStore(), message_logger=RecordingMessageLogger())
            gateway.register("web", WebAdapter())
            await gateway.receive({"user_id": "u1", "content": "hi"}, "web")

        old = os.environ.get("HERMES_DISABLE")
        os.environ["HERMES_DISABLE"] = "1"
        try:
            with self.assertRaises(HermesDisabled):
                asyncio.run(run())
        finally:
            if old is None:
                os.environ.pop("HERMES_DISABLE", None)
            else:
                os.environ["HERMES_DISABLE"] = old


if __name__ == "__main__":
    unittest.main()
