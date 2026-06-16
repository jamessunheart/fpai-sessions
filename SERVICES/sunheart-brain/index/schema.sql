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

-- Telegram conversation buffer.
-- Every inbound (user) and outbound (bot) message is logged here.
-- An hourly curator job (tg_capture) compresses unprocessed batches into
-- summary notes that get ingested into note_chunks (and AppFlowy 01 · Notes).
CREATE TABLE IF NOT EXISTS tg_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    chat_id         TEXT NOT NULL,
    role            TEXT NOT NULL,           -- 'user' | 'bot'
    text            TEXT NOT NULL,
    private_flag    BOOLEAN NOT NULL DEFAULT FALSE,  -- skip during compression
    processed_at    TIMESTAMPTZ,             -- set when picked up by tg_capture
    note_row_id     TEXT,                    -- AppFlowy row this turn rolled up into
    update_id       BIGINT                   -- Telegram update_id for dedup
);

CREATE INDEX IF NOT EXISTS tg_messages_chat_idx       ON tg_messages (chat_id, at DESC);
CREATE INDEX IF NOT EXISTS tg_messages_unprocessed_idx ON tg_messages (chat_id, at) WHERE processed_at IS NULL AND NOT private_flag;

-- Correction memory loop.
-- Each row captures James correcting the previous bot turn. The Telegram bot
-- injects the most recent correction pairs into future prompts so failures
-- become visible immediately instead of waiting for hourly compression.
CREATE TABLE IF NOT EXISTS corrections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     TEXT NOT NULL,
    bot_turn_id         UUID REFERENCES tg_messages(id) ON DELETE SET NULL,
    original_response   TEXT NOT NULL,
    james_correction    TEXT NOT NULL,
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS corrections_conversation_idx
    ON corrections (conversation_id, captured_at DESC);

-- Beacon Growth Engine.
-- Campaigns and content variants stay draft/review-gated until James approves.
CREATE TABLE IF NOT EXISTS beacon_campaigns (
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

CREATE TABLE IF NOT EXISTS beacon_variants (
    id serial PRIMARY KEY,
    campaign_id text REFERENCES beacon_campaigns(campaign_id),
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

CREATE INDEX IF NOT EXISTS beacon_campaigns_status_idx ON beacon_campaigns(status);
CREATE INDEX IF NOT EXISTS beacon_variants_campaign_idx ON beacon_variants(campaign_id);

CREATE TABLE IF NOT EXISTS beacon_events (
    id serial PRIMARY KEY,
    campaign_id text REFERENCES beacon_campaigns(campaign_id),
    variant_label text,
    event_type text,
    at timestamp DEFAULT now()
);

CREATE INDEX IF NOT EXISTS beacon_events_at_idx ON beacon_events(at DESC);
CREATE INDEX IF NOT EXISTS beacon_events_campaign_idx ON beacon_events(campaign_id, at DESC);
