-- Sunheart Brain — postgres initialization
-- Runs once, on first container start (thanks to /docker-entrypoint-initdb.d/).
-- All the standard AppFlowy bootstrap is handled by the appflowy_cloud image;
-- here we only add what pgvector + brain-index need on top.

-- pgvector extension lives in the same DB that AppFlowy uses. AppFlowy doesn't
-- touch the brain_index schema, so there's no risk of collision.
CREATE EXTENSION IF NOT EXISTS vector;

-- Dedicated schema for the semantic index (isolated from appflowy_cloud tables).
CREATE SCHEMA IF NOT EXISTS brain_index;

-- Role the brain-index service uses (least privilege: only brain_index schema).
-- Password is passed via environment at bootstrap-time by scripts/bootstrap.sh.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'brain_index') THEN
    CREATE ROLE brain_index LOGIN;
  END IF;
END $$;

GRANT USAGE, CREATE ON SCHEMA brain_index TO brain_index;
ALTER DEFAULT PRIVILEGES IN SCHEMA brain_index
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO brain_index;

-- Tables are created by brain-index on first startup (Alembic-style but simpler).
-- See index/schema.sql.
