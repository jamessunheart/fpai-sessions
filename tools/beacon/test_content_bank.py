from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.beacon import seed_content_bank, throttle, variant_generator


class ContentBankTests(unittest.TestCase):
    def test_seed_writes_all_seven_drafts_with_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ops.jsonl"

            result = seed_content_bank.seed_content_bank(
                repo_root=root,
                ops_ledger=ledger,
                generator=lambda asset, _sources: f"# {asset.title}\n\nGenerated draft.",
                notify=False,
            )

            self.assertFalse(result["disabled"])
            self.assertEqual(len(result["written"]), 7)
            for asset in seed_content_bank.ASSETS:
                text = (root / "docs" / "content_bank" / asset.filename).read_text(encoding="utf-8")
                self.assertIn(seed_content_bank.DRAFT_TAG, text)

            row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["event"], "content_bank_generated")
            self.assertEqual(row["assets"], 7)
            self.assertEqual(row["written"], 7)

    def test_seed_skips_existing_non_draft_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_dir = root / "docs" / "content_bank"
            content_dir.mkdir(parents=True)
            protected = content_dir / "02_cora_explainer.md"
            protected.write_text("# James edited\n\nKeep this.", encoding="utf-8")

            result = seed_content_bank.seed_content_bank(
                repo_root=root,
                ops_ledger=root / "ops.jsonl",
                generator=lambda asset, _sources: f"# {asset.title}\n\nGenerated draft.",
                notify=False,
            )

            self.assertIn("02_cora_explainer.md", result["skipped"])
            self.assertEqual(protected.read_text(encoding="utf-8"), "# James edited\n\nKeep this.")

    def test_seed_skips_existing_draft_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            content_dir = root / "docs" / "content_bank"
            content_dir.mkdir(parents=True)
            protected = content_dir / "01_what_is_sunheart_ai.md"
            original = f"{seed_content_bank.DRAFT_TAG}\n\n# James edited draft\n\nKeep this."
            protected.write_text(original, encoding="utf-8")

            result = seed_content_bank.seed_content_bank(
                repo_root=root,
                ops_ledger=root / "ops.jsonl",
                generator=lambda asset, _sources: f"# {asset.title}\n\nGenerated draft.",
                notify=False,
            )

            self.assertIn("01_what_is_sunheart_ai.md", result["skipped"])
            self.assertEqual(protected.read_text(encoding="utf-8"), original)

    def test_seed_campaigns_contains_required_fields(self) -> None:
        text = (seed_content_bank.REPO_ROOT / "docs" / "content_bank" / "SEED_CAMPAIGNS.md").read_text(encoding="utf-8")
        for campaign in ("Campaign A", "Campaign B", "Campaign C"):
            self.assertIn(campaign, text)
        for field in ("Concept:", "Best for:", "Flow:", "Content asset:", "Guard:"):
            self.assertIn(field, text)
        self.assertIn("5 organic chat-starts", text)

    def test_content_bank_disable_skips_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"CONTENT_BANK_DISABLE": "1"}):
            result = seed_content_bank.seed_content_bank(repo_root=Path(tmp), ops_ledger=Path(tmp) / "ops.jsonl", notify=False)
            self.assertTrue(result["disabled"])
            self.assertFalse((Path(tmp) / "docs" / "content_bank").exists())

    def test_variant_generator_reads_campaign_a_content_bank_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            content_dir = Path(tmp)
            asset = content_dir / "02_cora_explainer.md"
            asset.write_text(f"{seed_content_bank.DRAFT_TAG}\n\n# CORA\n\nUnique CORA source sentence.", encoding="utf-8")

            variants = variant_generator.generate_variants("campaign_a", content_dir=content_dir)

            self.assertEqual(variants[0].source_asset, "02_cora_explainer.md")
            self.assertIn("Unique CORA source sentence", variants[0].text)

    def test_farming_guard_triggers_above_ratio_ten(self) -> None:
        result = throttle.evaluate_pacing_signals({"cora_earned": 111, "proofs_created": 10})
        guard = result["cora_farming_guard"]
        self.assertTrue(guard["triggered"])
        self.assertEqual(guard["action"], "tighten_rewards_and_flag_james_review")

    def test_farming_guard_triggers_when_zero_proofs_and_earned(self) -> None:
        guard = throttle.cora_farming_guard(5, 0)
        self.assertTrue(guard.triggered)

    def test_farming_guard_allows_ratio_ten(self) -> None:
        guard = throttle.cora_farming_guard(100, 10)
        self.assertFalse(guard.triggered)


if __name__ == "__main__":
    unittest.main()
