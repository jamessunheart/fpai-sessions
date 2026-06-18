from __future__ import annotations

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools.bandwidth import weekly_report


NOW = dt.datetime(2026, 6, 18, 12, 0, tzinfo=dt.timezone.utc)


class WeeklyBandwidthReportTest(unittest.TestCase):
    def test_week_over_week_t1_rate_and_recovered_capacity(self) -> None:
        rows = [
            {"ts": "2026-06-10T10:00:00Z", "task_type": "router", "tier_used": "T1", "outcome": "completed"},
            {"ts": "2026-06-10T10:01:00Z", "task_type": "router", "tier_used": "T3", "outcome": "escalated"},
            {"ts": "2026-06-17T10:00:00Z", "task_type": "router", "tier_used": "T1", "outcome": "completed"},
            {"ts": "2026-06-17T10:01:00Z", "task_type": "router", "tier_used": "T1", "outcome": "completed"},
            {"ts": "2026-06-17T10:02:00Z", "task_type": "router", "tier_used": "T3", "outcome": "escalated"},
            {"ts": "2026-06-17T10:03:00Z", "task_type": "council", "tier_used": "T1", "outcome": "completed"},
        ]

        report = weekly_report.build_report(rows, now=NOW)

        self.assertEqual(report.status, "RECOVERING")
        self.assertEqual(report.current_week, "2026-W25")
        self.assertEqual(report.previous_week, "2026-W24")
        self.assertEqual(report.current_t1_rate_pct, 75.0)
        self.assertEqual(report.previous_t1_rate_pct, 50.0)
        self.assertEqual(report.t1_rate_delta_pct, 25.0)
        self.assertEqual(report.recovered_decisions, 3)
        self.assertEqual(report.recovered_minutes, 60)
        self.assertEqual(report.leak_task_types, ("router",))

    def test_empty_ledger_is_explicit_no_data(self) -> None:
        report = weekly_report.build_report([], now=NOW)

        self.assertEqual(report.status, "NO_DATA")
        self.assertEqual(report.current_t1_rate_pct, 0.0)
        self.assertTrue(any("Start logging" in item for item in report.recommendations))

    def test_writes_json_markdown_and_state_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = weekly_report.build_report(
                [
                    {
                        "ts": "2026-06-18T10:00:00Z",
                        "task_type": "router",
                        "tier_used": "T1",
                        "outcome": "completed",
                    }
                ],
                now=NOW,
            )

            weekly_report.write_report(
                report,
                json_path=root / "bandwidth.json",
                markdown_path=root / "bandwidth.md",
                state_path=root / "state.md",
            )

            payload = json.loads((root / "bandwidth.json").read_text(encoding="utf-8"))
            state = (root / "state.md").read_text(encoding="utf-8")

        self.assertEqual(payload["schema"], weekly_report.SCHEMA)
        self.assertIn("# Bandwidth Ledger", state)
        self.assertIn("Recovered This Week", state)


if __name__ == "__main__":
    unittest.main()

