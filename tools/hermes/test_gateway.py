#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path

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
    RecordingMessageLogger,
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
        async def run() -> tuple[HermesGateway, InMemoryUserChannelStore, list[HermesMessage]]:
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
            )
            web_response = await gateway.process(
                {
                    "user_id": "web-user-1",
                    "content": "hello from web",
                },
                "web",
            )

            self.assertEqual(telegram_response.content, "echo: hello from telegram")
            self.assertEqual(web_response.content, "echo: hello from web")
            self.assertEqual(len(logger.inbound), 2)
            self.assertEqual(len(logger.outbound), 2)
            return gateway, store, calls

        _gateway, store, calls = asyncio.run(run())
        self.assertEqual([call.channel for call in calls], ["telegram", "web"])
        self.assertEqual(calls[0].content, "hello from telegram")
        self.assertEqual(calls[1].content, "hello from web")
        self.assertIn(("telegram", "12345"), store.rows)
        self.assertIn(("web", "web-user-1"), store.rows)
        self.assertTrue(store.rows[("telegram", "12345")]["user_id"])
        self.assertEqual(store.rows[("web", "web-user-1")]["user_id"], "web-user-1")

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
