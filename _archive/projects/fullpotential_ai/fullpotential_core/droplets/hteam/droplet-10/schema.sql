-- DROPLET #10: ORCHESTRATOR DATABASE SCHEMA
-- Version: 2.0
-- PostgreSQL 15+

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- TABLE: droplets
-- Tracks all registered droplets in the mesh
-- ============================================================================
CREATE TABLE IF NOT EXISTS droplets (
    id SERIAL PRIMARY KEY,
    droplet_id INTEGER UNIQUE NOT NULL,  -- From Registry
    name VARCHAR(100) NOT NULL,
    steward VARCHAR(100),
    endpoint VARCHAR(255) NOT NULL,
    capabilities JSONB DEFAULT '[]'::jsonb,  -- Array of capability strings
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive', 'error')),
    last_heartbeat TIMESTAMP,
    registered_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_droplets_status ON droplets(status);
CREATE INDEX idx_droplets_heartbeat ON droplets(last_heartbeat);
CREATE INDEX idx_droplets_capabilities ON droplets USING GIN(capabilities);
CREATE INDEX idx_droplets_droplet_id ON droplets(droplet_id);

-- ============================================================================
-- TABLE: tasks
-- Central task management and routing
-- ============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    trace_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    task_type VARCHAR(50) NOT NULL,  -- 'build', 'verify', 'deploy', 'monitor', etc.
    title VARCHAR(255) NOT NULL,
    description TEXT,
    payload JSONB NOT NULL,  -- Task-specific data
    
    -- Routing
    required_capability VARCHAR(100),  -- Must match droplet capability
    assigned_droplet_id INTEGER REFERENCES droplets(id) ON DELETE SET NULL,
    
    -- State machine
    status VARCHAR(20) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled')),
    
    -- Priority & timing
    priority INTEGER DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),  -- 1=highest, 10=lowest
    created_at TIMESTAMP DEFAULT NOW(),
    assigned_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    deadline TIMESTAMP,
    
    -- Results
    result JSONB,  -- Success/failure data
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Metadata
    created_by VARCHAR(100),  -- Droplet or user who created task
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_trace_id ON tasks(trace_id);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_assigned_droplet ON tasks(assigned_droplet_id);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_capability ON tasks(required_capability);
CREATE INDEX idx_tasks_type ON tasks(task_type);

