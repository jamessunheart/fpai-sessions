from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_ORDER = REPO_ROOT / "core" / "BUILD" / "improvement_proposals" / "SPEC_d143_active_days_share_closeout.md"


class D143WorkOrderTest(unittest.TestCase):
    def test_work_order_has_required_experiment_guardrails(self) -> None:
        text = WORK_ORDER.read_text(encoding="utf-8")
        lowered = text.lower()

        self.assertIn("active_days_share", text)
        self.assertIn("9/14", text)
        self.assertIn("0.642857", text)
        self.assertIn("FPAI_ACTIVE_DAYS_CLOSEOUT_EXPERIMENT=0", text)
        self.assertIn("Exactly one experiment", text)
        self.assertIn("Acceptance Criteria", text)
        self.assertIn("Measurement Plan", text)
        self.assertIn("feature_outcome", text)
        self.assertIn("Rollback", text)
        for blocked in (
            "no production deploy",
            "push",
            "merge",
            "outreach",
            "secrets",
            "money movement",
        ):
            self.assertIn(blocked, lowered)

    def test_work_order_stays_artifact_only_not_activation(self) -> None:
        text = WORK_ORDER.read_text(encoding="utf-8")

        self.assertIn("does not install a timer", text)
        self.assertIn("nothing runs and no files are written", text)
        self.assertNotIn("systemctl enable", text)
        self.assertNotIn("launchctl load", text)


if __name__ == "__main__":
    unittest.main()
