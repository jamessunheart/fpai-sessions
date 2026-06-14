"""curator/db.py — async psycopg helper for brain-index.

Always uses BRAIN_INDEX_DB_URL (same as brain-index) so schema drift is
impossible. pgvector registered on every new connection.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import psycopg
from pgvector.psycopg import register_vector_async

DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)


@asynccontextmanager
async def connect():
    conn = await psycopg.AsyncConnection.connect(DB_URL, autocommit=True)
    try:
        await register_vector_async(conn)
        yield conn
    finally:
        await conn.close()
