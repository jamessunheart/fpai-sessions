from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.learn import seed_preference_pairs as seed


class FakeCursor:
    def __init__(self, conn: "FakeConn") -> None:
        self.conn = conn
        self.sql = ""
        self.params: Any = None

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def execute(self, sql: str, params: Any = None) -> None:
        self.sql = sql
        self.params = params
        self.conn.executed.append((sql, params))
        if sql.lstrip().upper().startswith("UPDATE"):
            self.conn.updated_ids.extend(str(item) for item in (params or []))

    def fetchall(self) -> list[tuple[Any, ...]]:
        if "information_schema.columns" in self.sql:
            return [(column,) for column in self.conn.columns]
        if "WHERE \"preference_pair_exported\" IS NULL" in self.sql:
            cols = self._select_columns()
            return [tuple(row.get(col) for col in cols) for row in self.conn.rows]
        return []

    def fetchone(self) -> tuple[int]:
        if "COUNT(*)" in self.sql:
            return (self.conn.older_count,)
        return (0,)

    def _select_columns(self) -> list[str]:
        before_from = self.sql.split(" FROM ", 1)[0]
        raw = before_from.removeprefix("SELECT ").split(",")
        return [item.strip().strip('"') for item in raw]


class FakeConn:
    def __init__(self, *, columns: list[str], rows: list[dict[str, Any]], older_count: int = 0) -> None:
        self.columns = columns
        self.rows = rows
        self.older_count = older_count
        self.executed: list[tuple[str, Any]] = []
        self.updated_ids: list[str] = []
        self.committed = False

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)

    def commit(self) -> None:
        self.committed = True


class SeedPreferencePairsTest(unittest.TestCase):
    def root(self) -> Path:
        return Path(tempfile.mkdtemp(prefix="fpai-d022-seed-"))

    def test_exports_spec_columns_stamps_rows_and_logs_count(self) -> None:
        root = self.root()
        output = root / "data" / "preference_pairs.jsonl"
        ledger = root / "ops_ledger.jsonl"
        conn = FakeConn(
            columns=[
                "id",
                "session_id",
                "bot_response",
                "correction_text",
                "preference_pair_exported",
                "captured_at",
            ],
            rows=[
                {
                    "id": "1",
                    "session_id": "session-a",
                    "bot_response": "Ask James to pick every reversible default.",
                    "correction_text": "Pick the reversible default and report rollback.",
                }
            ],
        )

        result = seed.export(conn, output=output, ops_ledger=ledger)

        self.assertEqual(result.exported, 1)
        self.assertEqual(result.output_lines, 1)
        self.assertEqual(conn.updated_ids, ["1"])
        self.assertTrue(conn.committed)
        row = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(
            row,
            {
                "prompt": "session-a",
                "chosen": "Pick the reversible default and report rollback.",
                "rejected": "Ask James to pick every reversible default.",
            },
        )
        ledger_row = json.loads(ledger.read_text(encoding="utf-8"))
        self.assertEqual(ledger_row["row_count"], 1)
        self.assertEqual(ledger_row["artifact"], str(output))

    def test_supports_d014_correction_column_names_after_d021_watermark(self) -> None:
        root = self.root()
        output = root / "pairs.jsonl"
        conn = FakeConn(
            columns=[
                "id",
                "conversation_id",
                "original_response",
                "james_correction",
                "preference_pair_exported",
                "captured_at",
            ],
            rows=[
                {
                    "id": "corr-1",
                    "conversation_id": "chat-7",
                    "original_response": "d010 is not relevant.",
                    "james_correction": "d010 is the preference dataset spine.",
                }
            ],
        )

        result = seed.export(conn, output=output, ops_ledger=root / "ledger.jsonl")

        self.assertEqual(result.exported, 1)
        row = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(row["prompt"], "chat-7")
        self.assertEqual(row["chosen"], "d010 is the preference dataset spine.")
        self.assertEqual(row["rejected"], "d010 is not relevant.")

    def test_missing_preference_pair_exported_fails_d021_gate(self) -> None:
        conn = FakeConn(
            columns=["id", "conversation_id", "original_response", "james_correction", "captured_at"],
            rows=[],
        )

        with self.assertRaisesRegex(RuntimeError, "d021 gate not verified live"):
            seed.detect_columns(conn)

    def test_proof_requires_existing_lines_and_no_old_unexported_rows(self) -> None:
        passing = seed.ExportResult(
            read=0,
            exported=0,
            output="/tmp/preference_pairs.jsonl",
            output_lines=3,
            unexported_older_than_24h=0,
            dry_run=False,
        )
        failing = seed.ExportResult(
            read=0,
            exported=0,
            output="/tmp/preference_pairs.jsonl",
            output_lines=3,
            unexported_older_than_24h=1,
            dry_run=False,
        )

        self.assertTrue(seed.proof_passes(passing))
        self.assertFalse(seed.proof_passes(failing))


if __name__ == "__main__":
    unittest.main()
