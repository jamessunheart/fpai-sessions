from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from tools.probe import award_cora

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, conn: "FakeConn"):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if "information_schema.columns" in normalized:
            table = params[0]
            self.rows = [(col,) for col in self.conn.columns_by_table.get(table, set())]
        elif normalized.startswith("create schema") or normalized.startswith("alter table") or normalized.startswith("create table"):
            self.rows = []
        elif "from brain_index.probe_sessions" in normalized:
            cutoff = params[0]
            rows = []
            for session in self.conn.sessions:
                message_count = session.get("message_count")
                if message_count is None:
                    message_count = session.get("drop_off_message", 0)
                completed = bool(session.get("completed_spark"))
                closed = completed or (session.get("last_message_at") or session.get("initiated_at")) <= cutoff
                meaningful = completed or int(message_count or 0) >= 5
                if not meaningful or not closed:
                    continue
                rows.append((
                    session.get("probe_id"),
                    session.get("tester_identifier"),
                    session.get("notes"),
                    completed,
                    message_count or 0,
                    session.get("corrections_triggered", 0),
                    session.get("last_message_at"),
                    session.get("initiated_at"),
                    session.get("last_message"),
                ))
            self.rows = rows
        elif normalized.startswith("insert into brain_index.cora_ledger"):
            event_type, tester_identifier, points, source_type, source_id, metadata, created_at = params
            key = (source_type, source_id)
            if key in self.conn.ledger_keys:
                self.rows = []
                return
            self.conn.ledger_keys.add(key)
            self.conn.ledger.append({
                "event_type": event_type,
                "tester_identifier": tester_identifier,
                "points": points,
                "source_type": source_type,
                "source_id": source_id,
                "metadata": json.loads(metadata),
                "created_at": created_at,
            })
            self.rows = [(len(self.conn.ledger),)]
        else:
            self.rows = []

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConn:
    def __init__(self, sessions=None, columns_by_table=None):
        self.sessions = list(sessions or [])
        self.columns_by_table = {
            "probe_sessions": {
                "probe_id",
                "tester_identifier",
                "notes",
                "completed_spark",
                "drop_off_message",
                "corrections_triggered",
                "last_message_at",
                "initiated_at",
                "last_message",
            }
        }
        if columns_by_table:
            self.columns_by_table.update({key: set(value) for key, value in columns_by_table.items()})
        self.ledger = []
        self.ledger_keys = set()
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


class AwardCoraTests(unittest.TestCase):
    def test_awards_credit_on_completed_spark(self):
        conn = FakeConn([
            {
                "probe_id": "probe-1",
                "tester_identifier": "tester@example.com",
                "notes": "{}",
                "completed_spark": True,
                "drop_off_message": 2,
                "corrections_triggered": 0,
                "last_message_at": NOW - timedelta(minutes=5),
                "initiated_at": NOW - timedelta(hours=1),
                "last_message": "done",
            }
        ])
        awards = award_cora.award_cora(conn=conn, now=NOW)
        self.assertEqual(len(awards), 1)
        self.assertEqual(awards[0].points, 10)
        self.assertEqual(conn.ledger[0]["event_type"], "probe_conversation_complete")
        self.assertEqual(conn.ledger[0]["source_id"], "probe-1")

    def test_no_double_award_for_same_probe_id(self):
        conn = FakeConn([
            {
                "probe_id": "probe-1",
                "tester_identifier": "@tester",
                "notes": "{}",
                "completed_spark": True,
                "drop_off_message": 5,
                "corrections_triggered": 0,
                "last_message_at": NOW - timedelta(days=4),
                "initiated_at": NOW - timedelta(days=4),
                "last_message": "",
            }
        ])
        first = award_cora.award_cora(conn=conn, now=NOW)
        second = award_cora.award_cora(conn=conn, now=NOW)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 0)
        self.assertEqual(len(conn.ledger), 1)

    def test_correction_bonus_triggers_on_corrections_triggered(self):
        conn = FakeConn([
            {
                "probe_id": "probe-2",
                "tester_identifier": "@tester",
                "notes": json.dumps({"specific_gap_reported": True}),
                "completed_spark": False,
                "drop_off_message": 5,
                "corrections_triggered": 1,
                "last_message_at": NOW - timedelta(days=4),
                "initiated_at": NOW - timedelta(days=4),
                "last_message": "The system should say this differently.",
            }
        ])
        awards = award_cora.award_cora(conn=conn, now=NOW)
        self.assertEqual(len(awards), 1)
        self.assertEqual(awards[0].points, 25)
        self.assertEqual(awards[0].specific_gap_bonus, 5)
        self.assertEqual(awards[0].validated_correction_bonus, 10)


if __name__ == "__main__":
    unittest.main()
