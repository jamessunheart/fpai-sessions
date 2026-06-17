from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.identity_pairing import guard


NOW = datetime(2026, 6, 17, 12, tzinfo=timezone.utc)


class IdentityPairingGuardTest(unittest.TestCase):
    def observed(self) -> guard.ObservedIdentity:
        return guard.ObservedIdentity(
            provider="telegram",
            provider_user_id="123",
            chat_id="123",
            username="james",
        )

    def pairing(self, **overrides: object) -> guard.PairingRecord:
        identity = self.observed()
        values = {
            "subject_id": "james",
            "ai_agent": "sunheart-brain",
            "provider": "telegram",
            "provider_user_id": "123",
            "chat_id": "123",
            "status": "verified",
            "verified_at": NOW - timedelta(days=1),
            "assurance_level": 2,
            "identity_fingerprint": guard.identity_fingerprint(identity, "secret"),
        }
        values.update(overrides)
        return guard.PairingRecord(**values)

    def test_verified_pairing_allows_matching_identity(self) -> None:
        decision = guard.evaluate_pairing(
            self.pairing(),
            self.observed(),
            ai_agent="sunheart-brain",
            fingerprint_secret="secret",
            now=NOW,
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.action, "allow")
        self.assertEqual(decision.reasons, ())

    def test_missing_pairing_blocks(self) -> None:
        decision = guard.evaluate_pairing(None, self.observed(), ai_agent="sunheart-brain", now=NOW)

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, "block")
        self.assertIn("no_verified_pairing", decision.reasons)

    def test_provider_or_chat_drift_blocks_takeover(self) -> None:
        observed = guard.ObservedIdentity(provider="telegram", provider_user_id="123", chat_id="999")

        decision = guard.evaluate_pairing(
            self.pairing(),
            observed,
            ai_agent="sunheart-brain",
            fingerprint_secret="secret",
            now=NOW,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, "block")
        self.assertIn("chat_id_mismatch", decision.reasons)
        self.assertIn("identity_fingerprint_mismatch", decision.reasons)

    def test_stale_or_low_assurance_pairing_challenges(self) -> None:
        decision = guard.evaluate_pairing(
            self.pairing(verified_at=NOW - timedelta(days=120), assurance_level=1),
            self.observed(),
            ai_agent="sunheart-brain",
            fingerprint_secret="secret",
            now=NOW,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, "challenge")
        self.assertIn("verification_stale", decision.reasons)
        self.assertIn("assurance_too_low", decision.reasons)

    def test_revoked_pairing_blocks_even_if_identity_matches(self) -> None:
        decision = guard.evaluate_pairing(
            self.pairing(status="revoked"),
            self.observed(),
            ai_agent="sunheart-brain",
            fingerprint_secret="secret",
            now=NOW,
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.action, "block")
        self.assertIn("pairing_status_revoked", decision.reasons)

    def test_detects_multi_subject_takeover_anomalies(self) -> None:
        findings = guard.detect_pairing_anomalies([
            {
                "subject_id": "james",
                "ai_agent": "sunheart-brain",
                "provider": "telegram",
                "provider_user_id": "123",
                "chat_id": "123",
                "status": "verified",
            },
            {
                "subject_id": "attacker",
                "ai_agent": "sunheart-brain",
                "provider": "telegram",
                "provider_user_id": "123",
                "chat_id": "123",
                "status": "verified",
            },
        ])

        titles = {finding["title"] for finding in findings}
        self.assertIn("One provider user id is bound to multiple subjects", titles)
        self.assertIn("One chat id is bound to multiple subjects", titles)

    def test_report_writes_json_and_markdown(self) -> None:
        root = Path(tempfile.mkdtemp())
        report = guard.run_report(
            [{"subject_id": "james", "ai_agent": "brain", "provider": "telegram", "provider_user_id": "123", "chat_id": "1"}],
            json_path=root / "pairing.json",
            markdown_path=root / "pairing.md",
            now=NOW,
        )

        self.assertEqual(report["summary"]["pairings_scanned"], 1)
        loaded = json.loads((root / "pairing.json").read_text(encoding="utf-8"))
        self.assertEqual(loaded["schema"], guard.SCHEMA)
        self.assertIn("AI Pairing Security Report", (root / "pairing.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

