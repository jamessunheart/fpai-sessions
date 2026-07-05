import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from tools.growth import voice_receptionist


FIXTURE = Path("core/BUILD/results/SPEC_d205_voice_call.fixture.json")


class VoiceReceptionistTest(unittest.TestCase):
    def test_fixture_call_produces_expected_appointment_payload(self) -> None:
        payload = voice_receptionist.build_payload(voice_receptionist.load_fixture(FIXTURE))
        expected = json.loads(Path("core/BUILD/results/SPEC_d205_voice_call.expected_payload.json").read_text())

        self.assertEqual(payload, expected)
        self.assertEqual(payload["schema"], voice_receptionist.SCHEMA)
        self.assertEqual(payload["opportunity_id"], "ai-voice-receptionist")
        self.assertEqual(payload["mode"], "sandbox_fixture")
        self.assertEqual(payload["status"], "requires_human_review")
        self.assertFalse(payload["live_phone_number_touched"])
        self.assertFalse(payload["live_send_performed"])
        self.assertFalse(payload["calendar_write_performed"])
        self.assertEqual(payload["marginal_cost_usd"], 0)
        self.assertTrue(payload["quality_gate"]["passed"])
        self.assertEqual(payload["caller"]["name"], "Maria Lopez")
        self.assertEqual(payload["caller"]["phone"], "+19255550142")
        self.assertEqual(payload["caller"]["email"], "maria@example.com")
        self.assertEqual(payload["appointment_request"]["business_name"], "Bayview Dental")
        self.assertEqual(
            payload["appointment_request"]["service_requested"],
            "AI missed-call receptionist setup",
        )
        self.assertEqual(payload["appointment_request"]["requested_start"], "2026-07-08T10:00:00-07:00")
        self.assertEqual(payload["appointment_request"]["timezone"], "America/Los_Angeles")
        self.assertEqual(payload["appointment_request"]["fallback_window"], "Thursday afternoon")

    def test_missing_required_field_blocks_payload_completion(self) -> None:
        fixture = voice_receptionist.load_fixture(FIXTURE)
        fixture["transcript"] = [
            turn for turn in fixture["transcript"] if "Wednesday July 8 at 10 AM Pacific" not in turn["text"]
        ]

        payload = voice_receptionist.build_payload(fixture)

        self.assertEqual(payload["status"], "incomplete_intake")
        self.assertIn("requested_start", payload["quality_gate"]["missing_fields"])
        self.assertFalse(payload["quality_gate"]["passed"])

    def test_rollback_path_is_machine_readable_and_live_runtime_hold(self) -> None:
        payload = voice_receptionist.build_payload(voice_receptionist.load_fixture(FIXTURE))

        rollback = payload["rollback"]
        self.assertTrue(rollback["available"])
        self.assertEqual(rollback["scope"], "sandbox-only")
        self.assertIn("No live runtime exists", rollback["runtime_hold"])
        self.assertGreaterEqual(len(rollback["steps"]), 4)

    def test_capability_learning_append_uses_fixture_ledger_not_live_ledger(self) -> None:
        payload = voice_receptionist.build_payload(voice_receptionist.load_fixture(FIXTURE))
        row = voice_receptionist.capability_learning_row(payload)

        self.assertEqual(row["source_type"], "build_fixture")
        self.assertEqual(row["source_id"], "SPEC_d205_auto-spot-topple-ai-voice-recept")
        self.assertEqual(row["total_capability_gain"], 2.0)
        self.assertEqual(row["expected_total_capability_gain"], 2.0)
        self.assertIn("No live phone number", row["basis"])

        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "capability.jsonl"
            with redirect_stdout(StringIO()):
                voice_receptionist.main([
                    "--fixture",
                    str(FIXTURE),
                    "--capability-ledger",
                    str(ledger),
                ])
            lines = ledger.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["source_id"], row["source_id"])


if __name__ == "__main__":
    unittest.main()
