from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from tools.metabolism import nightly


class NightlyMetabolismTest(unittest.TestCase):
    def temp_root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-metabolism-"))

    def test_picks_lowest_health_measurable_conversion(self) -> None:
        data = {
            "conversions": [
                {"name": "question_to_spec", "value": "80%", "target": "90%"},
                {"name": "spec_to_feature_outcome", "value": "20%", "target": "75%"},
                {"name": "not_measurable", "value": "n/a"},
            ]
        }

        weakest = nightly.pick_weakest(nightly.measurable_conversions(data))

        self.assertIsNotNone(weakest)
        assert weakest is not None
        self.assertEqual(weakest.name, "spec_to_feature_outcome")
        self.assertAlmostEqual(weakest.health, 0.2 / 0.75)

    def test_lower_is_better_metric_can_be_weakest(self) -> None:
        data = {
            "metrics": {
                "handoff_latency": {"value": 12, "target": 4},
                "activation_rate": {"value": 0.7, "target": 0.8},
            }
        }

        weakest = nightly.pick_weakest(nightly.measurable_conversions(data))

        self.assertIsNotNone(weakest)
        assert weakest is not None
        self.assertEqual(weakest.name, "handoff_latency")
        self.assertFalse(weakest.higher_is_better)

    def test_dry_run_writes_no_ledger_or_forge_work_order(self) -> None:
        root = self.temp_root()
        conversion = root / "conversion_latest.json"
        ledger = root / "ops.jsonl"
        forge = root / "forge"
        result_md = root / "latest.md"
        conversion.write_text(json.dumps({"metrics": {"merge_gate_conversion": {"value": 0.1, "target": 0.8}}}), encoding="utf-8")
        args = argparse.Namespace(
            conversion_latest=conversion,
            ops_ledger=ledger,
            forge_dir=forge,
            operating_principle=root / "missing.md",
            result=result_md,
            execute=False,
            optimizer_command=[],
            optimizer_timeout=1,
        )

        result = nightly.build_cycle(args)

        self.assertTrue(result["ok"])
        self.assertEqual(result["row"]["status"], "dry_run")
        self.assertFalse(ledger.exists())
        self.assertFalse(forge.exists())

    def test_execute_queues_one_experiment_and_appends_ledger(self) -> None:
        root = self.temp_root()
        conversion = root / "conversion_latest.json"
        ledger = root / "ops.jsonl"
        forge = root / "forge"
        conversion.write_text(
            json.dumps({"conversions": [{"name": "activation_quality", "value": 0.2, "target": 0.9}]}),
            encoding="utf-8",
        )
        ledger.write_text(
            json.dumps(
                {
                    "event": "feature_outcome",
                    "metric_name": "activation_quality",
                    "spec_id": "SPEC_prev",
                    "verdict": "flat",
                    "delta": "no activation improvement",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        args = argparse.Namespace(
            conversion_latest=conversion,
            ops_ledger=ledger,
            forge_dir=forge,
            operating_principle=root / "missing.md",
            result=root / "latest.md",
            execute=True,
            optimizer_command=[],
            optimizer_timeout=1,
        )

        result = nightly.build_cycle(args)

        self.assertTrue(result["ok"])
        self.assertEqual(result["row"]["status"], "experiment_queued")
        orders = list(forge.glob("*.md"))
        self.assertEqual(len(orders), 1)
        self.assertIn("no production deploy", orders[0].read_text(encoding="utf-8").lower())
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(rows[-1]["event"], "nightly_metabolism")
        self.assertEqual(rows[-1]["prod_deploy"], "blocked")

    def test_missing_conversion_file_fails_without_side_effects(self) -> None:
        root = self.temp_root()
        args = argparse.Namespace(
            conversion_latest=root / "missing.json",
            ops_ledger=root / "ops.jsonl",
            forge_dir=root / "forge",
            operating_principle=root / "missing.md",
            result=root / "latest.md",
            execute=True,
            optimizer_command=[],
            optimizer_timeout=1,
        )

        result = nightly.build_cycle(args)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "missing_conversion_latest")
        self.assertFalse((root / "ops.jsonl").exists())
        self.assertFalse((root / "forge").exists())


if __name__ == "__main__":
    unittest.main()

