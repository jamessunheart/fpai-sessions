from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.growth import ad_engine as ads


class AdEngineTests(unittest.TestCase):
    def test_generates_six_variants_across_three_frames(self) -> None:
        variants = ads.generated_variants(6)
        self.assertEqual(len(variants), 6)
        self.assertEqual({variant.frame for variant in variants}, {"promise", "exec", "savings"})
        self.assertTrue(all("utm_campaign=" in variant.url for variant in variants))

    def test_ledger_scoring_marks_champion_and_loser(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ledger = Path(td) / "ads.jsonl"
            rows = [variant.row() for variant in ads.generated_variants(2)]
            rows[0].update({"impressions": 1000, "clicks": 50, "leads": 2, "spend_usd": 10})
            rows[1].update({"impressions": 800, "clicks": 8, "leads": 0, "spend_usd": 10})
            ads.write_ledger(ledger, rows)
            scored = ads.score_ledger(ledger)
        by_id = {row["variant_id"]: row for row in scored}
        self.assertEqual(by_id[rows[0]["variant_id"]]["status"], "champion")
        self.assertEqual(by_id[rows[1]["variant_id"]]["status"], "killed")
        self.assertGreater(by_id[rows[0]["variant_id"]]["score"], by_id[rows[1]["variant_id"]]["score"])

    def test_apply_outcomes_from_variant_rows(self) -> None:
        rows = [variant.row() for variant in ads.generated_variants(1)]
        updated = ads.apply_outcomes(
            rows,
            [{"variant_id": rows[0]["variant_id"], "impressions": 12, "clicks": 3, "leads": 1, "spend_usd": 2.5}],
        )
        self.assertEqual(updated[0]["leads"], 1)
        self.assertEqual(updated[0]["spend_usd"], 2.5)

    def test_spend_gate_requires_account_ok_budget_kill_switch_and_james_unlock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            kill = Path(td) / "PAUSE_ALL"
            blocked = ads.spend_gate(
                account_status=2,
                requested_daily_budget_usd=10,
                kill_switch_path=kill,
                james_unlock=True,
            )
            self.assertFalse(blocked["ok"])
            self.assertIn("meta_account_status_not_1", blocked["reasons"])
            over = ads.spend_gate(
                account_status=1,
                requested_daily_budget_usd=10.01,
                kill_switch_path=kill,
                james_unlock=True,
            )
            self.assertFalse(over["ok"])
            self.assertIn("daily_budget_over_10_usd", over["reasons"])
            kill.write_text("pause", encoding="utf-8")
            paused = ads.spend_gate(
                account_status=1,
                requested_daily_budget_usd=10,
                kill_switch_path=kill,
                james_unlock=True,
            )
            self.assertFalse(paused["ok"])
            self.assertIn("pause_all_kill_switch_present", paused["reasons"])
            kill.unlink()
            missing_unlock = ads.spend_gate(
                account_status=1,
                requested_daily_budget_usd=10,
                kill_switch_path=kill,
                james_unlock=False,
            )
            self.assertFalse(missing_unlock["ok"])
            self.assertIn("james_spend_unlock_missing", missing_unlock["reasons"])
            allowed = ads.spend_gate(
                account_status=1,
                requested_daily_budget_usd=10,
                kill_switch_path=kill,
                james_unlock=True,
            )
            self.assertTrue(allowed["ok"], json.dumps(allowed))


if __name__ == "__main__":
    unittest.main()
