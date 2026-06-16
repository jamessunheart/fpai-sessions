CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.probe_pool (
    id SERIAL PRIMARY KEY,
    pool TEXT NOT NULL CHECK (pool IN ('warm', 'adjacent', 'cold')),
    handle TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('telegram', 'email', 'twitter', 'discord')),
    added_by TEXT NOT NULL CHECK (added_by IN ('james', 'system')),
    last_probed_at TIMESTAMPTZ,
    do_not_contact BOOLEAN DEFAULT false
);

CREATE TABLE IF NOT EXISTS brain_index.probe_sessions (
    id SERIAL PRIMARY KEY,
    probe_id TEXT NOT NULL UNIQUE,
    pool TEXT NOT NULL CHECK (pool IN ('warm', 'adjacent', 'cold')),
    initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    engaged BOOLEAN,
    drop_off_message INT,
    completed_spark BOOLEAN DEFAULT false,
    completed_onboarding BOOLEAN DEFAULT false,
    quality_score FLOAT CHECK (quality_score IS NULL OR (quality_score >= 0.0 AND quality_score <= 1.0)),
    corrections_triggered INT NOT NULL DEFAULT 0,
    last_message TEXT,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS probe_pool_contact_idx
    ON brain_index.probe_pool (pool, do_not_contact, last_probed_at);

CREATE INDEX IF NOT EXISTS probe_sessions_recent_idx
    ON brain_index.probe_sessions (initiated_at DESC, pool);

CREATE INDEX IF NOT EXISTS probe_sessions_quality_idx
    ON brain_index.probe_sessions (quality_score)
    WHERE quality_score IS NOT NULL;
