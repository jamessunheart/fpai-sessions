-- brain-index — pgvector tables in the brain_index schema.
-- Applied by brain-index on first startup if tables don't exist.

-- Include public so the pgvector `vector` type (installed into public) resolves.
SET search_path TO brain_index, public;

-- One row per Note chunk (Notes >4KB get split; each chunk has its own embedding).
CREATE TABLE IF NOT EXISTS note_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_row_id     TEXT NOT NULL,               -- AppFlowy row_id in "01 · Notes"
    chunk_idx       INTEGER NOT NULL DEFAULT 0,
    content         TEXT NOT NULL,
    content_sha1    TEXT NOT NULL,               -- lets us skip re-embedding unchanged chunks
    embedding       vector(768),                 -- nomic-embed-text dimension; 1536 if switched to OpenAI
    embedding_model TEXT NOT NULL,
    source          TEXT,
    source_id       TEXT,
    tags            TEXT[] DEFAULT '{}',
    sensitivity     TEXT NOT NULL DEFAULT 'public',  -- public | personal | private
    pii_flags       TEXT[] DEFAULT '{}',
    concept_id      UUID,                        -- FK to concepts.id (deferred, see below)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (note_row_id, chunk_idx)
);

-- Backfill columns for any pre-existing rows (idempotent).
DO $$ BEGIN
    BEGIN
        ALTER TABLE note_chunks ADD COLUMN sensitivity TEXT NOT NULL DEFAULT 'public';
    EXCEPTION WHEN duplicate_column THEN NULL; END;
    BEGIN
        ALTER TABLE note_chunks ADD COLUMN pii_flags TEXT[] DEFAULT '{}';
    EXCEPTION WHEN duplicate_column THEN NULL; END;
END $$;

CREATE INDEX IF NOT EXISTS note_chunks_sensitivity_idx ON note_chunks (sensitivity);

CREATE INDEX IF NOT EXISTS note_chunks_embedding_idx
    ON note_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS note_chunks_source_id_idx ON note_chunks (source, source_id);
CREATE INDEX IF NOT EXISTS note_chunks_concept_idx   ON note_chunks (concept_id);
CREATE INDEX IF NOT EXISTS note_chunks_tags_idx      ON note_chunks USING GIN (tags);

-- Canonical concepts. AppFlowy has a mirror row per concept in "02 · Concepts"
-- (linked via appflowy_row_id) so users can curate in the UI and the index
-- stays the source of truth for centroids/similarity.
CREATE TABLE IF NOT EXISTS concepts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appflowy_row_id     TEXT UNIQUE,
    name                TEXT NOT NULL,
    aliases             TEXT[] DEFAULT '{}',
    description         TEXT,
    centroid            vector(768),         -- mean of linked note embeddings
    note_count          INTEGER NOT NULL DEFAULT 0,
    parent_concept_id   UUID REFERENCES concepts(id),
    domain              TEXT[] DEFAULT '{}',
    salience            TEXT,                -- matches AppFlowy's single_select
    first_seen          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reinforced     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS concepts_centroid_idx
    ON concepts USING hnsw (centroid vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS concepts_name_trgm_idx
    ON concepts USING GIN (name gin_trgm_ops);  -- only if pg_trgm exists

-- A log of every merge decision the dedup pass makes. Auditable + reversible.
CREATE TABLE IF NOT EXISTS merge_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    kept_concept_id UUID NOT NULL REFERENCES concepts(id),
    merged_ids      UUID[] NOT NULL,
    cosine_mean     FLOAT NOT NULL,
    auto            BOOLEAN NOT NULL,            -- true = >0.95 auto-merge, false = manual
    agent           TEXT,                        -- which MCP token did it
    reason          TEXT
);

-- Optional: pg_trgm for fuzzy concept name lookups. If it isn't installed the
-- trgm index above will fail silently during migrate; harmless.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Audit: every MCP/index call with its scope, outcome, and result count.
-- Mirrored into AppFlowy's '06 · Audit' db for easy human review.
CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent           TEXT NOT NULL,
    tool            TEXT NOT NULL,
    scope_used      TEXT NOT NULL,
    query_prefix    TEXT,
    result_count    INTEGER NOT NULL DEFAULT 0,
    blocked         BOOLEAN NOT NULL DEFAULT FALSE,
    source_ip       TEXT,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS audit_log_at_idx       ON audit_log (at DESC);
CREATE INDEX IF NOT EXISTS audit_log_agent_idx    ON audit_log (agent);
CREATE INDEX IF NOT EXISTS audit_log_blocked_idx  ON audit_log (blocked) WHERE blocked;
