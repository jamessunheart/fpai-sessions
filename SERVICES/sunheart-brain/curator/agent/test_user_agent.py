from __future__ import annotations

import unittest
from datetime import datetime, timezone

from .capability_registry import request_capability
from .operator import PermissionDenied, is_operator, operator_only
from .user_agent import InMemoryAgentStore, RateLimitExceeded, UserAgent


class UserAgentTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.store = InMemoryAgentStore()

    async def test_user_a_cannot_read_user_b_thread(self) -> None:
        user_a = await UserAgent.create("alice12345", "telegram", "beacon-a", store=self.store)
        await UserAgent.create("bob12345", "telegram", "beacon-b", store=self.store)
        self.store.thread.extend(
            [
                {"user_id": "alice12345", "role": "user", "text": "alice private", "at": "2026-06-16T10:00:00Z"},
                {"user_id": "bob12345", "role": "user", "text": "bob private", "at": "2026-06-16T10:01:00Z"},
            ]
        )

        context = await user_a.get_context()

        self.assertEqual([row["text"] for row in context], ["alice private"])

    async def test_james_thread_unreachable_from_non_operator_user(self) -> None:
        user = await UserAgent.create("tenant1", "telegram", "beacon", store=self.store)
        self.store.thread.extend(
            [
                {"user_id": "james", "role": "james", "text": "operator memory", "at": "2026-06-16T10:00:00Z"},
                {"user_id": "tenant1", "role": "user", "text": "tenant memory", "at": "2026-06-16T10:01:00Z"},
            ]
        )

        context = await user.get_context()

        self.assertEqual([row["text"] for row in context], ["tenant memory"])

    def test_is_operator_only_for_james(self) -> None:
        self.assertTrue(is_operator("james"))
        self.assertFalse(is_operator("James"))
        self.assertFalse(is_operator("tenant1"))

        @operator_only
        def guarded(user_id: str) -> str:
            return "ok"

        self.assertEqual(guarded("james"), "ok")
        with self.assertRaises(PermissionDenied):
            guarded("tenant1")

    async def test_capability_grant_requires_consent(self) -> None:
        user = await UserAgent.create("tenant1", "telegram", "beacon", store=self.store)
        self.store.rows["tenant1"]["tier"] = "basic"
        user = await UserAgent.load("tenant1", store=self.store)

        msg = request_capability(user, "send_email")
        self.assertIn("Consent required", msg)
        self.assertFalse(user.can("send_email"))

        await user.grant("send_email", "2026-06-16T10:00:00Z")

        self.assertTrue(user.can("send_email"))
        self.assertIn("available", request_capability(user, "send_email"))

    async def test_tier_gate_blocks_pro_capability_for_free_user(self) -> None:
        user = await UserAgent.create("tenant1", "telegram", "beacon", store=self.store)

        self.assertFalse(user.can("book_travel"))
        self.assertIn("requires the pro tier", request_capability(user, "book_travel"))

    async def test_free_tier_hits_rate_limit_at_10_messages(self) -> None:
        user = await UserAgent.create("tenant1", "telegram", "beacon", store=self.store)

        for _ in range(10):
            await user.record_message_or_raise()

        with self.assertRaises(RateLimitExceeded):
            await user.record_message_or_raise()

    async def test_create_generates_unique_memory_namespace(self) -> None:
        user_a = await UserAgent.create("sameuser99", "telegram", "beacon-a", store=self.store)
        user_b = await UserAgent.create("sameuser98", "telegram", "beacon-b", store=self.store)

        self.assertNotEqual(user_a.namespace, user_b.namespace)
        self.assertTrue(user_a.namespace.startswith("u_sameuser_telegram"))
        self.assertTrue(user_b.namespace.startswith("u_sameuser_telegram"))

    async def test_deletion_requested_at_set_on_request_deletion(self) -> None:
        user = await UserAgent.create("tenant1", "telegram", "beacon", store=self.store)

        await user.request_deletion()

        self.assertIsNotNone(user.deletion_requested_at)
        stored = self.store.rows["tenant1"]["deletion_requested_at"]
        datetime.fromisoformat(str(stored).replace("Z", "+00:00")).astimezone(timezone.utc)


if __name__ == "__main__":
    unittest.main()
