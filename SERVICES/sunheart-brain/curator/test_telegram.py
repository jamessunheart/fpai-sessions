from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("telegram.py")
SPEC = importlib.util.spec_from_file_location("telegram", MODULE_PATH)
assert SPEC and SPEC.loader
telegram = importlib.util.module_from_spec(SPEC)
sys.modules["telegram"] = telegram
SPEC.loader.exec_module(telegram)


class FakeResponse:
    status_code = 200
    text = "ok"

    def json(self) -> dict:
        return {"result": {"message_id": 42}}


class FakeAsyncClient:
    posts: list[tuple[str, dict | None]] = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, *, json: dict | None = None, **kwargs):
        self.posts.append((url, json))
        return FakeResponse()


class TelegramTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        FakeAsyncClient.posts = []
        telegram.BOT_TOKEN = "token"
        telegram.CHAT_ID = "owner-chat"

    async def test_send_keeps_explicit_chat_id_support(self) -> None:
        with patch.object(telegram.httpx, "AsyncClient", FakeAsyncClient):
            sent = await telegram.send("hello", chat_id=123)

        self.assertTrue(sent)
        self.assertEqual(FakeAsyncClient.posts[0][1]["chat_id"], "123")

    async def test_send_typing_uses_requested_chat(self) -> None:
        with patch.object(telegram.httpx, "AsyncClient", FakeAsyncClient):
            await telegram.send_typing(chat_id="stream-chat")

        payload = FakeAsyncClient.posts[0][1]
        self.assertEqual(payload["chat_id"], "stream-chat")
        self.assertEqual(payload["action"], "typing")

    async def test_send_and_get_id_returns_telegram_message_id(self) -> None:
        with patch.object(telegram.httpx, "AsyncClient", FakeAsyncClient):
            message_id = await telegram.send_and_get_id("working", chat_id="stream-chat")

        self.assertEqual(message_id, 42)
        self.assertEqual(FakeAsyncClient.posts[0][1]["chat_id"], "stream-chat")


if __name__ == "__main__":
    unittest.main()
