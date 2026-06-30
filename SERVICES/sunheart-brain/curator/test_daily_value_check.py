import tempfile
import types
import unittest
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.modules.pop("curator", None)
sys.path.insert(0, str(SERVICE_ROOT))

from curator import daily_value_check as dvc


class _FakeCursor:
    def __init__(self):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, sql, params=None):
        self.calls.append((sql, params))


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


class DailyValueCheckTest(unittest.IsolatedAsyncioTestCase):
    async def test_send_due_check_writes_awaiting_state_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "daily.json"
            sent = []

            async def sender(text, **kwargs):
                sent.append((text, kwargs))
                return True

            result = await dvc.send_due_check(
                state_file=state,
                disable_file=Path(tmp) / ".disabled",
                required_hour=20,
                sender=sender,
                now=datetime.fromisoformat("2026-06-30T20:00:00+03:00"),
            )
            again = await dvc.send_due_check(
                state_file=state,
                disable_file=Path(tmp) / ".disabled",
                required_hour=20,
                sender=sender,
                now=datetime.fromisoformat("2026-06-30T20:10:00+03:00"),
            )

            self.assertEqual(result.status, "sent")
            self.assertEqual(again.status, "skipped")
            self.assertEqual(sent, [(dvc.PROMPT, {})])
            self.assertIn('"status": "awaiting_reply"', state.read_text(encoding="utf-8"))

    async def test_send_due_check_honors_time_and_disable_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "daily.json"
            disabled = Path(tmp) / ".daily_value_check_disabled"
            disabled.write_text("", encoding="utf-8")

            result = await dvc.send_due_check(
                state_file=state,
                disable_file=disabled,
                now=datetime.fromisoformat("2026-06-30T20:00:00+03:00"),
            )
            self.assertEqual(result.status, "disabled")

            disabled.unlink()
            result = await dvc.send_due_check(
                state_file=state,
                disable_file=disabled,
                required_hour=20,
                now=datetime.fromisoformat("2026-06-30T19:00:00+03:00"),
            )
            self.assertEqual(result.status, "skipped_time")

    async def test_capture_reply_writes_source_correction_and_marks_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "daily.json"
            state.write_text(
                '{"date":"2026-06-30","prompt":"Did I help you today? What would have helped more?","status":"awaiting_reply"}',
                encoding="utf-8",
            )
            cursor = _FakeCursor()

            fake_db = types.ModuleType("curator.db")
            fake_db.connect = lambda: _FakeConn(cursor)

            with patch.dict(sys.modules, {"curator.db": fake_db}):
                result = await dvc.capture_reply_if_pending(
                    conversation_id="123",
                    james_message="Yes, but earlier proof would have helped.",
                    state_file=state,
                    disable_file=Path(tmp) / ".disabled",
                )

            self.assertEqual(result.status, "captured")
            self.assertIn('"status": "captured"', state.read_text(encoding="utf-8"))
            insert_sql, params = cursor.calls[-1]
            self.assertIn("INSERT INTO brain_index.corrections", insert_sql)
            self.assertEqual(params, ("123", dvc.PROMPT, "Yes, but earlier proof would have helped.", "daily_value_check"))

    async def test_capture_reply_ignores_without_pending_or_multiline(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "daily.json"
            self.assertEqual(
                (
                    await dvc.capture_reply_if_pending(
                        conversation_id="123",
                        james_message="No pending",
                        state_file=state,
                        disable_file=Path(tmp) / ".disabled",
                    )
                ).status,
                "ignored",
            )
            state.write_text('{"date":"2026-06-30","status":"awaiting_reply"}', encoding="utf-8")
            self.assertEqual(
                (
                    await dvc.capture_reply_if_pending(
                        conversation_id="123",
                        james_message="line one\nline two",
                        state_file=state,
                        disable_file=Path(tmp) / ".disabled",
                    )
                ).status,
                "ignored",
            )


if __name__ == "__main__":
    unittest.main()
