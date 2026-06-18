from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.bandwidth import routing_log


NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.timezone.utc)


class RoutingLogTest(unittest.TestCase):
    def test_log_routing_decision_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "routing_log.jsonl"

            result = routing_log.log_routing_decision(
                task_type="auto-routing",
                tier_used="T1",
                outcome="completed",
                ledger_path=ledger,
                now=NOW,
            )

            self.assertTrue(result["logged"])
            rows = ledger.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 1)
            parsed = json.loads(rows[0])
            self.assertEqual(parsed["task_type"], "auto-routing")
            self.assertEqual(parsed["tier_used"], "T1")
            self.assertEqual(parsed["outcome"], "completed")
            self.assertEqual(parsed["ts"], "2026-06-18T12:00:00Z")

    def test_disable_switch_skips_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "routing_log.jsonl"
            old = os.environ.get("BANDWIDTH_LEDGER_DISABLE")
            os.environ["BANDWIDTH_LEDGER_DISABLE"] = "1"
            try:
                result = routing_log.log_routing_decision(
                    task_type="auto-routing",
                    tier_used="T1",
                    outcome="completed",
                    ledger_path=ledger,
                    now=NOW,
                )
            finally:
                if old is None:
                    os.environ.pop("BANDWIDTH_LEDGER_DISABLE", None)
                else:
                    os.environ["BANDWIDTH_LEDGER_DISABLE"] = old

            self.assertFalse(result["logged"])
            self.assertFalse(ledger.exists())

    def test_invalid_tier_returns_non_blocking_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = routing_log.log_routing_decision(
                task_type="auto-routing",
                tier_used="bad",
                outcome="completed",
                ledger_path=Path(tmp) / "routing_log.jsonl",
                now=NOW,
            )

        self.assertFalse(result["logged"])
        self.assertIn("ValueError", result["reason"])


if __name__ == "__main__":
    unittest.main()

