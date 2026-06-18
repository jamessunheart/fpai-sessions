from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tools.adoption import frontier_adoption


class FrontierAdoptionTest(unittest.TestCase):
    def test_dittofeed_event_hashes_identity_and_excludes_pii(self) -> None:
        session = {
            "id": 10,
            "probe_id": "probe-private",
            "pool": "warm",
            "engaged": True,
            "completed_spark": True,
            "quality_score": 0.9,
            "notes": '{"email":"person@example.com","name":"A Person"}',
        }

        event = frontier_adoption.dittofeed_event_from_probe_session(session)

        self.assertEqual(event.stage, "awaken")
        self.assertTrue(event.user_id.startswith("anon_"))
        text = json.dumps(event.__dict__, sort_keys=True)
        self.assertNotIn("person@example.com", text)
        self.assertNotIn("A Person", text)
        frontier_adoption.assert_public_payload(event.__dict__)

    def test_private_pattern_gate_blocks_bad_payload(self) -> None:
        with self.assertRaises(ValueError):
            frontier_adoption.assert_public_payload({"email": "person@example.com"})
        with self.assertRaises(ValueError):
            frontier_adoption.assert_public_payload({"secret": "api_key=abc"})

    def test_router_eval_has_ten_decisions_and_private_routes_do_not_leave(self) -> None:
        config = frontier_adoption.router_eval_config()

        self.assertEqual(config["required_decisions_before_replace"], 10)
        self.assertEqual(config["passed_decision_count"], 10)
        private_routes = {
            row["expected_route"]
            for row in config["fixtures"]
            if row["privacy"] in {"private", "reserved"}
        }
        self.assertEqual(private_routes, {"local_guard", "blocked_private", "james_gate"})

    def test_write_outputs_generates_state_and_signal(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-frontier-adoption-"))
        signal = root / "frontier_adoptions.json"
        state = root / "FRONTIER_ADOPTIONS.md"

        payload = frontier_adoption.write_outputs(
            signal,
            state,
            now=datetime(2026, 6, 18, 23, 59, tzinfo=timezone.utc),
        )

        self.assertEqual(payload["generated_at"], "2026-06-18T23:59:00Z")
        self.assertTrue(signal.exists())
        self.assertTrue(state.exists())
        saved = json.loads(signal.read_text(encoding="utf-8"))
        self.assertEqual(saved["mode"], "shadow_only_no_deploy_no_sends_no_installs")
        report = state.read_text(encoding="utf-8")
        self.assertIn("Frontier Adoptions", report)
        self.assertIn("GEPA", report)
        self.assertIn("Dittofeed", report)
        self.assertIn("LiteLLM", report)


if __name__ == "__main__":
    unittest.main()
