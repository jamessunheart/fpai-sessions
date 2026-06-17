from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from tools.hermes import email_reply_parser

NOW = datetime(2026, 6, 17, 12, 0, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if normalized.startswith("select id, probe_id"):
            since = params[0]
            self.rows = [
                (row["id"], row["probe_id"], row["initiated_at"], row.get("notes"), row.get("message_id"))
                for row in self.conn.sessions
                if row["initiated_at"] >= since and not row.get("engaged")
            ]
        elif "information_schema.columns" in normalized:
            self.rows = [(col,) for col in self.conn.columns_by_table.get(params[0], set())]
        elif normalized.startswith("update brain_index.probe_sessions set engaged = true"):
            when, last_message, extra, session_id = params
            row = self.conn.by_id[session_id]
            row["engaged"] = True
            row["last_message_at"] = when
            row["last_message"] = last_message
            row["notes"] = (row.get("notes") or "") + extra
        elif normalized.startswith("update brain_index.probe_sessions set engaged = false"):
            extra, session_id = params
            row = self.conn.by_id[session_id]
            row["engaged"] = False
            row["notes"] = (row.get("notes") or "") + extra

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, sessions, columns_by_table=None):
        self.sessions = sessions
        self.by_id = {row["id"]: row for row in sessions}
        self.columns_by_table = {"probe_sessions": {"id", "probe_id", "initiated_at", "notes", "message_id"}}
        if columns_by_table:
            self.columns_by_table.update({key: set(value) for key, value in columns_by_table.items()})
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


def make_reply(message_id: str, text: str, *, from_email: str = "champ@example.com") -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = f"Champion <{from_email}>"
    if message_id:
        msg["In-Reply-To"] = f"<{message_id}>"
        msg["References"] = f"<{message_id}>"
    msg.set_content(text)
    return msg


class ReplyParserTests(unittest.TestCase):
    def test_positive_reply_marks_engaged_and_records_bot_link(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(hours=2),
                "engaged": False,
                "notes": json.dumps({"message_id": "brevo-1"}),
                "message_id": "brevo-1",
            }
        ])
        sent = []
        result = email_reply_parser.process_replies(
            conn=conn,
            messages=[make_reply("brevo-1", "yes, interested")],
            now=NOW,
            send_bot_link=lambda session: sent.append(session["probe_id"]) or True,
        )
        self.assertEqual(result.engaged, 1)
        self.assertEqual(sent, ["p1"])
        self.assertTrue(conn.sessions[0]["engaged"])
        self.assertIn(email_reply_parser.BOT_LINK, conn.sessions[0]["last_message"])

    def test_negative_reply_does_not_mark_engaged(self):
        conn = FakeConn([
            {"id": 1, "probe_id": "p1", "initiated_at": NOW - timedelta(hours=2), "engaged": False, "notes": "{}", "message_id": "brevo-1"}
        ])
        result = email_reply_parser.process_replies(conn=conn, messages=[make_reply("brevo-1", "ok, no thanks, not interested")], now=NOW)
        self.assertEqual(result.engaged, 0)
        self.assertFalse(conn.sessions[0]["engaged"])

    def test_reply_can_match_by_sender_when_thread_id_differs(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(hours=2),
                "engaged": False,
                "notes": json.dumps({"handle": "champ@example.com"}),
                "message_id": "brevo-api-id",
            }
        ])
        result = email_reply_parser.process_replies(
            conn=conn,
            messages=[make_reply("different-rfc-message-id", "yes", from_email="champ@example.com")],
            now=NOW,
        )
        self.assertEqual(result.engaged, 1)
        self.assertTrue(conn.sessions[0]["engaged"])

    def test_old_schema_without_message_id_column_uses_notes_handle(self):
        conn = FakeConn(
            [{
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(hours=2),
                "engaged": False,
                "notes": json.dumps({"handle": "champ@example.com"}),
            }],
            columns_by_table={"probe_sessions": {"id", "probe_id", "initiated_at", "notes"}},
        )
        result = email_reply_parser.process_replies(
            conn=conn,
            messages=[make_reply("", "yes", from_email="champ@example.com")],
            now=NOW,
        )
        self.assertEqual(result.engaged, 1)
        self.assertTrue(conn.sessions[0]["engaged"])

    def test_no_reply_after_72h_marks_false(self):
        conn = FakeConn([
            {"id": 1, "probe_id": "p1", "initiated_at": NOW - timedelta(hours=73), "engaged": False, "notes": "{}", "message_id": "brevo-1"}
        ])
        result = email_reply_parser.process_replies(conn=conn, messages=[], now=NOW)
        self.assertEqual(result.expired, 1)
        self.assertIn("no_reply_72h", conn.sessions[0]["notes"])

    def test_late_positive_reply_is_not_expired_same_pass(self):
        conn = FakeConn([
            {"id": 1, "probe_id": "p1", "initiated_at": NOW - timedelta(hours=73), "engaged": False, "notes": "{}", "message_id": "brevo-1"}
        ])
        result = email_reply_parser.process_replies(conn=conn, messages=[make_reply("brevo-1", "sure")], now=NOW)
        self.assertEqual(result.engaged, 1)
        self.assertEqual(result.expired, 0)
        self.assertTrue(conn.sessions[0]["engaged"])
        self.assertNotIn("no_reply_72h", conn.sessions[0]["notes"])


if __name__ == "__main__":
    unittest.main()