-- ============================================================================
-- TABLE: task_state_history
-- Audit trail of all state changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS task_state_history (
    id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    from_status VARCHAR(20),
    to_status VARCHAR(20) NOT NULL,
    changed_by VARCHAR(100),  -- Droplet ID or system
    reason TEXT,
    metadata JSONB,
    changed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_task_history_task_id ON task_state_history(task_id);
CREATE INDEX idx_task_history_changed_at ON task_state_history(changed_at);

-- ============================================================================
-- TABLE: heartbeats
-- Recent heartbeat history for health monitoring
-- ============================================================================
CREATE TABLE IF NOT EXISTS heartbeats (
    id SERIAL PRIMARY KEY,
    droplet_id INTEGER NOT NULL REFERENCES droplets(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    metrics JSONB,  -- CPU, memory, request count, etc.
    received_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_heartbeats_droplet_id ON heartbeats(droplet_id);
CREATE INDEX idx_heartbeats_received_at ON heartbeats(received_at DESC);

-- ============================================================================
-- TABLE: orchestrator_metrics
-- System-wide performance tracking
-- ============================================================================
CREATE TABLE IF NOT EXISTS orchestrator_metrics (
    id SERIAL PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    labels JSONB,  -- Additional dimensions (droplet_id, task_type, etc.)
    recorded_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_metrics_name_time ON orchestrator_metrics(metric_name, recorded_at DESC);
CREATE INDEX idx_metrics_recorded_at ON orchestrator_metrics(recorded_at DESC);
CREATE INDEX idx_metrics_name ON orchestrator_metrics(metric_name);

-- ============================================================================
-- TRIGGERS: Auto-update timestamps
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_droplets_updated_at
    BEFORE UPDATE ON droplets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- CLEANUP FUNCTION: Remove old heartbeats (keep 24 hours only)
-- Run this as scheduled job
-- ============================================================================
CREATE OR REPLACE FUNCTION cleanup_old_heartbeats()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM heartbeats
    WHERE received_at < NOW() - INTERVAL '24 hours';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA: Self-register Orchestrator droplet
-- ============================================================================
INSERT INTO droplets (droplet_id, name, steward, endpoint, capabilities, status, last_heartbeat)
VALUES (
    10,
    'Orchestrator',
    'Tnsae',
    'https://orchestrator.fullpotential.ai',
    '["task_routing", "droplet_discovery", "health_monitoring", "workflow_management"]'::jsonb,
    'active',
    NOW()
)
ON CONFLICT (droplet_id) DO UPDATE
SET 
    name = EXCLUDED.name,
    steward = EXCLUDED.steward,
    endpoint = EXCLUDED.endpoint,
    capabilities = EXCLUDED.capabilities,
    status = EXCLUDED.status,
    last_heartbeat = EXCLUDED.last_heartbeat,
    updated_at = NOW();

-- ============================================================================
-- VIEWS: Useful query shortcuts
-- ============================================================================

-- Active tasks summary
CREATE OR REPLACE VIEW v_active_tasks AS
SELECT 
    t.id,
    t.trace_id,
    t.task_type,
    t.title,
    t.status,
    t.priority,
    t.created_at,
    t.assigned_at,
    t.started_at,
    d.droplet_id,
    d.name AS assigned_droplet_name,
    d.steward AS assigned_steward
FROM tasks t
LEFT JOIN droplets d ON t.assigned_droplet_id = d.id
WHERE t.status IN ('pending', 'assigned', 'in_progress')
ORDER BY t.priority ASC, t.created_at ASC;

-- Droplet health summary
CREATE OR REPLACE VIEW v_droplet_health AS
SELECT 
    d.droplet_id,
    d.name,
    d.steward,
    d.status,
    d.last_heartbeat,
    EXTRACT(EPOCH FROM (NOW() - d.last_heartbeat)) AS seconds_since_heartbeat,
    COUNT(t.id) FILTER (WHERE t.status IN ('assigned', 'in_progress')) AS active_tasks,
    COUNT(t.id) FILTER (WHERE t.status = 'completed') AS completed_tasks,
    COUNT(t.id) FILTER (WHERE t.status = 'failed') AS failed_tasks
FROM droplets d
LEFT JOIN tasks t ON t.assigned_droplet_id = d.id
GROUP BY d.id, d.droplet_id, d.name, d.steward, d.status, d.last_heartbeat
ORDER BY d.droplet_id;

-- Task performance metrics
CREATE OR REPLACE VIEW v_task_performance AS
SELECT 
    task_type,
    COUNT(*) AS total_count,
    COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed_count,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / 
        NULLIF(COUNT(*) FILTER (WHERE status IN ('completed', 'failed')), 0) * 100,
        2
    ) AS success_rate_percent,
    ROUND(
        AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) 
        FILTER (WHERE status = 'completed'),
        2
    ) AS avg_duration_seconds,
    ROUND(
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)))
        FILTER (WHERE status = 'completed'),
        2
    ) AS p50_duration_seconds,
    ROUND(
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)))
        FILTER (WHERE status = 'completed'),
        2
    ) AS p95_duration_seconds
FROM tasks
WHERE created_at > NOW() - INTERVAL '30 days'
GROUP BY task_type
ORDER BY total_count DESC;

-- ============================================================================
-- GRANTS: Ensure application user has necessary permissions
-- ============================================================================
-- Assuming application connects as user 'orchestrator_app'
-- Run these after creating the user:
-- CREATE USER orchestrator_app WITH PASSWORD 'secure_password';
-- GRANT CONNECT ON DATABASE orchestrator_db TO orchestrator_app;
-- GRANT USAGE ON SCHEMA public TO orchestrator_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO orchestrator_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO orchestrator_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO orchestrator_app;

-- ============================================================================
-- SCHEMA VERSION TRACKING
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_version (
    version VARCHAR(10) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES ('2.0.0', 'Initial Orchestrator v2 schema with full task management and health monitoring')
ON CONFLICT (version) DO NOTHING;