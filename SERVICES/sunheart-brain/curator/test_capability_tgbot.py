from __future__ import annotations

import os
import time
import unittest
from unittest.mock import AsyncMock, patch

from . import tgbot


class TelegramCapabilityFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tgbot._CAPABILITY_PENDING.clear()

    def tearDown(self):
        tgbot._CAPABILITY_PENDING.clear()

    def test_default_grants_only_read_only_search(self):
        with patch.dict(os.environ, {}, clear=True):
            agent = tgbot._TelegramCapabilityAgent("u1")

        self.assertTrue(agent.can("search_web"))
        self.assertFalse(agent.can("send_email"))
        self.assertFalse(agent.can("book_calendar"))

    async def test_declined_pending_action_is_audited(self):
        tgbot._CAPABILITY_PENDING["123"] = {
            "capability": "send_email",
            "stage": "confirm",
            "params": {"to": "a@example.com", "subject": "Hi", "body": "Body"},
            "created_at": time.time(),
        }
        sent = AsyncMock()
        logged = AsyncMock()

        with patch.object(tgbot.tg, "send", sent), patch.object(tgbot, "_log_capability_cancelled", logged):
            handled = await tgbot._handle_capability_turn(123, "u1", "no")

        self.assertTrue(handled)
        self.assertNotIn("123", tgbot._CAPABILITY_PENDING)
        logged.assert_awaited_once()
        self.assertEqual(logged.await_args.args[0], "u1")
        self.assertEqual(logged.await_args.args[1], "send_email")
        self.assertEqual(logged.await_args.args[3], "user_cancelled")
        sent.assert_awaited_once_with("Cancelled.")

    async def test_expired_pending_action_is_audited_and_not_executed(self):
        tgbot._CAPABILITY_PENDING["123"] = {
            "capability": "book_calendar",
            "stage": "confirm",
            "params": {"title": "Meet", "date": "2026-06-17", "time": "09:00", "duration": 30},
            "created_at": 0,
        }
        sent = AsyncMock()
        logged = AsyncMock()
        executed = AsyncMock()

        with (
            patch.object(tgbot.tg, "send", sent),
            patch.object(tgbot, "_log_capability_cancelled", logged),
            patch.object(tgbot, "_execute_tg_capability", executed),
        ):
            handled = await tgbot._handle_capability_turn(123, "u1", "yes")

        self.assertTrue(handled)
        self.assertNotIn("123", tgbot._CAPABILITY_PENDING)
        logged.assert_awaited_once()
        self.assertEqual(logged.await_args.args[3], "timeout")
        executed.assert_not_awaited()

    async def test_proposal_sets_expiring_pending_state(self):
        sent = AsyncMock()
        with patch.object(tgbot.tg, "send", sent):
            handled = await tgbot._handle_capability_turn(123, "u1", "look up capability execution")

        self.assertTrue(handled)
        self.assertEqual(tgbot._CAPABILITY_PENDING["123"]["capability"], "search_web")
        self.assertEqual(tgbot._CAPABILITY_PENDING["123"]["stage"], "proposal")
        self.assertGreater(tgbot._CAPABILITY_PENDING["123"]["created_at"], 0)


if __name__ == "__main__":
    unittest.main()
