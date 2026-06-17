CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.contact_pool (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    channel TEXT,
    notes TEXT,
    url_hints JSONB DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS brain_index.contact_profiles (
    id SERIAL PRIMARY KEY,
    contact_id INT REFERENCES brain_index.contact_pool(id) ON DELETE CASCADE,
    researched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sources JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT NOT NULL,
    resonance_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    suggested_subject TEXT NOT NULL,
    suggested_body TEXT NOT NULL,
    raw_notes TEXT NOT NULL,
    confidence FLOAT NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    privacy_tier TEXT NOT NULL DEFAULT 'private' CHECK (privacy_tier = 'private')
);

CREATE INDEX IF NOT EXISTS contact_profiles_contact_idx
    ON brain_index.contact_profiles (contact_id, researched_at DESC);

CREATE INDEX IF NOT EXISTS contact_profiles_confidence_idx
    ON brain_index.contact_profiles (confidence);

CREATE INDEX IF NOT EXISTS contact_pool_status_idx
    ON brain_index.contact_pool (status, created_at);
