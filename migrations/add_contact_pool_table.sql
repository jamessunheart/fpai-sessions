CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.contact_pool (
    id TEXT PRIMARY KEY,
    name TEXT,
    wa_id TEXT,
    email TEXT,
    tg_handle TEXT,
    channel TEXT NOT NULL CHECK (channel IN ('whatsapp', 'email', 'telegram')),
    source TEXT NOT NULL DEFAULT 'manual',
    notes JSONB,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'outreach_sent', 'replied', 'in_probe', 'completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS contact_pool_wa_id_idx
    ON brain_index.contact_pool (wa_id)
    WHERE wa_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS contact_pool_email_idx
    ON brain_index.contact_pool (lower(email))
    WHERE email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS contact_pool_tg_handle_idx
    ON brain_index.contact_pool (lower(tg_handle))
    WHERE tg_handle IS NOT NULL;

ALTER TABLE brain_index.probe_pool
    DROP CONSTRAINT IF EXISTS probe_pool_platform_check;

ALTER TABLE brain_index.probe_pool
    ADD CONSTRAINT probe_pool_platform_check
    CHECK (platform IN ('telegram', 'email', 'whatsapp', 'twitter', 'discord', 'reddit', 'instagram', 'hn', 'github'));
