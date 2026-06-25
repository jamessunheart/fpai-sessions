"""User namespace helpers for the Sunheart Brain curator.

The live brain_index schema is the source of truth. These helpers avoid schema
migrations and adapt to the existing users/user_agents columns where possible.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import importlib.util as _ilu
from pathlib import Path
from typing import Any, AsyncIterator, Callable

try:
    from .db import connect as default_connect
except ImportError as _db_import_error:
    _db_path = Path(__file__).resolve().with_name("db.py")
    _db_spec = _ilu.spec_from_file_location("sunheart_curator_db", _db_path)
    if _db_spec is not None and _db_spec.loader is not None:
        try:
            _db_mod = _ilu.module_from_spec(_db_spec)
            _db_spec.loader.exec_module(_db_mod)
            default_connect = _db_mod.connect
        except ImportError:
            @asynccontextmanager
            async def default_connect():
                raise RuntimeError("curator.db dependencies are unavailable") from _db_import_error
    else:
        @asynccontextmanager
        async def default_connect():
            raise RuntimeError("curator.db could not be loaded") from _db_import_error


ConnectFactory = Callable[[], AsyncIterator[Any]]


@dataclass(frozen=True)
class UserActivation:
    user_id: str
    paid: bool
    namespace: str
    telegram_chat_id: str | None = None


async def _columns(conn: Any, table_name: str) -> set[str]:
    rows = await conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND table_schema = ANY (current_schemas(false))
        """,
        (table_name,),
    )
    return {str(row[0]) for row in await rows.fetchall()}


def _first(columns: set[str], names: tuple[str, ...]) -> str | None:
    return next((name for name in names if name in columns), None)


async def set_paid(
    user_id: str,
    *,
    connect_factory: ConnectFactory = default_connect,
) -> str | None:
    """Mark a brain_index user paid and return a known Telegram chat id, if any."""
    async with connect_factory() as conn:
        columns = await _columns(conn, "users")
        if "paid" not in columns:
            raise RuntimeError("brain_index.users.paid column is missing")

        user_id_column = _first(columns, ("id", "user_id"))
        if user_id_column is None:
            raise RuntimeError("brain_index.users id/user_id column is missing")

        chat_column = _first(columns, ("telegram_chat_id", "telegram_id", "tg_chat_id", "chat_id"))
        returning = f"RETURNING {chat_column}" if chat_column else ""
        result = await conn.execute(
            f"UPDATE users SET paid = TRUE WHERE {user_id_column} = %s {returning}",
            (user_id,),
        )
        if result.rowcount != 1:
            raise RuntimeError(f"brain_index.users row not found for user_id={user_id!r}")

        if not chat_column:
            return None
        row = await result.fetchone()
        if not row or row[0] is None:
            return None
        return str(row[0])


async def init_namespace(
    user_id: str,
    *,
    connect_factory: ConnectFactory = default_connect,
) -> str:
    """Create or reactivate the per-user agent namespace row."""
    namespace = f"user:{user_id}"
    async with connect_factory() as conn:
        columns = await _columns(conn, "user_agents")
        if not columns:
            raise RuntimeError("brain_index.user_agents table is missing")
        if "user_id" not in columns:
            raise RuntimeError("brain_index.user_agents.user_id column is missing")

        existing = await conn.execute(
            "SELECT user_id FROM user_agents WHERE user_id = %s LIMIT 1",
            (user_id,),
        )
        row = await existing.fetchone()
        if row:
            assignments: list[str] = []
            values: list[Any] = []
            if "namespace" in columns:
                assignments.append("namespace = %s")
                values.append(namespace)
            if "status" in columns:
                assignments.append("status = %s")
                values.append("active")
            if "archived" in columns:
                assignments.append("archived = FALSE")
            if "updated_at" in columns:
                assignments.append("updated_at = NOW()")
            if assignments:
                values.append(user_id)
                await conn.execute(
                    f"UPDATE user_agents SET {', '.join(assignments)} WHERE user_id = %s",
                    tuple(values),
                )
            return namespace

        insert_columns = ["user_id"]
        insert_values: list[Any] = [user_id]
        if "namespace" in columns:
            insert_columns.append("namespace")
            insert_values.append(namespace)
        if "status" in columns:
            insert_columns.append("status")
            insert_values.append("active")
        if "archived" in columns:
            insert_columns.append("archived")
            insert_values.append(False)
        if "created_at" in columns:
            insert_columns.append("created_at")
            insert_values.append("NOW()")
        if "updated_at" in columns:
            insert_columns.append("updated_at")
            insert_values.append("NOW()")

        placeholders = ["%s"] * len(insert_columns)
        for idx, value in enumerate(insert_values):
            if value == "NOW()":
                placeholders[idx] = "NOW()"
        sql_values = [value for value in insert_values if value != "NOW()"]
        await conn.execute(
            f"INSERT INTO user_agents ({', '.join(insert_columns)}) VALUES ({', '.join(placeholders)})",
            tuple(sql_values),
        )
        return namespace


async def activate_paid_user(
    user_id: str,
    *,
    telegram_chat_id: str | None = None,
    connect_factory: ConnectFactory = default_connect,
) -> UserActivation:
    """Mark paid and initialize the namespace for a checkout-completed user."""
    db_chat_id = await set_paid(user_id, connect_factory=connect_factory)
    namespace = await init_namespace(user_id, connect_factory=connect_factory)
    return UserActivation(
        user_id=user_id,
        paid=True,
        namespace=namespace,
        telegram_chat_id=telegram_chat_id or db_chat_id,
    )
