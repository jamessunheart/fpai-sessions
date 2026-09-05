from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import tgbot
from tools.allocation import capability_ledger
from tools.allocation import opportunity_engine


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

    def test_hands_free_steering_maps_safe_spoken_phrases_only(self) -> None:
        self.assertEqual(tgbot._hands_free_steering_command("what's building right now"), "/builds")
        self.assertEqual(tgbot._hands_free_steering_command("show pending approvals"), "/pending")
        self.assertEqual(tgbot._hands_free_steering_command("what needs my decision"), "/north")
        self.assertEqual(tgbot._hands_free_steering_command("what can you do"), "/whatcanyoudo")
        self.assertEqual(tgbot._hands_free_steering_command("voice off"), "/voice off")
        self.assertIsNone(tgbot._hands_free_steering_command("build a hands-free steering bridge"))
        self.assertIsNone(tgbot._hands_free_steering_command("run git pull on the server"))

    def test_decision_payload_is_captured_not_buildable(self) -> None:
        payload = tgbot._queue_payload_for_intent(
            "should we move the digest later?",
            "decision",
            source="telegram_text",
        )

        self.assertEqual(payload["status"], "captured")
        self.assertFalse(payload["needs_build"])
        self.assertEqual(payload["build_spec"], "")

    def test_repo_root_uses_env_in_live_sh_brain_checkout_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "FPAI_Cockpit"
            (repo / "tools" / "synthesis").mkdir(parents=True)
            with mock.patch.dict(tgbot.os.environ, {"FPAI_REPO_ROOT": str(repo)}, clear=False):
                self.assertEqual(repo, tgbot._repo_root())

    async def test_owner_text_can_steer_build_status_without_queueing_build(self) -> None:
        msg = {
            "message_id": 42,
            "text": "what's building right now",
            "chat": {"id": 123, "type": "private"},
            "from": {"id": 123},
        }

        with (
            mock.patch.object(tgbot, "OWNER_CHAT_ID", "123"),
            mock.patch.object(tgbot, "_handle_command", new=mock.AsyncMock(return_value="<b>Builds</b>")) as handle_command,
            mock.patch.object(tgbot, "_append_self_check_footer", new=mock.AsyncMock(return_value="<b>Builds</b>\nfooter")),
            mock.patch.object(tgbot, "_queue_owner_intent", new=mock.AsyncMock()) as queue_intent,
            mock.patch.object(tgbot.tg, "send", new=mock.AsyncMock()) as send,
        ):
            await tgbot._handle_message(msg)

        handle_command.assert_awaited_once_with("/builds", 123)
        queue_intent.assert_not_awaited()
        send.assert_awaited_once_with("<b>Builds</b>\nfooter")

    async def test_whatcanyoudo_command_is_honest_about_boundaries(self) -> None:
        reply = await tgbot._handle_command("/whatcanyoudo", 123)

        self.assertIn("What I can do", reply or "")
        self.assertIn("Queue build/change/decision", reply or "")
        self.assertIn("What I cannot do directly", reply or "")
        self.assertIn("Execute bash", reply or "")
        self.assertIn("Move money", reply or "")

    async def test_capability_command_reports_ledger_totals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            capability_ledger.append_row(
                path,
                capability_ledger.capability_row(
                    source_type="build",
                    source_id="SPEC_d185",
                    title="Capability ledger",
                    scores={"knowledge_gained": 1, "trust": 1, "automation": 2},
                    reusable_intelligence="tools/allocation/capability_ledger.py#RUBRIC",
                    ts="2026-07-05T00:10:00Z",
                ),
            )
            with mock.patch.dict(
                tgbot.os.environ,
                {"FPAI_REPO_ROOT": str(Path(__file__).resolve().parents[3]), "FPAI_CAPABILITY_LEDGER": str(path)},
                clear=False,
            ):
                reply = await tgbot._handle_command("/capability", 123)

        self.assertIn("Capability Created", reply or "")
        self.assertIn("capability created today: +4", reply or "")
        self.assertIn("7d: <b>+4</b>", reply or "")
        self.assertIn("30d: <b>+4</b>", reply or "")

    async def test_opportunities_command_returns_ranked_portfolio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opportunities.json"
            opportunity_engine.ensure_seeded(path, now="2026-07-05T01:00:00Z")
            with (
                mock.patch.dict(
                    tgbot.os.environ,
                    {"FPAI_REPO_ROOT": str(Path(__file__).resolve().parents[3]), "FPAI_OPPORTUNITY_LEDGER": str(path)},
                    clear=False,
                ),
                mock.patch.object(tgbot.tg, "send", mock.AsyncMock()),
                mock.patch.object(tgbot.asyncio, "create_task", side_effect=lambda coro: coro.close()),
            ):
                reply = await tgbot._handle_command("/opportunities", 123)

        self.assertIn("Opportunity Portfolio", reply or "")
        self.assertIn("Top by Opportunity Score", reply or "")
        self.assertIn("Do-now by Allocation Score", reply or "")
        self.assertIn("Resource Optimization Audit", reply or "")


if __name__ == "__main__":
    unittest.main()
