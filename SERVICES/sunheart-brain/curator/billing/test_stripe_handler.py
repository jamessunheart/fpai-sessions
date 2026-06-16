from __future__ import annotations

import importlib.util
import json
import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("stripe_handler.py")
SERVICE_ROOT = MODULE_PATH.parents[2]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))
SPEC = importlib.util.spec_from_file_location("stripe_handler", MODULE_PATH)
assert SPEC and SPEC.loader
stripe_handler = importlib.util.module_from_spec(SPEC)
sys.modules["stripe_handler"] = stripe_handler
SPEC.loader.exec_module(stripe_handler)


class FakeCursor:
    def __init__(self, db: "FakeDB") -> None:
        self.db = db
        self.description = None
        self.rows: list[tuple] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *exc) -> None:
        return None

    def execute(self, sql: str, params: tuple = ()) -> None:
        collapsed = " ".join(sql.split())
        self.description = None
        self.rows = []
        if collapsed.startswith("SELECT user_id, tier, subscription_status"):
            user = self.db.users.get(params[0])
            self.description = ("rows",)
            if user:
                self.rows = [
                    (
                        params[0],
                        user.get("tier"),
                        user.get("subscription_status"),
                        user.get("stripe_customer_id"),
                        user.get("stripe_subscription_id"),
                        user.get("cora_balance", 0),
                        user.get("beacon_id"),
                        user.get("subscription_grace_until"),
                    )
                ]
            return
        if collapsed.startswith("SELECT user_id FROM brain_index.user_agents WHERE stripe_customer_id"):
            self.description = ("rows",)
            customer_id = params[0]
            for user_id, user in self.db.users.items():
                if user.get("stripe_customer_id") == customer_id:
                    self.rows = [(user_id,)]
                    break
            return
        if collapsed.startswith("INSERT INTO brain_index.user_agents"):
            user_id, tier, status, customer_id, subscription_id, grace_until = params
            user = self.db.users.setdefault(user_id, {"cora_balance": 0})
            user.update(
                {
                    "tier": tier,
                    "subscription_status": status,
                    "subscription_grace_until": grace_until,
                }
            )
            if customer_id:
                user["stripe_customer_id"] = customer_id
            if subscription_id:
                user["stripe_subscription_id"] = subscription_id
            return
        if collapsed.startswith("UPDATE brain_index.user_agents SET cora_balance"):
            amount, user_id = params
            user = self.db.users.setdefault(user_id, {"tier": "free", "subscription_status": "free"})
            user["cora_balance"] = user.get("cora_balance", 0) + amount
            return
        if collapsed.startswith("INSERT INTO brain_index.ops_ledger"):
            event_type, user_id, tier, customer_id, meta = params
            self.db.ledger.append(
                {
                    "event": "stripe_webhook",
                    "type": event_type,
                    "user_id": user_id,
                    "tier": tier,
                    "stripe_customer_id": customer_id,
                    "meta": json.loads(meta),
                }
            )
            return
        raise AssertionError(f"Unexpected SQL: {collapsed}")

    def fetchall(self) -> list[tuple]:
        return self.rows


class FakeConnection:
    def __init__(self, db: "FakeDB") -> None:
        self.db = db

    def __enter__(self) -> "FakeConnection":
        self.db.connects += 1
        return self

    def __exit__(self, *exc) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.db)


class FakeDB:
    def __init__(self) -> None:
        self.users: dict[str, dict] = {}
        self.ledger: list[dict] = []
        self.connects = 0

    def connect(self) -> FakeConnection:
        return FakeConnection(self)


class FakeStripe:
    class Webhook:
        should_fail = False

        @classmethod
        def construct_event(cls, payload: bytes, sig: str, secret: str) -> dict:
            if cls.should_fail or sig != "good":
                raise ValueError("bad signature")
            return json.loads(payload.decode("utf-8"))

    class checkout:
        class Session:
            created: dict | None = None

            @classmethod
            def create(cls, **kwargs) -> dict:
                cls.created = kwargs
                return {"url": "https://checkout.stripe.test/session_123"}

    class billing_portal:
        class Session:
            created: dict | None = None

            @classmethod
            def create(cls, **kwargs) -> dict:
                cls.created = kwargs
                return {"url": "https://billing.stripe.test/portal_123"}


class StripeHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = FakeDB()
        FakeStripe.Webhook.should_fail = False
        FakeStripe.checkout.Session.created = None
        FakeStripe.billing_portal.Session.created = None
        stripe_handler.configure_for_tests(connect_factory=self.db.connect, stripe_client=FakeStripe)
        self.env = patch.dict(
            os.environ,
            {
                "STRIPE_WEBHOOK_SECRET": "whsec_test",
                "STRIPE_SECRET_KEY": "sk_test",
                "STRIPE_PRICE_BASIC_ID": "price_basic",
                "STRIPE_PRICE_PRO_ID": "price_pro",
            },
            clear=False,
        )
        self.env.start()
        self.notify_subscription = stripe_handler._notify_subscription
        self.notify_payment_failed = stripe_handler._notify_payment_failed
        stripe_handler._notify_subscription = lambda user_id, tier, amount: None
        stripe_handler._notify_payment_failed = lambda user_id: None

    def tearDown(self) -> None:
        stripe_handler._notify_subscription = self.notify_subscription
        stripe_handler._notify_payment_failed = self.notify_payment_failed
        self.env.stop()
        stripe_handler.configure_for_tests()
        sys.modules.pop("tools.beacon.events", None)

    def webhook_payload(self, event_type: str, obj: dict) -> bytes:
        return json.dumps({"type": event_type, "data": {"object": obj}}).encode("utf-8")

    def test_webhook_rejects_unverified_signature_before_db(self) -> None:
        with self.assertRaises(stripe_handler.WebhookVerificationError):
            stripe_handler.handle_webhook(self.webhook_payload("checkout.session.completed", {}), "bad")

        self.assertEqual(self.db.connects, 0)
        self.assertEqual(self.db.users, {})

    def test_checkout_completed_updates_user_tier_and_stripe_ids(self) -> None:
        payload = self.webhook_payload(
            "checkout.session.completed",
            {
                "customer": "cus_123",
                "subscription": "sub_123",
                "metadata": {"user_id": "u1", "tier": "basic"},
            },
        )

        stripe_handler.handle_webhook(payload, "good")

        self.assertEqual(self.db.users["u1"]["tier"], "basic")
        self.assertEqual(self.db.users["u1"]["subscription_status"], "active")
        self.assertEqual(self.db.users["u1"]["stripe_customer_id"], "cus_123")
        self.assertEqual(self.db.users["u1"]["stripe_subscription_id"], "sub_123")
        self.assertEqual(self.db.ledger[-1]["type"], "checkout.session.completed")

    def test_subscription_deleted_sets_tier_free_after_grace_period(self) -> None:
        self.db.users["u1"] = {
            "tier": "pro",
            "subscription_status": "active",
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "cora_balance": 0,
        }

        stripe_handler.handle_webhook(
            self.webhook_payload(
                "customer.subscription.deleted",
                {"id": "sub_123", "customer": "cus_123", "metadata": {"user_id": "u1"}},
            ),
            "good",
        )

        self.assertEqual(self.db.users["u1"]["tier"], "free")
        self.assertEqual(self.db.users["u1"]["subscription_status"], "cancelled")
        self.assertIsNotNone(self.db.users["u1"]["subscription_grace_until"])

    def test_cora_award_and_beacon_event_fire_on_subscription_start(self) -> None:
        calls: list[tuple[str, str]] = []
        fake_events = types.ModuleType("tools.beacon.events")
        fake_events.record_event = lambda beacon_id, event: calls.append((beacon_id, event))
        sys.modules["tools.beacon.events"] = fake_events
        self.db.users["u1"] = {
            "tier": "free",
            "subscription_status": "free",
            "cora_balance": 5,
            "beacon_id": "beacon-1",
        }

        stripe_handler.handle_webhook(
            self.webhook_payload(
                "checkout.session.completed",
                {
                    "customer": "cus_123",
                    "subscription": "sub_123",
                    "metadata": {"user_id": "u1", "tier": "pro"},
                },
            ),
            "good",
        )

        self.assertEqual(self.db.users["u1"]["cora_balance"], 505)
        self.assertEqual(calls, [("beacon-1", "paid_conversion")])

    def test_create_checkout_session_returns_url_with_user_metadata(self) -> None:
        url = stripe_handler.create_checkout_session("u1", "basic")

        self.assertEqual(url, "https://checkout.stripe.test/session_123")
        created = FakeStripe.checkout.Session.created
        self.assertIsNotNone(created)
        self.assertEqual(created["metadata"], {"user_id": "u1", "tier": "basic"})
        self.assertEqual(created["line_items"][0]["price"], "price_basic")

    def test_existing_active_subscriber_gets_portal_not_second_checkout(self) -> None:
        self.db.users["u1"] = {
            "tier": "basic",
            "subscription_status": "active",
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "cora_balance": 0,
        }

        url = stripe_handler.create_checkout_session("u1", "pro")

        self.assertEqual(url, "https://billing.stripe.test/portal_123")
        self.assertIsNone(FakeStripe.checkout.Session.created)
        self.assertEqual(FakeStripe.billing_portal.Session.created["customer"], "cus_123")

    def test_cancelled_subscription_keeps_paid_tier_during_grace(self) -> None:
        self.db.users["u1"] = {
            "tier": "pro",
            "subscription_status": "active",
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "cora_balance": 0,
        }

        with patch.dict(os.environ, {"STRIPE_CANCEL_GRACE_DAYS": "7"}, clear=False):
            stripe_handler.handle_webhook(
                self.webhook_payload(
                    "customer.subscription.deleted",
                    {"id": "sub_123", "customer": "cus_123", "metadata": {"user_id": "u1"}},
                ),
                "good",
            )
            view = stripe_handler.get_user_tier("u1")

        self.assertEqual(self.db.users["u1"]["tier"], "pro")
        self.assertEqual(view.tier, "pro")
        self.assertEqual(view.status, "cancelled_grace")

    def test_cancelled_subscription_downgrades_after_grace_expires(self) -> None:
        self.db.users["u1"] = {
            "tier": "pro",
            "subscription_status": "cancelled",
            "subscription_grace_until": datetime.now(timezone.utc) - timedelta(seconds=1),
            "stripe_customer_id": "cus_123",
            "stripe_subscription_id": "sub_123",
            "cora_balance": 0,
        }

        view = stripe_handler.get_user_tier("u1")

        self.assertEqual(view.tier, "free")
        self.assertEqual(view.status, "cancelled")

    def test_stripe_disable_treats_all_users_as_basic(self) -> None:
        with patch.dict(os.environ, {"STRIPE_DISABLE": "1"}, clear=False):
            self.assertEqual(stripe_handler.effective_tier("free"), "basic")
            self.assertEqual(stripe_handler.message_limit_for_tier("free"), 100)
            self.assertTrue(stripe_handler.can_use_capability("free", "calendar"))

    def test_upgrade_command_sends_checkout_url_not_wall_message(self) -> None:
        tgbot_source = (SERVICE_ROOT / "curator" / "tgbot.py").read_text(encoding="utf-8")
        self.assertIn('if cmd == "upgrade":', tgbot_source)
        self.assertIn("return await _cmd_upgrade(chat_id, rest.strip().lower())", tgbot_source)
        self.assertIn("from .billing.stripe_handler import upgrade_reply", tgbot_source)

        reply = stripe_handler.upgrade_reply("123", "basic")

        self.assertIn("https://checkout.stripe.test/session_123", reply)
        self.assertNotIn("can't", reply.lower())
        self.assertNotIn("cannot", reply.lower())

    def test_plain_chat_path_calls_billing_message_gate(self) -> None:
        tgbot_source = (SERVICE_ROOT / "curator" / "tgbot.py").read_text(encoding="utf-8")
        gate_idx = tgbot_source.index("gate_prompt = await _billing_message_gate(chat_id)")
        log_idx = tgbot_source.index('await _log_tg_message(str(chat_id), "user", text, update_id=update_id)')

        self.assertLess(gate_idx, log_idx)


if __name__ == "__main__":
    unittest.main()
