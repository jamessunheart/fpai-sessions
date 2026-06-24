from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from tools.visual import visual_digest


FIXTURE_CONTEXT = {
    "generated_at": "2026-06-16 15:00 EEST",
    "date": "Tuesday, 2026-06-16",
    "top_three": ["Keep James upstream.", "Log measured proof.", "Ship the next clean move."],
    "open_decisions": {
        "count": 2,
        "items": [
            {"id": "d1", "title": "Approve merge for visual digest", "status": "awaiting"},
            {"id": "d2", "title": "Pick next build", "status": "open"},
        ],
    },
    "build_state": {
        "currently_building": [{"id": "SPEC_d026_visual-digest-agent-v0-1-daily-p", "branch": "build/SPEC_d026"}],
        "recently_merged": [{"id": "SPEC_cartographer-auto-refresh", "branch": "build/SPEC_cartographer"}],
        "queued": [{"id": "SPEC_next", "path": "core/BUILD/specs/SPEC_next.md"}],
        "queued_count": 1,
    },
    "server_health": [
        {"name": "fpai-build-loop", "state": "active", "ok": True},
        {"name": "fpai-morning-digest", "state": "failed", "ok": False},
    ],
    "proof_today": 3,
    "event_count": 9,
    "backup_status": {
        "icon": "green",
        "label": "backup complete + offsite",
        "detail": "/opt/fpai-backup/brain_2026-06-16_03-00.sql.gz",
        "failure_count": 0,
    },
    "next_move": "Check service health: fpai-morning-digest",
}


