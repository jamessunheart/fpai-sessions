from __future__ import annotations

import datetime as dt
import importlib.util
import unittest
from pathlib import Path


MODULE = Path(__file__).with_name("daily_sync.py")
SPEC = importlib.util.spec_from_file_location("daily_sync", MODULE)
assert SPEC and SPEC.loader
daily_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(daily_sync)


class CoherenceGateTest(unittest.TestCase):
    def test_after_midnight_next_move_is_checkpoint_sleep(self) -> None:
        move = daily_sync.james_next_move(dt.datetime(2026, 6, 7, 3, 50))

        self.assertTrue(move["rest_gate"])
        self.assertEqual(move["yes"], "checkpoint")
        self.assertIn("sleep", move["title"].lower())
        self.assertIn("checkpoint", move["say"])

    def test_late_evening_next_move_is_closure(self) -> None:
        move = daily_sync.james_next_move(dt.datetime(2026, 6, 6, 23, 15))

        self.assertTrue(move["rest_gate"])
        self.assertEqual(move["yes"], "checkpoint")
        self.assertIn("no new major calls", move["title"].lower())

    def test_care_check_is_direct_after_midnight(self) -> None:
        note = daily_sync.care_check(dt.datetime(2026, 6, 7, 3, 50))

        self.assertIn("sleep", note.lower())
        self.assertIn("checkpoint", note)

    def test_next_move_has_conscious_routing_contract(self) -> None:
        move = daily_sync.james_next_move(dt.datetime(2026, 6, 7, 3, 50))

        fields = daily_sync.conscious_routing_fields(move)

        self.assertEqual(set(fields), {"aware", "aligned", "care", "proof"})
        self.assertIn("after midnight", fields["aware"].lower())
        self.assertIn("coherence", fields["aligned"].lower())
        self.assertIn("sleep", fields["care"].lower())
        self.assertIn("checkpoint", fields["proof"].lower())

    def test_go_autonomous_decision_names_downstream_action(self) -> None:
        original = daily_sync.decisions_top
        try:
            daily_sync.decisions_top = lambda n=3: (
                [
                    (
                        "Go autonomous — run the self-standing one-day test?",
                        "Rungs 0-3 are built",
                        'say "go autonomous" / "not yet" / "checkpoint"',
                    )
                ],
                0,
            )

            move = daily_sync.next_decision_move(dt.datetime(2026, 6, 7, 11, 0))
        finally:
            daily_sync.decisions_top = original

        self.assertEqual(move["yes"], "go autonomous")
        self.assertIn("guarded self-standing one-day test", move["downstream"])
        self.assertIn("Safety Seal", move["downstream"])
        self.assertIn("zero James-glue", move["proof"])

    def test_dispatched_builds_decision_names_downstream_action(self) -> None:
        original = daily_sync.decisions_top
        try:
            daily_sync.decisions_top = lambda n=3: (
                [
                    (
                        "Run the dispatched builds",
                        "3 collision-free Codex builds are queued",
                        'say "running them" / "after X" / "checkpoint"',
                    )
                ],
                0,
            )

            move = daily_sync.next_decision_move(dt.datetime(2026, 6, 7, 11, 0))
        finally:
            daily_sync.decisions_top = original

        self.assertEqual(move["yes"], "running them")
        self.assertIn("queued Codex builds", move["downstream"])
        self.assertIn("branch isolation", move["care"])
        self.assertIn("files changed", move["proof"])


if __name__ == "__main__":
    unittest.main()
