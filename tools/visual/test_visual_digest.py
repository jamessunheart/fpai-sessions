from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

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
