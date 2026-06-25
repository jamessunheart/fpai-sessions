from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from .executor import (
    CapabilityAuditStore,
    PermissionDenied,
    execute_capability,
    reverse_capability_action,
)


class FakeAgent:
    def __init__(self, allowed: set[str], user_id: str = "u1"):
        self.allowed = allowed
        self.user_id = user_id

    def can(self, capability: str) -> bool:
        return capability in self.allowed


class FakeStore(CapabilityAuditStore):
    def __init__(self, *, email_consent: bool = True, calendar_connected: bool = True):
        self.email_consent = email_consent
        self.calendar_connected = calendar_connected
        self.logs: list[dict] = []
        self.actions: dict[int, dict] = {}
        self.next_id = 1

    async def log(self, **kwargs):
        audit_id = self.next_id
        self.next_id += 1
        row = {"id": audit_id, **kwargs, "reversed_at": None}
        self.logs.append(row)
        self.actions[audit_id] = {
            "id": audit_id,
            "user_id": kwargs["user_id"],
            "capability": kwargs["capability"],
            "params": kwargs["params"],
            "result": kwargs["result"],
            "success": kwargs["success"],
            "reversible": kwargs["reversible"],
            "reversed_at": None,
        }
        return audit_id

    async def has_email_consent(self, user_id: str) -> bool:
        return self.email_consent

    async def has_calendar_connection(self, user_id: str) -> bool:
        return self.calendar_connected

    async def get_action(self, audit_id, user_id=None):
        action = self.actions.get(int(audit_id))
        if user_id is not None and action and action["user_id"] != user_id:
            return None
        return action

    async def mark_reversed(self, audit_id, result):
        action = self.actions[int(audit_id)]
        action["reversed_at"] = "now"
        action["result"] = {**action["result"], **result}


class ExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_execute_capability_raises_permission_denied_without_grant(self):
        with self.assertRaises(PermissionDenied):
            await execute_capability(
                FakeAgent(set()),
                "search_web",
                {"query": "x", "confirmed": True},
                store=FakeStore(),
                providers={"search_web": self._search_provider},
            )

    async def test_send_email_requires_confirmation_before_sending(self):
        sent: list[dict] = []

        async def send(params: dict) -> dict:
            sent.append(params)
            return {"tracking_id": "msg-1"}

        store = FakeStore()
        result = await execute_capability(
            FakeAgent({"send_email"}),
            "send_email",
            {"to": "a@example.com", "subject": "Hi", "body": "Body"},
            store=store,
            providers={"send_email": send},
        )

        self.assertFalse(result.success)
        self.assertFalse(result.action_taken)
        self.assertEqual(sent, [])
        self.assertEqual(store.logs[0]["result"]["status"], "cancelled")

    async def test_cancelled_email_does_not_send(self):
        sent: list[dict] = []

        async def send(params: dict) -> dict:
            sent.append(params)
            return {"tracking_id": "msg-1"}

        result = await execute_capability(
            FakeAgent({"send_email"}),
            "send_email",
            {"to": "a@example.com", "subject": "Hi", "body": "Body", "confirmed": "no"},
            store=FakeStore(),
            providers={"send_email": send},
        )

        self.assertFalse(result.action_taken)
        self.assertEqual(sent, [])

    async def test_book_calendar_creates_event_on_yes_and_skips_on_no(self):
        created: list[dict] = []

        async def book(params: dict) -> dict:
            created.append(params)
            return {"event_id": "evt-1", "event_url": "https://cal.example/evt-1", "title": params["title"]}

        store = FakeStore()
        no_result = await execute_capability(
            FakeAgent({"book_calendar"}),
            "book_calendar",
            {"title": "Meet", "date": "2026-06-17", "time": "09:00", "duration": 30, "confirmed": False},
            store=store,
            providers={"book_calendar": book},
        )
        yes_result = await execute_capability(
            FakeAgent({"book_calendar"}),
            "book_calendar",
            {"title": "Meet", "date": "2026-06-17", "time": "09:00", "duration": 30, "confirmed": True},
            store=store,
            providers={"book_calendar": book},
        )

        self.assertFalse(no_result.action_taken)
        self.assertTrue(yes_result.action_taken)
        self.assertEqual(len(created), 1)
        self.assertTrue(yes_result.reversible)

    async def test_all_actions_logged_to_capability_log(self):
        store = FakeStore()
        result = await execute_capability(
            FakeAgent({"search_web"}),
            "search_web",
            {"query": "full potential ai", "confirmed": True},
            store=store,
            providers={"search_web": self._search_provider},
        )

        self.assertTrue(result.success)
        self.assertEqual(len(store.logs), 1)
        self.assertEqual(store.logs[0]["capability"], "search_web")
        self.assertEqual(store.logs[0]["success"], True)

    async def test_provider_failure_does_not_report_email_sent(self):
        async def send(params: dict) -> dict:
            return {"success": False, "error": "provider rejected request"}

        result = await execute_capability(
            FakeAgent({"send_email"}),
            "send_email",
            {"to": "a@example.com", "subject": "Hi", "body": "Body", "confirmed": True},
            store=FakeStore(),
            providers={"send_email": send},
        )

        self.assertFalse(result.success)
        self.assertEqual(result.output, "provider rejected request")
        self.assertFalse(result.action_taken)

    async def test_reversal_clears_calendar_event_but_email_irreversible(self):
        store = FakeStore()

        async def book(params: dict) -> dict:
            return {"event_id": "evt-1", "title": params["title"]}

        calendar = await execute_capability(
            FakeAgent({"book_calendar"}),
            "book_calendar",
            {"title": "Meet", "date": "2026-06-17", "time": "09:00", "duration": 30, "confirmed": True},
            store=store,
            providers={"book_calendar": book},
        )
        cancelled: list[str] = []

        async def cancel(event_id: str) -> dict:
            cancelled.append(event_id)
            return {"cancelled": True, "event_id": event_id}

        undo = await reverse_capability_action(calendar.audit_id, store=store, cancel_provider=cancel)
        self.assertTrue(undo.success)
        self.assertEqual(cancelled, ["evt-1"])
        self.assertIsNotNone(store.actions[int(calendar.audit_id)]["reversed_at"])

        async def send(params: dict) -> dict:
            return {"tracking_id": "msg-1"}

        email = await execute_capability(
            FakeAgent({"send_email"}),
            "send_email",
            {"to": "a@example.com", "subject": "Hi", "body": "Body", "confirmed": True},
            store=store,
            providers={"send_email": send},
        )
        blocked = await reverse_capability_action(email.audit_id, store=store)
        self.assertFalse(blocked.success)
        self.assertIn("cannot be reversed", blocked.output)

    async def test_capabilities_disable_returns_offline_message(self):
        with patch.dict(os.environ, {"CAPABILITIES_DISABLE": "1"}):
            result = await execute_capability(
                FakeAgent({"search_web"}),
                "search_web",
                {"query": "x", "confirmed": True},
                store=FakeStore(),
                providers={"search_web": self._search_provider},
            )
        self.assertFalse(result.success)
        self.assertEqual(result.output, "Capabilities are currently offline.")

    async def _search_provider(self, params: dict) -> dict:
        return {"results": [{"title": "A", "snippet": "B", "url": "https://example.com"}]}


if __name__ == "__main__":
    unittest.main()
