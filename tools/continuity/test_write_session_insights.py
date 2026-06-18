from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("write_session_insights.py")
SPEC = importlib.util.spec_from_file_location("write_session_insights", MODULE_PATH)
assert SPEC and SPEC.loader
write_session_insights = importlib.util.module_from_spec(SPEC)
sys.modules["write_session_insights"] = write_session_insights
SPEC.loader.exec_module(write_session_insights)


class FakeCursor:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple | None]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=None) -> None:
        self.executed.append((sql, params))


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_obj = FakeCursor()

    def cursor(self) -> FakeCursor:
        return self.cursor_obj


class WriteSessionInsightsTest(unittest.TestCase):
    def test_load_insights_accepts_json_and_extracts_specs(self) -> None:
        payload = json.dumps(
            {
                "insights": [
                    {
                        "type": "architecture",
                        "title": "d110 writes every Claude Code decision",
                        "body": "Bot should see SPEC_d110 from session_insights.",
                        "weight": 9,
                    }
                ]
            }
        )

        insights = write_session_insights.load_insights(insights_json=payload)

        self.assertEqual(len(insights), 1)
        self.assertEqual(insights[0].insight_type, "architecture")
        self.assertEqual(insights[0].weight, 9)
        self.assertIn("d110", insights[0].specs_affected)
        self.assertIn("SPEC_d110", insights[0].specs_affected)

    def test_write_insights_creates_schema_and_inserts_rows(self) -> None:
        conn = FakeConnection()
        insights = [
            write_session_insights.SessionInsight(
                insight_type="decision",
                title="Session write-through is required",
                body="Make the bot aware of all surfaces.",
                specs_affected=["d110"],
                weight=8,
            )
        ]

        written = write_session_insights.write_insights(
            conn,
            session_id="session-1",
            surface="claude_code",
            insights=insights,
        )

        self.assertEqual(written, 1)
        executed_sql = "\n".join(sql for sql, _params in conn.cursor_obj.executed)
        self.assertIn("CREATE TABLE IF NOT EXISTS brain_index.session_insights", executed_sql)
        insert_params = conn.cursor_obj.executed[-1][1]
        self.assertEqual(insert_params[0], "session-1")
        self.assertEqual(insert_params[1], "claude_code")
        self.assertEqual(insert_params[3], "Session write-through is required")

    def test_high_weight_invalidates_prompt_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalidate"
            did_invalidate = write_session_insights.invalidate_system_prompt_cache(
                path,
                insights=[write_session_insights.SessionInsight("decision", "James directive", weight=8)],
            )
            self.assertTrue(did_invalidate)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
