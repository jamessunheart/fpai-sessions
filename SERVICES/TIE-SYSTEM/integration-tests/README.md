# TIE System Integration Tests

**Comprehensive integration testing for TIE core services**

**Status:** BUILDING
**Version:** 1.0.0

---

## Purpose

Validate that the 4 core TIE services work together correctly:

1. **sol-treasury-core** (Port 8920) - SOL deposits/withdrawals
2. **tie-contract-manager** (Port 8921) - NFT contract issuance
3. **voting-weight-tracker** (Port 8922) - 2:1 voting enforcement
4. **governance-guardian** (Port 8926) - Control monitoring

---

## Test Scenarios

### Scenario 1: Happy Path - Deposit → Contract → Voting
**Flow:**
```
User deposits 10 SOL
  ↓
sol-treasury-core creates deposit record
  ↓
sol-treasury-core calls tie-contract-manager to mint contract
  ↓
tie-contract-manager mints NFT (20 SOL value, 2x)
  ↓
tie-contract-manager calls voting-weight-tracker (+2 votes)
  ↓
voting-weight-tracker updates wallet voting power
  ↓
governance-guardian detects governance check (next poll)
```

**Assertions:**
- ✅ Treasury balance increases by 10 SOL
- ✅ Contract created with 20 SOL value (2x)
- ✅ NFT minted with correct metadata
- ✅ Wallet receives 2 voting power
- ✅ Holder control percentage increases
- ✅ Governance remains stable (>51%)

### Scenario 2: Redemption Flow - Contract → Voting Update
**Flow:**
```
User redeems TIE contract
  ↓
redemption-algorithm approves (TODO: service not built yet)
  ↓
tie-contract-manager updates NFT status (HELD → REDEEMED)
  ↓
tie-contract-manager calls voting-weight-tracker (2 → 1 vote)
  ↓
voting-weight-tracker updates wallet (holder_votes-=2, seller_votes+=1)
  ↓
governance-guardian detects change (next poll)
```

**Assertions:**
- ✅ Contract status updated to REDEEMED
- ✅ NFT metadata updated
- ✅ Wallet voting power decreased by 1 (2 → 1)
- ✅ Total holder votes decreased
- ✅ Total seller votes increased
- ✅ Holder control percentage decreases slightly but stays >51%

### Scenario 3: Governance Monitoring - Multiple Deposits
**Flow:**
```
100 users each deposit 1 SOL
  ↓
100 contracts minted (each 2 SOL value)
  ↓
100 wallets receive 2 votes each (200 total votes)
  ↓
governance-guardian polls every 30 seconds
  ↓
Holder control = 100% (all held, no redemptions)
```

**Assertions:**
- ✅ Treasury has 100 SOL
- ✅ 100 contracts minted
- ✅ Total votes = 200 (all holder votes)
- ✅ Holder control = 100%
- ✅ Governance level = "excellent"
- ✅ No alerts triggered

### Scenario 4: Threshold Violation - Governance Alert
**Flow:**
```
100 users deposit (200 holder votes)
  ↓
50 users redeem (50 holder votes + 50 seller votes = 100 total)
  ↓
Holder control = 50 / 100 = 50%
  ↓
governance-guardian detects <51% on next poll
  ↓
Creates critical alert
  ↓
PAUSES redemptions
```

**Assertions:**
- ✅ Holder control drops to 50%
- ✅ governance-guardian creates critical alert
- ✅ System status = "redemptions_paused"
- ✅ Pause record created in database
- ✅ Audit event logged
- ✅ Alert notification sent (TODO: when implemented)

### Scenario 5: Caution Threshold - Increased Monitoring
**Flow:**
```
100 users deposit (200 holder votes)
  ↓
30 users redeem (70 holder votes + 30 seller votes = 100 total)
  ↓
Holder control = 70 / 100 = 70% (excellent)
  ↓
20 more users redeem (50 holder votes + 50 seller votes = 100 total)
  ↓
Holder control = 50 / 100 = 50% < 55%
  ↓
governance-guardian creates caution alert
  ↓
Monitoring interval: 30s → 5s
```

**Assertions:**
- ✅ Caution alert created
- ✅ Monitoring interval reduced to 5 seconds
- ✅ System remains operational
- ✅ No pause triggered (still >51%)

