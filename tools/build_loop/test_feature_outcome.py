from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.build_loop import feature_outcome


class FeatureOutcomeTest(unittest.TestCase):
    def test_appends_required_feature_outcome_shape(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-feature-outcome-"))
        ledger = root / "ops.jsonl"

        row = feature_outcome.append_feature_outcome(
            ledger,
            spec_id="SPEC_d129",
            metric_name="runtime_quality",
            baseline="unknown",
            observed="activated",
            delta="activation completed",
            verdict="improved",
            branch="build/SPEC_d129",
            evidence=["liveness:pass: ok"],
        )

        saved = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertEqual(saved["event"], "feature_outcome")
        self.assertEqual(saved["spec_id"], "SPEC_d129")
        self.assertEqual(saved["metric_name"], "runtime_quality")
        self.assertEqual(saved["baseline"], "unknown")
        self.assertEqual(saved["observed"], "activated")
        self.assertEqual(saved["delta"], "activation completed")
        self.assertEqual(saved["verdict"], "improved")
        self.assertEqual(row["verdict"], "improved")

    def test_infers_regressed_from_post_activation_failures(self) -> None:
        rows = [
            {"event": "activated", "detail": "SPEC_bad (activate.sh ran)", "artifact": "build/SPEC_bad"},
            {"event": "liveness:fail", "detail": "SPEC_bad dead", "spec_id": "SPEC_bad"},
        ]

        observed, delta, verdict, evidence = feature_outcome.infer_activation_outcome(
            rows,
            spec_id="SPEC_bad",
            activated=True,
        )

        self.assertEqual(observed, "post_activation_checks_failed")
        self.assertEqual(delta, "runtime regression detected")
        self.assertEqual(verdict, "regressed")
        self.assertTrue(evidence)


if __name__ == "__main__":
    unittest.main()
