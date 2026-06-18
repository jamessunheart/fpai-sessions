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

-- Session write-through.
-- Claude Code, phone, and other non-Telegram surfaces write significant
-- decisions and architectural insights here at settle. The Telegram bot reads
-- this same layer so it can see recent decisions that did not pass through
-- brain_index.tg_messages.
CREATE TABLE IF NOT EXISTS session_insights (
    id             SERIAL PRIMARY KEY,
    ts             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    session_id     TEXT,
    surface        TEXT NOT NULL DEFAULT 'claude_code',
    insight_type   TEXT NOT NULL,
    title          TEXT NOT NULL,
    body           TEXT,
    specs_affected TEXT[] NOT NULL DEFAULT '{}',
    weight         INTEGER NOT NULL DEFAULT 5,
    expires_at     TIMESTAMPTZ,
    CHECK (weight BETWEEN 1 AND 10),
    CHECK (surface IN ('claude_code', 'codex', 'telegram', 'phone', 'other')),
    CHECK (insight_type IN ('decision', 'architecture', 'spec_queue', 'feedback', 'frontier', 'housekeeping'))
);

CREATE INDEX IF NOT EXISTS session_insights_ts_idx
    ON session_insights (ts DESC);
CREATE INDEX IF NOT EXISTS session_insights_type_weight_idx
    ON session_insights (insight_type, weight DESC);
CREATE INDEX IF NOT EXISTS session_insights_active_idx
    ON session_insights (weight DESC, ts DESC)
    WHERE expires_at IS NULL;

-- Relevance-triggered attention surfacing.
-- Rows are append-only proof that a current query caused pgvector memory to
-- surface. This replaces reminder-style scheduled checks with query-time
-- relevance evidence; no row here sends a message or creates an approval.
CREATE TABLE IF NOT EXISTS attention_surface_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    surfaced_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    conversation_id TEXT,
    query           TEXT NOT NULL,
    threshold       FLOAT NOT NULL DEFAULT 0.72,
    surfaced_count  INTEGER NOT NULL DEFAULT 0,
    candidates      JSONB NOT NULL DEFAULT '[]'::jsonb,
    CHECK (threshold >= 0 AND threshold <= 1),
    CHECK (surfaced_count >= 0)
);

CREATE INDEX IF NOT EXISTS attention_surface_events_at_idx
    ON attention_surface_events (surfaced_at DESC);
CREATE INDEX IF NOT EXISTS attention_surface_events_conversation_idx
    ON attention_surface_events (conversation_id, surfaced_at DESC)
    WHERE conversation_id IS NOT NULL;

-- Becoming Engine v1 SEE model.
-- Advisory per-person journey state for One Chat. This lets the bot see a
-- person's current becoming stage and next nurture action without sending
-- proactive messages or blocking the answer path.
CREATE TABLE IF NOT EXISTS becoming (
    person_id              TEXT PRIMARY KEY,
    identity_contact       JSONB NOT NULL DEFAULT '{}'::jsonb,
    source                 TEXT NOT NULL DEFAULT 'unknown',
    stage                  TEXT NOT NULL DEFAULT 'spark',
    stated_intent          TEXT NOT NULL DEFAULT '',
    proofs                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_blocker        TEXT NOT NULL DEFAULT '',
    cora_balance           NUMERIC,
    last_touch             TIMESTAMPTZ,
    next_nurture_action    TEXT NOT NULL DEFAULT '',
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (stage IN ('spark', 'awaken', 'activate', 'build', 'contribute', 'coach'))
);

CREATE INDEX IF NOT EXISTS becoming_stage_idx
    ON becoming (stage, updated_at DESC);
CREATE INDEX IF NOT EXISTS becoming_source_idx
    ON becoming (source, updated_at DESC);

-- Cognee graph memory layer.
-- Additive relationship tissue over existing brain_index rows. These tables do
-- not replace note_chunks/probe_pool/becoming/corrections; they store graph
-- nodes and edges derived from those tables so relationship traversal can be
-- queried and rehydrated across sessions.
CREATE TABLE IF NOT EXISTS graph_memory_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type       TEXT NOT NULL,
    node_key        TEXT NOT NULL,
    label           TEXT NOT NULL,
    properties      JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_table    TEXT,
    source_id       TEXT,
    backend         TEXT NOT NULL DEFAULT 'postgres',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (node_type, node_key)
);

