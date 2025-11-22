-- Migration 002: Tokenization System
-- Creates tables for strategy tokens, AI wallets, and portfolio management
-- Purpose: Enable tokenized AI agent strategies with AI wallet optimization

-- ============================================================================
-- MIGRATION TRACKING (Create first if doesn't exist)
-- ============================================================================

CREATE TABLE IF NOT EXISTS migration_history (
    version INTEGER PRIMARY KEY,
    description TEXT NOT NULL,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- STRATEGY TOKENS
-- ============================================================================

-- Strategy tokens represent ownership in backtested treasury strategies
CREATE TABLE IF NOT EXISTS strategy_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_symbol TEXT UNIQUE NOT NULL,           -- e.g., STRAT-AAVE-MOMENTUM-001
    strategy_id INTEGER NOT NULL,                 -- References agent in memory (future: foreign key)
    strategy_name TEXT NOT NULL,                  -- Human-readable name
    strategy_description TEXT,                    -- Strategy logic summary

    -- Token economics
    total_supply INTEGER NOT NULL,                -- Fixed at creation
    circulating_supply INTEGER NOT NULL,          -- Currently held by wallets
    reserved_supply INTEGER DEFAULT 0,            -- Team/insurance reserve

    -- Pricing and NAV
    current_nav REAL NOT NULL,                    -- Net Asset Value per token
    initial_nav REAL NOT NULL,                    -- NAV at token creation
    total_aum REAL NOT NULL DEFAULT 0.0,          -- Assets Under Management

    -- Lifecycle
    status TEXT NOT NULL CHECK(status IN ('proving', 'active', 'paused', 'retired')),
    creation_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tokenization_date TIMESTAMP,                  -- When moved from proving to active
    retirement_date TIMESTAMP,                    -- When strategy was retired

    -- Performance (cached for quick access)
    sharpe_ratio REAL,
    max_drawdown REAL,
    total_return_pct REAL,
    last_30d_return_pct REAL,
    last_7d_return_pct REAL,

    -- Metadata
    min_purchase REAL DEFAULT 1.0,                -- Minimum tokens per purchase
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_strategy_tokens_status ON strategy_tokens(status);
CREATE INDEX idx_strategy_tokens_symbol ON strategy_tokens(token_symbol);

-- ============================================================================
-- AI WALLETS
-- ============================================================================

-- AI wallets manage user capital with AI-powered allocation
CREATE TABLE IF NOT EXISTS ai_wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_address TEXT UNIQUE NOT NULL,          -- Unique identifier (UUID)

    -- User identification (church/trust)
    user_id TEXT NOT NULL,                        -- Church/trust identifier
    user_email TEXT,
    user_name TEXT,

    -- Wallet mode
    mode TEXT NOT NULL CHECK(mode IN ('full_ai', 'hybrid', 'manual')) DEFAULT 'hybrid',
    ai_optimizer_active BOOLEAN DEFAULT TRUE,

    -- Capital
    total_capital REAL NOT NULL,                  -- USD value of all holdings
    cash_balance REAL NOT NULL DEFAULT 0.0,       -- Uninvested cash
    invested_balance REAL NOT NULL DEFAULT 0.0,   -- Value of token holdings

    -- Performance tracking
    initial_capital REAL NOT NULL,                -- Starting capital (for returns calc)
    all_time_high REAL NOT NULL,                  -- Peak capital (for drawdown)
    total_return_pct REAL DEFAULT 0.0,
    sharpe_ratio REAL,
    max_drawdown REAL,

    -- Risk preferences
    risk_tolerance TEXT CHECK(risk_tolerance IN ('conservative', 'moderate', 'aggressive')) DEFAULT 'moderate',
    max_single_strategy_pct REAL DEFAULT 20.0,    -- Max % in any one strategy
    min_diversification INTEGER DEFAULT 5,         -- Minimum number of strategies

    -- Compliance
    church_verified BOOLEAN DEFAULT FALSE,
    attestation_signed BOOLEAN DEFAULT FALSE,
    attestation_date TIMESTAMP,

    -- Lifecycle
    status TEXT NOT NULL CHECK(status IN ('active', 'suspended', 'closed')) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_rebalance_at TIMESTAMP
);

CREATE INDEX idx_ai_wallets_user ON ai_wallets(user_id);
CREATE INDEX idx_ai_wallets_status ON ai_wallets(status);
CREATE INDEX idx_ai_wallets_mode ON ai_wallets(mode);

-- ============================================================================
-- TOKEN HOLDINGS
-- ============================================================================

-- Tracks which wallets own which tokens
CREATE TABLE IF NOT EXISTS token_holdings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id INTEGER NOT NULL REFERENCES ai_wallets(id) ON DELETE CASCADE,
    token_id INTEGER NOT NULL REFERENCES strategy_tokens(id),

    -- Position details
    quantity REAL NOT NULL,                       -- Number of tokens owned
    avg_cost_basis REAL NOT NULL,                 -- Average price paid per token
    current_value REAL NOT NULL,                  -- Current market value (quantity * NAV)
    unrealized_pnl REAL NOT NULL,                 -- Profit/loss (current - cost)
    unrealized_pnl_pct REAL NOT NULL,             -- % gain/loss

    -- Timing
    first_acquired_at TIMESTAMP NOT NULL,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure one row per wallet-token pair
    UNIQUE(wallet_id, token_id)
);

