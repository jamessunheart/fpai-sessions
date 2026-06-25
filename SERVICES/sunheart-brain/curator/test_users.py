from __future__ import annotations

import unittest
from contextlib import asynccontextmanager

from curator import users


class FakeResult:
    def __init__(self, rows=None, rowcount: int = 0):
        self._rows = list(rows or [])
        self.rowcount = rowcount

    async def fetchall(self):
        return self._rows

    async def fetchone(self):
        if not self._rows:
            return None
        return self._rows.pop(0)


class FakeConn:
    def __init__(self) -> None:
        self.executed: list[tuple[str, tuple]] = []
        self.table_columns = {
            "users": {"id", "paid", "telegram_chat_id"},
            "user_agents": {"user_id", "namespace", "status", "archived", "created_at", "updated_at"},
        }

    async def execute(self, sql: str, params: tuple = ()):
        normalized = " ".join(sql.split())
        self.executed.append((normalized, params))
        if "information_schema.columns" in normalized:
            table = params[0]
            return FakeResult([(column,) for column in sorted(self.table_columns[table])])
        if normalized.startswith("UPDATE users SET paid = TRUE"):
            return FakeResult([("777",)], rowcount=1)
        if normalized.startswith("SELECT user_id FROM user_agents"):
            return FakeResult([])
        if normalized.startswith("INSERT INTO user_agents"):
            return FakeResult(rowcount=1)
        raise AssertionError(f"unexpected SQL: {normalized}")


class UsersTest(unittest.IsolatedAsyncioTestCase):
    async def test_activate_paid_user_updates_user_and_initializes_namespace(self) -> None:
        conn = FakeConn()

        @asynccontextmanager
        async def fake_connect():
            yield conn

        activation = await users.activate_paid_user("u_123", connect_factory=fake_connect)

        self.assertEqual(activation.user_id, "u_123")
        self.assertTrue(activation.paid)
        self.assertEqual(activation.namespace, "user:u_123")
        self.assertEqual(activation.telegram_chat_id, "777")
        self.assertTrue(any("UPDATE users SET paid = TRUE" in sql for sql, _ in conn.executed))
        self.assertTrue(any("INSERT INTO user_agents" in sql for sql, _ in conn.executed))


if __name__ == "__main__":
    unittest.main()
