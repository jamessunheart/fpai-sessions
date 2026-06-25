#!/usr/bin/env python3
"""Idempotently add brain_index.user_profiles."""
from __future__ import annotations

import os

import psycopg


DB_URL = os.environ.get(
    "BRAIN_INDEX_DB_URL",
    "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
)


DDL = """
CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.user_profiles (
    user_id text PRIMARY KEY,
    situation text,
    goals jsonb DEFAULT '[]'::jsonb,
    energy_level text,
    life_areas jsonb DEFAULT '{}'::jsonb,
    routing_history jsonb DEFAULT '[]'::jsonb,
    dominant_path text,
    strengths jsonb DEFAULT '[]'::jsonb,
    preferred_tone text,
    avg_message_length int,
    response_speed text,
    best_session_day text,
    best_session_hour int,
    streak_days int DEFAULT 0,
    longest_streak int DEFAULT 0,
    connected_services jsonb DEFAULT '{}'::jsonb,
    match_tags jsonb DEFAULT '[]'::jsonb,
    match_open bool DEFAULT false,
    last_updated timestamp DEFAULT now()
);

DO $$
BEGIN
    IF to_regclass('brain_index.user_agents') IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
             FROM pg_constraint
            WHERE conname = 'user_profiles_user_id_fkey'
              AND conrelid = 'brain_index.user_profiles'::regclass
       ) THEN
        ALTER TABLE brain_index.user_profiles
            ADD CONSTRAINT user_profiles_user_id_fkey
            FOREIGN KEY (user_id) REFERENCES brain_index.user_agents(user_id);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS user_profiles_last_updated_idx
    ON brain_index.user_profiles (last_updated DESC);
CREATE INDEX IF NOT EXISTS user_profiles_match_open_idx
    ON brain_index.user_profiles (match_open) WHERE match_open;
"""


def migrate(db_url: str = DB_URL) -> None:
    with psycopg.connect(db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)


if __name__ == "__main__":
    migrate()