CREATE INDEX idx_token_holdings_wallet ON token_holdings(wallet_id);
CREATE INDEX idx_token_holdings_token ON token_holdings(token_id);

-- ============================================================================
-- ALLOCATION SNAPSHOTS
-- ============================================================================

-- Historical record of wallet allocations (for performance analysis)
CREATE TABLE IF NOT EXISTS allocation_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id INTEGER NOT NULL REFERENCES ai_wallets(id) ON DELETE CASCADE,
    snapshot_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Portfolio state
    total_value REAL NOT NULL,
    cash_balance REAL NOT NULL,
    invested_balance REAL NOT NULL,
    num_holdings INTEGER NOT NULL,

    -- Allocations (JSON: {token_id: {quantity, value, percent, nav}})
    allocations TEXT NOT NULL,                    -- JSON blob

    -- AI optimizer decision (if AI mode)
    optimizer_decision TEXT,                      -- JSON: {reasoning, changes, expected_sharpe}
    rebalance_executed BOOLEAN DEFAULT FALSE,

    -- Performance metrics at snapshot
    total_return_pct REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_allocation_snapshots_wallet ON allocation_snapshots(wallet_id);
CREATE INDEX idx_allocation_snapshots_date ON allocation_snapshots(snapshot_date);

-- ============================================================================
-- TRANSACTIONS
-- ============================================================================

-- Audit log of all token purchases and sales
CREATE TABLE IF NOT EXISTS token_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id INTEGER NOT NULL REFERENCES ai_wallets(id),
    token_id INTEGER NOT NULL REFERENCES strategy_tokens(id),

    -- Transaction details
    transaction_type TEXT NOT NULL CHECK(transaction_type IN ('buy', 'sell', 'mint', 'burn')),
    quantity REAL NOT NULL,
    price_per_token REAL NOT NULL,                -- NAV at time of transaction
    total_value REAL NOT NULL,                    -- quantity * price

    -- Fees
    platform_fee REAL DEFAULT 0.0,
    performance_fee REAL DEFAULT 0.0,

    -- Context
    triggered_by TEXT CHECK(triggered_by IN ('user', 'ai_optimizer', 'admin')),
    notes TEXT,

    -- Timing
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_token_transactions_wallet ON token_transactions(wallet_id);
CREATE INDEX idx_token_transactions_token ON token_transactions(token_id);
CREATE INDEX idx_token_transactions_date ON token_transactions(executed_at);

-- ============================================================================
-- AI OPTIMIZER DECISIONS
-- ============================================================================

