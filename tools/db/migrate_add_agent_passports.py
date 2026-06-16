"""Idempotent brain_index migration for onboarding Agent Passports and beacons."""
from __future__ import annotations

import os


SQL = """
SET search_path TO brain_index, public;

CREATE TABLE IF NOT EXISTS agent_passports (
    user_id             TEXT PRIMARY KEY,
    goals               TEXT NOT NULL,
    situation           TEXT NOT NULL,
    energy              TEXT NOT NULL,
    beacon_id           TEXT,
    channel             TEXT NOT NULL,
    onboarding_path     TEXT NOT NULL,
    cora_balance        INTEGER NOT NULL DEFAULT 0,
    proof_count         INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS agent_passports_beacon_idx
    ON agent_passports (beacon_id);
CREATE INDEX IF NOT EXISTS agent_passports_last_seen_idx
    ON agent_passports (last_seen DESC);

CREATE TABLE IF NOT EXISTS beacons (
    beacon_id           TEXT PRIMARY KEY,
    source              TEXT NOT NULL,
    campaign            TEXT NOT NULL,
    expected_intent     TEXT NOT NULL,
    opening_tone        TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    click_count         INTEGER NOT NULL DEFAULT 0,
    converted_count     INTEGER NOT NULL DEFAULT 0
);

DO $$ BEGIN
    BEGIN
        ALTER TABLE beacons ADD COLUMN converted_count INTEGER NOT NULL DEFAULT 0;
    EXCEPTION WHEN duplicate_column THEN NULL; END;
END $$;

CREATE TABLE IF NOT EXISTS user_channels (
    user_id             TEXT NOT NULL,
    channel             TEXT NOT NULL,
    onboarded           BOOLEAN NOT NULL DEFAULT FALSE,
    beacon_id           TEXT,
    last_seen           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, channel)
);

CREATE TABLE IF NOT EXISTS thread (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id             TEXT,
    surface             TEXT NOT NULL,
    role                TEXT NOT NULL,
    text                TEXT NOT NULL
);

INSERT INTO beacons (beacon_id, source, campaign, expected_intent, opening_tone)
VALUES
    ('camp_zen', 'field', 'Camp Zen', 'retreat coherence', 'Let''s keep this grounded and human.'),
    ('general', 'direct', 'General', 'open exploration', 'We can start from what is alive now.'),
    ('business_builder', 'offer', 'Business Builder', 'business growth', 'We''ll look for the clearest business next step.'),
    ('community', 'community', 'Community', 'community participation', 'We''ll route you toward the right shared room.')
ON CONFLICT (beacon_id) DO NOTHING;
"""


def migrate(db_url: str | None = None) -> None:
    db_url = db_url or os.environ.get("BRAIN_INDEX_DB_URL")
    if not db_url:
        raise RuntimeError("BRAIN_INDEX_DB_URL is required to run this migration")
    import psycopg

    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute(SQL)


if __name__ == "__main__":
    migrate()
