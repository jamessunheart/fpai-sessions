from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from . import llm, tgbot


class TGBotModelHealthTest(unittest.IsolatedAsyncioTestCase):
    async def test_synthesize_alerts_and_labels_llama_fallback(self) -> None:
        fallback = llm.LLMResult(
            "Fallback answer",
            "ollama:llama3.2:3b",
            "hash",
            10,
            4,
            fallback_from="claude-cli",
            fallback_reason="exited 1: not logged in",
        )

        with mock.patch.object(
            tgbot,
            "_context_blocks_for_route",
            return_value={
                "system_state": False,
                "buildstream": False,
                "corrections": False,
                "becoming": False,
                "brain_search": False,
            },
        ), mock.patch.object(
            tgbot, "_recent_chat_history_context", new=mock.AsyncMock(return_value="")
        ), mock.patch.object(
            llm, "complete", new=mock.AsyncMock(return_value=fallback)
        ), mock.patch.object(
            tgbot, "_alert_model_fallback", new=mock.AsyncMock()
        ) as alert:
            answer = await tgbot._synthesize_answer("what is current?", [], conversation_id="123")

        self.assertIn("Fallback answer", answer)
        self.assertIn("Model: llama-fallback", answer)
        alert.assert_awaited_once_with("exited 1: not logged in")

    async def test_model_alert_writes_counter_and_sends_ops_line(self) -> None:
        original_path = tgbot.MODEL_HEALTH_PATH
        with tempfile.TemporaryDirectory() as tmp:
            tgbot.MODEL_HEALTH_PATH = Path(tmp) / "model_health.json"
            try:
                with mock.patch.object(tgbot.tg, "send", new=mock.AsyncMock(return_value=True)) as send:
                    await tgbot._alert_model_fallback("exited 1: not logged in")
            finally:
                path = tgbot.MODEL_HEALTH_PATH
                tgbot.MODEL_HEALTH_PATH = original_path

            data = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(data["status"], "degraded")
        self.assertEqual(data["counters"]["fallback"], 1)
        self.assertIn("not logged in", data["last_reason"])
        sent = send.await_args.args[0]
        self.assertIn("TG bot fell back to llama3.2:3b", sent)
        self.assertIn("not logged in", sent)
        self.assertIn("chat_id", send.await_args.kwargs)

    async def test_startup_self_test_alerts_on_failure(self) -> None:
        with mock.patch.object(llm, "claude_cli_self_test", new=mock.AsyncMock(return_value=(False, "not logged in"))), \
                mock.patch.object(tgbot, "_alert_model_fallback", new=mock.AsyncMock()) as alert:
            await tgbot._startup_claude_self_test()

        alert.assert_awaited_once_with("not logged in", startup=True)


if __name__ == "__main__":
    unittest.main()
