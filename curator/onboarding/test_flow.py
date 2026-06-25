from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

from curator.onboarding.flow import (
    HermesMessage,
    SQLiteOnboardingStore,
    complete_onboarding,
    extract_passport_fields,
    route_next_step,
    start_onboarding,
)


class OnboardingFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db")
        self.store = SQLiteOnboardingStore(self.tmp.name)
        self.old_env = {
            "HERMES_DISABLE": os.environ.get("HERMES_DISABLE"),
            "ONBOARDING_SQLITE_PATH": os.environ.get("ONBOARDING_SQLITE_PATH"),
            "CORA_POLICY_LIVE": os.environ.get("CORA_POLICY_LIVE"),
        }
        os.environ["HERMES_DISABLE"] = "0"
        os.environ["ONBOARDING_SQLITE_PATH"] = self.tmp.name
        os.environ["CORA_POLICY_LIVE"] = "0"

    def tearDown(self) -> None:
        for key, value in self.old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.tmp.close()

    def test_beacon_context_loads_for_known_beacon(self) -> None:
        response = start_onboarding(
            HermesMessage(user_id="u1", text="hello", channel="one_chat", beacon_id="camp_zen")
        )

        self.assertIn("Camp Zen", response.text)
        self.assertIn("What brought you here today?", response.text)

    def test_three_question_flow_extracts_at_least_two_passport_fields(self) -> None:
        fields = extract_passport_fields(
            [
                "I am trying to get out of a messy work loop.",
                "A clear 30-day plan and one paying client would feel like a win.",
                "Running on fumes, but still moving.",
            ]
        )

        present = [fields.situation, fields.goals, fields.energy]
        self.assertGreaterEqual(sum(bool(value) for value in present), 2)
        self.assertEqual(fields.energy, "running on fumes")

    def test_exactly_one_next_step_is_routed_not_a_list(self) -> None:
        fields = extract_passport_fields(
            [
                "Camp Zen made me curious.",
                "I want a reset this month.",
                "Pretty tired.",
            ]
        )
        path = route_next_step(fields, self.store.load_beacon("camp_zen"))

        self.assertIsInstance(path, str)
        self.assertEqual(path, "camp_zen_invite")
        self.assertNotIn(",", path)

    def test_cora_award_skipped_when_policy_not_live(self) -> None:
        msg = HermesMessage(
            user_id="u2",
            text="answers",
            channel="one_chat",
            beacon_id="general",
            metadata={
                "onboarding_answers": [
                    "I need business clarity.",
                    "One offer shipped.",
                    "Full energy.",
                ]
            },
        )

        response = start_onboarding(msg)

        self.assertTrue(response.onboarding_complete)
        self.assertEqual(response.cora_awarded, 0)
        self.assertNotIn("CORA", response.text)

    def test_agent_passport_row_created_on_completion(self) -> None:
        msg = HermesMessage(user_id="u3", text="answers", channel="one_chat", beacon_id="business_builder")
        complete_onboarding(
            msg,
            [
                "I am building a service business.",
                "I want one clean offer in 30 days.",
                "Full energy.",
            ],
            store=self.store,
        )

        with sqlite3.connect(self.tmp.name) as conn:
            row = conn.execute(
                "SELECT user_id, goals, situation, energy, channel, onboarding_path, cora_balance "
                "FROM agent_passports WHERE user_id = ?",
                ("u3",),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "u3")
        self.assertIn("offer", row[1])
        self.assertEqual(row[3], "full energy")
        self.assertEqual(row[4], "one_chat")
        self.assertEqual(row[6], 0)

    def test_beacon_converted_count_incremented(self) -> None:
        msg = HermesMessage(user_id="u4", text="answers", channel="one_chat", beacon_id="community")
        complete_onboarding(
            msg,
            [
                "I want community.",
                "A useful call this month.",
                "Full energy.",
            ],
            store=self.store,
        )

        with sqlite3.connect(self.tmp.name) as conn:
            converted = conn.execute(
                "SELECT converted_count FROM beacons WHERE beacon_id = ?",
                ("community",),
            ).fetchone()[0]

        self.assertEqual(converted, 1)


if __name__ == "__main__":
    unittest.main()
