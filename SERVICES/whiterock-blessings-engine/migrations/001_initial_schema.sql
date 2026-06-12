-- ===========================================
-- WhiteRock CORA Blessings Engine v2.1
-- Initial Database Schema
-- ===========================================

-- Enable UUID extension if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- MEMBERS
-- ===========================================
CREATE TABLE IF NOT EXISTS members (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    address_line1 VARCHAR(255),
    address_line2 VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    
    -- Membership & Standing
    membership_tier VARCHAR(50) DEFAULT 'seedling',
    cora_balance INTEGER DEFAULT 0,
    cora_cap INTEGER DEFAULT 1000, -- Based on tier
    
    -- Engagement Tracking (for decay)
    last_engagement_date TIMESTAMP DEFAULT NOW(),
    decay_warning_sent_at TIMESTAMP,
    
    -- Compliance
    disclosure_signed_at TIMESTAMP,
    disclosure_version VARCHAR(20),
    profile_complete BOOLEAN DEFAULT FALSE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    deactivation_reason TEXT,
    
    -- Admin flags
    is_admin BOOLEAN DEFAULT FALSE,
    is_committee BOOLEAN DEFAULT FALSE,
    is_auditor BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_members_email ON members(email);
CREATE INDEX IF NOT EXISTS idx_members_tier ON members(membership_tier);
CREATE INDEX IF NOT EXISTS idx_members_engagement ON members(last_engagement_date);

-- ===========================================
-- MEMBERSHIP TIERS (Reference)
-- ===========================================
CREATE TABLE IF NOT EXISTS membership_tiers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    cora_threshold INTEGER NOT NULL,
    cora_cap INTEGER NOT NULL,
    description TEXT,
    access_privileges JSONB DEFAULT '{}'
);

INSERT INTO membership_tiers (name, cora_threshold, cora_cap, description, access_privileges) VALUES
('seedling', 0, 1000, 'New member', '{"events": "community", "facilities": "basic"}'),
('sprout', 500, 2500, 'Active participant', '{"events": "all_public", "facilities": "standard"}'),
('steward', 2000, 5000, 'Committed member', '{"events": "all", "facilities": "full", "voting": true}'),
('elder', 5000, 10000, 'Senior member', '{"events": "all", "facilities": "priority", "voting": true, "committee_eligible": true}')
ON CONFLICT (name) DO NOTHING;

