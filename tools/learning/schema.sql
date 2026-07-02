CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.learning_signals (
    id SERIAL PRIMARY KEY,
    task_id TEXT,
    signal_type TEXT NOT NULL CHECK (signal_type IN ('correction', 'approval', 'reversal', 'merge_outcome', 'engagement', 'council_verdict')),
    prompt TEXT,
    response TEXT,
    value FLOAT CHECK (value >= -1.0 AND value <= 1.0),
    weight FLOAT DEFAULT 1.0 CHECK (weight > 0),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brain_index.review_signals (
    id SERIAL PRIMARY KEY,
    spec_id TEXT NOT NULL,
    verdict TEXT NOT NULL,
    reasons TEXT NOT NULL,
    code_ref TEXT NOT NULL UNIQUE,
    captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brain_index.model_directives (
    id SERIAL PRIMARY KEY,
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    pragmatist_input TEXT,
    visionary_input TEXT,
    skeptic_input TEXT,
    weighting JSONB,
    rationale TEXT
);

CREATE TABLE IF NOT EXISTS brain_index.model_versions (
    id SERIAL PRIMARY KEY,
    version TEXT NOT NULL,
    trained_at TIMESTAMPTZ DEFAULT NOW(),
    signal_count INT,
    metrics JSONB,
    directive_id INT REFERENCES brain_index.model_directives(id)
);
