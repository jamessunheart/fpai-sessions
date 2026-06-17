from __future__ import annotations

import unittest

from tools.public_private_boundary import boundary


class PublicPrivateBoundaryTest(unittest.TestCase):
    def test_public_signal_is_allowed(self) -> None:
        verdict = boundary.classify_text("A public glimpse of the Full Potential OS loop with visible proof.")
        self.assertEqual(verdict.lane, "public")
        self.assertTrue(verdict.public_allowed)

    def test_unmatched_text_defaults_private(self) -> None:
        verdict = boundary.classify_text("James is in Athens with Maria tonight.")
        self.assertEqual(verdict.lane, "private")
        self.assertFalse(verdict.public_allowed)
        self.assertIsNone(boundary.sanitize_public_text("James is in Athens with Maria tonight."))

    def test_credentials_are_sensitive_and_not_sanitized(self) -> None:
        text = "Use TELEGRAM_BOT_TOKEN and database_url before posting."
        verdict = boundary.classify_text(text)
        self.assertEqual(verdict.lane, "sensitive")
        self.assertIn("credential_or_secret", verdict.categories)
        self.assertIsNone(boundary.sanitize_public_text(text))

    def test_phone_numbers_are_sensitive(self) -> None:
        text = "My phone number is 555-123-4567 for the public story."
        verdict = boundary.classify_text(text)
        self.assertEqual(verdict.lane, "sensitive")
        self.assertIn("credential_or_secret", verdict.categories)
        self.assertIsNone(boundary.sanitize_public_text(text))

    def test_money_wallet_and_raw_ids_are_generalized_or_redacted(self) -> None:
        text = "Public story for SPEC_d065: runway is $12,345 and wallet 0x1234567890abcdef1234567890abcdef12345678."
        clean = boundary.sanitize_public_text(text, escape=False)
        self.assertIsNotNone(clean)
        assert clean is not None
        self.assertIn("the routed build", clean)
        self.assertIn("[private figure]", clean)
        self.assertIn("[private address]", clean)
        boundary.validate_public_text(clean)

    def test_personal_context_stays_private(self) -> None:
        text = "James has no sleep and is going next to the airport."
        verdict = boundary.classify_text(text)
        self.assertEqual(verdict.lane, "private")
        self.assertIsNone(boundary.sanitize_public_text(text))

    def test_mixed_conversation_splits_public_from_private(self) -> None:
        mixed = "\n".join(
            [
                "Public story: visible proof over private claims.",
                "James has no sleep and is at the hotel.",
                "Next public glimpse: the loop is practicing careful routing.",
                "Use api_key before publishing.",
            ]
        )
        routed = boundary.route_conversation(mixed)
        self.assertEqual(routed["route"], "split")
        self.assertEqual(routed["public_count"], 2)
        self.assertEqual(routed["private_count"], 2)
        self.assertIn("visible proof", routed["public_text"])
        self.assertNotIn("hotel", routed["public_text"])
        self.assertNotIn("api_key", routed["public_text"])
        boundary.validate_public_text(routed["public_text"])

    def test_enforce_public_text_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            boundary.enforce_public_text("Correction log: you forgot the wallet 0x1234567890abcdef1234567890abcdef12345678")


if __name__ == "__main__":
    unittest.main()
