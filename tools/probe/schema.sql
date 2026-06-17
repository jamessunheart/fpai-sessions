CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.probe_pool (
    id SERIAL PRIMARY KEY,
    pool TEXT NOT NULL CHECK (pool IN ('warm', 'adjacent', 'cold')),
    handle TEXT NOT NULL,
    platform TEXT NOT NULL CHECK (platform IN ('telegram', 'email', 'twitter', 'discord', 'reddit', 'instagram', 'hn', 'github')),
    added_by TEXT NOT NULL CHECK (added_by IN ('james', 'system')),
    source TEXT,
    topic_signal TEXT,
    discovery_score FLOAT DEFAULT 0.5,
    metadata JSONB,
    last_probed_at TIMESTAMPTZ,
    do_not_contact BOOLEAN DEFAULT false
);

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS source TEXT;

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS metadata JSONB;

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS topic_signal TEXT;

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS discovery_score FLOAT DEFAULT 0.5;

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
    sent_at TIMESTAMPTZ,
    message_id TEXT,
    notes TEXT
);

ALTER TABLE brain_index.probe_sessions
    ADD COLUMN IF NOT EXISTS sent_at TIMESTAMPTZ;

ALTER TABLE brain_index.probe_sessions
    ADD COLUMN IF NOT EXISTS message_id TEXT;

CREATE INDEX IF NOT EXISTS probe_pool_contact_idx
    ON brain_index.probe_pool (pool, do_not_contact, last_probed_at);

CREATE INDEX IF NOT EXISTS probe_pool_discovery_score_idx
    ON brain_index.probe_pool (discovery_score)
    WHERE COALESCE(do_not_contact, false) = false;

CREATE INDEX IF NOT EXISTS probe_sessions_recent_idx
    ON brain_index.probe_sessions (initiated_at DESC, pool);

CREATE INDEX IF NOT EXISTS probe_sessions_quality_idx
    ON brain_index.probe_sessions (quality_score)
    WHERE quality_score IS NOT NULL;
