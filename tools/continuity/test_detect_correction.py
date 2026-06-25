from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from typing import Any

MODULE_PATH = Path(__file__).with_name("detect_correction.py")
SPEC = importlib.util.spec_from_file_location("detect_correction", MODULE_PATH)
assert SPEC and SPEC.loader
detect_correction = importlib.util.module_from_spec(SPEC)
sys.modules["detect_correction"] = detect_correction
SPEC.loader.exec_module(detect_correction)


class FakeCursor:
    def __init__(self, response: str = "last Ember answer") -> None:
        self.response = response
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        self.calls.append((query, params))

    def fetchone(self) -> tuple[str] | None:
        return (self.response,) if self.response else None


class FakeConnection:
    def __init__(self, response: str = "last Ember answer") -> None:
        self.cursor_obj = FakeCursor(response)
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1


class DetectCorrectionHookTest(unittest.TestCase):
    def test_detects_spec_phrases(self) -> None:
        examples = [
            "No, that was not the right spec.",
            "Wrong, use the build branch.",
            "That's not right.",
            "Incorrect.",
            "Not what I meant.",
            "Fix the hook wiring.",
            "Change that to Claude Code.",
            "Use this instead.",
            "Actually, d125 is the active build.",
        ]

        for text in examples:
            with self.subTest(text=text):
                self.assertTrue(detect_correction.detect_correction_signal(text).matched)

    def test_ignores_normal_prompt(self) -> None:
        signal = detect_correction.detect_correction_signal("What is the next build?")

        self.assertFalse(signal.matched)

    def test_prompt_prefers_env_and_falls_back_to_json_stdin(self) -> None:
        self.assertEqual(
            detect_correction.prompt_from_hook_input('{"prompt":"stdin"}', {"CLAUDE_USER_PROMPT": "env"}),
            "env",
        )
        self.assertEqual(detect_correction.prompt_from_hook_input('{"prompt":"stdin"}', {}), "stdin")

    def test_capture_reads_last_claude_assistant_and_writes_null_bot_turn(self) -> None:
        conn = FakeConnection("original assistant text")

        capture = detect_correction.capture_prompt_if_correction(
            conn=conn,
            conversation_id="session-1",
            james_prompt="Actually, capture Claude Code corrections.",
        )

        self.assertIsNotNone(capture)
        self.assertEqual(conn.commits, 1)
        select_query = conn.cursor_obj.calls[0][0]
        insert_query, insert_params = conn.cursor_obj.calls[1]
        self.assertIn("surface = 'claude_code'", select_query)
        self.assertIn("role IN ('assistant', 'ember')", select_query)
        self.assertIn("INSERT INTO brain_index.corrections", insert_query)
        self.assertEqual(insert_params[0], "session-1")
        self.assertIsNone(insert_params[1])
        self.assertEqual(insert_params[2], "original assistant text")
        self.assertEqual(insert_params[3], "Actually, capture Claude Code corrections.")

    def test_no_write_without_signal_or_original_response(self) -> None:
        conn = FakeConnection("original assistant text")
        self.assertIsNone(
            detect_correction.capture_prompt_if_correction(
                conn=conn,
                conversation_id="session-1",
                james_prompt="What is queued?",
            )
        )
        self.assertEqual(conn.cursor_obj.calls, [])

        empty_conn = FakeConnection("")
        self.assertIsNone(
            detect_correction.capture_prompt_if_correction(
                conn=empty_conn,
                conversation_id="session-1",
                james_prompt="Actually, this is a correction.",
            )
        )
        self.assertEqual(len(empty_conn.cursor_obj.calls), 1)
        self.assertEqual(empty_conn.commits, 0)


if __name__ == "__main__":
    unittest.main()