### Scenario 6: Load Test - 1000 Users
**Flow:**
```
1000 users each deposit 1 SOL
  ↓
1000 contracts minted
  ↓
2000 holder votes created
  ↓
governance-guardian monitors continuously
  ↓
200 users redeem (sequential, not all at once)
  ↓
Holder control remains >70% throughout
```

**Assertions:**
- ✅ All 1000 deposits processed successfully
- ✅ All 1000 contracts minted
- ✅ Voting power accurate (2000 → 1600 + 200 = 1800 total)
- ✅ Holder control = 1600/1800 = 88.9% (excellent)
- ✅ No performance degradation
- ✅ No data inconsistencies

### Scenario 7: Recovery - Holder Control Restoration
**Flow:**
```
System paused at 50% holder control
  ↓
50 new users deposit (100 new holder votes)
  ↓
Holder control = 100 / 150 = 66.7%
  ↓
Admin verifies governance restored
  ↓
POST /guardian/resume
  ↓
System resumes operations
```

**Assertions:**
- ✅ Holder control restored above 51%
- ✅ Resume successful
- ✅ Pause record updated (resumed_at, resumed_by)
- ✅ Audit event logged
- ✅ System status = "operational"
- ✅ Alerts cleared

---

## Test Structure

### Unit Tests (per service)
Each service has its own unit tests:
- `sol-treasury-core/tests/` - Treasury operations
- `tie-contract-manager/tests/` - NFT minting
- `voting-weight-tracker/tests/` - Vote calculations
- `governance-guardian/tests/` - Threshold detection

### Integration Tests (this directory)
Cross-service workflows:
- `test_deposit_flow.py` - Deposit → Contract → Voting
- `test_redemption_flow.py` - Redeem → Voting update
- `test_governance_monitoring.py` - Guardian monitoring
- `test_threshold_violations.py` - Alert triggers
- `test_load.py` - Performance under load

### End-to-End Tests
Complete user journeys:
- `test_e2e_deposit_redeem.py` - Full lifecycle
- `test_e2e_governance_crisis.py` - Threshold violation → recovery
- `test_e2e_multiple_users.py` - Concurrent operations

---

## Running Tests

### Prerequisites
```bash
# Start all services
cd sol-treasury-core && uvicorn app.main:app --port 8920 &
cd tie-contract-manager && uvicorn app.main:app --port 8921 &
cd voting-weight-tracker && uvicorn app.main:app --port 8922 &
cd governance-guardian && uvicorn app.main:app --port 8926 &

# Or use Docker Compose (TODO: after deployment automation built)
docker-compose up
```

### Run All Tests
```bash
cd integration-tests
pytest -v
```

### Run Specific Scenario
```bash
pytest test_deposit_flow.py -v
pytest test_threshold_violations.py -v
```

### Run with Coverage
```bash
pytest --cov=. --cov-report=html
```

---

## Test Configuration

### Environment Variables
```bash
# Service URLs
SOL_TREASURY_URL=http://localhost:8920
TIE_CONTRACT_URL=http://localhost:8921
VOTING_TRACKER_URL=http://localhost:8922
GOVERNANCE_GUARDIAN_URL=http://localhost:8926

# Test Configuration
TEST_WALLET_1=7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU
TEST_WALLET_2=8yLZuh3DW98e98UYKTEqcDZ6kfAU94VXSdJiJpxHbDvZ
NUM_TEST_USERS=100
```

---

## Success Criteria

All integration tests must pass:
- ✅ No data inconsistencies across services
- ✅ Correct vote calculations (2:1 ratio maintained)
- ✅ Governance monitoring accurate
- ✅ Threshold alerts triggered correctly
- ✅ Pause/resume mechanisms work
- ✅ Audit trails complete
- ✅ Performance acceptable (<100ms per operation)

---

## Next Steps

After integration tests pass:
1. Build redemption-algorithm (Port 8923)
2. Build experience-marketplace (Port 8924)
3. Build remaining services
4. Production deployment

---

**Status:** 🏗️ **BUILDING** - Integration test suite

**Session #12 - Autonomous Build** 🏗️⚡💎
