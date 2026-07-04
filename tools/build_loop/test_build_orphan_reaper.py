#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

from tools.build_loop import build_orphan_reaper as reaper

ROOT = Path(__file__).resolve().parents[2]


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if normalized.startswith("alter table if exists brain_index.decisions add column"):
            self.conn.column_ensured = True
            return
        if normalized.startswith("update brain_index.decisions set build_attempts = 0"):
            self.conn.null_attempts_zeroed = True
            return
        if normalized.startswith("alter table if exists brain_index.decisions alter column"):
            self.conn.default_ensured = True
            return
        if normalized.startswith("select id::text, coalesce(build_attempts"):
            self._rows = [(row["id"], row.get("build_attempts", 0)) for row in self.conn.orphans]
            self.conn.select_params = params
            return
        if "set spec_written = false" in normalized:
            decision_id = params[0]
            self.conn.reset.append(decision_id)
            for row in self.conn.orphans:
                if row["id"] == decision_id:
                    row["spec_written"] = False
                    row["build_attempts"] = row.get("build_attempts", 0) + 1
            return
        if "set build_status = 'blocked'" in normalized:
            decision_id = params[0]
            self.conn.blocked.append(decision_id)
            for row in self.conn.orphans:
                if row["id"] == decision_id:
                    row["build_status"] = "blocked"
            return
        raise AssertionError(f"unexpected SQL: {sql}")

    def fetchall(self):
        return list(self._rows)


class FakeConn:
    def __init__(self, orphans):
        self.orphans = list(orphans)
        self.reset = []
        self.blocked = []
        self.executed = []
        self.select_params = ()
        self.column_ensured = False
        self.default_ensured = False
        self.null_attempts_zeroed = False
        self.committed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True


class BuildOrphanReaperTest(unittest.TestCase):
    def test_resets_orphans_below_retry_limit_and_increments_attempts(self) -> None:
        conn = FakeConn(
            [
                {"id": "d149", "build_attempts": 0, "spec_written": True},
                {"id": "d152", "build_attempts": 1, "spec_written": True},
            ]
        )

        result = reaper.reap_orphaned_decisions(conn, older_minutes=30, retry_limit=2)

        self.assertEqual(result.reset, ("d149", "d152"))
        self.assertEqual(result.blocked, ())
        self.assertEqual(conn.reset, ["d149", "d152"])
        self.assertEqual([row["build_attempts"] for row in conn.orphans], [1, 2])
        self.assertFalse(any(row["spec_written"] for row in conn.orphans))
        self.assertTrue(conn.committed)

    def test_blocks_orphans_at_retry_limit(self) -> None:
        conn = FakeConn([{"id": "d152", "build_attempts": 2, "spec_written": True}])

        result = reaper.reap_orphaned_decisions(conn, older_minutes=30, retry_limit=2)

        self.assertEqual(result.reset, ())
        self.assertEqual(result.blocked, ("d152",))
        self.assertEqual(conn.blocked, ["d152"])
        self.assertEqual(conn.orphans[0]["build_status"], "blocked")
        self.assertTrue(conn.committed)

    def test_query_matches_spec_written_none_no_branch_age_shape(self) -> None:
        conn = FakeConn([])

        reaper.reap_orphaned_decisions(conn, older_minutes=45, retry_limit=2)

        select_sql = next(sql for sql, _ in conn.executed if sql.startswith("select id::text"))
        self.assertIn("coalesce(spec_written, false) = true", select_sql)
        self.assertIn("lower(coalesce(build_status, 'none')) = 'none'", select_sql)
        self.assertIn("coalesce(build_branch, '') = ''", select_sql)
        self.assertIn("coalesce(updated_at, created_at, now()) < now() -", select_sql)
        self.assertEqual(conn.select_params, ("45 minutes",))

    def test_ensures_build_attempts_column(self) -> None:
        conn = FakeConn([])

        reaper.reap_orphaned_decisions(conn)

        self.assertTrue(conn.column_ensured)
        self.assertTrue(conn.null_attempts_zeroed)
        self.assertTrue(conn.default_ensured)

    def test_server_loop_runs_reaper_before_pending_builds(self) -> None:
        text = (ROOT / "tools" / "build_loop" / "server_build_loop.sh").read_text(encoding="utf-8")

        self.assertIn("build_orphan_reaper.py", text)
        self.assertLess(text.index("build_orphan_reaper.py"), text.index("PENDING=$(dec pending-builds"))


if __name__ == "__main__":
    unittest.main()
