from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from tools.probe import followup

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
            cutoff, marker, limit = params
            rows = []
            for row in self.conn.sessions:
                if row["initiated_at"] >= cutoff:
                    continue
                if row.get("engaged") is True:
                    continue
                if marker.strip("%") in (row.get("notes") or ""):
                    continue
                rows.append((row["id"], row["probe_id"], row["initiated_at"], row.get("notes"), row.get("message_id")))
            self.rows = rows[:limit]
        elif "returning id" in normalized and normalized.startswith("update brain_index.probe_sessions"):
            claim, session_id, sent_marker, claimed_marker = params
            row = self.conn.by_id[session_id]
            notes = row.get("notes") or ""
            if sent_marker.strip("%") in notes or claimed_marker.strip("%") in notes:
                self.rows = []
            else:
                row["notes"] = notes + claim
                self.rows = [(session_id,)]
        elif "set notes = replace" in normalized:
            claim, session_id = params
            row = self.conn.by_id[session_id]
            row["notes"] = (row.get("notes") or "").replace(claim, "")
            self.rows = []
        elif normalized.startswith("update brain_index.probe_sessions set notes"):
            extra, session_id = params
            row = self.conn.by_id[session_id]
            row["notes"] = (row.get("notes") or "") + extra
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

    def cursor(self):
        return FakeCursor(self)


class FollowupTests(unittest.TestCase):
    def test_followup_sends_after_3_days_no_engagement(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(days=4),
                "engaged": None,
                "notes": json.dumps({"handle": "alex@example.com", "name": "Alex Human"}),
                "message_id": "brevo-1",
            }
        ])
        seen = []

        def sender(session):
            seen.append(session)
            return SimpleNamespace(sent=True, dry_run=False, message_id="follow-1", sent_at="2026-06-17T12:00:00Z", reason="sent")

        result = followup.run_followups(conn=conn, sender=sender, now=NOW)
        self.assertEqual(result.sent, 1)
        self.assertEqual(seen[0].email, "alex@example.com")
        self.assertEqual(seen[0].name, "Alex")
        self.assertIn("tg_cta_sent", conn.sessions[0]["notes"])

    def test_followup_not_sent_when_tg_cta_already_in_notes(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(days=4),
                "engaged": None,
                "notes": json.dumps({"handle": "alex@example.com"}) + "\ntg_cta_sent={}",
                "message_id": "brevo-1",
            }
        ])
        result = followup.run_followups(
            conn=conn,
            sender=lambda _session: self.fail("should not send duplicate Telegram CTA"),
            now=NOW,
        )
        self.assertEqual(result.sent, 0)
        self.assertEqual(result.eligible, 0)

    def test_followup_skips_recent_and_non_email_sessions(self):
        conn = FakeConn([
            {"id": 1, "probe_id": "recent", "initiated_at": NOW - timedelta(days=1), "engaged": None, "notes": json.dumps({"handle": "alex@example.com"})},
            {"id": 2, "probe_id": "tg", "initiated_at": NOW - timedelta(days=4), "engaged": None, "notes": json.dumps({"handle": "@alex"})},
        ])
        result = followup.run_followups(
            conn=conn,
            sender=lambda _session: self.fail("should not send"),
            now=NOW,
        )
        self.assertEqual(result.eligible, 0)

    def test_followup_payload_uses_telegram_cta_and_probe_reply_address(self):
        session = followup.FollowupSession(
            id=1,
            probe_id="p1",
            email="alex@example.com",
            name="Alex",
            initiated_at=NOW,
            notes="{}",
        )
        payload = followup.build_followup_payload(session, env={})
        self.assertEqual(payload["subject"], followup.FOLLOWUP_SUBJECT)
        self.assertEqual(payload["replyTo"]["email"], "probe-replies@fullpotential.ai")
        self.assertIn("@sunheartbrain_bot", payload["textContent"])
        self.assertIn("Hi Alex,", payload["textContent"])

    def test_failed_live_followup_releases_claim_for_retry(self):
        conn = FakeConn([
            {
                "id": 1,
                "probe_id": "p1",
                "initiated_at": NOW - timedelta(days=4),
                "engaged": None,
                "notes": json.dumps({"handle": "alex@example.com"}),
                "message_id": "brevo-1",
            }
        ])
        old_live = followup.email_adapter.is_live_enabled
        followup.email_adapter.is_live_enabled = lambda *_args, **_kwargs: True
        try:
            result = followup.run_followups(
                conn=conn,
                sender=lambda _session: SimpleNamespace(sent=False, dry_run=False, message_id=None, sent_at=None, reason="missing_brevo_api_key"),
                now=NOW,
            )
        finally:
            followup.email_adapter.is_live_enabled = old_live
        self.assertEqual(result.failed, 1)
        self.assertNotIn("tg_cta_claimed", conn.sessions[0]["notes"])
        self.assertNotIn("tg_cta_sent", conn.sessions[0]["notes"])


if __name__ == "__main__":
    unittest.main()
