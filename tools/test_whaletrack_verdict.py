from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools import whaletrack_verdict


class WhaletrackVerdictTest(unittest.TestCase):
    def write_jsonl(self, rows) -> Path:
        path = Path(tempfile.mkdtemp(prefix="fpai-verdict-test-")) / "trades.jsonl"
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        return path

    def test_report_joins_live_and_paper_and_computes_delta(self) -> None:
        live = self.write_jsonl(
            [
                {"phase": "entry", "symbol": "ETH", "side": "short", "ts": "2026-06-11T00:00:00+00:00", "price": 3600},
                {"phase": "exit", "symbol": "ETH", "side": "short", "ts": "2026-06-11T01:00:00+00:00", "pnl": 12.5},
            ]
        )
        paper = self.write_jsonl(
            [
                {"phase": "entry", "symbol": "ETH", "side": "short", "ts": "2026-06-11T00:00:10+00:00", "price": 3601},
                {"phase": "exit", "symbol": "ETH", "side": "short", "ts": "2026-06-11T01:00:00+00:00", "pnl": 15.0},
            ]
        )

        report = whaletrack_verdict.render_report(live, paper)

        self.assertIn("Live actual", report)
        self.assertIn("Paper would-have", report)
        self.assertIn("Delta live-paper", report)
        self.assertIn("| ETH | short |", report)
        self.assertIn("-2.50", report)


if __name__ == "__main__":
    unittest.main()