-- Log of all AI optimizer recommendations and actions
CREATE TABLE IF NOT EXISTS ai_optimizer_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id INTEGER NOT NULL REFERENCES ai_wallets(id),

    -- Decision context
    decision_type TEXT NOT NULL CHECK(decision_type IN ('rebalance', 'enter', 'exit', 'increase', 'decrease')),
    current_allocation TEXT NOT NULL,             -- JSON: current state
    recommended_allocation TEXT NOT NULL,         -- JSON: recommended state

    -- Reasoning
    reasoning TEXT NOT NULL,                      -- AI explanation
    expected_sharpe_improvement REAL,
    expected_return_improvement REAL,
    risk_assessment TEXT,

    -- User response (if hybrid mode)
    user_approved BOOLEAN,
    user_approved_at TIMESTAMP,
    user_notes TEXT,

    -- Execution
    executed BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMP,
    actual_sharpe_change REAL,                    -- Measured after execution

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_optimizer_wallet ON ai_optimizer_decisions(wallet_id);
CREATE INDEX idx_ai_optimizer_executed ON ai_optimizer_decisions(executed);

-- ============================================================================
-- STRATEGY PERFORMANCE HISTORY
-- ============================================================================

-- Daily snapshots of strategy token performance
CREATE TABLE IF NOT EXISTS strategy_performance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id INTEGER NOT NULL REFERENCES strategy_tokens(id),
    snapshot_date DATE NOT NULL,

    -- Performance metrics
    nav REAL NOT NULL,
    aum REAL NOT NULL,
    daily_return_pct REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,

    -- Volume
    holders_count INTEGER DEFAULT 0,
    circulating_supply REAL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(token_id, snapshot_date)
);

CREATE INDEX idx_strategy_performance_token ON strategy_performance_history(token_id);
CREATE INDEX idx_strategy_performance_date ON strategy_performance_history(snapshot_date);

-- ============================================================================
-- COMPLIANCE ATTESTATIONS
-- ============================================================================

-- Records of user attestations for legal compliance
CREATE TABLE IF NOT EXISTS compliance_attestations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id INTEGER NOT NULL REFERENCES ai_wallets(id),

    -- Attestation type
    attestation_type TEXT NOT NULL CHECK(attestation_type IN ('church_status', 'risk_acknowledgment', 'terms_of_service')),

    -- Details
    attested_by TEXT NOT NULL,                    -- Name of attester
    attested_email TEXT,
    church_name TEXT,
    church_ein TEXT,                              -- Tax ID (optional)

    -- Legal text
    attestation_text TEXT NOT NULL,               -- Full legal text shown to user
    user_signature TEXT,                          -- Digital signature (optional)
    ip_address TEXT,

    -- Timing
    attested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,                         -- Annual renewal required

    -- Status
    status TEXT CHECK(status IN ('active', 'expired', 'revoked')) DEFAULT 'active'
);

CREATE INDEX idx_compliance_wallet ON compliance_attestations(wallet_id);
CREATE INDEX idx_compliance_type ON compliance_attestations(attestation_type);
CREATE INDEX idx_compliance_status ON compliance_attestations(status);

-- ============================================================================
-- VIEWS (for common queries)
-- ============================================================================

-- Active tokens with recent performance
CREATE VIEW IF NOT EXISTS active_tokens_view AS
SELECT
    st.id,
    st.token_symbol,
    st.strategy_name,
    st.current_nav,
    st.total_aum,
    st.sharpe_ratio,
    st.max_drawdown,
    st.total_return_pct,
    st.last_30d_return_pct,
    st.last_7d_return_pct,
    st.circulating_supply,
    COUNT(DISTINCT th.wallet_id) as holders_count
FROM strategy_tokens st
LEFT JOIN token_holdings th ON st.id = th.token_id
WHERE st.status = 'active'
GROUP BY st.id;

-- Wallet portfolio summary
CREATE VIEW IF NOT EXISTS wallet_portfolio_view AS
SELECT
    w.id as wallet_id,
    w.wallet_address,
    w.user_name,
    w.mode,
    w.total_capital,
    w.cash_balance,
    w.invested_balance,
    w.total_return_pct,
    w.sharpe_ratio,
    COUNT(th.id) as num_holdings,
    w.last_rebalance_at
FROM ai_wallets w
LEFT JOIN token_holdings th ON w.id = th.wallet_id
WHERE w.status = 'active'
GROUP BY w.id;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Version tracking
INSERT INTO migration_history (version, description, executed_at)
VALUES (2, 'Tokenization system: strategy tokens, AI wallets, allocations', CURRENT_TIMESTAMP)
ON CONFLICT(version) DO NOTHING;
