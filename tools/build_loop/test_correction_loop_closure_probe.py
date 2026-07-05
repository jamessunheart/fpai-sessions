from __future__ import annotations

import asyncio
import contextlib
import io
import json
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.build_loop import correction_loop_closure_probe as probe


ROOT = Path(__file__).resolve().parents[2]
SERVER_LOOP = ROOT / "tools" / "build_loop" / "server_build_loop.sh"


class CorrectionLoopClosureProbeTest(unittest.TestCase):
    def tearDown(self) -> None:
        for name in list(sys.modules):
            if name == "curator" or name.startswith("curator."):
                sys.modules.pop(name, None)

    def test_fingerprint_normalizes_case_and_whitespace(self) -> None:
        first = probe.CorrectionRow(
            row_id="1",
            conversation_id="chat",
            bot_turn_id="a",
            original_response="  James should review it later.\n",
            james_correction="Actually, James stays upstream.",
            captured_at="2026-06-26T00:00:00Z",
        )
        second = probe.CorrectionRow(
            row_id="2",
            conversation_id="CHAT",
            bot_turn_id="b",
            original_response="james   should REVIEW it later.",
            james_correction=" actually, james stays upstream. ",
            captured_at="2026-06-26T00:01:00Z",
        )

        self.assertEqual(probe.correction_fingerprint(first), probe.correction_fingerprint(second))

    def test_find_recurrences_flags_same_pair_at_threshold(self) -> None:
        rows = [
            probe.CorrectionRow("1", "chat", "a", "old answer", "correct answer", "2026-06-26T00:00:00Z"),
            probe.CorrectionRow("2", "chat", "b", "OLD  answer", "Correct answer", "2026-06-26T00:05:00Z"),
            probe.CorrectionRow("3", "chat", "c", "different", "correct answer", "2026-06-26T00:06:00Z"),
        ]

        found = probe.find_recurrences(rows, threshold=2)

        self.assertEqual(1, len(found))
        self.assertEqual(2, found[0].count)
        self.assertEqual("2026-06-26T00:05:00Z", found[0].latest_seen)

    def test_run_probe_passes_without_duplicate(self) -> None:
        root = self.make_curator(
            [
                ("1", "chat", "a", "old answer", "correct answer", "2026-06-26T00:00:00Z"),
                ("2", "chat", "b", "another answer", "another correction", "2026-06-26T00:05:00Z"),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="fpai-loop-probe-") as tmp:
            result = asyncio.run(
                probe.run_probe(curator_parent=root, ops_ledger=Path(tmp) / "ops.jsonl")
            )

        self.assertEqual("pass", result["status"])
        self.assertFalse(result["alert_recommended"])

    def test_run_probe_fails_and_recommends_first_alert(self) -> None:
        root = self.make_curator(
            [
                ("1", "chat", "a", "old answer", "correct answer", "2026-06-26T00:00:00Z"),
                ("2", "chat", "b", "old answer", "correct answer", "2026-06-26T00:05:00Z"),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="fpai-loop-probe-") as tmp:
            result = asyncio.run(
                probe.run_probe(curator_parent=root, ops_ledger=Path(tmp) / "ops.jsonl")
            )

        self.assertEqual("fail", result["status"])
        self.assertEqual(2, result["count"])
        self.assertTrue(result["alert_recommended"])
        self.assertIn("fingerprint", result)

    def test_cooldown_suppresses_duplicate_alert_for_same_fingerprint(self) -> None:
        row = probe.CorrectionRow(
            "1", "chat", "a", "old answer", "correct answer", "2026-06-26T00:00:00Z"
        )
        fingerprint = probe.correction_fingerprint(row)
        with tempfile.TemporaryDirectory(prefix="fpai-loop-probe-") as tmp:
            ledger = Path(tmp) / "ops.jsonl"
            ledger.write_text(
                json.dumps(
                    {
                        "ts": "2026-06-26T00:10:00Z",
                        "loop": "correction-loop",
                        "event": "correction-loop:fail",
                        "fingerprint": fingerprint,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            alerted = probe.alert_recently_sent(
                ops_ledger=ledger,
                fingerprint=fingerprint,
                now=datetime(2026, 6, 26, 1, 0, tzinfo=timezone.utc),
                cooldown_hours=24,
            )

        self.assertTrue(alerted)

    def test_cli_returns_one_on_recurrence(self) -> None:
        root = self.make_curator(
            [
                ("1", "chat", "a", "old answer", "correct answer", "2026-06-26T00:00:00Z"),
                ("2", "chat", "b", "old answer", "correct answer", "2026-06-26T00:05:00Z"),
            ]
        )
        with tempfile.TemporaryDirectory(prefix="fpai-loop-probe-") as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = probe.main(["--curator-parent", str(root), "--ops-ledger", str(Path(tmp) / "ops.jsonl")])

        self.assertEqual(1, rc)
        self.assertIn('"status": "fail"', out.getvalue())

    def test_server_loop_runs_closure_probe_after_retention_smoke(self) -> None:
        text = SERVER_LOOP.read_text(encoding="utf-8")

        retention = text.index("run_correction_retention_smoke")
        closure = text.index("run_correction_loop_closure_probe", retention)
        # Auto-merge is SILENT now (James directive 2026-06-18: no TG ask; only BLOCKED surfaces),
        # so the old `tg "$V · AUTO-MERGED'` notification was intentionally removed. The real
        # guarantee — closure probe runs AFTER the retention smoke — is what we assert.
        self.assertLess(retention, closure)
        self.assertIn("CORRECTION_LOOP_CLOSURE_PROBE_DISABLE", text)
        self.assertIn("correction_loop_closure_probe.py", text)
        self.assertIn('"correction-loop:pass"', text)
        self.assertIn('"correction-loop:fail"', text)
        self.assertIn("queue_correction_loop_closure_followup", text)

    def make_curator(self, rows: list[tuple[str, str, str, str, str, str]]) -> Path:
        root = Path(tempfile.mkdtemp(prefix="fpai-loop-probe-curator-"))
        package = root / "curator"
        package.mkdir()
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "db.py").write_text(
            textwrap.dedent(
                f"""
                ROWS = {rows!r}

                class Cursor:
                    def __init__(self):
                        self.rows = []

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, exc_type, exc, tb):
                        return False

                    async def execute(self, sql, params=()):
                        normalized = " ".join(sql.split()).lower()
                        if "from brain_index.corrections" not in normalized:
                            raise AssertionError(sql)
                        limit = int(params[-1])
                        self.rows = ROWS[:limit]

                    async def fetchall(self):
                        return self.rows

                class Connection:
                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, exc_type, exc, tb):
                        return False

                    def cursor(self):
                        return Cursor()

                def connect():
                    return Connection()
                """
            ),
            encoding="utf-8",
        )
        return root


if __name__ == "__main__":
    unittest.main()
