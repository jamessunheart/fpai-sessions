from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.governance.constitution_check import check_proposal


class ConstitutionCheckTest(unittest.TestCase):
    def test_laptop_awake_antipattern_is_rejected(self) -> None:
        proposal = {
            "id": "laptop-awake",
            "kind": "build-decision",
            "risk_class": "build",
            "text": "Require James to keep the laptop awake so the autonomous loop can continue.",
        }

        result = check_proposal(proposal, write_ledger=False)

        self.assertFalse(result["accepted"])
        self.assertEqual(result["decision"], "reject")
        self.assertIn("requires James's laptop/Mac to stay awake", result["checks"]["human_dependency"]["hits"])

    def test_manual_merge_antipattern_is_rejected_for_autonomous_build(self) -> None:
        proposal = {
            "id": "manual-merge",
            "kind": "build-decision",
            "risk_class": "safe-auto",
            "text": "After independent AI approval, wait for James to manually merge this reversible build.",
        }

        result = check_proposal(proposal, write_ledger=False)

        self.assertFalse(result["accepted"])
        self.assertIn("rejects James/manual dependency for work delegated to a lower tier", result["reasons"])

    def test_untagged_manual_merge_antipattern_is_rejected(self) -> None:
        result = check_proposal("Wait for James to manually merge this.", write_ledger=False)

        self.assertFalse(result["accepted"])
        self.assertIn("rejects unnecessary James/manual dependency without a Reserved Class signal", result["reasons"])

    def test_reserved_protocol_violation_is_rejected(self) -> None:
        proposal = {
            "id": "prod-deploy",
            "risk_class": "low",
            "text": "Deploy to production and send public outreach automatically.",
        }

        result = check_proposal(proposal, write_ledger=False)

        self.assertFalse(result["accepted"])
        self.assertGreaterEqual(len(result["checks"]["protocol_violations"]), 2)

    def test_learning_autonomous_proposal_is_accepted_and_logged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "governance.jsonl"
            proposal = {
                "id": "auto-proof",
                "risk_class": "build",
                "text": "Add autonomous proof logging, tests, and a rollback path without James steps.",
            }

            result = check_proposal(proposal, ledger_path=ledger)

            self.assertTrue(result["accepted"])
            self.assertEqual(result["checks"]["human_dependency"]["direction"], "decrease")
            self.assertEqual(result["checks"]["learning_engine"]["direction"], "improve")
            rows = ledger.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(rows), 1)
            self.assertEqual(json.loads(rows[0])["result"]["decision"], "approve")


if __name__ == "__main__":
    unittest.main()
