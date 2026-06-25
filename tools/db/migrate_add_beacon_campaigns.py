#!/usr/bin/env python3
"""Create Beacon campaign/variant tables in brain_index.

Idempotent migration. Reads BRAIN_INDEX_DB_URL and performs no data deletion.
"""
from __future__ import annotations

import os


DDL = """
CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.beacon_campaigns (
    id serial PRIMARY KEY,
    campaign_id text UNIQUE,
    channel text,
    creative_type text,
    cta text,
    audience text,
    beacon_url text,
    beacon_qr_path text,
    status text DEFAULT 'draft',
    cost_budget_usd numeric DEFAULT 0,
    cost_spent_usd numeric DEFAULT 0,
    clicks int DEFAULT 0,
    chat_starts int DEFAULT 0,
    passports_created int DEFAULT 0,
    cora_earned int DEFAULT 0,
    first_actions int DEFAULT 0,
    proofs_created int DEFAULT 0,
    paid_conversions int DEFAULT 0,
    cost_per_proof numeric GENERATED ALWAYS AS (
        CASE WHEN proofs_created > 0 THEN cost_spent_usd / proofs_created ELSE NULL END
    ) STORED,
    james_approved_at timestamp,
    created_at timestamp DEFAULT now()
);

DO $$ BEGIN
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN creative_type text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN cta text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN audience text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN beacon_url text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN beacon_qr_path text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN status text DEFAULT 'draft'; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN cost_budget_usd numeric DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN cost_spent_usd numeric DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN clicks int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN chat_starts int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN passports_created int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN cora_earned int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN first_actions int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN proofs_created int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN paid_conversions int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN cost_per_proof numeric GENERATED ALWAYS AS (CASE WHEN proofs_created > 0 THEN cost_spent_usd / proofs_created ELSE NULL END) STORED; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN james_approved_at timestamp; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_campaigns ADD COLUMN created_at timestamp DEFAULT now(); EXCEPTION WHEN duplicate_column THEN NULL; END;
END $$;

CREATE TABLE IF NOT EXISTS brain_index.beacon_variants (
    id serial PRIMARY KEY,
    campaign_id text REFERENCES brain_index.beacon_campaigns(campaign_id),
    variant_label text,
    content_type text,
    headline text,
    body text,
    cta_text text,
    intent_lane text,
    tone_score numeric,
    alignment_score numeric,
    clicks int DEFAULT 0,
    chat_starts int DEFAULT 0,
    proofs int DEFAULT 0,
    james_approved_at timestamp,
    published_at timestamp
);

DO $$ BEGIN
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN content_type text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN headline text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN body text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN cta_text text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN intent_lane text; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN tone_score numeric; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN alignment_score numeric; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN clicks int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN chat_starts int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN proofs int DEFAULT 0; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN james_approved_at timestamp; EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN ALTER TABLE brain_index.beacon_variants ADD COLUMN published_at timestamp; EXCEPTION WHEN duplicate_column THEN NULL; END;
END $$;

CREATE INDEX IF NOT EXISTS beacon_campaigns_status_idx ON brain_index.beacon_campaigns(status);
CREATE INDEX IF NOT EXISTS beacon_variants_campaign_idx ON brain_index.beacon_variants(campaign_id);

CREATE TABLE IF NOT EXISTS brain_index.beacon_events (
    id serial PRIMARY KEY,
    campaign_id text REFERENCES brain_index.beacon_campaigns(campaign_id),
    variant_label text,
    event_type text,
    at timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS beacon_events_at_idx ON brain_index.beacon_events(at DESC);
CREATE INDEX IF NOT EXISTS beacon_events_campaign_idx ON brain_index.beacon_events(campaign_id, at DESC);
"""


def migrate(db_url: str | None = None) -> None:
    import psycopg

    url = db_url or os.environ.get(
        "BRAIN_INDEX_DB_URL",
        "postgres://brain_index:changeme@127.0.0.1:25432/appflowy",
    )
    with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(DDL)


if __name__ == "__main__":
    migrate()
    print("beacon campaign migration applied")
