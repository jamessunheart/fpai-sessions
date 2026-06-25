#!/usr/bin/env python3
"""Idempotent migration for brain_index.user_channels."""
from __future__ import annotations

import argparse
import os
import sys


SQL = """
CREATE SCHEMA IF NOT EXISTS brain_index;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS brain_index.user_channels (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             TEXT NOT NULL,
    channel             TEXT NOT NULL,
    channel_user_id     TEXT NOT NULL,
    beacon_id           TEXT,
    first_seen          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    permissions         JSONB NOT NULL DEFAULT '{"memory": true, "marketing": false, "human_followup": false}'::jsonb,
    UNIQUE (channel, channel_user_id)
);

ALTER TABLE brain_index.user_channels
    ADD COLUMN IF NOT EXISTS beacon_id TEXT;
ALTER TABLE brain_index.user_channels
    ADD COLUMN IF NOT EXISTS first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE brain_index.user_channels
    ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE brain_index.user_channels
    ADD COLUMN IF NOT EXISTS permissions JSONB NOT NULL DEFAULT '{"memory": true, "marketing": false, "human_followup": false}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS user_channels_channel_identity_uidx
    ON brain_index.user_channels (channel, channel_user_id);
CREATE INDEX IF NOT EXISTS user_channels_user_idx
    ON brain_index.user_channels (user_id);
CREATE INDEX IF NOT EXISTS user_channels_last_seen_idx
    ON brain_index.user_channels (last_seen DESC);
"""


def database_url() -> str:
    for key in ("BRAIN_INDEX_DB_URL", "DATABASE_URL", "DB_URL"):
        value = os.environ.get(key)
        if value:
            return value
    return "postgres://brain_index:changeme@127.0.0.1:25432/appflowy"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print SQL without applying it")
    parser.add_argument("--dsn", default=None, help="database DSN; defaults to BRAIN_INDEX_DB_URL/DATABASE_URL/DB_URL")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(SQL.strip())
        return 0

    try:
        import psycopg
    except ImportError:
        print("psycopg is required to run the migration", file=sys.stderr)
        return 2

    with psycopg.connect(args.dsn or database_url(), autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
    print("ok: brain_index.user_channels ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
