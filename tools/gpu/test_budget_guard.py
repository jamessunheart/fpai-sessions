import unittest
from pathlib import Path
import tempfile
import json

from tools.gpu import budget_guard


class BudgetGuardTest(unittest.TestCase):
    def test_blocks_when_daily_spend_exceeds_90_percent_cutoff(self):
        decision = budget_guard.check_budget(
            api_key="rp_test",
            daily_limit_usd=50.0,
            spend_fetcher=lambda _key: 46.0,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.cutoff_usd, 45.0)
        self.assertIn("exceeds", decision.reason)

    def test_budget_zero_is_kill_switch(self):
        decision = budget_guard.check_budget(
            api_key="rp_test",
            daily_limit_usd=0.0,
            spend_fetcher=lambda _key: 0.0,
        )

        self.assertFalse(decision.allowed)
        self.assertIn("0", decision.reason)

    def test_allows_when_spend_under_cutoff(self):
        decision = budget_guard.check_budget(
            api_key="rp_test",
            daily_limit_usd=50.0,
            spend_fetcher=lambda _key: 12.5,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.daily_spend_usd, 12.5)

    def test_budget_alert_writes_ops_row_when_blocked(self):
        ledger = Path(tempfile.mkdtemp(prefix="fpai-budget-test-")) / "ops.jsonl"
        decision = budget_guard.BudgetDecision(False, 46.0, 50.0, 45.0, "over")

        wrote = budget_guard.log_budget_alert(decision, ops_ledger=ledger)

        self.assertTrue(wrote)
        row = json.loads(ledger.read_text(encoding="utf-8").strip())
        self.assertEqual(row["event"], "budget_alert")
        self.assertIn("skip GLM", row["next"])


if __name__ == "__main__":
    unittest.main()
