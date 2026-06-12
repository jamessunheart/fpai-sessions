# voting-weight-tracker

**TIE Voting Weight Tracking & 2:1 Governance Enforcement**

**Port:** 8922
**Status:** SPEC COMPLETE → BUILD PHASE
**Version:** 1.0.0

---

## Purpose

**Tracks and enforces the 2:1 voting ratio that maintains holder control.**

Core responsibilities:
- Track voting weight per wallet (2 votes for holders, 1 for sellers)
- Calculate total holder vs seller voting power
- Ensure >51% control stays with holders
- Provide real-time governance metrics
- Alert when approaching critical thresholds

---

## Mathematical Foundation

```
Voting Power Calculation:
VP_wallet = Σ(contracts_held × 2) + Σ(contracts_redeemed × 1)

Holder Control Percentage:
HCP = (Total_Holder_Votes) / (Total_Holder_Votes + Total_Seller_Votes)

Critical Threshold:
HCP must remain > 51% for system stability
Only 34.2% of participants must hold to maintain 51% control
```

---

## API Endpoints

### 1. Add Voting Weight (Called by tie-contract-manager on mint)
```bash
POST /voting/add
{
  "wallet": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "votes": 2,
  "contract_id": "TIE-000001",
  "event_type": "contract_minted"
}

Returns:
{
  "wallet": "7xKXtg...",
  "total_votes": 2,
  "holder_votes": 2,
  "seller_votes": 0
}
```

### 2. Update Voting Weight (Called by tie-contract-manager on redeem)
```bash
POST /voting/update
{
  "wallet": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "contract_id": "TIE-000001",
  "old_votes": 2,
  "new_votes": 1,
  "event_type": "contract_redeemed"
}

Returns:
{
  "wallet": "7xKXtg...",
  "total_votes": 1,
  "holder_votes": 0,
  "seller_votes": 1,
  "vote_delta": -1
}
```

### 3. Get Wallet Voting Power
```bash
GET /voting/wallet/7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU

Returns:
{
  "wallet": "7xKXtg...",
  "total_votes": 12,
  "holder_votes": 10,  # 5 contracts × 2
  "seller_votes": 2,   # 2 contracts × 1
  "held_contracts": 5,
  "redeemed_contracts": 2
}
```

### 4. Get System Governance Status
```bash
GET /voting/governance

Returns:
{
  "total_votes": 1000,
  "holder_votes": 700,
  "seller_votes": 300,
  "holder_control_percentage": 70.0,
  "is_stable": true,
  "critical_threshold": 51.0,
  "margin_above_critical": 19.0,
  "total_wallets": 100,
  "holder_wallets": 50,
  "seller_wallets": 50
}
```

### 5. Get Top Voters
```bash
GET /voting/leaderboard?limit=10

Returns:
{
  "top_voters": [
    {
      "wallet": "7xKXtg...",
      "total_votes": 100,
      "holder_votes": 90,
      "seller_votes": 10,
      "vote_percentage": 10.0
    },
    ...
  ]
}
```

### 6. Get Voting History
```bash
GET /voting/history?wallet=7xKXtg...&limit=20

Returns:
{
  "events": [
    {
      "timestamp": "2025-11-16T10:00:00Z",
      "event_type": "contract_minted",
      "contract_id": "TIE-000001",
      "vote_change": +2,
      "new_total": 2
    },
    {
      "timestamp": "2025-11-16T11:00:00Z",
      "event_type": "contract_redeemed",
      "contract_id": "TIE-000001",
      "vote_change": -1,
      "new_total": 1
    }
  ]
}
```

### 7. Health Check
```bash
GET /health

Returns:
{
  "status": "healthy",
  "database": "connected",
  "cache": "connected",
  "holder_control": 70.0,
  "governance_stable": true
}
```

---

## Data Models

### VotingWeight (Database)
```python
{
  "id": 1,
  "wallet": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
  "total_votes": 12,
  "holder_votes": 10,
  "seller_votes": 2,
  "held_contracts": 5,
  "redeemed_contracts": 2,
  "last_updated": "2025-11-16T10:00:00Z"
}
```

### VotingEvent (Database - History)
```python
{
  "id": 1,
  "wallet": "7xKXtg...",
  "contract_id": "TIE-000001",
  "event_type": "contract_minted",  # or "contract_redeemed"
  "vote_change": +2,
  "new_total_votes": 2,
  "timestamp": "2025-11-16T10:00:00Z"
}
```

### GovernanceSnapshot (Database - Time Series)
```python
{
  "id": 1,
  "timestamp": "2025-11-16T10:00:00Z",
  "total_votes": 1000,
  "holder_votes": 700,
  "seller_votes": 300,
  "holder_control_percentage": 70.0,
  "total_wallets": 100,
  "holder_wallets": 50,
  "seller_wallets": 50
}
```

