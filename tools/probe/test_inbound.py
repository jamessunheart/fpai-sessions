from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from tools.probe import inbound_webhook

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
        if normalized.startswith("select id, message_id"):
            self.rows = [
                (row["id"], row.get("message_id"), row.get("notes"))
                for row in sorted(self.conn.sessions, key=lambda item: item["initiated_at"], reverse=True)
                if row.get("engaged") is not True
            ][:250]
        elif normalized.startswith("update brain_index.probe_sessions set engaged = true"):
            when, last_message, extra, session_id = params
            row = self.conn.by_id[session_id]
            row["engaged"] = True
            row["last_message_at"] = when
            row["last_message"] = last_message
            row["notes"] = (row.get("notes") or "") + extra
        elif normalized.startswith("insert into brain_index.probe_reply_queue"):
            self.conn.reply_queue.append(params)
            self.rows = [(len(self.conn.reply_queue),)]
        elif normalized.startswith("create table if not exists brain_index.probe_reply_queue"):
            self.rows = []

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConn:
    def __init__(self, sessions):
        self.sessions = sessions
        self.by_id = {row["id"]: row for row in sessions}
        self.executed = []
        self.reply_queue = []

    def cursor(self):
        return FakeCursor(self)


class InboundTests(unittest.TestCase):
    def test_inbound_reply_disabled_by_default(self):
        conn = FakeConn([])
        result = inbound_webhook.handle_inbound_reply(
            inbound_webhook.InboundReply(from_email="alex@example.com", body="yes"),
            conn=conn,
            env={},
            now=NOW,
        )
        self.assertFalse(result.enabled)
        self.assertEqual(result.reason, "pipe_disabled")

    def test_inbound_reply_matches_email_and_updates_session(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(days=1),
                "engaged": None,
                "message_id": "brevo-1",
                "notes": json.dumps({"handle": "alex@example.com"}),
            }
        ])
        result = inbound_webhook.handle_inbound_reply(
            inbound_webhook.InboundReply(
                from_email="Alex <alex@example.com>",
                subject="Re: Still here",
                body="Yes, I want to talk.",
                message_id="<reply-1>",
                in_reply_to="<unknown-id>",
            ),
            conn=conn,
            env={"PROBE_PIPE_ENABLED": "1", "PROBE_PIPE_TOKEN": "secret"},
            pipe_token="secret",
            now=NOW,
        )
        self.assertTrue(result.matched)
        self.assertEqual(result.session_id, 1)
        self.assertTrue(conn.sessions[0]["engaged"])
        self.assertEqual(conn.sessions[0]["last_message"], "Yes, I want to talk.")
        self.assertIn("queued_probe_reply", conn.sessions[0]["notes"])
        self.assertEqual(len(conn.reply_queue), 1)

    def test_inbound_reply_matches_message_id(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(days=1),
                "engaged": None,
                "message_id": "brevo-1",
                "notes": "{}",
            }
        ])
        result = inbound_webhook.handle_inbound_reply(
            inbound_webhook.InboundReply(
                from_email="other@example.com",
                body="sure",
                in_reply_to="<brevo-1>",
            ),
            conn=conn,
            env={"PROBE_PIPE_ENABLED": "1", "PROBE_PIPE_TOKEN": "secret"},
            pipe_token="secret",
            now=NOW,
        )
        self.assertTrue(result.matched)
        self.assertTrue(conn.sessions[0]["engaged"])

    def test_inbound_reply_rejects_invalid_pipe_token(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(days=1),
                "engaged": None,
                "message_id": "brevo-1",
                "notes": "{}",
            }
        ])
        result = inbound_webhook.handle_inbound_reply(
            inbound_webhook.InboundReply(from_email="alex@example.com", body="yes", in_reply_to="<brevo-1>"),
            conn=conn,
            env={"PROBE_PIPE_ENABLED": "1", "PROBE_PIPE_TOKEN": "secret"},
            pipe_token="wrong",
            now=NOW,
        )
        self.assertFalse(result.matched)
        self.assertEqual(result.reason, "pipe_token_invalid")
        self.assertFalse(conn.sessions[0].get("engaged"))


if __name__ == "__main__":
    unittest.main()
