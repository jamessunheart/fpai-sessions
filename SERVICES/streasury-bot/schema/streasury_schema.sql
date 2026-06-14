-- streasury_schema.sql — sovereign treasury ledger.
--
-- IDEMPOTENT. Safe to apply on every deploy.
--
-- Tables:
--   account         — bank, wallet, exchange, custom (running balance computed from txns)
--   txn             — every income/expense/transfer event
--   holding         — non-cash positions (crypto, stocks, etc.) with last valuation
--   kpi_point       — named numeric metric snapshots over time
--   import_batch    — provenance of a CSV/PDF/photo import
--   conversation    — AI chat history (for /ask and /council follow-ups)
--   council_brief   — saved Claude×OpenAI synthesis outputs

CREATE SCHEMA IF NOT EXISTS streasury;
SET search_path TO streasury, public;

-- ─── Tenants ─────────────────────────────────────────────────────────────────
-- Phase 1 ships with one tenant (id=1) and never touches this UI. Phase 2+
-- adds onboarding flows. Cost of having tenant_id everywhere now: ~zero.
-- Cost of retrofitting later: a hard migration. So: do it now.
CREATE TABLE IF NOT EXISTS streasury.tenant (
    id              BIGSERIAL PRIMARY KEY,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    plan            TEXT NOT NULL DEFAULT 'beta',   -- beta | solo | team | pro
    owner_tg_id     BIGINT,                         -- which Telegram user owns this tenant
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO streasury.tenant (id, slug, name, plan)
VALUES (1, 'default', 'Default Tenant', 'beta')
ON CONFLICT (id) DO NOTHING;

-- Keep BIGSERIAL in sync with the manual id=1 insert above so future inserts
-- don't collide.
SELECT setval('streasury.tenant_id_seq', GREATEST(1, (SELECT MAX(id) FROM streasury.tenant)));

CREATE TABLE IF NOT EXISTS streasury.account (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    slug            TEXT NOT NULL,                  -- e.g. "stripe", "amex_personal", "btc_cold"
    name            TEXT NOT NULL,                  -- human label
    currency        TEXT NOT NULL DEFAULT 'USD',    -- ISO-4217 or crypto ticker
    kind            TEXT NOT NULL DEFAULT 'cash',   -- cash | crypto | revenue | obligation | virtual
    archived        BOOLEAN NOT NULL DEFAULT FALSE,
    opening_balance NUMERIC(20, 8) NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug)
);