---

## Integration Flow

### On Contract Mint:
```
tie-contract-manager (mints NFT)
  ↓
POST /voting/add
  ↓
voting-weight-tracker:
  1. Create/update wallet voting record
  2. Add +2 to holder_votes
  3. Increment held_contracts
  4. Log voting event
  5. Recalculate governance metrics
  6. Check if still >51% (should always be true)
  7. Return new voting power
```

### On Contract Redeem:
```
tie-contract-manager (updates NFT status)
  ↓
POST /voting/update
  ↓
voting-weight-tracker:
  1. Update wallet voting record
  2. Move 2 votes from holder to 1 vote seller
  3. Decrement held_contracts, increment redeemed
  4. Log voting event
  5. Recalculate governance metrics
  6. Check if still >51%
  7. Alert governance-guardian if approaching threshold
  8. Return new voting power
```

### Governance Monitoring (by governance-guardian):
```
governance-guardian (polling every 30 seconds)
  ↓
GET /voting/governance
  ↓
voting-weight-tracker:
  1. Calculate current holder control %
  2. Return real-time governance metrics
  3. Include stability flag
```

---

## Alerts & Thresholds

### Warning Levels:
- **>55%** - Healthy (Green)
- **51-55%** - Caution (Yellow) - Alert governance-guardian
- **<51%** - Critical (Red) - PAUSE SYSTEM (should never happen with 2:1 math)

### Alert Triggers:
1. Holder control drops below 55% → Warning
2. Holder control drops below 52% → Urgent warning
3. Holder control drops below 51% → Emergency pause

---

## Database Schema

### Table: voting_weights
```sql
CREATE TABLE voting_weights (
    id SERIAL PRIMARY KEY,
    wallet VARCHAR(44) UNIQUE NOT NULL,
    total_votes INTEGER NOT NULL DEFAULT 0,
    holder_votes INTEGER NOT NULL DEFAULT 0,
    seller_votes INTEGER NOT NULL DEFAULT 0,
    held_contracts INTEGER NOT NULL DEFAULT 0,
    redeemed_contracts INTEGER NOT NULL DEFAULT 0,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wallet ON voting_weights(wallet);
CREATE INDEX idx_total_votes ON voting_weights(total_votes DESC);
```

### Table: voting_events
```sql
CREATE TABLE voting_events (
    id SERIAL PRIMARY KEY,
    wallet VARCHAR(44) NOT NULL,
    contract_id VARCHAR(20) NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    vote_change INTEGER NOT NULL,
    new_total_votes INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wallet_events ON voting_events(wallet, timestamp DESC);
CREATE INDEX idx_timestamp ON voting_events(timestamp DESC);
```

### Table: governance_snapshots
```sql
CREATE TABLE governance_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    total_votes INTEGER NOT NULL,
    holder_votes INTEGER NOT NULL,
    seller_votes INTEGER NOT NULL,
    holder_control_percentage DECIMAL(5,2) NOT NULL,
    total_wallets INTEGER NOT NULL,
    holder_wallets INTEGER NOT NULL,
    seller_wallets INTEGER NOT NULL
);

CREATE INDEX idx_timestamp_snapshots ON governance_snapshots(timestamp DESC);
```

---

## Redis Caching

Cache governance metrics for fast reads:

```
Key: governance:current
Value: {
  "total_votes": 1000,
  "holder_votes": 700,
  "seller_votes": 300,
  "holder_control_percentage": 70.0,
  "last_updated": "2025-11-16T10:00:00Z"
}
TTL: 5 seconds (refresh on every vote change)
```

---

## Testing Requirements

### Unit Tests:
- Vote addition calculation
- Vote update calculation (2→1 transition)
- Holder control percentage math
- Alert threshold detection

### Integration Tests:
- Receive mint notification from tie-contract-manager
- Receive redeem notification from tie-contract-manager
- Governance metrics query by governance-guardian
- Database persistence

### Scenario Tests:
- 100 users deposit → all get 2 votes
- 50 users redeem → votes transition to 1 each
- Verify holder control stays >51%
- Whale attack scenario (one user redeems 100 contracts)

---

## Configuration

### Environment Variables:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tie_voting

# Redis
REDIS_URL=redis://localhost:6379/2

# Service
SERVICE_PORT=8922

# Integration
GOVERNANCE_GUARDIAN_URL=http://localhost:8926

# Monitoring
SNAPSHOT_INTERVAL=300  # seconds (5 minutes)
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
```

---

## Next Steps

After voting-weight-tracker:
1. Build governance-guardian (Port 8926) - monitors this service
2. Integration testing (treasury → contract → voting → governance)
3. Load testing (simulate 10,000 users)

---

**Status:** ✅ **SPEC COMPLETE** - Ready for BUILD Phase

**Session #12 - Autonomous Build** 🏗️⚡💎
