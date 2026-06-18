from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from app import payment_activation


class FakeUsers:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    async def activate_paid_user(self, user_id: str, *, telegram_chat_id: str | None = None):
        self.calls.append((user_id, telegram_chat_id))
        return SimpleNamespace(
            user_id=user_id,
            paid=True,
            namespace=f"user:{user_id}",
            telegram_chat_id=telegram_chat_id,
        )


class PaymentActivationTest(unittest.TestCase):
    def test_checkout_completed_activates_user_namespace_and_sends_ready_message(self) -> None:
        users = FakeUsers()
        sent: list[dict[str, str]] = []

        def send_message(**kwargs):
            sent.append(kwargs)
            return True

        result = asyncio.run(
            payment_activation.activate_paid_checkout_session(
                {
                    "id": "cs_test_123",
                    "metadata": {
                        "user_id": "u_123",
                        "telegram_chat_id": "777",
                    },
                },
                users_module=users,
                send_message=send_message,
            )
        )

        self.assertEqual(users.calls, [("u_123", "777")])
        self.assertEqual(
            sent,
            [
                {
                    "platform": "telegram",
                    "handle": "777",
                    "text": "Your agent is ready.",
                }
            ],
        )
        self.assertEqual(result.user_id, "u_123")
        self.assertEqual(result.namespace, "user:u_123")
        self.assertEqual(result.telegram_chat_id, "777")
        self.assertTrue(result.telegram_sent)
        self.assertIsNone(result.skipped_reason)

    def test_missing_user_id_skips_without_side_effects(self) -> None:
        users = FakeUsers()

        result = asyncio.run(
            payment_activation.activate_paid_checkout_session(
                {"id": "cs_test_123", "metadata": {"telegram_chat_id": "777"}},
                users_module=users,
                send_message=lambda **_: True,
            )
        )

        self.assertEqual(users.calls, [])
        self.assertIsNone(result.user_id)
        self.assertEqual(result.skipped_reason, "missing_user_id")

    def test_client_reference_id_can_supply_user_id(self) -> None:
        self.assertEqual(
            payment_activation.extract_user_id({"client_reference_id": "u_client"}),
            "u_client",
        )


if __name__ == "__main__":
    unittest.main()
