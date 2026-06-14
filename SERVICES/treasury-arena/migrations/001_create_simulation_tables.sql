-- Simulation Engine Database Schema
-- Created: 2025-11-16
-- Purpose: Store historical market data cache and simulation results

-- Table: market_data
-- Historical price data for assets (BTC, SOL, etc.)
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset TEXT NOT NULL,
    date DATE NOT NULL,
    price_usd REAL NOT NULL,
    volume_24h REAL,
    market_cap REAL,
    mvrv REAL,  -- For BTC only
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(asset, date)
);

CREATE INDEX IF NOT EXISTS idx_market_data_asset_date ON market_data(asset, date);

-- Table: protocol_data
-- Historical APY data for DeFi protocols (Aave, Pendle, Curve, etc.)
CREATE TABLE IF NOT EXISTS protocol_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol TEXT NOT NULL,
    date DATE NOT NULL,
    apy REAL NOT NULL,
    tvl REAL,
    volume_24h REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(protocol, date)
);

CREATE INDEX IF NOT EXISTS idx_protocol_data_protocol_date ON protocol_data(protocol, date);

-- Table: simulation_runs
-- Metadata for each complete simulation run
CREATE TABLE IF NOT EXISTS simulation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_agents INTEGER NOT NULL,
    final_agents INTEGER NOT NULL,
    total_spawned INTEGER NOT NULL,
    total_killed INTEGER NOT NULL,
    initial_capital REAL NOT NULL,
    final_capital REAL NOT NULL,
    total_return REAL NOT NULL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    config TEXT,  -- JSON config as TEXT for SQLite compatibility
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Table: simulation_snapshots
-- Daily snapshots of agent state during simulation
CREATE TABLE IF NOT EXISTS simulation_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    date DATE NOT NULL,
    agent_id TEXT NOT NULL,
    virtual_capital REAL NOT NULL,
    fitness_score REAL,
    sharpe_ratio REAL,
    status TEXT,
    tier TEXT,
    FOREIGN KEY (run_id) REFERENCES simulation_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_run_date ON simulation_snapshots(run_id, date);
CREATE INDEX IF NOT EXISTS idx_snapshots_run_agent ON simulation_snapshots(run_id, agent_id);
