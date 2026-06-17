CREATE SCHEMA IF NOT EXISTS brain_index;

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS source TEXT;

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS topic_signal TEXT;

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS discovery_score FLOAT DEFAULT 0.5;

ALTER TABLE brain_index.probe_pool
    ADD COLUMN IF NOT EXISTS metadata JSONB;

DO $$
BEGIN
    ALTER TABLE brain_index.probe_pool
        DROP CONSTRAINT IF EXISTS probe_pool_platform_check;

    ALTER TABLE brain_index.probe_pool
        ADD CONSTRAINT probe_pool_platform_check
        CHECK (platform IN ('telegram', 'email', 'twitter', 'discord', 'reddit', 'instagram', 'hn', 'github'));
END $$;

CREATE INDEX IF NOT EXISTS probe_pool_discovery_score_idx
    ON brain_index.probe_pool (discovery_score)
    WHERE COALESCE(do_not_contact, false) = false;

CREATE INDEX IF NOT EXISTS probe_pool_handle_platform_idx
    ON brain_index.probe_pool (LOWER(handle), LOWER(platform));
