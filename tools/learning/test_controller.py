from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.learning import controller


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []

    def execute(self, sql: str, params: tuple[object, ...] | None = None) -> None:
        self.executed.append((sql, params))

    def fetchone(self) -> tuple[int]:
        return (123,)

    def close(self) -> None:
        pass


class FakeConn:
    def __init__(self) -> None:
        self.cursor_obj = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.cursor_obj


class LearningControllerTest(unittest.TestCase):
    def test_collect_signal_writes_fallback_jsonl(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="fpai-learning-signal-"))
        path = root / "signals.jsonl"

        result = controller.collect_signal(
            "task-1",
            "prompt",
            "response",
            "correction",
            -1,
            fallback_path=path,
        )

        self.assertEqual(result.status, "fallback_jsonl")
        row = json.loads(path.read_text(encoding="utf-8").strip())
        self.assertEqual(row["signal_type"], "correction")
        self.assertEqual(row["value"], -1.0)

    def test_collect_signal_uses_brain_index_connection(self) -> None:
        conn = FakeConn()

        result = controller.collect_signal("task-2", "p", "r", "approval", 1, conn=conn)

        self.assertEqual(result.status, "db_inserted")
        sql, params = conn.cursor_obj.executed[0]
        self.assertIn("brain_index.learning_signals", sql)
        self.assertEqual(params[:2], ("task-2", "approval"))

    def test_finetune_ready_requires_learning_enabled_and_min_signals(self) -> None:
        with patch.dict("os.environ", {"LEARNING_ENABLED": "1"}, clear=False):
            self.assertTrue(controller.ready_for_finetune(controller.MIN_SIGNALS))
        with patch.dict("os.environ", {"LEARNING_ENABLED": "0"}, clear=False):
            self.assertFalse(controller.ready_for_finetune(controller.MIN_SIGNALS))

    def test_rejects_invalid_signal_type(self) -> None:
        with self.assertRaises(controller.LearningSignalError):
            controller.collect_signal("task", "p", "r", "mood", 0)


if __name__ == "__main__":
    unittest.main()
