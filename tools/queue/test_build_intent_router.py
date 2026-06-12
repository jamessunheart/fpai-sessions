#!/usr/bin/env python3
"""Tests for build_intent_router — capture, idempotency, trigger-gating."""
import json
import tempfile
import unittest
from pathlib import Path

import tools.queue.build_intent_router as bir


class BuildIntentRouterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.inbox = self.tmp / "messages.jsonl"
        self.cursor = self.tmp / "cursor.txt"
        self.intents = self.tmp / "intents"

    def _write(self, msgs):
        self.inbox.write_text("\n".join(json.dumps(m) for m in msgs), encoding="utf-8")

    def _cap(self):
        return bir.capture(self.inbox, self.cursor, self.intents)

    def test_captures_build_prefix_only(self):
        self._write([
            {"update_id": 1, "text": "build: a daily treasury report"},
            {"update_id": 2, "text": "running them"},            # a verb, not a build
            {"update_id": 3, "text": "hello there"},             # conversation
        ])
        got = self._cap()
        self.assertEqual(len(got), 1)
        self.assertIn("daily treasury report", got[0]["intent"])
        files = list(self.intents.glob("*.md"))
        self.assertEqual(len(files), 1)
        self.assertIn("status: open", files[0].read_text())

    def test_idempotent_via_cursor(self):
        self._write([{"update_id": 5, "text": "build: thing one"}])
        self.assertEqual(len(self._cap()), 1)
        # second run over the same inbox captures nothing new
        self.assertEqual(len(self._cap()), 0)

    def test_new_message_after_cursor(self):
        self._write([{"update_id": 5, "text": "build: thing one"}])
        self._cap()
        self._write([
            {"update_id": 5, "text": "build: thing one"},
            {"update_id": 6, "text": "build: thing two"},
        ])
        got = self._cap()
        self.assertEqual(len(got), 1)
        self.assertIn("thing two", got[0]["intent"])

    def test_empty_intent_skipped(self):
        self._write([{"update_id": 7, "text": "build:"}])
        self.assertEqual(len(self._cap()), 0)

    def test_no_inbox_no_crash(self):
        self.assertEqual(bir.capture(self.tmp / "nope.jsonl", self.cursor, self.intents), [])


if __name__ == "__main__":
    unittest.main()
