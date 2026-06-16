-- Review-only SQL artifact for USER_OS_BLUEPRINT v0.1.
-- This file is intentionally outside SERVICES/*/migrations and is not applied
-- by this branch. Promote into a real migration only after ops review.

SET search_path TO brain_index, public;

CREATE TABLE IF NOT EXISTS replication_insights (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    note_type               TEXT NOT NULL DEFAULT 'replication_insight.v1',
    source                  TEXT NOT NULL,
    source_conversation_id  TEXT NOT NULL,
    source_message_id       TEXT,
    user_id                 TEXT,
    blueprint_version       TEXT NOT NULL DEFAULT '0.1',
    insight_kind            TEXT NOT NULL,
    blueprint_section       TEXT NOT NULL,
    summary                 TEXT NOT NULL,
    evidence                TEXT,
    status                  TEXT NOT NULL DEFAULT 'new',
    captured_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at             TIMESTAMPTZ,
    reviewer                TEXT,
    review_notes            TEXT,
    CHECK (note_type = 'replication_insight.v1'),
    CHECK (insight_kind IN (
        'gap',
        'proven_pattern',
        'onboarding_confusion',
        'safety_gate',
        'upgrade_trigger'
    )),
    CHECK (blueprint_section IN (
        'minimum_install_checklist',
        'what_works_today',
        'gap_log',
        'journey_refinement_hooks',
        'agent_passport_schema_stub'
    )),
    CHECK (status IN ('new', 'reviewed', 'accepted', 'rejected'))
);

CREATE OR REPLACE FUNCTION prevent_replication_insights_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'replication_insights is append-only; insert a new row instead';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS replication_insights_no_update_delete
    ON replication_insights;

CREATE TRIGGER replication_insights_no_update_delete
    BEFORE UPDATE OR DELETE ON replication_insights
    FOR EACH ROW EXECUTE FUNCTION prevent_replication_insights_mutation();

CREATE INDEX IF NOT EXISTS replication_insights_status_idx
    ON replication_insights (status, captured_at DESC);

CREATE INDEX IF NOT EXISTS replication_insights_user_idx
    ON replication_insights (user_id, captured_at DESC);

CREATE INDEX IF NOT EXISTS replication_insights_section_idx
    ON replication_insights (blueprint_section, captured_at DESC);
