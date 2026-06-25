from __future__ import annotations

import hashlib
import hmac
import json
import unittest
from types import SimpleNamespace

from tools.hermes import whatsapp_adapter


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def execute(self, sql, params=()):
        normalized = " ".join(sql.lower().split())
        self.conn.executed.append((normalized, params))
        if "from brain_index.contact_pool" in normalized:
            match = next((row for row in self.conn.contacts if row["wa_id"] == params[1]), None)
            self.rows = [(match["id"],)] if match else []
        elif "insert into brain_index.contact_pool" in normalized:
            contact_id = len(self.conn.contacts) + 1
            self.conn.contacts.append({"id": contact_id, "wa_id": params[2], "status": params[6]})
            self.rows = [(contact_id,)]
        elif normalized.startswith("update brain_index.contact_pool"):
            self.rows = []
        elif "from brain_index.probe_pool" in normalized:
            match = next((row for row in self.conn.pool if row["platform"] == params[0] and row["handle"] == params[1]), None)
            self.rows = [(match["id"],)] if match else []
        elif "insert into brain_index.probe_pool" in normalized:
            pool_id = len(self.conn.pool) + 1
            self.conn.pool.append({"id": pool_id, "platform": params[2], "handle": params[1], "metadata": params[7]})
            self.rows = [(pool_id,)]
        elif normalized.startswith("insert into brain_index.probe_sessions"):
            self.conn.sessions.append({"probe_id": params[0], "last_message": params[5], "notes": params[6]})
            self.rows = []
        else:
            self.rows = []

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConn:
    def __init__(self):
        self.contacts = []
        self.pool = []
        self.sessions = []
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


class WhatsAppAdapterTests(unittest.TestCase):
    def test_webhook_signature_verification(self):
        body = b'{"hello":"world"}'
        signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        self.assertTrue(whatsapp_adapter.verify_meta_signature(body, signature, "secret"))
        self.assertFalse(whatsapp_adapter.verify_meta_signature(body, signature, "wrong"))

    def test_inbound_message_routes_to_contact_and_probe_pool(self):
        payload = {
            "entry": [{
                "changes": [{
                    "value": {
                        "contacts": [{"wa_id": "15551234567", "profile": {"name": "Alex"}}],
                        "messages": [{
                            "from": "15551234567",
                            "id": "wamid.inbound",
                            "timestamp": "1710000000",
                            "type": "text",
                            "text": {"body": "I'm interested"},
                        }],
                    }
                }]
            }]
        }
        message = whatsapp_adapter.parse_incoming_messages(payload)[0]
        sent = []
        conn = FakeConn()
        result = whatsapp_adapter.route_incoming_message(
            message,
            conn=conn,
            sender=lambda to, text: sent.append((to, text)) or SimpleNamespace(sent=False, dry_run=True, disabled=False, reason="dry_run"),
        )
        self.assertTrue(result.accepted)
        self.assertEqual(conn.contacts[0]["wa_id"], "15551234567")
        self.assertEqual(conn.pool[0]["platform"], "whatsapp")
        self.assertEqual(conn.pool[0]["handle"], "15551234567")
        self.assertEqual(conn.sessions[0]["last_message"], "I'm interested")
        self.assertEqual(sent[0][0], "15551234567")

    def test_handle_webhook_rejects_bad_signature(self):
        status, data = whatsapp_adapter.handle_webhook_post(
            b"{}",
            {"X-Hub-Signature-256": "sha256=bad"},
            conn=FakeConn(),
            app_secret="secret",
        )
        self.assertEqual(status, 403)
        self.assertEqual(data["reason"], "bad_signature")

    def test_handle_webhook_accepts_signed_payload(self):
        body = json.dumps({
            "entry": [{"changes": [{"value": {"messages": [{"from": "15551234567", "type": "text", "text": {"body": "yes"}}]}}]}]
        }).encode("utf-8")
        signature = "sha256=" + hmac.new(b"secret", body, hashlib.sha256).hexdigest()
        status, data = whatsapp_adapter.handle_webhook_post(
            body,
            {"X-Hub-Signature-256": signature},
            conn=FakeConn(),
            app_secret="secret",
            sender=lambda _to, _text: SimpleNamespace(sent=False, dry_run=True, disabled=False, reason="dry_run"),
        )
        self.assertEqual(status, 200)
        self.assertEqual(data["routed"], 1)
        self.assertEqual(data["send_reasons"], ["dry_run"])


if __name__ == "__main__":
    unittest.main()