class VisualDigestTest(unittest.TestCase):
    def test_template_renders_fixture_context(self) -> None:
        html = visual_digest.render_template(FIXTURE_CONTEXT)
        self.assertIn("FPOS Daily Pulse", html)
        self.assertIn("Open Decisions", html)
        self.assertIn("Server Health", html)
        self.assertIn("Brain Backup", html)
        self.assertIn("Check service health", html)

    def test_ops_ledger_reader_handles_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "ops_ledger.jsonl"
            ledger.write_text("", encoding="utf-8")
            state = visual_digest.load_ops_state(ledger)
        self.assertEqual(state["event_count"], 0)
        self.assertEqual(state["proof_count"], 0)
        self.assertEqual(state["events"], [])

    def test_run_produces_png_over_10kb_and_calls_telegram_with_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "visuals"
            ledger = Path(tmp) / "ops_ledger.jsonl"
            sender = Mock(return_value=True)

            def fake_render(_html: str, png_path: Path) -> bool:
                png_path.parent.mkdir(parents=True, exist_ok=True)
                png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + (b"0" * 12000))
                return True

            with patch.object(visual_digest, "build_context", return_value=FIXTURE_CONTEXT):
                result = asyncio.run(
                    visual_digest.run(
                        output_root=root,
                        ops_ledger=ledger,
                        render_func=fake_render,
                        send_func=sender,
                    )
                )

            self.assertTrue(result.rendered)
            self.assertTrue(result.sent)
            self.assertIsNotNone(result.png_path)
            assert result.png_path is not None
            self.assertTrue(result.png_path.exists())
            self.assertGreater(result.png_path.stat().st_size, 10_000)
            sender.assert_called_once_with(str(result.png_path))
            self.assertIn('"type": "visual_digest"', ledger.read_text(encoding="utf-8"))
            self.assertIn(str(result.png_path), ledger.read_text(encoding="utf-8"))

    def test_public_summary_strips_sensitive_content(self) -> None:
        context = {
            **FIXTURE_CONTEXT,
            "top_three": [
                "Treasury runway is $12,345 and wallet 0x1234567890abcdef1234567890abcdef12345678",
                "Correction log: you forgot the prior answer",
                "Free observation is the public hook for d052",
                "Use TELEGRAM_BOT_TOKEN from DATABASE_URL",
            ],
            "next_move": "Resolve SPEC_d052_cora-nation-public-story-feed-v before spend hits 300 USDC",
        }

        summary = visual_digest.render_public_summary(context)

        self.assertIn("Cora Nation story feed", summary)
        self.assertIn("[private figure]", summary)
        self.assertIn("[private address]", summary)
        self.assertNotIn("d052", summary.lower())
        self.assertNotIn("SPEC_d052", summary)
        self.assertNotIn("Correction log", summary)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", summary)
        self.assertNotIn("300 USDC", summary)
        visual_digest.validate_public_summary(summary)

    def test_public_summary_escapes_html_and_strips_private_links(self) -> None:
        context = {
            **FIXTURE_CONTEXT,
            "top_three": [
                '<span data-x="1">Free observation</span>',
                "Free observation is the public hook.",
            ],
            "next_move": '<script>alert("x")</script> then read https://private.example/status',
        }
        with patch.dict("os.environ", {"ONE_CHAT_BOT_LINK": "https://t.me/fullpotential_bot"}):
            summary = visual_digest.render_public_summary(context)

        self.assertNotIn("<span", summary)
        self.assertNotIn("<script>", summary)
        self.assertNotIn("https://private.example", summary)
        self.assertIn("&lt;span", summary)
        self.assertIn("[private link]", summary)
        self.assertIn("https://t.me/fullpotential_bot", summary)
        visual_digest.validate_public_summary(summary)

    def test_public_bot_link_rejects_non_telegram_urls(self) -> None:
        with patch.dict("os.environ", {"ONE_CHAT_BOT_LINK": "https://private.example/bot"}):
            summary = visual_digest.render_public_summary(FIXTURE_CONTEXT)
        self.assertNotIn("https://private.example", summary)
        self.assertNotIn("Get this for your life", summary)

    def test_public_summary_validator_rejects_leaks(self) -> None:
        with self.assertRaises(ValueError):
            visual_digest.validate_public_summary("Post decision d052 with TELEGRAM_BOT_TOKEN and $100")

    def test_run_sends_public_story_when_channel_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "visuals"
            ledger = Path(tmp) / "ops_ledger.jsonl"
            private_sender = Mock(return_value=True)
            public_sender = Mock(return_value=True)

            def fake_render(_html: str, png_path: Path) -> bool:
                png_path.parent.mkdir(parents=True, exist_ok=True)
                png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + (b"0" * 12000))
                return True

            with patch.object(visual_digest, "build_context", return_value=FIXTURE_CONTEXT):
                result = asyncio.run(
                    visual_digest.run(
                        output_root=root,
                        ops_ledger=ledger,
                        render_func=fake_render,
                        send_func=private_sender,
                        public_send_func=public_sender,
                        public_channel_id="@cora_public",
                    )
                )

            self.assertTrue(result.sent)
            self.assertTrue(result.public_sent)
            private_sender.assert_called_once()
            public_sender.assert_called_once()
            public_text = public_sender.call_args.args[0]
            self.assertIn("Cora Nation story feed", public_text)
            self.assertEqual(public_sender.call_args.kwargs["chat_id"], "@cora_public")
            ledger_text = ledger.read_text(encoding="utf-8")
            self.assertIn('"type": "public_story_digest"', ledger_text)
            self.assertIn('"sent": true', ledger_text)

    def test_no_send_disables_public_story_even_when_env_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                "os.environ",
                {
                    "VISUAL_DIGEST_PUBLIC_CHANNEL_ID": "@cora_public",
                    "TELEGRAM_BOT_TOKEN": "test-token",
                },
            ), patch.object(visual_digest, "run", new_callable=AsyncMock) as run_mock:
                run_mock.return_value = visual_digest.DigestResult(
                    Path(tmp) / "daily.png",
                    None,
                    True,
                    True,
                    True,
                    public_sent=False,
                )
                code = visual_digest.main(["--output-root", tmp, "--ops-ledger", str(Path(tmp) / "ops.jsonl"), "--no-send"])

        self.assertEqual(code, 0)
        self.assertFalse(run_mock.call_args.kwargs["public_enabled"])
        self.assertIsNone(run_mock.call_args.kwargs["public_channel_id"])

    def test_kill_switch_exits_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"VISUAL_DIGEST_DISABLE": "1"}):
                result = asyncio.run(
                    visual_digest.run(
                        output_root=Path(tmp),
                        ops_ledger=Path(tmp) / "ops_ledger.jsonl",
                        render_func=Mock(return_value=True),
                        send_func=Mock(return_value=True),
                    )
                )
        self.assertTrue(result.skipped)
        self.assertFalse(result.rendered)


if __name__ == "__main__":
    unittest.main()
