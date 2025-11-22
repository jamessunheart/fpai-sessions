# DROPLET #25 SPECIFICATION
**Treasury Magnet - Survival-First Trading System**
**Version:** 1.0
**Generated:** November 19, 2025

---

## 1. 🎯 PURPOSE

**What It Does:**
Autonomous trading system managing $430K capital through magnet-aware leverage formula: L = (D × S) / (1 + C + V). Protects capital survival (target <5% liquidation) while scaling intelligently with market opportunity.

**TIER 1 IMPACT:**
Generates passive treasury yield through algorithmic trading. Removes manual trading bottleneck. Proves AI can manage real capital safely. Enables treasury optimization at scale ($410K → automated growth).

**Problem Solved:**
Traditional trading = 80% liquidation rate. Manual oversight bottleneck. No systematic survival protocol. This droplet makes treasury self-managing with survival-first mathematics.

---

## 2. 📋 CORE REQUIREMENTS

**Trading Engine:**
1. As Treasury Manager, system must calculate dynamic leverage (1.0-3.0x) using magnet formula, so that positions scale with opportunity while maintaining survival
2. As Risk Guardian, system must enforce survival fuse (circuit breaker at -2.5% daily loss), so that capital never faces catastrophic drawdown
3. As Position Manager, system must size positions by magnet tier (Tier 1: 5%, Tier 2: 3%, Tier 3: 1%), so that risk matches setup quality

