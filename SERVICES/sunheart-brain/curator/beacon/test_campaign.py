from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from curator.beacon.campaign import (
    BeaconCampaign,
    InMemoryBeaconStore,
    approve_from_text,
    parse_approval_text,
)
from curator.beacon.variant_generator import generate_variants
from tools.beacon.throttle import should_scale_traffic


class BeaconCampaignTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["BEACON_SKIP_CLAUDE"] = "1"
        os.environ.pop("BEACON_DISABLE", None)
        os.environ.pop("BEACON_PAID_ENABLED", None)
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_CHAT_ID", None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = InMemoryBeaconStore()
        self.campaign = BeaconCampaign(
            self.store,
            portal_url="https://portal.example",
            qr_dir=Path(self.tmp.name) / "qr",
            ops_ledger=Path(self.tmp.name) / "ops.jsonl",
        )

    def test_campaign_id_slug_and_url_contains_campaign_id(self) -> None:
        campaign_id = self.campaign.create(
            "telegram",
            "Earn CORA for attention",
            "curious founders and seekers",
            "curious",
            now=datetime(2026, 6, 16, 14, 30, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(campaign_id, "earn-cora-for-attention-20260616143000")
        row = self.store.campaigns[campaign_id]
        self.assertIn(campaign_id, row["beacon_url"])
        self.assertTrue(Path(row["beacon_qr_path"]).exists())
        self.assertEqual(len(self.store.variants), 3)

    def test_variant_generator_produces_required_fields_and_scores(self) -> None:
        self.campaign._current_campaign_id = "camp-1"

        def runner(_prompt: str) -> str:
            return json.dumps(
                [
                    {
                        "variant_label": "A",
                        "content_type": "post",
                        "headline": "Start with proof",
                        "body": "Come through the tracked link.",
                        "cta_text": "Start",
                        "tone_score": 0.8,
                        "alignment_score": 0.9,
                    },
                    {
                        "variant_label": "B",
                        "content_type": "post",
                        "headline": "Attention should become real",
                        "body": "One step, one proof.",
                        "cta_text": "Make proof",
                        "tone_score": 0.7,
                        "alignment_score": 0.8,
                    },
                    {
                        "variant_label": "C",
                        "content_type": "post",
                        "headline": "No dead-end inspiration",
                        "body": "Route the click home.",
                        "cta_text": "Enter",
                        "tone_score": 0.6,
                        "alignment_score": 0.7,
                    },
                ]
            )

        variants = generate_variants(
            self.campaign,
            cta_concept="Earn CORA for attention",
            audience="curious founders",
            intent_lane="curious",
            runner=runner,
            send_approval=False,
        )

        self.assertEqual([v.variant_label for v in variants], ["A", "B", "C"])
        for variant in variants:
            self.assertEqual(variant.campaign_id, "camp-1")
            self.assertTrue(variant.content_type)
            self.assertTrue(variant.headline)
            self.assertTrue(variant.body)
            self.assertTrue(variant.cta_text)
            self.assertIsNotNone(variant.tone_score)
            self.assertIsNotNone(variant.alignment_score)

    def test_record_event_increments_campaign_and_variant_counter(self) -> None:
        campaign_id = self.campaign.create(
            "telegram",
            "Earn CORA",
            "curious founders",
            "curious",
            now=datetime(2026, 6, 16, 14, 31, 0, tzinfo=timezone.utc),
        )

        self.campaign.record_event(f"{campaign_id}:A", "click")
        self.campaign.record_event(f"{campaign_id}:A", "chat_start")

        self.assertEqual(self.store.campaigns[campaign_id]["clicks"], 1)
        self.assertEqual(self.store.campaigns[campaign_id]["chat_starts"], 1)
        variant_a = next(v for v in self.store.variants if v["variant_label"] == "A")
        self.assertEqual(variant_a["clicks"], 1)
        self.assertEqual(variant_a["chat_starts"], 1)

    def test_proof_feedback_increments_proofs_created_and_logs(self) -> None:
        campaign_id = self.campaign.create(
            "telegram",
            "Earn CORA",
            "curious founders",
            "curious",
            now=datetime(2026, 6, 16, 14, 32, 0, tzinfo=timezone.utc),
        )

        self.campaign.proof_feedback(f"{campaign_id}:B")

        self.assertEqual(self.store.campaigns[campaign_id]["proofs_created"], 1)
        variant_b = next(v for v in self.store.variants if v["variant_label"] == "B")
        self.assertEqual(variant_b["proofs"], 1)
        self.assertIn("beacon_proof", (Path(self.tmp.name) / "ops.jsonl").read_text())

    def test_pacing_does_not_scale_when_completion_below_threshold(self) -> None:
        result = should_scale_traffic({"onboarding_completion_rate": 0.29})

        self.assertFalse(result["scale"])
        self.assertIn("below 0.30", result["reason"])

    def test_approval_intercept_pattern_matches_variant_format(self) -> None:
        self.assertEqual(parse_approval_text("bearn-cora-20260616:A"), ("earn-cora-20260616", ["A"]))
        self.assertEqual(parse_approval_text("bearn-cora-20260616:all"), ("earn-cora-20260616", ["A", "B", "C"]))
        self.assertIsNone(parse_approval_text("earn-cora-20260616:A"))

    def test_approval_marks_variants(self) -> None:
        campaign_id = self.campaign.create(
            "telegram",
            "Earn CORA",
            "curious founders",
            "curious",
            now=datetime(2026, 6, 16, 14, 33, 0, tzinfo=timezone.utc),
        )

        reply = approve_from_text(f"b{campaign_id}:A", self.store)

        self.assertIn("approved A", reply or "")
        self.assertEqual(self.store.campaigns[campaign_id]["status"], "approved")
        variant_a = next(v for v in self.store.variants if v["variant_label"] == "A")
        self.assertIsNotNone(variant_a["james_approved_at"])

    def test_approval_with_no_matching_variant_does_not_approve_campaign(self) -> None:
        campaign_id = self.campaign.create(
            "telegram",
            "Earn CORA",
            "curious founders",
            "curious",
            now=datetime(2026, 6, 16, 14, 35, 0, tzinfo=timezone.utc),
            generate=False,
        )

        reply = approve_from_text(f"b{campaign_id}:A", self.store)

        self.assertIn("no matching variants", reply or "")
        self.assertIsNone(self.store.campaigns[campaign_id]["james_approved_at"])
        self.assertEqual(self.store.campaigns[campaign_id]["status"], "draft")

    def test_beacon_disable_skips_proof_feedback_tracking_and_ledger(self) -> None:
        campaign_id = self.campaign.create(
            "telegram",
            "Earn CORA",
            "curious founders",
            "curious",
            now=datetime(2026, 6, 16, 14, 36, 0, tzinfo=timezone.utc),
        )
        os.environ["BEACON_DISABLE"] = "1"

        self.campaign.proof_feedback(f"{campaign_id}:A")

        self.assertEqual(self.store.campaigns[campaign_id]["proofs_created"], 0)
        self.assertFalse((Path(self.tmp.name) / "ops.jsonl").exists())

    def test_paid_campaign_cannot_go_live_without_approval_and_budget(self) -> None:
        os.environ["BEACON_PAID_ENABLED"] = "1"
        campaign_id = self.campaign.create(
            "telegram",
            "Paid proof loop",
            "curious founders",
            "curious",
            creative_type="ad",
            now=datetime(2026, 6, 16, 14, 34, 0, tzinfo=timezone.utc),
        )

        with self.assertRaises(PermissionError):
            self.campaign.mark_live(campaign_id, paid=True)

        approve_from_text(f"b{campaign_id}:all", self.store)
        with self.assertRaises(PermissionError):
            self.campaign.mark_live(campaign_id, paid=True)

        self.store.campaigns[campaign_id]["cost_budget_usd"] = Decimal("25")
        self.campaign.mark_live(campaign_id, paid=True)
        self.assertEqual(self.store.campaigns[campaign_id]["status"], "live")


if __name__ == "__main__":
    unittest.main()
