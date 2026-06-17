from __future__ import annotations

import unittest

from tools.economy import currency_optimizer, network_recruiter, netscore, offramp_tracker


class EconomyTests(unittest.TestCase):
    def test_optimizer_recommends_cora_when_both_parties_have_balance_and_want_credits(self) -> None:
        recommendation = currency_optimizer.recommend_currency(
            exchange_type="coaching_session",
            amount=75,
            from_identifier="@seeker",
            to_identifier="@coach",
            participants={
                "@seeker": {"cora_balance": 200, "wants_cora": True},
                "@coach": {"accepts_cora": True, "wants_cora": True},
            },
        )

        self.assertEqual(recommendation.recommended_currency, "cora")
        self.assertEqual(recommendation.estimated_friction, "zero")
        self.assertEqual(recommendation.estimated_extraction, 0.0)
        self.assertTrue(recommendation.internal_flag)

    def test_optimizer_recommends_fiat_only_when_no_internal_path_exists(self) -> None:
        recommendation = currency_optimizer.recommend_currency(
            exchange_type="external_vendor",
            amount=100,
            from_identifier="system",
            to_identifier="vendor",
            participants={
                "system": {"cora_balance": 500, "wallet": "0xabc"},
                "vendor": {"accepts_cora": True, "wallet": "0xdef"},
            },
        )

        self.assertEqual(recommendation.recommended_currency, "fiat")
        self.assertFalse(recommendation.internal_flag)
        self.assertEqual(recommendation.estimated_friction, "high")
        self.assertGreater(recommendation.estimated_extraction, 0)

    def test_optimizer_prefers_usdc_before_fiat_when_cora_unavailable(self) -> None:
        recommendation = currency_optimizer.recommend_currency(
            exchange_type="builder_payment",
            amount=50,
            from_identifier="system",
            to_identifier="@builder",
            participants={
                "system": {"cora_balance": 0, "wallet": "0xabc"},
                "@builder": {"accepts_cora": False, "wallet_address": "0xdef"},
            },
        )

        self.assertEqual(recommendation.recommended_currency, "usdc")
        self.assertEqual(recommendation.estimated_extraction, currency_optimizer.USDC_NETWORK_FEE)

    def test_nvs_scores_net_contributor_and_extractor(self) -> None:
        ledger = [
            {"from_identifier": "@builder", "to_identifier": "network", "amount": 200, "exchange_rate_to_cora": 1},
            {"from_identifier": "network", "to_identifier": "@builder", "amount": 50, "exchange_rate_to_cora": 1},
            {"from_identifier": "@extractor", "to_identifier": "network", "amount": 10, "exchange_rate_to_cora": 1},
            {"from_identifier": "network", "to_identifier": "@extractor", "amount": 80, "exchange_rate_to_cora": 1},
        ]

        contributor = netscore.calculate_nvs("@builder", ledger)
        extractor = netscore.calculate_nvs("@extractor", ledger)

        self.assertGreater(contributor.score, 1.0)
        self.assertEqual(contributor.tier, "net_contributor")
        self.assertLess(extractor.score, 1.0)
        self.assertEqual(extractor.tier, "net_extractor")
        self.assertTrue(contributor.private)

    def test_offramp_tracker_identifies_internal_vs_external_exchanges(self) -> None:
        ledger = [
            currency_optimizer.value_ledger_entry(
                from_identifier="@seeker",
                to_identifier="@coach",
                value_type="cora",
                amount=75,
                currency="cora",
                exchange_rate_to_cora=1,
                description="coaching session",
                internal_flag=True,
            ),
            currency_optimizer.value_ledger_entry(
                from_identifier="system",
                to_identifier="vendor",
                value_type="fiat",
                amount=100,
                currency="usd",
                exchange_rate_to_cora=2,
                description="external vendor",
                external_extraction=6,
                internal_flag=False,
            ),
        ]

        summary = offramp_tracker.summarize_exchanges(
            ledger,
            period_start="2026-06-10",
            period_end="2026-06-17",
            previous_summary={"internal_retention_rate": 0.87},
        )

        self.assertEqual(summary.total_cora_equivalent, 275)
        self.assertEqual(summary.internal_cora_equivalent, 75)
        self.assertEqual(summary.external_cora_equivalent, 200)
        self.assertEqual(summary.external_extraction, 6)
        self.assertIn("Network retained", offramp_tracker.retention_surface(summary))
        self.assertIsNotNone(
            offramp_tracker.offramp_alternative_prompt(
                identifier="@seeker",
                cora_balance=200,
                requested_need="coach session",
                internal_cost_cora=75,
            )
        )

    def test_network_recruiter_identifies_role_gaps_and_generates_role_specific_signals(self) -> None:
        members = [
            {"identifier": "@coach1", "role_signal": "coach"},
            {"identifier": "@builder1", "role_signal": "builder"},
            {"identifier": "@builder2", "role_signal": "builder"},
        ]

        gaps = network_recruiter.identify_role_gaps(
            members=members,
            targets={"builder": 3, "validator": 2, "patron": 1, "coach": 1},
        )
        signals = network_recruiter.beacon_search_signals(gaps)
        contact_signal = network_recruiter.generate_role_signal(
            {
                "handle": "@mira",
                "platform": "github",
                "bio": "I review AI tools, verify outcomes, and audit quality.",
            }
        )

        gap_roles = {gap.role for gap in gaps}
        self.assertIn("validator", gap_roles)
        self.assertIn("patron", gap_roles)
        self.assertIn("builder", gap_roles)
        self.assertTrue(any(row["role_signal"] == "validator" for row in signals))
        self.assertEqual(contact_signal["role_signal"], "validator")
        self.assertIn("review signal", contact_signal["outreach_angle"])


if __name__ == "__main__":
    unittest.main()

