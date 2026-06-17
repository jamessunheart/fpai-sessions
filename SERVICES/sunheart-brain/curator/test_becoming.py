from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("becoming.py")
SPEC = importlib.util.spec_from_file_location("becoming_test_module", MODULE_PATH)
assert SPEC and SPEC.loader
becoming = importlib.util.module_from_spec(SPEC)
sys.modules["becoming_test_module"] = becoming
SPEC.loader.exec_module(becoming)


class BecomingTest(unittest.TestCase):
    def test_infers_stage_intent_blocker_and_next_action(self) -> None:
        state = becoming.infer_becoming_update(
            "I want to build a coaching offer. I am stuck on choosing the first proof.",
            person_id="tg:123",
            identity_contact={"username": "atlas"},
        )

        self.assertEqual(state.stage, "coach")
        self.assertIn("build a coaching offer", state.stated_intent)
        self.assertIn("choosing the first proof", state.current_blocker)
        self.assertIn("unblock", state.next_nurture_action)
        self.assertEqual(state.identity_contact["username"], "atlas")
        self.assertEqual(state.proofs["signals"][-1]["stage"], "coach")

    def test_stage_only_moves_forward(self) -> None:
        current = becoming.BecomingState(person_id="tg:123", stage="build")

        state = becoming.infer_becoming_update(
            "I am curious and want to learn more.",
            current=current,
            person_id="tg:123",
        )

        self.assertEqual(state.stage, "build")

    def test_render_is_bounded_and_advisory(self) -> None:
        state = becoming.BecomingState(
            person_id="tg:123",
            stage="activate",
            stated_intent="start a daily practice",
            next_nurture_action="Convert intent into one concrete next action with proof.",
            proofs={"signals": [{"stage": "activate", "text": "x" * 500}]},
        )

        rendered = becoming.render_becoming_state(state, max_chars=360)

        self.assertLessEqual(len(rendered), 360)
        self.assertIn("BECOMING STATE", rendered)
        self.assertIn("advisory", rendered)
        self.assertIn("Do not proactively message", rendered)


if __name__ == "__main__":
    unittest.main()
