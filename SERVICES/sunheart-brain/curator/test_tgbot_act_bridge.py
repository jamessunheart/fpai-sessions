from __future__ import annotations

import unittest

from . import tgbot


class TelegramActBridgeTests(unittest.IsolatedAsyncioTestCase):
    def test_classifies_build_decision_journal_and_question(self) -> None:
        self.assertEqual(tgbot._classify_owner_intent("build a clean queue bridge"), "build_request")
        self.assertEqual(tgbot._classify_owner_intent("fix the bot prompt"), "build_request")
        self.assertEqual(tgbot._classify_owner_intent("should we do this tomorrow"), "decision")
        self.assertEqual(tgbot._classify_owner_intent("journal this: I felt clear today"), "journal")
        self.assertEqual(tgbot._classify_owner_intent("what built overnight?"), "question")

    def test_build_payload_matches_pending_build_predicate(self) -> None:
        payload = tgbot._queue_payload_for_intent(
            "build a voice-first Telegram bot",
            "build_request",
            source="telegram_voice",
        )

        self.assertEqual(payload["status"], "answered")
        self.assertTrue(payload["needs_build"])
        self.assertIn("build a voice-first Telegram bot", str(payload["build_spec"]))
        self.assertIn("Bot queued this only", str(payload["build_spec"]))
        self.assertIn("telegram_voice", str(payload["liveness"]))

    def test_decision_payload_is_captured_not_buildable(self) -> None:
        payload = tgbot._queue_payload_for_intent(
            "should we move the digest later?",
            "decision",
            source="telegram_text",
        )

        self.assertEqual(payload["status"], "captured")
        self.assertFalse(payload["needs_build"])
        self.assertEqual(payload["build_spec"], "")

    async def test_whatcanyoudo_command_is_honest_about_boundaries(self) -> None:
        reply = await tgbot._handle_command("/whatcanyoudo", 123)

        self.assertIn("What I can do", reply or "")
        self.assertIn("Queue build/change/decision", reply or "")
        self.assertIn("What I cannot do directly", reply or "")
        self.assertIn("Execute bash", reply or "")
        self.assertIn("Move money", reply or "")


if __name__ == "__main__":
    unittest.main()
