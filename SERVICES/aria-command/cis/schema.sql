-- Continuity Intelligence System (CIS) Schema
-- SQLite version (can be migrated to Supabase)

-- Users
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  external_id TEXT UNIQUE,
  name TEXT,
  timezone TEXT DEFAULT 'UTC',
  created_at TEXT DEFAULT (datetime('now')),
  settings TEXT DEFAULT '{}'
);

-- Current user state
CREATE TABLE IF NOT EXISTS user_state (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  state TEXT CHECK (state IN ('calm', 'busy', 'overloaded', 'stuck', 'open')),
  intensity INTEGER CHECK (intensity BETWEEN 1 AND 5),
  confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
  source TEXT CHECK (source IN ('explicit', 'inferred', 'default')),
  captured_at TEXT DEFAULT (datetime('now')),
  expires_at TEXT,
  inference_signals TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_user_state_user ON user_state(user_id);

-- State history
CREATE TABLE IF NOT EXISTS state_history (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  state TEXT,
  intensity INTEGER,
  confidence TEXT,
  source TEXT,
  captured_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_state_history_user ON state_history(user_id, captured_at DESC);

-- Actions library
CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,
  action_key TEXT UNIQUE NOT NULL,
  category TEXT CHECK (category IN ('stabilize', 'disrupt', 'execute', 'coordinate')),
  name TEXT NOT NULL,
  description TEXT,
  instruction TEXT NOT NULL,
  duration_seconds INTEGER DEFAULT 30,
  reversible INTEGER DEFAULT 1,
  requires_permission INTEGER DEFAULT 0,
  rate_limit_per_hour INTEGER DEFAULT 2,
  effective_states TEXT DEFAULT '["busy", "overloaded", "stuck"]',
  min_intensity INTEGER DEFAULT 1,
  max_intensity INTEGER DEFAULT 5,
  active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Action weights (learning)
CREATE TABLE IF NOT EXISTS action_weights (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  action_id TEXT REFERENCES actions(id),
  state TEXT NOT NULL,
  trials INTEGER DEFAULT 0,
  successes INTEGER DEFAULT 0,
  avg_delta REAL DEFAULT 0.0,
  last_used TEXT,
  last_outcome TEXT,
  weight REAL DEFAULT 1.0,
  UNIQUE(user_id, action_id, state)
);

CREATE INDEX IF NOT EXISTS idx_action_weights ON action_weights(user_id, state);

-- Interventions log
CREATE TABLE IF NOT EXISTS interventions (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  action_id TEXT REFERENCES actions(id),
  trigger_type TEXT CHECK (trigger_type IN ('spike', 'stuck', 'risk', 'silence_drift', 'scheduled')),
  state_at_trigger TEXT,
  intensity_at_trigger INTEGER,
  confidence_at_trigger TEXT,
  decision_type TEXT CHECK (decision_type IN ('stabilize', 'disrupt', 'pause', 'execute', 'ask', 'silence')),
  decision_confidence REAL,
  channel TEXT CHECK (channel IN ('sms', 'slack', 'push', 'telegram', 'silent')),
  message_sent TEXT,
  delivered_at TEXT DEFAULT (datetime('now')),
  outcome TEXT CHECK (outcome IN ('helped', 'same', 'no', 'pending', 'no_response')),
  outcome_at TEXT,
  intensity_after INTEGER,
  suppressed INTEGER DEFAULT 0,
  suppression_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_interventions_user ON interventions(user_id, delivered_at DESC);

-- Delivery log (rate limiting)
CREATE TABLE IF NOT EXISTS delivery_log (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  channel TEXT,
  message_type TEXT CHECK (message_type IN ('ping', 'status_mirror', 'silent', 'outcome_request')),
  delivered_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_delivery_log ON delivery_log(user_id, channel, delivered_at DESC);

-- Fuses (guardrails)
CREATE TABLE IF NOT EXISTS fuses (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  fuse_type TEXT NOT NULL,
  triggered_at TEXT DEFAULT (datetime('now')),
  expires_at TEXT,
  reason TEXT,
  active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_fuses ON fuses(user_id, active);

-- User channels
CREATE TABLE IF NOT EXISTS user_channels (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  channel TEXT CHECK (channel IN ('sms', 'slack', 'push', 'telegram')),
  channel_address TEXT NOT NULL,
  priority INTEGER DEFAULT 1,
  active INTEGER DEFAULT 1,
  verified INTEGER DEFAULT 0,
  UNIQUE(user_id, channel)
);

-- ============================================================================
-- CONTINUITY LEDGER ENHANCEMENTS
-- ============================================================================

-- Open threads (things in progress)
CREATE TABLE IF NOT EXISTS open_threads (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  description TEXT NOT NULL,
  domain TEXT CHECK (domain IN ('trading', 'building', 'personal', 'system', 'other')),
  opened_at TEXT DEFAULT (datetime('now')),
  last_mentioned TEXT DEFAULT (datetime('now')),
  status TEXT CHECK (status IN ('active', 'dormant', 'resolved')) DEFAULT 'active',
  mentions INTEGER DEFAULT 1,
  resolved_at TEXT,
  resolution TEXT
);

CREATE INDEX IF NOT EXISTS idx_open_threads ON open_threads(user_id, status);

-- Inferred states (from sensors, not explicit)
CREATE TABLE IF NOT EXISTS inferred_states (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  state TEXT CHECK (state IN ('calm', 'busy', 'overloaded', 'stuck', 'open')),
  intensity INTEGER CHECK (intensity BETWEEN 1 AND 5),
  confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
  source TEXT CHECK (source IN ('trading', 'message', 'silence', 'external', 'aggregated')),
  signals TEXT DEFAULT '{}',
  inferred_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_inferred_states ON inferred_states(user_id, inferred_at DESC);

-- Message log (for pattern sensing)
CREATE TABLE IF NOT EXISTS message_log (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  content TEXT,
  direction TEXT CHECK (direction IN ('inbound', 'outbound')),
  word_count INTEGER,
  tone_signals TEXT DEFAULT '{}',
  response_time_seconds INTEGER,
  timestamp TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_message_log ON message_log(user_id, timestamp DESC);

-- Recovery patterns (how long to return to calm after strain)
CREATE TABLE IF NOT EXISTS recovery_patterns (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  from_state TEXT,
  from_intensity INTEGER,
  to_state TEXT,
  to_intensity INTEGER,
  duration_hours REAL,
  recorded_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_recovery ON recovery_patterns(user_id, recorded_at DESC);

