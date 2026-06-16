#!/usr/bin/env python3
"""Idempotently add brain_index.capability_log."""
from __future__ import annotations

import os


DDL = """
CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.capability_log (
    id serial PRIMARY KEY,
    user_id text NOT NULL,
    capability text NOT NULL,
    params jsonb NOT NULL DEFAULT '{}'::jsonb,
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    success bool NOT NULL DEFAULT false,
    reversible bool NOT NULL DEFAULT false,
    reversed_at timestamp,
    executed_at timestamp NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS capability_log_user_executed_idx
    ON brain_index.capability_log (user_id, executed_at DESC);

CREATE INDEX IF NOT EXISTS capability_log_reversible_idx
    ON brain_index.capability_log (user_id, reversible, reversed_at, executed_at DESC);

CREATE TABLE IF NOT EXISTS brain_index.consent_log (
    id serial PRIMARY KEY,
    user_id text NOT NULL,
    consent_type text NOT NULL,
    granted_at timestamp NOT NULL DEFAULT now(),
    revoked bool NOT NULL DEFAULT false
);

ALTER TABLE brain_index.consent_log
    ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE brain_index.consent_log
    ADD COLUMN IF NOT EXISTS consent_type text;
ALTER TABLE brain_index.consent_log
    ADD COLUMN IF NOT EXISTS granted_at timestamp DEFAULT now();
ALTER TABLE brain_index.consent_log
    ADD COLUMN IF NOT EXISTS revoked bool DEFAULT false;

CREATE INDEX IF NOT EXISTS consent_log_user_type_idx
    ON brain_index.consent_log (user_id, consent_type, granted_at DESC);

CREATE TABLE IF NOT EXISTS brain_index.connected_services (
    id serial PRIMARY KEY,
    user_id text NOT NULL,
    calendar_provider text,
    connected_at timestamp NOT NULL DEFAULT now(),
    disabled bool NOT NULL DEFAULT false
);

ALTER TABLE brain_index.connected_services
    ADD COLUMN IF NOT EXISTS user_id text;
ALTER TABLE brain_index.connected_services
    ADD COLUMN IF NOT EXISTS calendar_provider text;
ALTER TABLE brain_index.connected_services
    ADD COLUMN IF NOT EXISTS connected_at timestamp DEFAULT now();
ALTER TABLE brain_index.connected_services
    ADD COLUMN IF NOT EXISTS disabled bool DEFAULT false;

CREATE INDEX IF NOT EXISTS connected_services_user_idx
    ON brain_index.connected_services (user_id);
"""


def main() -> int:
    try:
        import psycopg
    except Exception as exc:
        raise SystemExit(f"psycopg is required for migration: {exc}") from exc

    dsn = os.environ.get(
        "BRAIN_INDEX_DB_URL",
        "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
    )
    with psycopg.connect(dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
    print("brain_index.capability_log ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