CREATE TABLE IF NOT EXISTS graph_memory_edges (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_node_id    UUID NOT NULL REFERENCES graph_memory_nodes(id) ON DELETE CASCADE,
    to_node_id      UUID NOT NULL REFERENCES graph_memory_nodes(id) ON DELETE CASCADE,
    relation        TEXT NOT NULL,
    evidence        JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_table    TEXT,
    source_id       TEXT,
    backend         TEXT NOT NULL DEFAULT 'postgres',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (from_node_id, to_node_id, relation)
);

CREATE TABLE IF NOT EXISTS graph_memory_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ran_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    backend         TEXT NOT NULL DEFAULT 'postgres',
    contacts_seen   INTEGER NOT NULL DEFAULT 0,
    nodes_written   INTEGER NOT NULL DEFAULT 0,
    edges_written   INTEGER NOT NULL DEFAULT 0,
    query_proof     JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS graph_memory_nodes_type_key_idx
    ON graph_memory_nodes (node_type, node_key);
CREATE INDEX IF NOT EXISTS graph_memory_nodes_label_idx
    ON graph_memory_nodes (LOWER(label));
CREATE INDEX IF NOT EXISTS graph_memory_edges_relation_idx
    ON graph_memory_edges (relation);
CREATE INDEX IF NOT EXISTS graph_memory_edges_from_idx
    ON graph_memory_edges (from_node_id, relation);
CREATE INDEX IF NOT EXISTS graph_memory_edges_to_idx
    ON graph_memory_edges (to_node_id, relation);

-- Verified AI/user pairings.
-- These rows bind an AI surface (for example the Telegram brain bot) to one
-- verified human subject and provider account. Runtime callers should fail
-- closed when AI_PAIRING_ENFORCE=1 and no active row matches the observed
-- provider user id + chat id + optional identity fingerprint.
CREATE TABLE IF NOT EXISTS ai_user_pairings (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id           TEXT NOT NULL,          -- stable human/account subject, e.g. "james"
    ai_agent             TEXT NOT NULL,          -- surface/agent using the binding
    provider             TEXT NOT NULL,          -- telegram | appflowy | email | ...
    provider_user_id     TEXT NOT NULL,
    chat_id              TEXT,
    username             TEXT,
    identity_fingerprint TEXT,                   -- HMAC over provider identity; not a secret
    verification_method  TEXT NOT NULL DEFAULT 'manual',
    assurance_level      INTEGER NOT NULL DEFAULT 1,
    status               TEXT NOT NULL DEFAULT 'pending',
    risk_flags           TEXT[] NOT NULL DEFAULT '{}',
    verified_at          TIMESTAMPTZ,
    last_seen_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (ai_agent, provider, provider_user_id),
    UNIQUE (ai_agent, provider, chat_id)
);

CREATE INDEX IF NOT EXISTS ai_user_pairings_subject_idx
    ON ai_user_pairings (subject_id, ai_agent, status);
CREATE INDEX IF NOT EXISTS ai_user_pairings_provider_idx
    ON ai_user_pairings (provider, provider_user_id, status);
CREATE INDEX IF NOT EXISTS ai_user_pairings_status_idx
    ON ai_user_pairings (status) WHERE status <> 'verified';

-- Account takeover / pairing drift audit trail. This table is append-only from
-- runtime guards and report-only scanners; it is not an enforcement queue by
-- itself.
CREATE TABLE IF NOT EXISTS ai_pairing_security_events (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    at                   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ai_agent             TEXT NOT NULL,
    subject_id           TEXT,
    provider             TEXT NOT NULL,
    provider_user_id     TEXT,
    chat_id              TEXT,
    action               TEXT NOT NULL,          -- allow | challenge | block | report
    severity             INTEGER NOT NULL DEFAULT 0,
    reasons              TEXT[] NOT NULL DEFAULT '{}',
    pairing_id           UUID REFERENCES ai_user_pairings(id) ON DELETE SET NULL,
    observed_username    TEXT,
    metadata             JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ai_pairing_security_events_at_idx
    ON ai_pairing_security_events (at DESC);
CREATE INDEX IF NOT EXISTS ai_pairing_security_events_subject_idx
    ON ai_pairing_security_events (subject_id, at DESC);
CREATE INDEX IF NOT EXISTS ai_pairing_security_events_block_idx
    ON ai_pairing_security_events (action, severity, at DESC)
    WHERE action IN ('challenge', 'block');
