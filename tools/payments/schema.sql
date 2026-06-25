CREATE SCHEMA IF NOT EXISTS brain_index;

CREATE TABLE IF NOT EXISTS brain_index.payment_agent_spawns (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    amount_cents INT,
    currency TEXT,
    customer_email TEXT,
    customer_id TEXT,
    namespace_id TEXT,
    agent_id TEXT,
    status TEXT NOT NULL DEFAULT 'spawned',
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brain_index.user_agents (
    id SERIAL PRIMARY KEY,
    agent_id TEXT NOT NULL UNIQUE,
    namespace_id TEXT NOT NULL UNIQUE,
    owner_email TEXT,
    owner_external_id TEXT,
    source_provider TEXT NOT NULL,
    source_event_id TEXT NOT NULL UNIQUE,
    access_level TEXT NOT NULL DEFAULT 'paid_member',
    status TEXT NOT NULL DEFAULT 'active',
    passport JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS user_agents_owner_email_idx
    ON brain_index.user_agents (owner_email)
    WHERE owner_email IS NOT NULL;

CREATE INDEX IF NOT EXISTS payment_agent_spawns_created_idx
    ON brain_index.payment_agent_spawns (created_at DESC);

