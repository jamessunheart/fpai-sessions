import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from tools.allocation import capability_ledger as ledger


NOW = dt.datetime(2026, 7, 5, 12, 0, tzinfo=dt.timezone.utc)


class CapabilityLedgerTest(unittest.TestCase):
    def test_missing_scores_are_zero_and_total_is_axis_sum(self) -> None:
        row = ledger.capability_row(
            source_type="build",
            source_id="SPEC_zero",
            title="Zero proof",
            scores={"time_saved": 2, "cash_flow": None, "trust": "bad"},
            reusable_intelligence="core/STATE/ACADEMY.md#zero-proof",
            ts="2026-07-05T01:00:00Z",
        )

        self.assertEqual(row["capability_gain"]["time_saved"], 2.0)
        self.assertEqual(row["capability_gain"]["cash_flow"], 0.0)
        self.assertEqual(row["capability_gain"]["trust"], 0.0)
        self.assertEqual(row["total_capability_gain"], 2.0)

    def test_positive_score_requires_reusable_intelligence_pointer(self) -> None:
        with self.assertRaises(ValueError):
            ledger.capability_row(
                source_type="proof",
                source_id="SPEC_missing_pointer",
                title="Missing pointer",
                scores={"knowledge_gained": 1},
            )

    def test_period_summary_and_trend_read_only_rollups(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ledger.jsonl"
            rows = [
                ledger.capability_row(
                    source_type="build",
                    source_id="SPEC_today",
                    title="Today",
                    scores={"time_saved": 1, "automation": 2},
                    reusable_intelligence="core/BUILD/results/today.md",
                    ts="2026-07-05T02:00:00Z",
                ),
                ledger.capability_row(
                    source_type="build",
                    source_id="SPEC_yesterday",
                    title="Yesterday",
                    scores={"trust": 3},
                    reusable_intelligence="core/BUILD/results/yesterday.md",
                    ts="2026-07-04T23:00:00Z",
                ),
            ]
            for row in rows:
                ledger.append_row(path, row)

            today = ledger.period_summary(path, days=1, now=NOW)
            thirty = ledger.period_summary(path, days=30, now=NOW)
            trend = ledger.trend(path, days=2, now=NOW)

            self.assertEqual(today["total_capability_gain"], 3.0)
            self.assertEqual(today["axis_totals"]["automation"], 2.0)
            self.assertEqual(thirty["total_capability_gain"], 6.0)
            self.assertEqual([day["date"] for day in trend], ["2026-07-04", "2026-07-05"])
            self.assertEqual([day["total_capability_gain"] for day in trend], [3.0, 3.0])

    def test_expected_vs_realized_delta_is_recorded_for_estimator_training(self) -> None:
        row = ledger.capability_row(
            source_type="intervention",
            source_id="nightly-7q",
            title="Nightly estimate",
            expected_capability_gain={"automation": 5},
            scores={"automation": 3},
            reusable_intelligence="core/STATE/ACADEMY.md#nightly-estimate",
        )

        self.assertEqual(row["expected_total_capability_gain"], 5.0)
        self.assertEqual(row["capability_estimate_delta"], -2.0)

    def test_format_summary_uses_contract_line(self) -> None:
        text = ledger.format_summary({
            "total_capability_gain": 46,
            "axis_totals": {
                "time_saved": 18,
                "knowledge_gained": 7,
                "cash_flow": 12,
                "trust": 5,
                "automation": 4,
            },
        })

        self.assertEqual(
            text,
            "capability created today: +46 (time+18 knowledge+7 cash+12 trust+5 auto+4).",
        )


if __name__ == "__main__":
    unittest.main()