-- ===========================================
-- DISCLOSURE VERSIONS
-- ===========================================
CREATE TABLE IF NOT EXISTS disclosure_versions (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    disclosure_text TEXT NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert current disclosure version
INSERT INTO disclosure_versions (version, disclosure_text, is_current) VALUES
('1.0.0', 'I understand this contribution is an irrevocable charitable gift to WhiteRock Church Trust, a 508(c)(1)(A) religious organization. I receive no ownership interest, investment return, or contractual right to any benefit. Any community support provided is at the sole discretion of church leadership and is not guaranteed. This blessing is a one-time discretionary gift and does not constitute an ongoing obligation or contract.', TRUE)
ON CONFLICT (version) DO NOTHING;

-- ===========================================
-- TITHES
-- ===========================================
CREATE TABLE IF NOT EXISTS tithes (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE RESTRICT,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    
    -- Payment
    stripe_payment_id VARCHAR(255),
    stripe_payment_status VARCHAR(50),
    
    -- Compliance (CRITICAL)
    disclosure_acknowledged BOOLEAN NOT NULL DEFAULT FALSE,
    disclosure_text TEXT NOT NULL,
    disclosure_version VARCHAR(20) NOT NULL,
    disclosure_scrolled_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Receipt
    receipt_sent_at TIMESTAMP,
    receipt_url TEXT,
    
    -- CORA
    cora_granted INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tithes_member ON tithes(member_id);
CREATE INDEX IF NOT EXISTS idx_tithes_created ON tithes(created_at);

-- ===========================================
-- CORA TRANSACTIONS
-- ===========================================
CREATE TABLE IF NOT EXISTS cora_transactions (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE RESTRICT,
    amount INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    description TEXT,
    granted_by INTEGER REFERENCES members(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cora_member ON cora_transactions(member_id);
CREATE INDEX IF NOT EXISTS idx_cora_type ON cora_transactions(transaction_type);

-- ===========================================
-- CORA DECAY EVENTS (Audit Trail)
-- ===========================================
CREATE TABLE IF NOT EXISTS cora_decay_events (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE RESTRICT,
    amount_decayed INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    decay_reason VARCHAR(50) NOT NULL,
    months_inactive INTEGER NOT NULL,
    notification_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_decay_member ON cora_decay_events(member_id);

-- ===========================================
-- SERVICE HOURS
-- ===========================================
CREATE TABLE IF NOT EXISTS service_hours (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE RESTRICT,
    hours DECIMAL(5,2) NOT NULL,
    activity_type VARCHAR(100) NOT NULL,
    activity_date DATE NOT NULL,
    description TEXT,
    
    -- Verification
    verified_by INTEGER REFERENCES members(id),
    verified_at TIMESTAMP,
    
    -- CORA
    cora_granted INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_service_member ON service_hours(member_id);
CREATE INDEX IF NOT EXISTS idx_service_date ON service_hours(activity_date);

-- ===========================================
-- BLESSING REQUESTS (State Machine)
-- ===========================================
CREATE TABLE IF NOT EXISTS blessing_requests (
    id SERIAL PRIMARY KEY,
    member_id INTEGER REFERENCES members(id) ON DELETE RESTRICT,
    
    -- Request Details
    category VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    amount_requested_cents INTEGER,
    supporting_docs_url TEXT,
    
    -- Vendor (for direct payment)
    vendor_name VARCHAR(255),
    vendor_contact VARCHAR(255),
    
    -- State Machine (CRITICAL)
    status VARCHAR(50) DEFAULT 'draft',
    state_transition_log JSONB DEFAULT '[]',
    
    -- Committee Review
    reviewed_by INTEGER REFERENCES members(id),
    reviewed_at TIMESTAMP,
    internal_notes TEXT,
    compliance_flag BOOLEAN DEFAULT FALSE,
    
    -- Outcome
    amount_approved_cents INTEGER,
    denial_reason TEXT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blessing_member ON blessing_requests(member_id);
CREATE INDEX IF NOT EXISTS idx_blessing_status ON blessing_requests(status);
CREATE INDEX IF NOT EXISTS idx_blessing_category ON blessing_requests(category);

-- ===========================================
-- BLESSING DISBURSEMENTS (Vendor-Direct)
-- ===========================================
CREATE TABLE IF NOT EXISTS blessing_disbursements (
    id SERIAL PRIMARY KEY,
    blessing_request_id INTEGER REFERENCES blessing_requests(id) ON DELETE RESTRICT,
    amount_cents INTEGER NOT NULL,
    
    -- Disbursement Method
    disbursement_method VARCHAR(50) NOT NULL,
    payment_direct_to_vendor BOOLEAN DEFAULT TRUE,
    
    -- Vendor Info
    vendor_name VARCHAR(255),
    vendor_contact VARCHAR(255),
    
    -- Tracking
    disbursement_reference VARCHAR(255),
    disbursed_by INTEGER REFERENCES members(id),
    
    -- Audit Flag
    cash_to_member_override BOOLEAN DEFAULT FALSE,
    override_approved_by INTEGER REFERENCES members(id),
    override_reason TEXT,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_disbursement_request ON blessing_disbursements(blessing_request_id);

-- ===========================================
-- COMMUNITY CAPACITY (Oracle - External Write Only)
-- ===========================================
CREATE TABLE IF NOT EXISTS community_capacity (
    id SERIAL PRIMARY KEY,
    capacity_level VARCHAR(20) NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by VARCHAR(100)
);

-- Seed initial value
INSERT INTO community_capacity (capacity_level, updated_by) 
SELECT 'high', 'system_init'
WHERE NOT EXISTS (SELECT 1 FROM community_capacity LIMIT 1);

-- ===========================================
-- AUDIT LOG (Compliance)
-- ===========================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,
    actor_id INTEGER REFERENCES members(id),
    actor_role VARCHAR(50),
    old_values JSONB,
    new_values JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    severity VARCHAR(20) DEFAULT 'info',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_severity ON audit_log(severity);

-- ===========================================
-- TITHE MILESTONES (CORA Grants)
-- ===========================================
CREATE TABLE IF NOT EXISTS tithe_milestones (
    id SERIAL PRIMARY KEY,
    cumulative_amount_cents INTEGER UNIQUE NOT NULL,
    cora_grant INTEGER NOT NULL,
    description TEXT
);

INSERT INTO tithe_milestones (cumulative_amount_cents, cora_grant, description) VALUES
(10000, 50, 'First $100 tithe'),
(50000, 150, '$500 total tithes'),
(100000, 300, '$1,000 total tithes'),
(250000, 500, '$2,500 total tithes'),
(500000, 1000, '$5,000 total tithes')
ON CONFLICT (cumulative_amount_cents) DO NOTHING;

-- ===========================================
-- CONSTRAINTS
-- ===========================================

-- Ensure no negative CORA balance
ALTER TABLE members DROP CONSTRAINT IF EXISTS chk_cora_non_negative;
ALTER TABLE members ADD CONSTRAINT chk_cora_non_negative CHECK (cora_balance >= 0);

-- Ensure CORA doesn't exceed cap
ALTER TABLE members DROP CONSTRAINT IF EXISTS chk_cora_cap;
ALTER TABLE members ADD CONSTRAINT chk_cora_cap CHECK (cora_balance <= cora_cap);

-- Ensure valid blessing states
ALTER TABLE blessing_requests DROP CONSTRAINT IF EXISTS chk_blessing_status;
ALTER TABLE blessing_requests ADD CONSTRAINT chk_blessing_status 
CHECK (status IN ('draft', 'pending', 'committee_review', 'info_requested', 'approved', 'denied', 'disbursed', 'closed'));

-- Ensure valid capacity levels
ALTER TABLE community_capacity DROP CONSTRAINT IF EXISTS chk_capacity_level;
ALTER TABLE community_capacity ADD CONSTRAINT chk_capacity_level 
CHECK (capacity_level IN ('high', 'medium', 'low', 'paused'));

-- ===========================================
-- HELPER FUNCTIONS
-- ===========================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at
DROP TRIGGER IF EXISTS update_members_updated_at ON members;
CREATE TRIGGER update_members_updated_at
    BEFORE UPDATE ON members
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_blessing_requests_updated_at ON blessing_requests;
CREATE TRIGGER update_blessing_requests_updated_at
    BEFORE UPDATE ON blessing_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ===========================================
-- END SCHEMA
-- ===========================================



