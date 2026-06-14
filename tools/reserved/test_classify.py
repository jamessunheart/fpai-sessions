from __future__ import annotations

import unittest

from tools.reserved.classify import gate_or_proceed, is_reserved


class ReservedClassifyTest(unittest.TestCase):
    def assert_reserved(self, action: str, category: str) -> None:
        verdict = is_reserved(action)
        self.assertTrue(verdict["reserved"], verdict)
        self.assertEqual(verdict["category"], category, verdict)

    def assert_delegable(self, action: str) -> None:
        verdict = is_reserved(action)
        self.assertFalse(verdict["reserved"], verdict)
        self.assertIsNone(verdict["category"], verdict)

    def test_money_out_examples_escalate(self) -> None:
        self.assert_reserved("Transfer SOL to the treasury wallet", "money")
        self.assert_reserved("Buy the SaaS subscription", "money")
        self.assert_reserved("Send the venue deposit", "money")
        self.assert_reserved("Send $500 to the Pendle vault", "money")

    def test_public_outbound_send_examples_escalate(self) -> None:
        self.assert_reserved("Send the outreach email", "public_outbound_send")
        self.assert_reserved("Post the announcement on Telegram", "public_outbound_send")

    def test_irreversible_legal_people_examples_escalate(self) -> None:
        self.assert_reserved("Deploy the bot to production", "irreversible_legal_people")
        self.assert_reserved("Hire the assistant", "irreversible_legal_people")
        self.assert_reserved("Delete the old service", "irreversible_legal_people")

    def test_strategic_positioning_examples_escalate(self) -> None:
        self.assert_reserved("Set Camp Zen pricing", "strategic_positioning")
        self.assert_reserved("Choose the first cohort offer", "strategic_positioning")
        self.assert_reserved("Change the doctrine", "strategic_positioning")

    def test_final_blessing_examples_escalate(self) -> None:
        self.assert_reserved("Approve this diff for merge", "final_blessing")
        self.assert_reserved("Wire the classifier into the live loop", "final_blessing")

    def test_delegable_advisory_work_clears(self) -> None:
        self.assert_delegable("Draft an outreach email for James to review")
        self.assert_delegable("Run a read-only scan of services")
        self.assert_delegable("Propose a lead list")
        self.assert_delegable("Write tests for the classifier")

    def test_ambiguous_consequential_defaults_to_escalate(self) -> None:
        verdict = is_reserved("do the thing")
        self.assertTrue(verdict["reserved"], verdict)
        self.assertEqual(verdict["category"], "uncertain", verdict)

        verdict = is_reserved("Execute the partner handoff")
        self.assertTrue(verdict["reserved"], verdict)
        self.assertEqual(verdict["category"], "uncertain", verdict)

        context_verdict = is_reserved("Proceed with the account update", {"external_effect": True})
        self.assertTrue(context_verdict["reserved"], context_verdict)
        self.assertEqual(context_verdict["category"], "uncertain", context_verdict)

    def test_empty_action_defaults_to_escalate(self) -> None:
        verdict = is_reserved("")
        self.assertTrue(verdict["reserved"], verdict)
        self.assertEqual(verdict["category"], "uncertain", verdict)

    def test_gate_or_proceed_uses_injected_writer(self) -> None:
        calls = []

        def fake_writer(**payload):
            calls.append(payload)
            return {"id": payload["gate_id"], "state": "open"}

        result = gate_or_proceed("Deploy the bot to production", apply_gate=True, gate_writer=fake_writer)
        self.assertFalse(result["proceed"], result)
        self.assertEqual(result["gate"]["state"], "open")
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0]["blocking"])

    def test_gate_or_proceed_allows_delegable_without_gate(self) -> None:
        result = gate_or_proceed("Draft a document")
        self.assertTrue(result["proceed"], result)
        self.assertIsNone(result["gate"])


if __name__ == "__main__":
    unittest.main()
