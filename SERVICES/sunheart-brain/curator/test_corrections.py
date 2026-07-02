from __future__ import annotations

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("corrections.py")
SPEC = importlib.util.spec_from_file_location("corrections", MODULE_PATH)
assert SPEC and SPEC.loader
corrections = importlib.util.module_from_spec(SPEC)
sys.modules["corrections"] = corrections
SPEC.loader.exec_module(corrections)


class CorrectionsTest(unittest.TestCase):
    def test_detects_explicit_correction(self) -> None:
        signal = corrections.detect_correction_signal("You forgot, I told you this was d010.")

        self.assertTrue(signal.matched)
        self.assertEqual(signal.reason, "explicit")

    def test_detects_negation_restatement(self) -> None:
        signal = corrections.detect_correction_signal("No, the preference loop is d010, not d011.")

        self.assertTrue(signal.matched)

    def test_ignores_normal_questions(self) -> None:
        signal = corrections.detect_correction_signal("What is the current build?")

        self.assertFalse(signal.matched)

    def test_capture_uses_previous_bot_turn(self) -> None:
        bot_turn = corrections.BotTurn(id="turn-1", text="I don't know anything about d010.")
        writes = []

        async def fake_write(pair):
            writes.append(pair)

        with (
            patch.object(corrections, "write_correction", fake_write),
            patch.dict("os.environ", {"BLUEPRINTS_DISABLE": "1"}),
        ):
            pair = asyncio.run(
                corrections.capture_if_correction(
                    conversation_id="chat-1",
                    james_message="Actually, d010 was the preference dataset.",
                    bot_turn=bot_turn,
                )
            )

        self.assertIsNotNone(pair)
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0].conversation_id, "chat-1")
        self.assertEqual(writes[0].bot_turn_id, "turn-1")
        self.assertIn("preference dataset", writes[0].james_correction)

    def test_capture_keeps_blueprint_gap_update(self) -> None:
        bot_turn = corrections.BotTurn(id="turn-1", text="The module is treasury.")
        blueprint_updates = []

        async def fake_write(pair):
            return None

        def fake_detect(text: str) -> str:
            self.assertIn("treasury", text)
            return "treasury"

        def fake_update(module: str, correction: str) -> None:
            blueprint_updates.append((module, correction))

        with (
            patch.object(corrections, "write_correction", fake_write),
            patch.object(corrections, "detect_module_from_text", fake_detect),
            patch.object(corrections, "update_blueprint_after_correction", fake_update),
        ):
            pair = asyncio.run(
                corrections.capture_if_correction(
                    conversation_id="chat-1",
                    james_message="Actually, treasury memory should stay visible.",
                    bot_turn=bot_turn,
                )
            )

        self.assertIsNotNone(pair)
        self.assertEqual(blueprint_updates, [("treasury", "Actually, treasury memory should stay visible.")])

    def test_render_corrections_block_is_bounded(self) -> None:
        pair = corrections.CorrectionPair(
            conversation_id="chat-1",
            bot_turn_id="turn-1",
            original_response="wrong " * 120,
            james_correction="right " * 120,
        )

        rendered = corrections.render_corrections_block([pair], max_chars=360)

        self.assertLessEqual(len(rendered), 360)
        self.assertIn("Recent corrections", rendered)
        self.assertIn("James corrected", rendered)


if __name__ == "__main__":
    unittest.main()
