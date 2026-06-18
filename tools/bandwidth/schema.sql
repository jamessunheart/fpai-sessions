CREATE TABLE IF NOT EXISTS brain_index.routing_log (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    task_type TEXT NOT NULL,
    tier_used TEXT NOT NULL,
    tier_intended TEXT,
    outcome TEXT NOT NULL,
    tokens_loaded INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    session_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_routing_log_ts ON brain_index.routing_log (ts DESC);
CREATE INDEX IF NOT EXISTS idx_routing_log_task_type ON brain_index.routing_log (task_type);
CREATE INDEX IF NOT EXISTS idx_routing_log_tier_used ON brain_index.routing_log (tier_used);
