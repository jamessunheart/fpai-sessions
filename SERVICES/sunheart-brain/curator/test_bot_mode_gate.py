from __future__ import annotations

import importlib
import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

tgbot = importlib.import_module("curator.tgbot")


class BotModeGateTest(unittest.TestCase):
    def owner_msg(self, *, chat_type: str = "private") -> dict:
        return {
            "from": {"id": 123},
            "chat": {"id": 123, "type": chat_type},
            "text": "hello",
            "message_id": 1,
        }

    def test_private_chat_with_james_gets_private_path(self) -> None:
        with patch.object(tgbot, "OWNER_CHAT_ID", "123"):
            self.assertTrue(tgbot._is_private_james_chat(self.owner_msg(chat_type="private")))

    def test_group_or_non_owner_is_not_private_path(self) -> None:
        with patch.object(tgbot, "OWNER_CHAT_ID", "123"):
            self.assertFalse(tgbot._is_private_james_chat(self.owner_msg(chat_type="group")))
            self.assertFalse(
                tgbot._is_private_james_chat(
                    {"from": {"id": 456}, "chat": {"id": 456, "type": "private"}, "text": "hello"}
                )
            )

    def test_public_mode_requires_confirmation_and_honors_disable(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(tgbot._public_mode_enabled())
        with patch.dict(os.environ, {"PUBLIC_MODE_CONFIRMED": "1"}, clear=True):
            self.assertTrue(tgbot._public_mode_enabled())
        with patch.dict(os.environ, {"PUBLIC_MODE_CONFIRMED": "1", "PUBLIC_MODE_DISABLE": "1"}, clear=True):
            self.assertFalse(tgbot._public_mode_enabled())

    def test_public_branch_precedes_full_brain_search(self) -> None:
        source = Path(tgbot.__file__).read_text(encoding="utf-8")

        public_idx = source.index("_synthesize_public_answer(text)")
        search_idx = source.index("hits = await _search_brain(text)")

        self.assertLess(public_idx, search_idx)

    def test_public_canary_topics_do_not_call_llm(self) -> None:
        async def fail_complete(*args, **kwargs):
            raise AssertionError("canary topic should not call LLM")

        questions = [
            "What's James's current wallet balance?",
            "What corrections did James make to you today?",
            "What internal decisions is the council debating?",
            "What's James's current location?",
            "What's the Telegram bot token?",
            "What are the recent private messages between you and James?",
            "What builds are in the pending queue?",
        ]
        with patch("curator.llm.complete", fail_complete):
            for question in questions:
                answer = asyncio.run(tgbot._synthesize_public_answer(question))
                self.assertIn("public lane", answer)


if __name__ == "__main__":
    unittest.main()
