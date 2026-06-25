from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from tools.payments import agent_spawn

NOW = datetime(2026, 6, 18, 7, 30, tzinfo=timezone.utc)


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
        if normalized.startswith("select namespace_id, agent_id"):
            event_id = params[0]
            row = self.conn.spawns.get(event_id)
            self.rows = [(row["namespace_id"], row["agent_id"])] if row else []
        elif normalized.startswith("insert into brain_index.user_agents"):
            (
                agent_id,
                namespace_id,
                owner_email,
                owner_external_id,
                source_provider,
                source_event_id,
                passport,
                created_at,
                updated_at,
            ) = params
            self.conn.user_agents.setdefault(
                source_event_id,
                {
                    "agent_id": agent_id,
                    "namespace_id": namespace_id,
                    "owner_email": owner_email,
                    "owner_external_id": owner_external_id,
                    "source_provider": source_provider,
                    "source_event_id": source_event_id,
                    "passport": json.loads(passport),
                    "created_at": created_at,
                    "updated_at": updated_at,
                },
            )
        elif normalized.startswith("insert into brain_index.payment_agent_spawns"):
            (
                provider,
                event_id,
                event_type,
                amount_cents,
                currency,
                customer_email,
                customer_id,
                namespace_id,
                agent_id,
                metadata,
                created_at,
            ) = params
            self.conn.spawns.setdefault(
                event_id,
                {
                    "provider": provider,
                    "event_id": event_id,
                    "event_type": event_type,
                    "amount_cents": amount_cents,
                    "currency": currency,
                    "customer_email": customer_email,
                    "customer_id": customer_id,
                    "namespace_id": namespace_id,
                    "agent_id": agent_id,
                    "metadata": json.loads(metadata),
                    "created_at": created_at,
                },
            )

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeConn:
    def __init__(self):
        self.executed = []
        self.spawns = {}
        self.user_agents = {}
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def close(self):
        self.closed = True


def stripe_checkout_event(event_id: str = "evt_paid_1") -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "payment_status": "paid",
                "amount_total": 4900,
                "currency": "usd",
                "customer": "cus_123",
                "customer_details": {"email": "Ada@Example.COM"},
                "metadata": {"offer": "founding_member"},
            }
        },
    }


class AgentSpawnTests(unittest.TestCase):
    def test_disabled_by_default(self):
        conn = FakeConn()
        event = agent_spawn.payment_event_from_payload(stripe_checkout_event())
        result = agent_spawn.spawn_agent_namespace(event, conn=conn, env={}, now=NOW)
        self.assertFalse(result.enabled)
        self.assertEqual(result.reason, "spawn_disabled")
        self.assertEqual(conn.spawns, {})

    def test_paid_event_spawns_namespace_and_passport(self):
        conn = FakeConn()
        event = agent_spawn.payment_event_from_payload(stripe_checkout_event())
        result = agent_spawn.spawn_agent_namespace(
            event,
            conn=conn,
            env={"PAYMENT_AGENT_SPAWN_ENABLED": "1"},
            now=NOW,
        )
        self.assertTrue(result.spawned)
        self.assertEqual(result.reason, "spawned")
        self.assertTrue(result.namespace_id.startswith("agent_ns_ada-example-com_"))
        self.assertEqual(len(conn.spawns), 1)
        self.assertEqual(len(conn.user_agents), 1)
        stored = next(iter(conn.user_agents.values()))
        self.assertEqual(stored["owner_email"], "ada@example.com")
        self.assertEqual(stored["passport"]["created_from"], "payment_event")
        self.assertEqual(stored["passport"]["access_level"], "paid_member")

    def test_duplicate_payment_event_is_idempotent(self):
        conn = FakeConn()
        event = agent_spawn.payment_event_from_payload(stripe_checkout_event())
        first = agent_spawn.spawn_agent_namespace(
            event,
            conn=conn,
            env={"PAYMENT_AGENT_SPAWN_ENABLED": "1"},
            now=NOW,
        )
        second = agent_spawn.spawn_agent_namespace(
            event,
            conn=conn,
            env={"PAYMENT_AGENT_SPAWN_ENABLED": "1"},
            now=NOW,
        )
        self.assertTrue(first.spawned)
        self.assertFalse(second.spawned)
        self.assertTrue(second.duplicate)
        self.assertEqual(second.namespace_id, first.namespace_id)
        self.assertEqual(len(conn.spawns), 1)

    def test_unpaid_or_unsupported_events_do_not_spawn(self):
        conn = FakeConn()
        unpaid = stripe_checkout_event()
        unpaid["data"]["object"]["payment_status"] = "unpaid"
        event = agent_spawn.payment_event_from_payload(unpaid)
        result = agent_spawn.spawn_agent_namespace(
            event,
            conn=conn,
            env={"PAYMENT_AGENT_SPAWN_ENABLED": "1"},
            now=NOW,
        )
        self.assertEqual(result.reason, "event_not_paid")

        missing_payment_status = stripe_checkout_event()
        del missing_payment_status["data"]["object"]["payment_status"]
        event = agent_spawn.payment_event_from_payload(missing_payment_status)
        result = agent_spawn.spawn_agent_namespace(
            event,
            conn=conn,
            env={"PAYMENT_AGENT_SPAWN_ENABLED": "1"},
            now=NOW,
        )
        self.assertEqual(result.reason, "event_not_paid")

        unsupported = agent_spawn.payment_event_from_payload({"id": "evt_x", "type": "customer.created", "customer_id": "cus_1"})
        result = agent_spawn.spawn_agent_namespace(
            unsupported,
            conn=conn,
            env={"PAYMENT_AGENT_SPAWN_ENABLED": "1"},
            now=NOW,
        )
        self.assertEqual(result.reason, "unsupported_event_type")
        self.assertEqual(conn.spawns, {})

    def test_webhook_requires_hmac_signature_before_spawn(self):
        conn = FakeConn()
        body = json.dumps(stripe_checkout_event()).encode("utf-8")
        env = {"PAYMENT_AGENT_SPAWN_ENABLED": "1", "PAYMENT_AGENT_SPAWN_SECRET": "secret"}
        bad = agent_spawn.handle_webhook_payload(body, signature="wrong", conn=conn, env=env, now=NOW)
        self.assertEqual(bad.reason, "invalid_signature")
        self.assertEqual(conn.spawns, {})

        signature = agent_spawn.sign_body(body, secret="secret", timestamp="1780000000")
        ok = agent_spawn.handle_webhook_payload(body, signature=signature, conn=conn, env=env, now=NOW)
        self.assertTrue(ok.spawned)
        self.assertEqual(len(conn.spawns), 1)


if __name__ == "__main__":
    unittest.main()
