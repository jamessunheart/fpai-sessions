#!/usr/bin/env python3
"""Add brain_index.user_agents and tenant indexes.

Idempotent migration for d039. It deliberately guards the thread index because
some local checkouts have the continuity thread table while others only have
tg_messages.
"""

from __future__ import annotations

import os

import psycopg


DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)


MIGRATION_SQL = """
CREATE SCHEMA IF NOT EXISTS brain_index;
SET search_path TO brain_index, public;

CREATE TABLE IF NOT EXISTS brain_index.user_agents (
    user_id text PRIMARY KEY,
    display_name text,
    tier text DEFAULT 'free',
    system_prompt_override text,
    memory_namespace text UNIQUE,
    capability_grants jsonb DEFAULT '{}'::jsonb,
    consent_log jsonb DEFAULT '[]'::jsonb,
    stripe_customer_id text,
    subscription_status text DEFAULT 'none',
    cora_balance int DEFAULT 0,
    proof_count int DEFAULT 0,
    session_count int DEFAULT 0,
    last_seen timestamp,
    created_at timestamp DEFAULT now(),
    data_region text DEFAULT 'eu',
    deletion_requested_at timestamp
);

CREATE TABLE IF NOT EXISTS brain_index.thread (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    at timestamptz NOT NULL DEFAULT now(),
    user_id text DEFAULT 'james',
    surface text NOT NULL,
    role text NOT NULL,
    text text NOT NULL
);

DO $$
BEGIN
    IF to_regclass('brain_index.thread') IS NOT NULL THEN
        BEGIN
            ALTER TABLE brain_index.thread ADD COLUMN user_id text DEFAULT 'james';
        EXCEPTION WHEN duplicate_column THEN
            NULL;
        END;

        CREATE INDEX IF NOT EXISTS idx_thread_user_id
            ON brain_index.thread(user_id);
    END IF;
END $$;
"""


def run() -> None:
    with psycopg.connect(DB_URL, autocommit=True) as conn:
        conn.execute(MIGRATION_SQL)


if __name__ == "__main__":
    run()
