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
        ) as alert, mock.patch.object(
            tgbot,
            "_self_check_state",
            new=mock.AsyncMock(return_value={
                "model": {
                    "label": "llama-fallback",
                    "actual": "ollama:llama3.2:3b",
                    "fallback_reason": "exited 1: not logged in",
                },
                "context": {"ok": False, "age_seconds": 7200, "reason": "stale", "bytes": 10},
                "voice": {"ok": False},
                "queue": {"ok": True},
                "recent_warnings": ["fallback warning"],
            }),
        ):
            answer = await tgbot._synthesize_answer("what is current?", [], conversation_id="123")

        self.assertIn("Fallback answer", answer)
        self.assertIn("Health: model llama-fallback", answer)
        self.assertIn("⚠️ on fallback model", answer)
        self.assertIn("my live state is 2.0h old", answer)
        self.assertIn("voice down", answer)
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

    async def test_startup_self_test_sends_one_degraded_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            original_path = tgbot.MODEL_HEALTH_PATH
            tgbot.MODEL_HEALTH_PATH = Path(tmp) / "model_health.json"
            try:
                with mock.patch.object(tgbot, "_claude_health", new=mock.AsyncMock(return_value={
                    "ok": False,
                    "model": "llama-fallback",
                    "reason": "not logged in",
                })), mock.patch.object(tgbot, "_queue_health", new=mock.AsyncMock(return_value={
                    "ok": True,
                    "table_exists": True,
                    "insert_privilege": True,
                    "reason": "reachable",
                })), mock.patch.object(tgbot, "_hot_state_health", return_value={
                    "ok": False,
                    "path": "/tmp/HOT_STATE.md",
                    "age_seconds": None,
                    "bytes": 0,
                    "reason": "empty",
                }), mock.patch.object(tgbot, "_voice_health", return_value={
                    "ok": False,
                    "reason": "missing faster-whisper-or-openai-whisper",
                }), mock.patch.object(tgbot, "_recent_log_warnings", return_value=[]), mock.patch.object(
                    tgbot.tg, "send", new=mock.AsyncMock(return_value=True)
                ) as send:
                    await tgbot._startup_self_test()
            finally:
                tgbot.MODEL_HEALTH_PATH = original_path

        send.assert_awaited_once()
        line = send.await_args.args[0]
        self.assertIn("bot started degraded:", line)
        self.assertIn("on fallback model", line)
        self.assertIn("voice STT is down", line)

    async def test_health_command_returns_full_state(self) -> None:
        with mock.patch.object(tgbot, "_claude_health", new=mock.AsyncMock(return_value={
            "ok": True,
            "model": "Sonnet",
            "reason": "ok",
        })), mock.patch.object(tgbot, "_self_check_state", new=mock.AsyncMock(return_value={
            "model": {"label": "Sonnet", "actual": "Sonnet", "fallback_reason": ""},
            "context": {"ok": True, "path": "/tmp/HOT_STATE.md", "age_seconds": 30, "bytes": 123, "reason": "fresh"},
            "voice": {"ok": True, "faster_whisper": False, "openai_whisper": True},
            "queue": {"ok": True, "table_exists": True, "insert_privilege": True, "reason": "reachable"},
            "recent_warnings": [],
        })):
            reply = await tgbot._handle_command("/health", 123)

        self.assertIn("Bot health", reply)
        self.assertIn("Model:", reply)
        self.assertIn("Context:", reply)
        self.assertIn("Voice STT:", reply)
        self.assertIn("Queue-write reachable:", reply)


if __name__ == "__main__":
    unittest.main()
