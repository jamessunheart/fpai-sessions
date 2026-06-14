"""app/db.py — async psycopg helper with a small connection pool.

Mirrors the curator/db.py pattern but uses an AsyncConnectionPool so each
Telegram update doesn't pay TCP/auth overhead.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import psycopg
from psycopg_pool import AsyncConnectionPool

from .config import settings

log = logging.getLogger("streasury.db")

_pool: AsyncConnectionPool | None = None


async def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=settings.database_url,
            min_size=1,
            max_size=5,
            kwargs={"autocommit": True, "options": "-c search_path=streasury,public"},
            open=False,
        )
        await _pool.open()
        await _pool.wait()
        log.info("db pool ready")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def connect() -> AsyncIterator[psycopg.AsyncConnection]:
    pool = await get_pool()
    async with pool.connection() as conn:
        yield conn