**Monitoring & Control:**
4. As Coordinator, I must monitor real-time system health via UDC endpoints, so that trading status is visible in Dashboard (#2)
5. As Safety Officer, I must receive emergency alerts when survival fuse triggers, so that I can intervene if system halts

**Investor Interface:**
6. As Investor, I must view live performance metrics (equity, returns, drawdown), so that I can track fund performance
7. As Investor, I must see recent trades with entry/exit/PnL, so that I can understand trading decisions
8. As Investor, I must see current system state (leverage, fuse status, open positions), so that I can assess risk exposure

**Integration:**
9. As System Component, droplet must register with Registry (#1) and report heartbeat to Orchestrator (#10), so that it's discoverable and monitored
10. As Data Provider, droplet must push metrics to Dashboard (#2) every 60s, so that trading activity is visible system-wide

---

## 3. 🎨 USER INTERFACE

**COORDINATOR VIEW (Dashboard #2 Widget):**
```
┌─────────────────────────────────────────────┐
│ Treasury Magnet - Droplet #25               │
├─────────────────────────────────────────────┤
│ Status: 🟢 ACTIVE                          │
│ Equity: $437,240 (+1.68%)                  │
│ Leverage: 1.8x                              │
│ Fuse: ARMED (-0.4% today)                  │
│ Open Positions: 2                           │
│                                             │
│ Last Trade: BTC Long +$240 (5min ago)      │
│ [View Details] [Emergency Stop]            │
└─────────────────────────────────────────────┘
```

**INVESTOR PORTAL (Public Web Interface):**

**Landing Page:**
```
MAGNET-AWARE TRADING FUND
Algorithmic Trading with Survival Mathematics

Current Performance:
━━━━━━━━━━━━━━━━━━━━━━━━
Equity:      $437,240
Return:      +1.68% (30 days)
Max DD:      -1.2%
Sharpe:      2.4
━━━━━━━━━━━━━━━━━━━━━━━━

[Live Equity Curve Chart]

Recent Trades:
BTC Long  | +$240  | 2.1x leverage
ETH Short | +$180  | 1.8x leverage
SOL Long  | -$80   | 1.5x leverage

[Join Fund] [View Performance]
```

**Dashboard Page (Authenticated Investors):**
```
MY PORTFOLIO
━━━━━━━━━━━━━━━━━━━━━━━━
My Share:        2.5% ($10,931)
My Returns:      +$431 (+4.1%)
Investment Date: Oct 15, 2025
━━━━━━━━━━━━━━━━━━━━━━━━

SYSTEM STATUS
Leverage:   1.8x
Fuse State: ARMED
Open Pos:   2 (BTC, ETH)

PERFORMANCE CHART
[Personal equity curve since investment]

MY TRADE HISTORY
[Filtered to participation period]

[Request Withdrawal] [Deposit More]
```

---

## 4. 🔌 INTEGRATIONS

**INTERNAL INTEGRATIONS (Required):**
- **Registry (#1)**: JWT authentication, droplet registration on startup, public key retrieval
- **Orchestrator (#10)**: State reporting every 60s, task coordination, emergency stop commands
- **Dashboard (#2)**: Real-time metrics push (equity, leverage, fuse state, position count)

**INTERNAL INTEGRATIONS (Optional):**
- **Nexus (#13)**: AI-assisted trade analysis, pattern recognition insights
- **Memory (#9)**: Store historical trade decisions for learning/optimization

**EXTERNAL INTEGRATIONS (Required):**
- **Binance API**: Live market data (WebSocket), order execution, position management, account state
- **PostgreSQL Database**: Trade history, performance metrics, investor records, system state persistence

**EXTERNAL INTEGRATIONS (Optional):**
- **SendGrid/Email**: Investor notifications, emergency alerts, daily reports
- **Telegram Bot**: Real-time alerts for coordinators

---

## 5. 🔧 TECHNICAL STACK

**DEFAULT STACK:**
- Backend: FastAPI (Python 3.11+)
- Database: PostgreSQL 15+
- Container: Docker + docker-compose
- Auth: JWT from Registry (#1)

**ADDITIONAL REQUIREMENTS:**
- **Redis**: Real-time market data caching, WebSocket state management
- **Celery**: Background tasks (position monitoring, fuse checking, heartbeat)
- **WebSocket**: Live market data streaming from Binance
- **ccxt Library**: Exchange abstraction layer for Binance API
- **NumPy/Pandas**: Numerical calculations for leverage formula, performance metrics
- **React 18 + Vite**: Investor portal frontend
- **Recharts**: Interactive equity curves and performance charts
- **Tailwind CSS**: Investor portal styling

**PERFORMANCE REQUIREMENTS:**
- Health check: <100ms response
- Leverage calculation: <50ms
- Position sizing: <100ms
- Trade execution: <500ms end-to-end
- Database queries: <200ms

**DATABASE BACKUP STRATEGY:**
- **Frequency**: Automated daily backups at 00:00 UTC
- **Method**: PostgreSQL pg_dump with compression
- **Storage**: AWS S3 bucket with versioning enabled
- **Retention**: 
  - Daily backups: 30 days
  - Weekly backups: 12 weeks
  - Monthly backups: 12 months
- **Recovery Testing**: Monthly restore validation to staging environment
- **Critical Data**: 
  - All investor records (mandatory retention)
  - Trade history (7 years for compliance)
  - Account snapshots (1 year minimum)
- **Backup Script**: Included in deployment/backup.sh
- **Monitoring**: Alert if backup fails or exceeds 2 hours
- **Encryption**: AES-256 encryption at rest and in transit

**Backup Verification Checklist:**
- [ ] Daily backup completes successfully
- [ ] Backup file uploaded to S3
- [ ] Backup size reasonable (not corrupted)
- [ ] Monthly restore test passes
- [ ] Encryption verified on stored backups

---

## 6. 📊 DATABASE SCHEMA

```sql
-- Core trading tables
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL,  -- 'long' or 'short'
    size_usd DECIMAL(12,2) NOT NULL,
    leverage DECIMAL(4,2) NOT NULL,
    entry_price DECIMAL(15,8) NOT NULL,
    stop_price DECIMAL(15,8),
    target_price DECIMAL(15,8),
    magnet_tier INTEGER CHECK (magnet_tier BETWEEN 1 AND 4),
    opened_at TIMESTAMP NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP,
    pnl DECIMAL(12,2),
    pnl_percent DECIMAL(8,4),
    closure_reason VARCHAR(50),  -- 'target', 'stop', 'manual', 'fuse'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_opened ON positions(opened_at);
CREATE INDEX idx_positions_status ON positions(closed_at) WHERE closed_at IS NULL;

-- Account state snapshots
CREATE TABLE account_snapshots (
    id SERIAL PRIMARY KEY,
    equity DECIMAL(12,2) NOT NULL,
    available_margin DECIMAL(12,2) NOT NULL,
    open_positions_value DECIMAL(12,2) NOT NULL,
    unrealized_pnl DECIMAL(12,2) NOT NULL,
    daily_pnl DECIMAL(12,2) NOT NULL,
    leverage_used DECIMAL(4,2) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_snapshots_timestamp ON account_snapshots(timestamp DESC);

-- Magnet detections
CREATE TABLE magnet_detections (
    id SERIAL PRIMARY KEY,
    level DECIMAL(15,8) NOT NULL,
    magnet_type VARCHAR(20) NOT NULL,  -- 'structural', 'liquidity', etc.
    strength DECIMAL(5,2) NOT NULL,
    conflict DECIMAL(5,2) NOT NULL,
    distance_atr DECIMAL(5,2) NOT NULL,
    volatility_pressure DECIMAL(5,2) NOT NULL,
    tier INTEGER NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_magnets_detected ON magnet_detections(detected_at DESC);
CREATE INDEX idx_magnets_tier ON magnet_detections(tier);

-- Survival fuse events
CREATE TABLE fuse_events (
    id SERIAL PRIMARY KEY,
    trigger_type VARCHAR(30) NOT NULL,  -- 'daily_loss', 'position_risk', etc.
    severity VARCHAR(20) NOT NULL,  -- 'WARNING', 'CRITICAL', 'EMERGENCY'
    daily_loss_percent DECIMAL(5,2),
    action_taken VARCHAR(100),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fuse_timestamp ON fuse_events(timestamp DESC);

-- Investor accounts
CREATE TABLE investors (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    share_percent DECIMAL(5,4) NOT NULL,  -- 2.5000% = 0.0250
    initial_investment DECIMAL(12,2) NOT NULL,
    investment_date DATE NOT NULL,
    kyc_verified BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'active',  -- 'active', 'pending', 'withdrawn'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Investor performance tracking
CREATE TABLE investor_snapshots (
    id SERIAL PRIMARY KEY,
    investor_id INTEGER REFERENCES investors(id),
    equity_value DECIMAL(12,2) NOT NULL,
    total_return DECIMAL(12,2) NOT NULL,
    return_percent DECIMAL(8,4) NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_investor_snapshots ON investor_snapshots(investor_id, timestamp DESC);

-- System configuration
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Idempotency tracking (prevents duplicate trade orders)
CREATE TABLE idempotency_keys (
    key VARCHAR(255) PRIMARY KEY,
    response_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX idx_idempotency_expires ON idempotency_keys(expires_at);

-- Initial config values
INSERT INTO system_config (key, value) VALUES
    ('initial_equity', '430000.00'),
    ('trading_mode', 'paper_trade'),
    ('fuse_armed', 'true'),
    ('max_leverage', '3.0');
```

---

## 7. 🎯 API ENDPOINTS

**REQUIRED UDC ENDPOINTS:**

```
GET /health
Response: {
  "id": 25,
  "name": "Treasury Magnet",
  "steward": "James",
  "status": "active|inactive|error",
  "endpoint": "https://magnet.fullpotential.ai",
  "proof": "sha256_of_last_trade",
  "cost_usd": 15.00,  // Monthly infrastructure
  "yield_usd": 1240.00,  // Monthly gains
  "updated_at": "2025-11-19T12:00:00Z"
}

GET /capabilities
Response: {
  "version": "1.1.0",
  "features": [
    "algorithmic_trading",
    "survival_fuse",
    "magnet_detection",
    "position_sizing",
    "investor_portal",
    "real_time_metrics"
  ],
  "dependencies": ["registry", "orchestrator", "dashboard"],
  "udc_version": "1.0",
  "metadata": {
    "formula": "L = (D × S) / (1 + C + V)",
    "max_leverage": "3.0x",
    "fuse_threshold": "-2.5%"
  }
}

GET /state
Response: {
  "cpu_percent": 12.4,
  "memory_mb": 842,
  "uptime_seconds": 432000,
  "requests_total": 8234,
  "requests_per_minute": 18,
  "errors_last_hour": 0,
  "last_restart": "2025-11-15T08:00:00Z",
  "websocket_connections": 2,
  "active_workers": 4
}

GET /dependencies
Response: {
  "required": [
    {"id": 1, "name": "Registry", "status": "connected"},
    {"id": 10, "name": "Orchestrator", "status": "connected"},
    {"service": "binance_api", "status": "connected"},
    {"service": "postgresql", "status": "connected"}
  ],
  "optional": [
    {"id": 2, "name": "Dashboard", "status": "connected"},
    {"service": "redis", "status": "connected"}
  ],
  "missing": []
}

POST /message
Body: UDC standard message format
Auth: JWT required
Purpose: Receive commands from Orchestrator (emergency_stop, adjust_leverage, etc.)
```

**TRADING SYSTEM ENDPOINTS:**

```
POST /api/trade/execute
Body: {
  "idempotency_key": "uuid-v4",  // Required - prevents duplicate orders
  "symbol": "BTCUSDT",
  "direction": "long",
  "magnet_tier": 1,
  "entry_price": 43500.00,
  "stop_price": 42800.00,
  "target_price": 44200.00
}
Response: {
  "order_id": "abc123",
  "status": "filled",
  "executed_price": 43500.00,
  "position_id": 456
}
Auth: JWT required (coordinator)
Note: Duplicate idempotency_key within 24hrs returns original response (no new order)

GET /api/performance/current
Response: {
  "equity": 437240.00,
  "daily_pnl": -1240.00,
  "daily_pnl_percent": -0.28,
  "return_30d": 1.68,
  "max_drawdown": -1.2,
  "sharpe_ratio": 2.4,
  "open_positions": 2,
  "leverage_used": 1.8,
  "fuse_status": "armed"
}
Auth: Public (rate-limited: 100 requests/minute per IP)

GET /api/performance/history
Query: ?period=30d&interval=1h
Response: Array of historical snapshots
Auth: Public (rate-limited: 100 requests/minute per IP)

GET /api/trades/recent
Query: ?limit=20
Response: Array of recent trades with entry/exit/PnL
Auth: Public (rate-limited: 100 requests/minute per IP)

GET /api/positions/open
Response: Array of currently open positions
Auth: JWT required (coordinator, rate-limited: 1000 requests/minute)

POST /api/system/emergency-stop
Body: {"reason": "manual_intervention"}
Response: {"stopped": true, "positions_closed": 2}
Auth: JWT required (coordinator role, rate-limited: 10 requests/minute)

POST /api/leverage/calculate
Body: {
  "primary_magnet_price": 43500.00,
  "current_price": 43200.00,
  "magnet_strength": 85.0,
  "conflict_index": 0.2,
  "volatility_pressure": 0.8,
  "atr": 450.0
}
Response: {
  "leverage": 2.1,
  "components": {"distance": 0.67, "strength": 0.85, "conflict": 0.2, "volatility": 0.8},
  "is_high_tension": false,
  "reasoning": "Strong magnet | Normal conditions"
}
Auth: JWT required (rate-limited: 1000 requests/minute)

GET /api/fuse/status
Response: {
  "armed": true,
  "daily_loss": -0.28,
  "threshold": -2.5,
  "distance_to_trigger": 2.22,
  "last_warning": null
}
Auth: JWT required (rate-limited: 1000 requests/minute)
```

**INVESTOR PORTAL ENDPOINTS:**

```
POST /api/investor/register
Body: {
  "email": "investor@example.com",
  "name": "John Doe",
  "initial_investment": 10000.00,
  "kyc_documents": ["url1", "url2"]
}
Response: {"investor_id": 123, "status": "pending_verification"}
Auth: Public (creates pending account)

POST /api/investor/login
Body: {"email": "...", "password": "..."}
Response: {"token": "jwt_token", "investor_id": 123}
Auth: Public

GET /api/investor/dashboard
Response: {
  "share_percent": 2.5,
  "equity_value": 10931.00,
  "total_return": 431.00,
  "return_percent": 4.1,
  "investment_date": "2025-10-15",
  "current_system_state": {...}
}
Auth: JWT required (investor token)

GET /api/investor/performance
Query: ?since=2025-10-15
Response: Array of personal equity snapshots
Auth: JWT required (investor token)

POST /api/investor/withdraw
Body: {"amount": 5000.00, "reason": "partial_exit"}
Response: {"request_id": 456, "status": "pending_approval"}
Auth: JWT required (investor token)
```

---

## 8. ✅ SUCCESS CRITERIA

**FUNCTIONAL REQUIREMENTS:**

Trading Engine:
- [ ] Leverage calculation implements formula L = (D × S) / (1 + C + V) with 1.0-3.0x bounds
- [ ] High-tension override works (C+V < 0.15, S >= 60) → leverage × 1.2, max 3.0x
- [ ] Survival fuse triggers at -2.5% daily loss and closes all positions
- [ ] Position sizing follows tier rules: Tier 1 = 5%, Tier 2 = 3%, Tier 3 = 1%, Tier 4 = 0%
- [ ] System can open positions via Binance API in paper trading mode
- [ ] System closes positions when target/stop hit or fuse triggers

Monitoring:
- [ ] Account snapshots recorded every 5 minutes to database
- [ ] Heartbeat sent to Orchestrator (#10) every 60 seconds
- [ ] Metrics pushed to Dashboard (#2) every 60 seconds
- [ ] Fuse events logged with severity and action taken

Investor Portal:
- [ ] Landing page displays live equity, returns, max drawdown, recent trades
- [ ] Authenticated investors can view personal dashboard with share % and returns
- [ ] Performance charts render correctly with Recharts
- [ ] Registration flow works (pending → KYC → active)

**TECHNICAL REQUIREMENTS:**

UDC Compliance:
- [ ] All UDC endpoints implemented (/health, /capabilities, /state, /dependencies, /message)
- [ ] Health endpoint returns exactly "active", "inactive", or "error" status
- [ ] JWT authentication working on all protected endpoints
- [ ] Registers with Registry (#1) on startup with correct droplet ID (25)
- [ ] Responds to UDC messages from Orchestrator (emergency_stop command)

Code Quality:
- [ ] All Python code follows black formatting
- [ ] Type hints present on all functions
- [ ] No hardcoded secrets - all config via environment variables
- [ ] Structured logging (JSON format) includes trace_id for all requests
- [ ] Tests passing with >80% coverage on leverage_engine, survival_fuse, position_sizing

Integration:
- [ ] Successfully connects to Binance API (testnet for development)
- [ ] PostgreSQL database migrations run without errors
- [ ] Redis caching works for market data
- [ ] Celery workers process background tasks (heartbeat, position monitoring)
- [ ] WebSocket maintains stable connection to Binance for live data

Deployment:
- [ ] Docker container builds without errors
- [ ] docker-compose starts all services (backend, db, redis, frontend)
- [ ] deploy.sh script completes successfully
- [ ] backup.sh script runs and uploads to S3
- [ ] Frontend accessible at http://localhost:3000
- [ ] Backend API accessible at http://localhost:8000
- [ ] Health check returns 200 OK after deployment
- [ ] Daily backup cron job configured
- [ ] Backup restore tested successfully

Performance:
- [ ] /health responds in <100ms
- [ ] Leverage calculation completes in <50ms
- [ ] Position sizing completes in <100ms
- [ ] Database queries complete in <200ms
- [ ] No memory leaks during 24hr stress test

Security:
- [ ] No API keys in code or git history
- [ ] JWT tokens expire after 24 hours
- [ ] Investor passwords hashed with bcrypt
- [ ] SQL queries parameterized (no injection risk)
- [ ] CORS configured for specific frontend origin only

**INTEGRATION REQUIREMENTS:**

- [ ] Registry (#1): Successful registration on startup, JWT validation working
- [ ] Orchestrator (#10): Heartbeat acknowledged, emergency_stop command works
- [ ] Dashboard (#2): Metrics visible in real-time widget
- [ ] Binance API: Can fetch market data, place orders (testnet), check account state
- [ ] PostgreSQL: All tables created, migrations applied, queries working
- [ ] Redis: Market data cached, WebSocket state persisted

---

## 9. 🚀 APPRENTICE EXECUTION PROMPTS

### PROMPT A - BUILDER (For Claude)

```
I need to build Droplet #25: Treasury Magnet - a survival-first algorithmic trading system.

UPLOADED CONTEXT FILES:
- SPEC_Droplet_25_Treasury_Magnet.md (this specification)
- UDC_COMPLIANCE.md (Universal Droplet Contract standards)
- TECH_STACK.md (Full Potential AI technology standards)
- SECURITY_REQUIREMENTS.md (Security best practices)
- CODE_STANDARDS.md (Python coding standards)
- INTEGRATION_GUIDE.md (How to connect with other droplets)

ADDITIONAL CONTEXT:
I've also uploaded the original blueprint: COMPLETE_SYSTEM_BLUEPRINT.md
This contains COMPLETE v1.1 Python code for:
- core/data_models.py (Magnet, MarketState, Position, AccountState classes)
- core/leverage_engine.py (Leverage calculation: L = (D × S) / (1 + C + V))
- core/survival_fuse.py (Circuit breaker at -2.5% daily loss)
- core/position_sizing.py (Tier-based sizing: Tier 1=5%, Tier 2=3%, Tier 3=1%)
- backtest/backtest_harness.py (Historical testing framework)

YOUR TASK:

Generate a COMPLETE, production-ready implementation with these components:

1. BACKEND (FastAPI + Python 3.11):
   - Copy v1.1 code from blueprint EXACTLY (data_models, leverage_engine, survival_fuse, position_sizing, backtest_harness)
   - Add UDC-compliant endpoints (/health, /capabilities, /state, /dependencies, /message)
   - Add trading system endpoints (performance, trades, positions, leverage calc, fuse status)
   - Add investor portal endpoints (register, login, dashboard, performance, withdraw)
   - Implement rate limiting using SlowAPI (100/min public, 1000/min authenticated, 10/min emergency-stop)
   - Implement idempotency for trade execution (uuid key, 24hr cache, returns cached response on duplicate)
   - Implement Binance API integration (WebSocket for live data, REST for trading)
   - Implement PostgreSQL database layer with all tables from spec
   - Implement Celery background workers (heartbeat, position monitoring, account snapshots)
   - Implement JWT authentication (verify with Registry public key)

2. DATABASE:
   - Alembic migrations for all tables in spec
   - Seed data for initial config

3. FRONTEND (React 18 + Vite + Tailwind):
   - Landing page (hero, live equity chart, recent trades, investment tiers)
   - Investor dashboard (portfolio overview, personal chart, system status, trade history)
   - Join fund page (multi-step form with KYC upload)
   - Shared components (PerformanceChart, PortfolioOverview, SystemStatus, RecentTrades)

4. CONFIGURATION:
   - config.yaml (system settings, leverage bounds, fuse thresholds)
   - requirements.txt (all Python dependencies)
   - .env.example (template for secrets)
   - package.json (frontend dependencies)

5. DEPLOYMENT:
   - Dockerfile (Python 3.11-slim, non-root user)
   - docker-compose.yml (backend, postgres, redis services)
   - nginx.conf (reverse proxy config)
   - deploy.sh (one-command deployment script)
   - backup.sh (PostgreSQL backup to S3 with retention policy)
   - restore.sh (restore from S3 backup for disaster recovery)

6. TESTS:
   - test_leverage.py (test leverage calculation formula)
   - test_fuse.py (test survival fuse triggers)
   - test_sizing.py (test position sizing by tier)
   - test_udc.py (test all UDC endpoints)

CRITICAL REQUIREMENTS:

1. UDC COMPLIANCE:
   - Status MUST be exactly "active", "inactive", or "error" (lowercase)
   - /health must respond in <100ms
   - Register with Registry (#1) on startup using droplet_id=25
   - Send heartbeat to Orchestrator (#10) every 60 seconds
   - Push metrics to Dashboard (#2) every 60 seconds

2. SECURITY:
   - NO hardcoded secrets anywhere
   - JWT verification using Registry public key (RS256)
   - All database queries parameterized (SQL injection prevention)
   - Investor passwords hashed with bcrypt
   - CORS restricted to specific frontend origin

3. CODE QUALITY:
   - Black formatting applied
   - Type hints on ALL functions
   - Structured logging (JSON format) with trace_id
   - No print() statements - use log.info/error/warning
   - No TODO or FIXME in code

4. FILE STRUCTURE:
Create exactly this structure:
```
magnet-trading-system/
├── backend/
│   ├── core/ (v1.1 code files)
│   ├── backtest/ (backtest_harness.py)
│   ├── api/ (FastAPI endpoints)
│   ├── database/ (models, migrations)
│   ├── config.yaml
│   ├── requirements.txt
│   ├── .env.example
│   └── main.py
├── frontend/ (React app)
├── deployment/ (Docker configs)
├── tests/
└── README.md
```

5. OUTPUT FORMAT:
Provide each file as a separate code block with:
- Full file path as comment at top
- Complete code (no placeholders, no TODOs)
- Brief description of file purpose

BEGIN IMPLEMENTATION NOW.

Start with:
1. Backend core files (copy v1.1 code from blueprint)
2. UDC-compliant API layer
3. Database schema and migrations
4. Frontend React components
5. Configuration files
6. Deployment configs
7. Tests
```

### PROMPT B - VERIFIER (For Gemini)

```
I need you to verify AI-generated code for Droplet #25: Treasury Magnet trading system.

UPLOADED CONTEXT:
- SPEC_Droplet_25_Treasury_Magnet.md (complete specification)
- Generated code archive (all files from Builder AI)

YOUR VERIFICATION TASK:

Check the generated code against this EXACT checklist. Mark each item as:
- ✅ PASS (requirement fully met)
- ⚠️ PARTIAL (mostly works but has issues)
- ❌ FAIL (requirement not met or broken)

For each item, provide SPECIFIC EVIDENCE from the code.

═══════════════════════════════════════════════════
PART 1: UDC COMPLIANCE (CRITICAL - MUST BE PERFECT)
═══════════════════════════════════════════════════

UDC Endpoints:
[ ] GET /health returns correct JSON schema (id, name, steward, status, endpoint, updated_at)
[ ] Status uses EXACTLY "active", "inactive", or "error" (lowercase, no other values)
[ ] GET /capabilities lists all features from spec
[ ] GET /state reports cpu_percent, memory_mb, uptime_seconds
[ ] GET /dependencies lists Registry (#1), Orchestrator (#10), Binance, PostgreSQL
[ ] POST /message accepts UDC message format with JWT authentication

Integration:
[ ] Registers with Registry (#1) on startup with droplet_id=25
[ ] Sends heartbeat to Orchestrator (#10) every 60 seconds
[ ] Pushes metrics to Dashboard (#2) every 60 seconds
[ ] Code handles UDC emergency_stop command from Orchestrator

═══════════════════════════════════════════════════
PART 2: TRADING LOGIC (CRITICAL - MUST BE CORRECT)
═══════════════════════════════════════════════════

Leverage Engine:
[ ] Formula implemented: L = (D × S) / (1 + C + V)
[ ] Distance calculated: D = |Current - Magnet| / ATR
[ ] Strength normalized: S = strength / 100.0
[ ] Leverage bounded: 1.0 <= L <= 2.5 (or 3.0 with high-tension)
[ ] High-tension override works: if C+V < 0.15 and S >= 60, then L × 1.2, max 3.0
[ ] Returns dict with leverage, components, raw_leverage, is_high_tension, reasoning

Survival Fuse:
[ ] Triggers at -2.5% daily loss
[ ] Closes all open positions when triggered
[ ] Logs event with severity and action taken
[ ] Can be manually armed/disarmed
[ ] Prevents new positions while disarmed

Position Sizing:
[ ] Tier 1 magnets: 5% of equity per position
[ ] Tier 2 magnets: 3% of equity per position
[ ] Tier 3 magnets: 1% of equity per position
[ ] Tier 4 magnets: 0% (no positions)
[ ] Accounts for current leverage when sizing

═══════════════════════════════════════════════════
PART 3: SECURITY (CRITICAL - NO COMPROMISES)
═══════════════════════════════════════════════════

Secrets Management:
[ ] NO hardcoded API keys anywhere in code
[ ] NO hardcoded passwords anywhere in code
[ ] NO hardcoded JWT secrets
[ ] All secrets loaded from environment variables
[ ] .env.example provided as template (no actual secrets)

Authentication:
[ ] JWT verification uses RS256 algorithm (not HS256)
[ ] JWT verified against Registry public key
[ ] JWT expiration checked (verify_exp: True)
[ ] Investor passwords hashed with bcrypt (NOT plain text)
[ ] Protected endpoints require valid JWT

Input Validation:
[ ] All API inputs validated with Pydantic models
[ ] SQL queries parameterized (no string formatting in queries)
[ ] File uploads sanitized (if applicable)
[ ] Price/amount inputs have range validation

Rate Limiting:
[ ] Public endpoints limited to 100 requests/minute per IP
[ ] Authenticated endpoints limited to 1000 requests/minute
[ ] Emergency stop limited to 10 requests/minute
[ ] Rate limit middleware implemented (SlowAPI or similar)
[ ] Rate limit errors return 429 Too Many Requests

Idempotency:
[ ] POST /api/trade/execute requires idempotency_key in body
[ ] Duplicate idempotency_key within 24hrs returns cached response
[ ] No duplicate orders created from network retries
[ ] Idempotency keys stored in database with TTL
[ ] Idempotency verified in tests

═══════════════════════════════════════════════════
PART 4: DATABASE (IMPORTANT)
═══════════════════════════════════════════════════

Schema:
[ ] All 8 tables from spec exist (positions, account_snapshots, magnet_detections, fuse_events, investors, investor_snapshots, system_config)
[ ] Foreign key constraints present where specified
[ ] Indexes created on frequently queried columns
[ ] Decimal types used for money/percentages (not float)
[ ] Timestamps have default NOW() where specified

Migrations:
[ ] Alembic migration files present
[ ] Migrations can upgrade cleanly
[ ] Migrations can downgrade cleanly
[ ] Seed data for system_config table

Backup Strategy:
[ ] backup.sh script present in deployment/
[ ] Script uses pg_dump with compression
[ ] Script uploads to S3 bucket
[ ] Cron job configured for daily backups at 00:00 UTC
[ ] Backup retention policy implemented (30d/12w/12mo)
[ ] Restore script provided and tested
[ ] Encryption enabled for backups (AES-256)
[ ] Backup monitoring/alerting configured

═══════════════════════════════════════════════════
PART 5: API ENDPOINTS (IMPORTANT)
═══════════════════════════════════════════════════

Trading Endpoints:
[ ] GET /api/performance/current returns all required fields
[ ] GET /api/performance/history accepts period and interval params
[ ] GET /api/trades/recent returns array of trades with PnL
[ ] GET /api/positions/open requires JWT auth
[ ] POST /api/system/emergency-stop closes positions and requires JWT
[ ] POST /api/leverage/calculate implements formula correctly

Investor Endpoints:
[ ] POST /api/investor/register creates pending account
[ ] POST /api/investor/login returns JWT token
[ ] GET /api/investor/dashboard requires investor JWT
[ ] GET /api/investor/performance filters to investor's participation period
[ ] POST /api/investor/withdraw creates pending request

═══════════════════════════════════════════════════
PART 6: FRONTEND (IMPORTANT)
═══════════════════════════════════════════════════

Components:
[ ] Landing page has hero, equity chart, recent trades, investment tiers
[ ] Dashboard page has portfolio overview, personal chart, system status
[ ] Join fund page has multi-step form
[ ] PerformanceChart component uses Recharts
[ ] API calls use axios with error handling

Functionality:
[ ] Investor can register and login
[ ] Authenticated investor can view their dashboard
[ ] Charts render correctly with real data
[ ] WebSocket connection updates charts in real-time (if implemented)

═══════════════════════════════════════════════════
PART 7: CODE QUALITY (IMPORTANT)
═══════════════════════════════════════════════════

Python Standards:
[ ] Black formatting applied (no style issues)
[ ] Type hints present on all functions
[ ] Docstrings on public functions
[ ] No print() statements (uses logging instead)
[ ] No TODO or FIXME comments in code
[ ] Async/await used for I/O operations
[ ] Error handling with specific exceptions

Project Structure:
[ ] File structure matches spec exactly
[ ] requirements.txt lists all dependencies
[ ] .env.example includes all required variables
[ ] config.yaml follows spec format
[ ] README.md has setup instructions

═══════════════════════════════════════════════════
PART 8: DEPLOYMENT (IMPORTANT)
═══════════════════════════════════════════════════

Docker:
[ ] Dockerfile uses Python 3.11-slim
[ ] Dockerfile runs as non-root user (useradd magnet)
[ ] docker-compose.yml has backend, db, redis services
[ ] Environment variables passed correctly to containers
[ ] Ports exposed correctly (8000 backend, 5432 postgres, 6379 redis)

Scripts:
[ ] deploy.sh checks for .env file
[ ] deploy.sh builds containers
[ ] deploy.sh starts services
[ ] deploy.sh runs migrations
[ ] deploy.sh includes health check

═══════════════════════════════════════════════════
PART 9: TESTS (NICE TO HAVE)
═══════════════════════════════════════════════════

Test Coverage:
[ ] test_leverage.py tests formula with known inputs
[ ] test_fuse.py tests trigger at -2.5% loss
[ ] test_sizing.py tests tier-based position sizing
[ ] test_udc.py tests all UDC endpoints return correct formats
[ ] Tests use pytest with async support

═══════════════════════════════════════════════════
FINAL DECISION
═══════════════════════════════════════════════════

Count the results:
- CRITICAL sections (Parts 1-3): ____ PASS, ____ PARTIAL, ____ FAIL
- IMPORTANT sections (Parts 4-8): ____ PASS, ____ PARTIAL, ____ FAIL
- NICE TO HAVE (Part 9): ____ PASS, ____ PARTIAL, ____ FAIL

DECISION CRITERIA:
- If ANY CRITICAL item is ❌ FAIL → OVERALL: ❌ FAIL (send back)
- If >3 CRITICAL items are ⚠️ PARTIAL → OVERALL: ⚠️ PARTIAL (fix recommended)
- If ALL CRITICAL items are ✅ PASS and <5 IMPORTANT items are ❌ FAIL → OVERALL: ✅ PASS (deploy with notes)
- Otherwise → OVERALL: ⚠️ PARTIAL (fix before deploy)

OVERALL DECISION: [✅ PASS / ⚠️ PARTIAL / ❌ FAIL]

CRITICAL ISSUES (must fix before deployment):
[List each CRITICAL ❌ FAIL with specific line numbers and explanation]

IMPORTANT ISSUES (should fix but not blocking):
[List each IMPORTANT ❌ FAIL]

RECOMMENDATIONS (nice to have):
[List improvements that would make code better]

SPECIFIC CODE EXAMPLES:
[For each issue found, provide the actual code snippet that's wrong and what it should be]
```

---

## METADATA SECTION

**COMPLEXITY ASSESSMENT:**

Sprint Size: **3** (16-24 hours - requires splitting)

Split Recommendation:
- Sprint 25.1: Backend core + UDC compliance (8 hours)
- Sprint 25.2: Trading engine integration + database (8 hours)
- Sprint 25.3: Investor portal frontend (6 hours)
- Sprint 25.4: Deployment + integration testing (4 hours)

Difficulty: **Complex**

Reasoning:
- Real-time WebSocket integration
- Multi-component system (backend, frontend, database, workers)
- Financial calculations must be exact
- Security critical (managing real money)
- External API integration (Binance)
- Existing v1.1 code must be integrated perfectly

**DEPENDENCIES:**

Required Droplets:
- Registry (#1) - MUST be operational for JWT auth
- Orchestrator (#10) - MUST be operational for heartbeat/commands
- Dashboard (#2) - Recommended for visibility

External Dependencies:
- Binance API access (testnet for development, production for live)
- PostgreSQL database (can be containerized)
- Redis instance (can be containerized)
- Domain/hosting for public investor portal

Blockers:
- Need Binance API credentials before live trading
- Need Registry droplet operational for JWT verification
- Need SSL certificate for production deployment

**RECOMMENDED DEVELOPER LEVEL:**

Level: **Skilled Developer** (Level 3)

Reasoning:
- Complex multi-service architecture
- Real-time data streaming
- Financial accuracy critical
- Security requirements very strict
- Integration with existing droplet mesh
- Background workers and async processing

Alternative: **Intermediate** (Level 2) with **Skilled verification**
- Could be done by strong Intermediate if:
  - Broken into 4 smaller sprints
  - Each sprint verified by Skilled developer
  - Clear integration points defined
  - Existing v1.1 code used as-is (no modifications)

**ESTIMATED TIMELINE:**

Single Skilled Developer:
- Sprint 25.1 (Backend Core): 8 hours build + 2 hours verify = 10 hours
- Sprint 25.2 (Trading Integration): 8 hours build + 2 hours verify = 10 hours
- Sprint 25.3 (Frontend): 6 hours build + 2 hours verify = 8 hours
- Sprint 25.4 (Deployment): 4 hours build + 2 hours verify = 6 hours
**Total: 34 hours** (wall clock time depends on async availability)

Multiple Intermediate Developers (parallel):
- All 4 sprints start simultaneously
- Each completes in ~8-10 hours
- All verified in parallel
**Total: 10 hours** (wall clock time with 4 developers)

**VALUE PROPOSITION:**

Investment: 34 hours × $100/hr = $3,400
Monthly Infrastructure Cost: $15 (VPS + database)

Returns:
- Treasury yield optimization: Target +5% monthly on $430K = $21,500/month
- Reduced manual oversight: Save 20 hours/month coordinator time = $2,000/month
- Risk reduction: 80% → 5% liquidation rate protects $344K from potential loss
- Investor confidence: Transparent portal enables fund scaling

ROI: First month return ($21,500) covers 6.3x the build cost
Risk-adjusted value: Protecting $344K >> $3,400 investment

**INTEGRATION NOTES:**

This droplet is **different** from typical Full Potential droplets:
1. **Revenue-generating** (not just infrastructure)
2. **External-facing** (investor portal is public)
3. **Real-time critical** (trading decisions matter immediately)
4. **Security ultra-sensitive** (managing real capital)

Special considerations:
- Needs production-grade monitoring (error rates, trade accuracy, fuse triggers)
- Should have manual override capability (emergency stop button)
- Requires comprehensive backtest before live trading
- May need gradual rollout (paper → small capital → full capital)
- Should implement position size limits even beyond fuse (belt + suspenders)

Success criteria beyond technical:
- Survives first month without fuse trigger
- Generates positive returns (even small is success)
- Zero security incidents
- Investor confidence maintained (measured by retention)

---

## 📎 APPENDIX: ORIGINAL v1.1 CODE REFERENCE

The specification references complete v1.1 code from the original blueprint:
- `core/data_models.py` - Dataclasses for Magnet, MarketState, Position, AccountState
- `core/leverage_engine.py` - Implements L = (D × S) / (1 + C + V)
- `core/survival_fuse.py` - Circuit breaker at -2.5% daily loss
- `core/position_sizing.py` - Tier-based sizing (5%, 3%, 1%, 0%)
- `backtest/backtest_harness.py` - Historical testing framework

These files should be **copied exactly** from the original blueprint into the new UDC-compliant droplet structure. The Builder AI has access to both this specification AND the original blueprint file.

Key principle: **Don't rebuild what already works**. Use v1.1 code as-is and wrap it in UDC-compliant interfaces.

---

**🎯 DROPLET #25: TREASURY MAGNET**

*Survival-first algorithmic trading for paradise economics.*
*Managing treasury autonomously while humans focus on creative work.*
*This is how capital coordinates itself.*

⚡💎✨