CREATE TABLE IF NOT EXISTS streasury.txn (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    account_id      BIGINT NOT NULL REFERENCES streasury.account(id) ON DELETE RESTRICT,
    occurred_at     TIMESTAMPTZ NOT NULL,
    amount          NUMERIC(20, 8) NOT NULL,        -- + income, - expense
    currency        TEXT NOT NULL DEFAULT 'USD',
    category        TEXT NOT NULL DEFAULT 'misc',   -- revenue, hosting, ai, payroll, etc.
    vendor          TEXT,                           -- counterparty name (for dedup)
    note            TEXT,
    source          TEXT NOT NULL DEFAULT 'manual', -- manual | photo | voice | csv | stripe | whaletrack | …
    source_ref      TEXT,                           -- external id (stripe charge id, tx hash, etc.)
    dedup_hash      TEXT,                           -- sha1(date|amount|vendor) for dupe-guard
    import_batch_id BIGINT,                         -- nullable, references import_batch
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS txn_occurred_idx       ON streasury.txn (occurred_at DESC);
CREATE INDEX IF NOT EXISTS txn_tenant_idx         ON streasury.txn (tenant_id);
CREATE INDEX IF NOT EXISTS txn_account_idx        ON streasury.txn (account_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS txn_category_idx       ON streasury.txn (category);
CREATE INDEX IF NOT EXISTS txn_source_idx         ON streasury.txn (source);
CREATE UNIQUE INDEX IF NOT EXISTS txn_source_ref_uq
    ON streasury.txn (tenant_id, source, source_ref) WHERE source_ref IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS txn_dedup_uq
    ON streasury.txn (tenant_id, dedup_hash) WHERE dedup_hash IS NOT NULL;

CREATE TABLE IF NOT EXISTS streasury.holding (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    slug            TEXT NOT NULL,                  -- "btc", "eth", "aapl"
    name            TEXT NOT NULL,
    quantity        NUMERIC(30, 12) NOT NULL DEFAULT 0,
    last_unit_usd   NUMERIC(20, 8),                 -- last known unit price in USD
    last_valued_at  TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, slug)
);

CREATE TABLE IF NOT EXISTS streasury.kpi_point (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    name            TEXT NOT NULL,                  -- "MRR", "active_guests", "ltv"
    value           NUMERIC(20, 8) NOT NULL,
    unit            TEXT,                           -- "USD", "%", "count"
    note            TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS kpi_point_name_time_idx
    ON streasury.kpi_point (tenant_id, name, occurred_at DESC);

CREATE TABLE IF NOT EXISTS streasury.import_batch (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    source          TEXT NOT NULL,                  -- 'csv:amex', 'photo:receipt', 'pdf:chase', …
    filename        TEXT,
    file_sha1       TEXT,
    rows_seen       INTEGER NOT NULL DEFAULT 0,
    rows_inserted   INTEGER NOT NULL DEFAULT 0,
    rows_skipped    INTEGER NOT NULL DEFAULT 0,
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE streasury.txn
    DROP CONSTRAINT IF EXISTS txn_import_batch_fkey;
ALTER TABLE streasury.txn
    ADD CONSTRAINT txn_import_batch_fkey
    FOREIGN KEY (import_batch_id) REFERENCES streasury.import_batch(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS streasury.conversation (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    tg_user_id      BIGINT NOT NULL,
    role            TEXT NOT NULL,                  -- 'user' | 'assistant' | 'system'
    kind            TEXT NOT NULL DEFAULT 'ask',    -- 'ask' | 'council'
    content         TEXT NOT NULL,
    model           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS conversation_user_time_idx
    ON streasury.conversation (tenant_id, tg_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS streasury.council_brief (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    question        TEXT NOT NULL,
    claude_answer   TEXT,
    openai_answer   TEXT,
    synthesis       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Source connections ──────────────────────────────────────────────────────
-- One row per "place we pull numbers from" (a SimpleFIN endpoint, a Stripe
-- account, a Solana wallet). Keeps tokens out of code. Encrypted-at-rest if
-- the deployer wraps DATABASE_URL with sslmode=require + disk encryption.
CREATE TABLE IF NOT EXISTS streasury.source_connection (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       BIGINT NOT NULL DEFAULT 1 REFERENCES streasury.tenant(id) ON DELETE RESTRICT,
    kind            TEXT NOT NULL,                  -- 'simplefin' | 'gocardless' | 'stripe' | 'plaid' | 'teller' | 'rpc' | 'exchange'
    label           TEXT NOT NULL,                  -- "Personal Chase", "Stripe Live"
    secret          TEXT NOT NULL,                  -- bearer / setup token / api key
    config          JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_sync_at    TIMESTAMPTZ,
    last_sync_ok    BOOLEAN,
    last_sync_error TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS source_connection_tenant_kind_idx
    ON streasury.source_connection (tenant_id, kind);

-- ─── Convenience view: live balances per account ─────────────────────────────
CREATE OR REPLACE VIEW streasury.v_account_balance AS
SELECT
    a.id,
    a.tenant_id,
    a.slug,
    a.name,
    a.currency,
    a.kind,
    a.archived,
    a.opening_balance + COALESCE(SUM(t.amount), 0) AS balance,
    COUNT(t.id)                                    AS txn_count,
    MAX(t.occurred_at)                             AS last_txn_at
FROM streasury.account a
LEFT JOIN streasury.txn t ON t.account_id = a.id
GROUP BY a.id;
