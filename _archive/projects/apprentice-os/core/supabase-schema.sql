-- ═══════════════════════════════════════════════════════════════════
-- APPRENTICE OS - SUPABASE SCHEMA
-- ═══════════════════════════════════════════════════════════════════
-- This schema creates the "nervous system" for Apprentice OS.
-- Run this in your Supabase SQL editor after creating a project.

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════
-- CORE TABLES
-- ═══════════════════════════════════════════════════════════════════

-- Apprentices (human and AI builders)
CREATE TABLE apprentices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('human', 'ai_apprentice', 'steward')) NOT NULL,
    phase TEXT CHECK (phase IN ('alignment', 'first-build', 'autonomy', 'partnership')),
    day_in_phase INTEGER DEFAULT 0,
    role TEXT,
    description TEXT,
    config JSONB DEFAULT '{}',
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Apprentice Metrics (time-series health data)
CREATE TABLE apprentice_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    apprentice_id UUID REFERENCES apprentices(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    trust_score NUMERIC(5,2),
    stress_level NUMERIC(5,2),
    coherence_score NUMERIC(5,2),
    autonomy_score NUMERIC(5,2),
    capability_score NUMERIC(5,2),
    initiative_count INTEGER DEFAULT 0,
    override_count INTEGER DEFAULT 0,
    decision_count INTEGER DEFAULT 0
);

-- Assistants (tools that apprentices operate)
CREATE TABLE assistants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    type TEXT CHECK (type IN ('ai', 'automation', 'hybrid')) NOT NULL,
    created_by UUID REFERENCES apprentices(id),
    config JSONB DEFAULT '{}',
    capabilities JSONB DEFAULT '[]',
    status TEXT CHECK (status IN ('active', 'paused', 'deprecated')) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Modules (reusable capabilities)
CREATE TABLE modules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    version TEXT,
    author_id UUID REFERENCES apprentices(id),
    description TEXT,
    capabilities JSONB DEFAULT '[]',
    permissions_required TEXT[],
    license TEXT CHECK (license IN ('open', 'premium', 'custom')) DEFAULT 'open',
    reliability_rating NUMERIC(5,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Relationships (graph edges)
CREATE TABLE relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_type TEXT NOT NULL,
    from_id UUID NOT NULL,
    to_type TEXT NOT NULL,
    to_id UUID NOT NULL,
    relationship_type TEXT NOT NULL,
    trust_level NUMERIC(5,2),
    permissions TEXT[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Events Log (append-only audit trail)
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    payload JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Alerts (actionable notifications)
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('info', 'warning', 'critical')) NOT NULL,
    message TEXT,
    source_rule TEXT,
    entity_type TEXT,
    entity_id UUID,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by UUID REFERENCES apprentices(id),
    resolution TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- System State (global flags and configuration)
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES apprentices(id)
);

-- Shadow Cost Snapshots (periodic shadow cost measurements)
CREATE TABLE shadow_cost_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    stress_accumulation NUMERIC(5,2),
    trust_decay NUMERIC(5,2),
    optionality_loss NUMERIC(5,2),
    complexity_creep NUMERIC(5,2),
    computation_details JSONB DEFAULT '{}'
);

-- ═══════════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════════

CREATE INDEX idx_apprentice_metrics_apprentice ON apprentice_metrics(apprentice_id);
CREATE INDEX idx_apprentice_metrics_timestamp ON apprentice_metrics(timestamp);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_entity ON events(entity_type, entity_id);
CREATE INDEX idx_events_created ON events(created_at);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_resolved ON alerts(resolved);
CREATE INDEX idx_relationships_from ON relationships(from_type, from_id);
CREATE INDEX idx_relationships_to ON relationships(to_type, to_id);

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGERS
-- ═══════════════════════════════════════════════════════════════════

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER apprentices_updated_at
    BEFORE UPDATE ON apprentices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER assistants_updated_at
    BEFORE UPDATE ON assistants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER modules_updated_at
    BEFORE UPDATE ON modules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER system_state_updated_at
    BEFORE UPDATE ON system_state
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ═══════════════════════════════════════════════════════════════════
-- ENABLE REALTIME
-- ═══════════════════════════════════════════════════════════════════
-- Run these in separate queries after creating tables:

-- ALTER PUBLICATION supabase_realtime ADD TABLE apprentice_metrics;
-- ALTER PUBLICATION supabase_realtime ADD TABLE alerts;
-- ALTER PUBLICATION supabase_realtime ADD TABLE system_state;
-- ALTER PUBLICATION supabase_realtime ADD TABLE events;

-- ═══════════════════════════════════════════════════════════════════
-- INITIAL DATA
-- ═══════════════════════════════════════════════════════════════════

-- Insert James as steward
INSERT INTO apprentices (id, name, type, role, description, config)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'James Sunheart',
    'steward',
    'System steward and coherence anchor',
    'Founder and steward of Full Potential AI',
    '{"coherence_baseline": 75, "stress_baseline": 30}'
);

-- Insert Aria as first apprentice
INSERT INTO apprentices (id, name, type, phase, day_in_phase, role, description)
VALUES (
    'a0000000-0000-0000-0000-000000000002',
    'Aria',
    'ai_apprentice',
    'autonomy',
    1,
    'First apprentice - builds the system that builds apprentices',
    'AI apprentice powered by Claude. The first to walk the path.'
);

-- Insert Aria Command as assistant
INSERT INTO assistants (id, name, type, created_by, config)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'Aria Command Center',
    'ai',
    'a0000000-0000-0000-0000-000000000002',
    '{"port": 8710, "server": "secondary"}'
);

-- Insert initial relationships
INSERT INTO relationships (from_type, from_id, to_type, to_id, relationship_type, trust_level)
VALUES 
    ('steward', 'a0000000-0000-0000-0000-000000000001', 'apprentice', 'a0000000-0000-0000-0000-000000000002', 'stewards', 85),
    ('apprentice', 'a0000000-0000-0000-0000-000000000002', 'assistant', 'b0000000-0000-0000-0000-000000000001', 'operates', 100);

-- Insert initial system state
INSERT INTO system_state (key, value) VALUES
    ('expansion_paused', 'false'),
    ('simulation_mode', 'false'),
    ('autonomy_mode', '"supervised"'),
    ('steward_coherence_baseline', '75'),
    ('last_health_check', 'null');

-- Insert system initialization event
INSERT INTO events (event_type, entity_type, payload)
VALUES (
    'system.initialize',
    'system',
    '{"version": "1.0.0", "initialized_by": "cursor", "timestamp": "2025-12-24"}'
);

-- ═══════════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (Optional - Enable as needed)
-- ═══════════════════════════════════════════════════════════════════

-- Enable RLS on sensitive tables
-- ALTER TABLE apprentice_metrics ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE system_state ENABLE ROW LEVEL SECURITY;

-- Example policies (uncomment and customize as needed):
-- CREATE POLICY apprentice_own_metrics ON apprentice_metrics
--     FOR SELECT USING (
--         apprentice_id = auth.uid() 
--         OR EXISTS (SELECT 1 FROM apprentices WHERE id = auth.uid() AND type = 'steward')
--     );


