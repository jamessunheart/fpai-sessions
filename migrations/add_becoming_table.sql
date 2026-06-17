CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.becoming (
    person_id TEXT PRIMARY KEY,
    identity_contact JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL DEFAULT 'unknown',
    stage TEXT NOT NULL DEFAULT 'spark',
    stated_intent TEXT NOT NULL DEFAULT '',
    proofs JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_blocker TEXT NOT NULL DEFAULT '',
    cora_balance NUMERIC,
    last_touch TIMESTAMPTZ,
    next_nurture_action TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (stage IN ('spark', 'awaken', 'activate', 'build', 'contribute', 'coach'))
);

CREATE INDEX IF NOT EXISTS becoming_stage_idx
    ON brain_index.becoming (stage, updated_at DESC);

CREATE INDEX IF NOT EXISTS becoming_source_idx
    ON brain_index.becoming (source, updated_at DESC);
