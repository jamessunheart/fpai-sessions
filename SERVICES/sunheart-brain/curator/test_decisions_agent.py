from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

CURATOR_DIR = Path(__file__).resolve().parent
MODULE_PATH = CURATOR_DIR / "decisions.py"
package = types.ModuleType("curator")
package.__path__ = [str(CURATOR_DIR)]
if not hasattr(sys.modules.get("curator"), "__path__"):
    sys.modules["curator"] = package
SPEC = importlib.util.spec_from_file_location("curator.decisions", MODULE_PATH)
assert SPEC and SPEC.loader
decisions = importlib.util.module_from_spec(SPEC)
sys.modules["curator.decisions"] = decisions
SPEC.loader.exec_module(decisions)


class FakeCursor:
    def __init__(self, conn: "FakeConn") -> None:
        self.conn = conn
        self.sql = ""
        self.params: Any = None

    async def __aenter__(self) -> "FakeCursor":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def execute(self, sql: str, params: Any = None) -> None:
        self.sql = sql
        self.params = params
        self.conn.executed.append((sql, params))
        if "INSERT INTO brain_index.corrections" in sql:
            self.conn.corrections.append(params)

    async def fetchone(self) -> tuple[Any, ...] | None:
        if "row_to_json" in self.sql:
            return (self.conn.decision,)
        if "COUNT(*)" in self.sql:
            return (0,)
        return None

    async def fetchall(self) -> list[tuple[Any, ...]]:
        return []


class FakeConn:
    def __init__(self) -> None:
        self.decision = {
            "id": "d028",
            "agent_answer": "run the safe default",
            "agent_why": "High-confidence reversible build.",
        }
        self.executed: list[tuple[str, Any]] = []
        self.corrections: list[Any] = []

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)


class DecisionsAgentWorkflowTest(unittest.TestCase):
    def test_override_writes_weighted_correction(self) -> None:
        conn = FakeConn()

        asyncio.run(decisions.write_override_correction(conn, "d028", "wait until morning", conversation_id="chat-1"))

        self.assertEqual(len(conn.corrections), 1)
        params = conn.corrections[0]
        self.assertEqual(params[0], "chat-1")
        self.assertIn("run the safe default", params[1])
        self.assertEqual(params[2], "Override d028: wait until morning")
        self.assertEqual(params[3], 2.0)

    def test_migration_is_idempotent_sql(self) -> None:
        self.assertIn("ADD COLUMN IF NOT EXISTS agent_score", decisions.MIGRATION_SQL)
        self.assertIn("ADD COLUMN IF NOT EXISTS agent_answer", decisions.MIGRATION_SQL)
        self.assertIn("ADD COLUMN IF NOT EXISTS agent_why", decisions.MIGRATION_SQL)
        self.assertIn("ADD COLUMN IF NOT EXISTS weight", decisions.MIGRATION_SQL)

        conn = FakeConn()
        asyncio.run(decisions.migrate_agent_columns(conn))
        asyncio.run(decisions.migrate_agent_columns(conn))

        self.assertEqual(len(conn.executed), 2)

    def test_parse_override_command(self) -> None:
        self.assertEqual(decisions.parse_override("override d028: wait until morning"), ("d028", "wait until morning"))
        self.assertIsNone(decisions.parse_override("d028: wait until morning"))

    def test_curator_decisions_imports_with_service_pythonpath_only(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import curator.decisions; print('ok')",
            ],
            cwd=str(Path(__file__).resolve().parents[3]),
            env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_surface_next_falls_back_to_card_when_agent_errors_after_awaiting(self) -> None:
        decision = {"id": "d028", "question": "Proceed?", "status": "open"}

        class FakeConnect:
            async def __aenter__(self):
                return FakeConn()

            async def __aexit__(self, *_: object) -> None:
                return None

        fake_db = types.ModuleType("curator.db")
        fake_db.connect = lambda: FakeConnect()

        with patch.dict(sys.modules, {"curator.db": fake_db}):
            with patch.object(decisions, "migrate_agent_columns", new=AsyncMock()):
                with patch.object(decisions, "_fetch_first_by_status", new=AsyncMock(side_effect=[None, decision])):
                    with patch.object(decisions, "_mark_awaiting", new=AsyncMock()):
                        with patch.object(
                            decisions,
                            "auto_answer_if_confident",
                            new=AsyncMock(side_effect=RuntimeError("boom")),
                        ):
                            with patch.object(decisions, "_send_decision_card", new=AsyncMock()) as send_card:
                                result = asyncio.run(decisions.surface_next())

        self.assertEqual(result, {"id": "d028", "auto_decided": False})
        send_card.assert_awaited_once_with(decision)


if __name__ == "__main__":
    unittest.main()
