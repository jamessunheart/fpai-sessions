from __future__ import annotations

import unittest

from tools.coach import credit_ledger, identifier, matcher, session_tracker


class CoachEconomyTests(unittest.TestCase):
    def test_identifier_flags_high_quality_domain_expertise_as_pending_coach(self) -> None:
        probe_session = {
            "probe_id": "probe-123",
            "identifier": "@mira",
            "platform": "telegram",
            "quality_score": 0.84,
        }
        conversation = [
            {"role": "seeker", "content": "I rebuilt my career after burnout."},
            {"role": "seeker", "content": "What helped me was a clear interview and founder routine."},
        ]

        coach = identifier.identify_potential_coach(probe_session=probe_session, conversation=conversation)

        self.assertIsNotNone(coach)
        self.assertEqual(coach["identifier"], "@mira")
        self.assertIn("career", coach["specialty_tags"])
        self.assertFalse(coach["active"])
        self.assertEqual(coach["recruited_from_probe_id"], "probe-123")

    def test_identifier_rejects_low_quality_session(self) -> None:
        coach = identifier.identify_potential_coach(
            probe_session={"probe_id": "probe-low", "quality_score": 0.69},
            conversation=["I built a career path and can help."],
        )
        self.assertIsNone(coach)

    def test_matcher_returns_active_matching_specialty_tags(self) -> None:
        coaches = [
            {"id": 1, "identifier": "@low", "specialty_tags": ["career"], "quality_score": 0.59, "active": True},
            {"id": 2, "identifier": "@rel", "specialty_tags": ["relationship"], "quality_score": 0.95, "active": True},
            {"id": 3, "identifier": "@career", "specialty_tags": ["career"], "quality_score": 0.8, "sessions_completed": 4, "active": True},
            {"id": 4, "identifier": "@inactive", "specialty_tags": ["career"], "quality_score": 0.99, "active": False},
            {"id": 5, "identifier": "@career-pro", "specialty_tags": ["career"], "quality_score": 0.8, "sessions_completed": 8, "active": True},
        ]

        matches = matcher.match_coaches(
            coaches=coaches,
            blocker_type="job",
            conversation_summary="The seeker is stuck choosing a next career move.",
        )

        self.assertEqual([match.coach["identifier"] for match in matches], ["@career-pro", "@career"])
        self.assertTrue(matches[0].ai_brief.startswith("Seeker blocker: career."))
        self.assertIn("avoid adding private assumptions", matches[0].ai_brief)

    def test_credit_award_is_idempotent_per_session(self) -> None:
        coach = {"id": 7, "cora_credits": 10, "sessions_completed": 2}
        session = session_tracker.new_session(
            session_id=22,
            seeker_identifier="@seeker",
            coach_id=7,
            blocker_type="career",
            session_type="voice",
            ai_brief="Career blocker brief",
        )

        updated_coach, updated_session, ledger = session_tracker.complete_session(
            session=session,
            coach=coach,
            seeker_rating=5,
            outcome_achieved=True,
            active_coaches=19,
        )
        self.assertEqual(updated_session["coach_credits_awarded"], 140)
        self.assertEqual(updated_coach["cora_credits"], 150)
        self.assertEqual(updated_coach["sessions_completed"], 3)
        self.assertIsNotNone(ledger)
        self.assertFalse(ledger["fiat_conversion_allowed"])

        second_coach, second_session, second_ledger = credit_ledger.award_session_credits(
            coach=updated_coach,
            session=updated_session,
            active_coaches=19,
        )
        self.assertEqual(second_coach["cora_credits"], 150)
        self.assertEqual(second_session["coach_credits_awarded"], 140)
        self.assertIsNone(second_ledger)

    def test_coach_table_records_fiat_phase_gate(self) -> None:
        phase_1 = credit_ledger.fiat_phase(19)
        phase_2 = credit_ledger.fiat_phase(20)

        self.assertEqual(phase_1.phase, 1)
        self.assertFalse(phase_1.conversion_allowed)
        self.assertEqual(phase_1.usd_per_credit, 0.0)
        self.assertIn("credits only", phase_1.reason)

        self.assertEqual(phase_2.phase, 2)
        self.assertTrue(phase_2.conversion_allowed)
        self.assertEqual(phase_2.usd_per_credit, 0.50)

    def test_learning_signal_is_correction_shaped(self) -> None:
        session = {
            "id": 3,
            "coach_id": 9,
            "blocker_type": "creative",
            "session_type": "text_async",
            "seeker_rating": 4,
            "outcome_achieved": False,
            "coach_credits_awarded": 40,
            "ai_brief": "Creative blocker brief",
        }

        signal = session_tracker.learning_signal(session=session, intervention_summary="Coach helped them pick one scene.")

        self.assertEqual(signal["source"], "coach_session")
        self.assertEqual(signal["signal"], "successful_human_intervention")
        self.assertEqual(signal["blocker_type"], "creative")
        self.assertEqual(signal["preferred"]["text"], "Coach helped them pick one scene.")


if __name__ == "__main__":
    unittest.main()

