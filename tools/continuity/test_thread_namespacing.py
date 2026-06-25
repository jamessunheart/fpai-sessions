from __future__ import annotations

import unittest
from pathlib import Path


class ThreadNamespacingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = Path(__file__).with_name("thread.py").read_text(encoding="utf-8")

    def test_recent_operator_thread_filters_to_james(self) -> None:
        self.assertIn("WHERE user_id = 'james'", self.source)

    def test_append_marks_operator_namespace(self) -> None:
        self.assertIn("INSERT INTO brain_index.thread (user_id, surface, role, text)", self.source)
        self.assertIn('("james", surface[:16], role[:16], (text or "")[:8000])', self.source)


if __name__ == "__main__":
    unittest.main()
