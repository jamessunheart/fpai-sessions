-- sh-brain postgres init
-- Runs ONCE on first container start (docker-entrypoint-initdb.d).
-- After this, AppFlowy-Cloud's migrations create af_* tables in the public schema,
-- and the brain-index service creates its own tables under brain_index.

-- pgvector: the reason this stack uses pgvector/pgvector:pg16 instead of
-- the stock postgres image.
CREATE EXTENSION IF NOT EXISTS vector;

-- Trigram for fuzzy concept name lookups (used by brain-index /search).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Dedicated schema + role for the brain-index service so it can't touch
-- AppFlowy's tables even if compromised. Role password is set by
-- scripts/bootstrap.sh after the cluster is up (via ALTER ROLE).
CREATE SCHEMA IF NOT EXISTS brain_index;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'brain_index') THEN
        CREATE ROLE brain_index LOGIN;
    END IF;
END $$;

GRANT USAGE, CREATE ON SCHEMA brain_index TO brain_index;
ALTER DEFAULT PRIVILEGES IN SCHEMA brain_index
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO brain_index;
ALTER DEFAULT PRIVILEGES IN SCHEMA brain_index
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO brain_index;
