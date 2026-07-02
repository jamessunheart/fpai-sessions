from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.build_loop import d010_reality_repair, post_merge_reality_check


class D010RealityRepairTest(unittest.TestCase):
    def test_appends_rows_that_satisfy_post_merge_reality_checker(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-d010-repair-"))
        ledger = root / "ops.jsonl"
        repo = Path(__file__).resolve().parents[2]

        result = d010_reality_repair.append_repair_proof(ledger, repo_root=repo)

        self.assertTrue(result["ok"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["event"] for row in rows], ["liveness:pass", "feature_outcome"])
        self.assertEqual(rows[0]["spec_id"], d010_reality_repair.ORIGINAL_SPEC_ID)
        self.assertEqual(rows[1]["verdict"], "improved")
        decision = post_merge_reality_check.MergedDecision(
            decision_id="d010",
            question="Self-evolution L1 preference dataset",
            build_branch=d010_reality_repair.ORIGINAL_BRANCH,
            build_spec=d010_reality_repair.ORIGINAL_SPEC_ID,
            proof_expected="liveness:pass and feature_outcome verdict=improved",
            liveness="",
            merged_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        evidence = post_merge_reality_check.collect_evidence(rows, decision)
        self.assertTrue(evidence.live)
        self.assertTrue(evidence.metric_moved)

    def test_returns_failure_without_improved_outcome_when_artifacts_missing(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-d010-repair-fail-"))
        ledger = root / "ops.jsonl"

        result = d010_reality_repair.append_repair_proof(ledger, repo_root=root)

        self.assertFalse(result["ok"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"], "liveness:fail")


if __name__ == "__main__":
    unittest.main()
