from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.apprentice.reflect import load_rows, render_markdown, summarize_rows, write_report


class ApprenticeReflectTest(unittest.TestCase):
    def make_rows(self) -> list[dict]:
        return [
            {
                "intent_id": "results-bottleneck-session",
                "stream": "Ventures",
                "status": "gated",
                "would_pause_at": "approve and send these 5",
                "reserved_reason": "matched Public / outbound send: send",
            },
            {
                "intent_id": "results-bottleneck-session",
                "stream": "Ventures",
                "status": "gated",
                "would_pause_at": "approve and send these 5",
                "reserved_reason": "matched Public / outbound send: send",
            },
            {
                "intent_id": "docs-helper",
                "stream": "Game",
                "status": "completed",
                "would_pause_at": None,
                "reserved_reason": None,
            },
        ]

    def test_summarize_rows_counts_repeated_bottlenecks(self) -> None:
        summary = summarize_rows(self.make_rows())

        self.assertEqual(summary["total_runs"], 3)
        self.assertEqual(summary["gated_runs"], 2)
        self.assertEqual(summary["completed_runs"], 1)
        self.assertEqual(summary["top_pauses"][0]["value"], "approve and send these 5")
        self.assertIn("Most repeated pause", summary["next_improvement"])

    def test_load_rows_reads_jsonl_and_empty_missing_file(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-apprentice-reflect-"))
        ledger = root / "ledger.jsonl"
        ledger.write_text("\n".join(json.dumps(row) for row in self.make_rows()) + "\n", encoding="utf-8")

        self.assertEqual(len(load_rows(ledger)), 3)
        self.assertEqual(load_rows(root / "missing.jsonl"), [])

    def test_render_and_write_report(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-apprentice-reflect-report-"))
        summary = summarize_rows(self.make_rows())

        text = render_markdown(summary)
        self.assertIn("Apprentice Reflection", text)
        self.assertIn("approve and send these 5", text)

        report = write_report(summary, root / "report.md")
        self.assertTrue(report.exists())
        self.assertIn("Top Pauses", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
