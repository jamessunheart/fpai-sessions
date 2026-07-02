from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.build_loop import post_merge_reality_check, self_audit_reality_repair


class SelfAuditRealityRepairTest(unittest.TestCase):
    def test_appends_rows_that_satisfy_post_merge_reality_checker(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-self-audit-repair-"))
        repo = root / "repo"
        ledger = root / "ops.jsonl"
        (repo / "tools" / "build_loop").mkdir(parents=True)
        (repo / "tools" / "build_loop" / "self_audit.py").write_text("# shipped artifact\n", encoding="utf-8")

        result = self_audit_reality_repair.append_repair_proof(ledger, repo_root=repo)

        self.assertTrue(result["ok"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["event"] for row in rows], ["liveness:pass", "feature_outcome"])
        self.assertEqual(rows[1]["verdict"], "improved")
        self.assertEqual(rows[1]["metric_name"], "standard_audit_probe_coverage")
        decision = post_merge_reality_check.MergedDecision(
            decision_id="bd1e3266-aab7-4e11-bc87-1de679e783d6",
            question="Standard audit rotation",
            build_branch=self_audit_reality_repair.ORIGINAL_BRANCH,
            build_spec=self_audit_reality_repair.ORIGINAL_SPEC_ID,
            proof_expected="liveness:pass and feature_outcome verdict=improved",
            liveness="",
            merged_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        evidence = post_merge_reality_check.collect_evidence(rows, decision)
        self.assertTrue(evidence.live)
        self.assertTrue(evidence.metric_moved)

    def test_returns_failure_without_improved_outcome_when_artifact_missing(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-self-audit-repair-fail-"))
        ledger = root / "ops.jsonl"

        result = self_audit_reality_repair.append_repair_proof(ledger, repo_root=root)

        self.assertFalse(result["ok"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event"], "liveness:fail")


if __name__ == "__main__":
    unittest.main()
