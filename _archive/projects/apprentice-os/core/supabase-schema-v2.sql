-- ============================================================================
-- APPRENTICE OS - SUPABASE SCHEMA v2
-- ============================================================================
-- Run this in Supabase SQL Editor to add the necessary columns and tables
-- for the apprentice onboarding system.
--
-- This is ADDITIVE - it won't break existing data.
-- ============================================================================

-- ============================================================================
-- 1. UPDATE APPRENTICES TABLE
-- ============================================================================

-- Add telegram_id column for Telegram integration
ALTER TABLE apprentices ADD COLUMN IF NOT EXISTS telegram_id BIGINT UNIQUE;

-- Add authority column
ALTER TABLE apprentices ADD COLUMN IF NOT EXISTS authority TEXT DEFAULT 'apprentice';

-- Add first_interaction timestamp (for onboarding detection)
ALTER TABLE apprentices ADD COLUMN IF NOT EXISTS first_interaction TIMESTAMP WITH TIME ZONE;

-- Add onboarding_complete flag
ALTER TABLE apprentices ADD COLUMN IF NOT EXISTS onboarding_complete BOOLEAN DEFAULT FALSE;

-- Create index for fast telegram_id lookups
CREATE INDEX IF NOT EXISTS idx_apprentices_telegram_id ON apprentices(telegram_id);

-- ============================================================================
-- 2. APPRENTICE ACTIVITY LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS apprentice_activity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    apprentice_id UUID REFERENCES apprentices(id),
    telegram_id BIGINT,
    activity_type TEXT NOT NULL,  -- 'message', 'tool_use', 'module_create', 'submission', 'onboarding'
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for querying by apprentice
CREATE INDEX IF NOT EXISTS idx_activity_apprentice ON apprentice_activity(apprentice_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_telegram ON apprentice_activity(telegram_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_type ON apprentice_activity(activity_type);

-- ============================================================================
-- 3. APPRENTICE PROGRESS
-- ============================================================================

CREATE TABLE IF NOT EXISTS apprentice_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    apprentice_id UUID REFERENCES apprentices(id),
    telegram_id BIGINT,
    challenge_id TEXT,
    status TEXT DEFAULT 'in_progress',  -- 'in_progress', 'submitted', 'completed', 'failed'
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    submission_path TEXT,  -- Path to their submitted work
    review_notes TEXT,     -- Steward's review
    UNIQUE(telegram_id, challenge_id)
);

-- Index for querying progress
CREATE INDEX IF NOT EXISTS idx_progress_apprentice ON apprentice_progress(apprentice_id);
CREATE INDEX IF NOT EXISTS idx_progress_telegram ON apprentice_progress(telegram_id);
CREATE INDEX IF NOT EXISTS idx_progress_status ON apprentice_progress(status);

-- ============================================================================
-- 4. USAGE COSTS (for cost attribution)
-- ============================================================================

CREATE TABLE IF NOT EXISTS usage_costs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT NOT NULL,
    operation TEXT NOT NULL,  -- 'claude_api', 'voice_tts', 'voice_stt', 'openai'
    tokens INTEGER,
    cost_usd DECIMAL(10, 6),
    model TEXT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for cost queries
CREATE INDEX IF NOT EXISTS idx_costs_telegram ON usage_costs(telegram_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_costs_operation ON usage_costs(operation);
CREATE INDEX IF NOT EXISTS idx_costs_date ON usage_costs(created_at);

-- ============================================================================
-- 5. RATE LIMIT TRACKING
-- ============================================================================

CREATE TABLE IF NOT EXISTS rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    telegram_id BIGINT NOT NULL,
    operation TEXT NOT NULL,  -- 'message', 'tool_call', 'voice', 'file_write'
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    count INTEGER DEFAULT 1,
    UNIQUE(telegram_id, operation, window_start)
);

-- Index for rate limit checks
CREATE INDEX IF NOT EXISTS idx_rate_limits_lookup ON rate_limits(telegram_id, operation, window_start);

-- ============================================================================
-- 6. HELPER FUNCTIONS
-- ============================================================================

-- Function to get apprentice by telegram_id
CREATE OR REPLACE FUNCTION get_apprentice_by_telegram(tid BIGINT)
RETURNS TABLE (
    id UUID,
    name TEXT,
    type TEXT,
    telegram_id BIGINT,
    phase TEXT,
    first_interaction TIMESTAMP WITH TIME ZONE,
    onboarding_complete BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.name,
        a.type,
        a.telegram_id,
        a.phase,
        a.first_interaction,
        a.onboarding_complete
    FROM apprentices a
    WHERE a.telegram_id = tid;
END;
$$ LANGUAGE plpgsql;

-- Function to get total costs by user
CREATE OR REPLACE FUNCTION get_user_costs(tid BIGINT, since TIMESTAMP WITH TIME ZONE DEFAULT NOW() - INTERVAL '30 days')
RETURNS TABLE (
    total_cost DECIMAL,
    total_tokens BIGINT,
    by_operation JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(cost_usd), 0) as total_cost,
        COALESCE(SUM(tokens), 0) as total_tokens,
        jsonb_object_agg(operation, op_cost) as by_operation
    FROM (
        SELECT 
            operation,
            SUM(cost_usd) as op_cost
        FROM usage_costs
        WHERE telegram_id = tid AND created_at >= since
        GROUP BY operation
    ) sub;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. UPDATE EXISTING DATA
-- ============================================================================

-- Update Aria's record to have the correct type if needed
UPDATE apprentices 
SET type = 'ai_apprentice', authority = 'apprentice'
WHERE name = 'Aria' AND type IS NULL;

-- Update James's record to have steward authority
UPDATE apprentices 
SET authority = 'steward'
WHERE name LIKE '%James%' OR type = 'steward';

-- ============================================================================
-- DONE! Schema v2 applied successfully.
-- ============================================================================


