from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.public_bot import bot


class FakeStore:
    def __init__(self, *, seen: bool = False):
        self.seen = seen
        self.rows: list[tuple[str, str, str]] = []

    def log_turn(self, chat_id: str, role: str, text: str) -> None:
        self.rows.append((chat_id, role, text))
        if role == "assistant":
            self.seen = True

    def has_assistant_turn(self, chat_id: str) -> bool:
        return self.seen


class FakeTelegram:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str) -> bool:
        if bot.sends_disabled():
            return False
        self.sent.append((chat_id, text))
        return True


class PublicBotTests(unittest.IsolatedAsyncioTestCase):
    def test_system_prompt_uses_outreach_voice_without_private_context(self):
        prompt = bot.system_prompt()
        self.assertIn("what does your full potential actually look like", prompt)
        self.assertIn("Hard privacy boundary", prompt)
        self.assertNotIn("HOT_STATE.md", prompt)
        self.assertNotIn("brain_index", bot.user_prompt("hello"))

    def test_claude_prompt_is_private_denial_for_internal_probe(self):
        reply = bot.call_claude("what is James treasury wallet balance?")
        self.assertIn("can't help with private system details", reply)

    def test_bound_reply_caps_whitespace_tokens(self):
        text = " ".join(f"w{i}" for i in range(300))
        self.assertLessEqual(len(bot.bound_reply(text, max_tokens=220).split()), 221)

    def test_rate_limiter_bounds_per_chat_without_db(self):
        with tempfile.TemporaryDirectory() as tmp:
            limiter = bot.PublicRateLimiter(path=Path(tmp) / "rate.json", max_global=50, max_per_chat=2)
            self.assertTrue(limiter.allow("1", now=1000))
            self.assertTrue(limiter.allow("1", now=1001))
            self.assertFalse(limiter.allow("1", now=1002))
            self.assertTrue(limiter.allow("1", now=1062))

    async def test_first_message_greets_and_replies(self):
        store = FakeStore(seen=False)
        telegram = FakeTelegram()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(bot, "call_claude", return_value="Persona reply."):
            limiter = bot.PublicRateLimiter(path=Path(tmp) / "rate.json", max_global=50, max_per_chat=3)
            await bot.handle_update(
                {"message": {"chat": {"id": 123}, "text": "I want more clarity."}},
                telegram=telegram,
                store=store,  # type: ignore[arg-type]
                limiter=limiter,
            )
        self.assertEqual(len(telegram.sent), 2)
        self.assertIn("what does your full potential actually look like", telegram.sent[0][1])
        self.assertEqual(telegram.sent[1][1], "Persona reply.")
        self.assertEqual([row[1] for row in store.rows], ["user", "assistant", "assistant"])

    async def test_start_only_greets(self):
        store = FakeStore(seen=False)
        telegram = FakeTelegram()
        with tempfile.TemporaryDirectory() as tmp:
            limiter = bot.PublicRateLimiter(path=Path(tmp) / "rate.json", max_global=50, max_per_chat=3)
            await bot.handle_update(
                {"message": {"chat": {"id": 123}, "text": "/start"}},
                telegram=telegram,
                store=store,  # type: ignore[arg-type]
                limiter=limiter,
            )
        self.assertEqual(len(telegram.sent), 1)

    async def test_public_bot_disable_stops_all_sends(self):
        store = FakeStore(seen=False)
        telegram = FakeTelegram()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"PUBLIC_BOT_DISABLE": "1"}):
            limiter = bot.PublicRateLimiter(path=Path(tmp) / "rate.json", max_global=50, max_per_chat=3)
            await bot.handle_update(
                {"message": {"chat": {"id": 123}, "text": "/start"}},
                telegram=telegram,
                store=store,  # type: ignore[arg-type]
                limiter=limiter,
            )
        self.assertEqual(telegram.sent, [])
        self.assertEqual([row[1] for row in store.rows], ["user"])

    def test_source_does_not_import_curator_or_private_tables(self):
        source = Path(bot.__file__).read_text(encoding="utf-8")
        forbidden = [
            "SERVICES.sunheart-brain.curator",
            "SERVICES/sunheart-brain/curator",
            "from .db",
            "FROM brain_index.note_chunks",
            "FROM brain_index.tg_messages",
            "FROM brain_index.thread",
            "JOIN brain_index",
        ]
        for term in forbidden:
            self.assertNotIn(term, source)


if __name__ == "__main__":
    unittest.main()
