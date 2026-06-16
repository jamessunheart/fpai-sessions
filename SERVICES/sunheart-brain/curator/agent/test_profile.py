from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("profile.py")
SPEC = importlib.util.spec_from_file_location("profile", MODULE_PATH)
profile = importlib.util.module_from_spec(SPEC)
sys.modules["profile"] = profile
SPEC.loader.exec_module(profile)


class InMemoryProfileStore:
    def __init__(self):
        self.rows = {}

    def upsert(self, item):
        self.rows[item.user_id] = item

    def get(self, user_id):
        return self.rows.get(user_id)


class UserProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = InMemoryProfileStore()
        self.upsert_patch = patch.object(profile, "_upsert_profile", self.store.upsert)
        self.get_patch = patch.object(profile, "_get_profile", self.store.get)
        self.upsert_patch.start()
        self.get_patch.start()
        self.addCleanup(self.upsert_patch.stop)
        self.addCleanup(self.get_patch.stop)

    def test_seed_profile_produces_required_fields(self) -> None:
        with patch.object(
            profile,
            "_claude_json",
            return_value={
                "situation": "Looking for structure while starting a new chapter.",
                "goals": [{"goal": "build a stable daily rhythm", "timeframe": "30 days"}],
                "energy_level": "medium",
                "life_areas": {"work": 7, "health": 4, "relationships": 6, "finances": 5, "creativity": 8, "purpose": 7},
                "preferred_tone": "direct",
            },
        ):
            seeded = profile.seed_profile("user-a", {"spark": "I need rhythm and support."})

        self.assertEqual(seeded.user_id, "user-a")
        self.assertEqual(seeded.situation, "Looking for structure while starting a new chapter.")
        self.assertEqual(seeded.goals[0]["status"], "active")
        self.assertEqual(seeded.energy_level, "medium")
        self.assertEqual(seeded.life_areas["health"], 4)
        self.assertEqual(seeded.preferred_tone, "direct")

    def test_get_agent_context_returns_200_tokens_or_less(self) -> None:
        self.store.upsert(
            profile.UserProfile(
                user_id="user-a",
                situation=" ".join(["situation"] * 120),
                goals=[{"goal": " ".join(["goal"] * 80), "status": "active"}],
                strengths=["follow-through", "careful support"],
                dominant_path="proof",
                energy_level="full",
            )
        )

        context = profile.get_agent_context("user-a")

        self.assertLessEqual(len(context.split()), 200)
        self.assertTrue(context.startswith("[User context]"))

    def test_update_profile_from_session_updates_streak_days(self) -> None:
        self.store.upsert(
            profile.UserProfile(
                user_id="user-a",
                last_updated=datetime(2026, 6, 15, 10, 0, tzinfo=timezone.utc),
                streak_days=2,
                longest_streak=3,
            )
        )

        profile.update_profile_from_session(
            "user-a",
            [
                {
                    "role": "user",
                    "text": "I have medium energy today.",
                    "at": "2026-06-16T09:00:00+00:00",
                }
            ],
        )

        updated = self.store.get("user-a")
        self.assertEqual(updated.streak_days, 3)
        self.assertEqual(updated.longest_streak, 3)
        self.assertEqual(updated.energy_level, "medium")

    def test_extract_strength_from_proof_appends_strength(self) -> None:
        self.store.upsert(profile.UserProfile(user_id="user-a"))
        with patch.object(profile, "_claude_json", return_value={"strength": "follow-through"}):
            profile.extract_strength_from_proof("user-a", "I shipped the promised proof.")

        self.assertEqual(self.store.get("user-a").strengths, ["follow-through"])

    def test_profile_data_never_crosses_user_namespaces(self) -> None:
        self.store.upsert(
            profile.UserProfile(
                user_id="user-a",
                goals=[{"goal": "private A", "status": "active"}],
            )
        )
        self.store.upsert(
            profile.UserProfile(
                user_id="user-b",
                goals=[{"goal": "private B", "status": "active"}],
            )
        )

        self.assertIn("private A", profile.get_agent_context("user-a"))
        self.assertNotIn("private B", profile.get_agent_context("user-a"))


if __name__ == "__main__":
    unittest.main()
