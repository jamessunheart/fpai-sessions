-- ===========================================
-- WhiteRock CORA Blessings Engine v2.2
-- Performance Optimization Indexes
-- ===========================================

-- ===========================================
-- COMPOSITE INDEXES
-- These speed up common query patterns
-- ===========================================

-- Tithes: Common query by member with date ordering
CREATE INDEX IF NOT EXISTS idx_tithes_member_created 
ON tithes(member_id, created_at DESC);

-- CORA Transactions: Query by member and type
CREATE INDEX IF NOT EXISTS idx_cora_member_type 
ON cora_transactions(member_id, transaction_type);

-- Blessing Requests: Filter by status with date ordering
CREATE INDEX IF NOT EXISTS idx_blessings_status_created 
ON blessing_requests(status, created_at ASC);

-- Service Hours: Query by member with date
CREATE INDEX IF NOT EXISTS idx_service_member_date 
ON service_hours(member_id, activity_date DESC);

-- Audit Log: Query by entity with date range
CREATE INDEX IF NOT EXISTS idx_audit_entity_created 
ON audit_log(entity_type, entity_id, created_at DESC);

-- ===========================================
-- PARTIAL INDEXES
-- Index only the rows that matter
-- ===========================================

-- Members approaching decay: Only active members with CORA
CREATE INDEX IF NOT EXISTS idx_members_decay_candidates 
ON members(last_engagement_date) 
WHERE is_active = true AND cora_balance > 0;

-- Pending blessings: Only those needing review
CREATE INDEX IF NOT EXISTS idx_blessings_pending_review 
ON blessing_requests(created_at ASC) 
WHERE status IN ('pending', 'committee_review', 'info_requested');

-- Active members for statistics
CREATE INDEX IF NOT EXISTS idx_members_active_stats 
ON members(created_at, membership_tier, cora_balance) 
WHERE is_active = true;

-- Unverified service hours
CREATE INDEX IF NOT EXISTS idx_service_unverified 
ON service_hours(created_at ASC) 
WHERE verified_at IS NULL;

-- ===========================================
-- COVERING INDEXES
-- Include frequently accessed columns
-- ===========================================

-- Members lookup by email (common for login)
DROP INDEX IF EXISTS idx_members_email;
CREATE INDEX IF NOT EXISTS idx_members_email_active 
ON members(email) 
WHERE is_active = true;

-- Tithes with receipt info
CREATE INDEX IF NOT EXISTS idx_tithes_receipt_lookup 
ON tithes(member_id, id, amount_cents, created_at, receipt_url) 
WHERE receipt_sent_at IS NOT NULL;

-- ===========================================
-- EXPRESSION INDEXES
-- For computed filters
-- ===========================================

-- Members by tier (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_members_tier_lower 
ON members(LOWER(membership_tier));

-- ===========================================
-- GIN INDEXES FOR JSONB
-- Fast lookups in JSONB columns
-- ===========================================

-- State transition log searches
CREATE INDEX IF NOT EXISTS idx_blessings_transition_log 
ON blessing_requests USING GIN (state_transition_log);

-- Tier privileges searches
CREATE INDEX IF NOT EXISTS idx_tiers_privileges 
ON membership_tiers USING GIN (access_privileges);

-- Audit log values searches
CREATE INDEX IF NOT EXISTS idx_audit_new_values 
ON audit_log USING GIN (new_values);

-- ===========================================
-- ANALYZE
-- Update statistics for query planner
-- ===========================================

ANALYZE members;
ANALYZE tithes;
ANALYZE cora_transactions;
ANALYZE blessing_requests;
ANALYZE service_hours;
ANALYZE audit_log;

-- ===========================================
-- END PERFORMANCE INDEXES
-- ===========================================



