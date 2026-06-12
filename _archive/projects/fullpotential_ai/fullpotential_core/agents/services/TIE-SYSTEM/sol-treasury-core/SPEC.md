# sol-treasury-core - SPEC

**Service:** TIE System Foundation - Treasury Management
**Port:** 8920
**Status:** BUILD Phase
**Created:** 2025-11-16

---

## Purpose

**Foundation service for TIE system - manages SOL deposits, issues 2x TIE contracts, maintains treasury balance, and enforces capital flow controls.**

The treasury is the beating heart of the abundance protocol. This service ensures MORE capital flows IN than OUT through smart contract custody and metered access.

---

## Requirements

### Functional Requirements
- [x] Accept SOL deposits from Phantom/Solflare/Sollet wallets
- [x] Issue TIE contract reference to depositor (NFT minted by tie-contract-manager)
- [x] Track total treasury balance (SOL deposited vs current)
- [x] Monitor control percentage (must maintain >51%)
- [x] Withdrawal queue for redemptions (metered by redemption-algorithm)
- [x] Emergency pause capability (circuit breaker)
- [x] Multi-sig treasury control for security
- [x] Real-time balance updates via WebSocket
- [x] Deposit history and analytics
- [x] Integration with tie-contract-manager (trigger NFT minting)

### Non-Functional Requirements
- [x] Performance: Transaction confirmation < 30 seconds (Solana speed)
- [x] Security: Smart contract audited, multi-sig control
- [x] Reliability: 99.9% uptime (critical financial infrastructure)
- [x] Scalability: Handle 1000+ deposits per day
- [x] Transparency: All transactions on-chain and verifiable
- [x] Gas Efficiency: Minimize transaction costs
- [x] Monitoring: Real-time alerts for large deposits/withdrawals

---

## Architecture

### Two-Layer Design:

```
┌─────────────────────────────────────────┐
│         LAYER 1: Solana Program         │
│         (Rust/Anchor Framework)         │
├─────────────────────────────────────────┤
│  • Accept SOL deposits                  │
│  • Custody SOL in program account       │
│  • Process withdrawals (with auth)      │
│  • Emit events for tracking             │
│  • Enforce invariants (no overdraft)    │
└─────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────┐
│      LAYER 2: Python API Service        │
│         (FastAPI on Port 8920)          │
├─────────────────────────────────────────┤
│  • Wallet connection interface          │
│  • Transaction preparation              │
│  • Event monitoring and indexing        │
│  • Analytics and reporting              │
│  • Integration with other services      │
│  • WebSocket for real-time updates      │
└─────────────────────────────────────────┘
```

---

## API Specs

### REST Endpoints

**POST /treasury/deposit**
- Description: Initiate SOL deposit to treasury
- Body: `{"wallet_address": "string", "amount_sol": float, "signature": "string"}`
- Returns: `{"transaction_id": "string", "tie_contract_value": float, "status": "pending"}`
- Status: 202 Accepted

**POST /treasury/withdraw**
- Description: Process approved withdrawal (called by redemption-algorithm)
- Body: `{"wallet_address": "string", "amount_sol": float, "authorization": "string"}`
- Returns: `{"transaction_id": "string", "status": "processing"}`
- Status: 202 Accepted
- Auth: Requires redemption-algorithm signature

**GET /treasury/balance**
- Description: Get current treasury balance
- Returns: `{"total_deposited": float, "current_balance": float, "treasury_ratio": float}`
- Status: 200 OK

**GET /treasury/control**
- Description: Get holder control percentage
- Returns: `{"holder_control_pct": float, "status": "green|yellow|orange|red", "threshold": 51.0}`
- Status: 200 OK

**GET /treasury/history**
- Description: Get deposit/withdrawal history
- Parameters: `?wallet_address=optional&limit=100&offset=0`
- Returns: `{"transactions": [...], "total": int}`
- Status: 200 OK

**POST /treasury/emergency/pause**
- Description: Pause all deposits/withdrawals (emergency only)
- Auth: Multi-sig required
- Returns: `{"paused": true, "timestamp": "ISO datetime"}`
- Status: 200 OK

**GET /health**
- Description: Health check
- Returns: `{"status": "ok", "service": "sol-treasury-core", "version": "1.0.0"}`
- Status: 200 OK

### WebSocket

**WS /ws/treasury**
- Real-time treasury updates
- Events: `deposit`, `withdrawal`, `balance_update`, `control_update`

---

## Solana Smart Contract (Anchor Program)

### Program Instructions:

```rust
use anchor_lang::prelude::*;

#[program]
pub mod sol_treasury {
    use super::*;

    /// Initialize treasury
    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;
        treasury.authority = ctx.accounts.authority.key();
        treasury.total_deposited = 0;
        treasury.total_withdrawn = 0;
        treasury.paused = false;
        Ok(())
    }

    /// Deposit SOL to treasury
    pub fn deposit(ctx: Context<Deposit>, amount: u64) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;

        require!(!treasury.paused, ErrorCode::TreasuryPaused);

        // Transfer SOL from user to treasury PDA
        let ix = anchor_lang::solana_program::system_instruction::transfer(
            &ctx.accounts.depositor.key(),
            &ctx.accounts.treasury_vault.key(),
            amount,
        );

        anchor_lang::solana_program::program::invoke(
            &ix,
            &[
                ctx.accounts.depositor.to_account_info(),
                ctx.accounts.treasury_vault.to_account_info(),
            ],
        )?;

        treasury.total_deposited += amount;

        emit!(DepositEvent {
            depositor: ctx.accounts.depositor.key(),
            amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// Withdraw SOL from treasury (authorized only)
    pub fn withdraw(ctx: Context<Withdraw>, amount: u64) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;

        require!(!treasury.paused, ErrorCode::TreasuryPaused);
        require!(
            ctx.accounts.authority.key() == treasury.authority,
            ErrorCode::Unauthorized
        );

        // Transfer SOL from treasury PDA to recipient
        **ctx.accounts.treasury_vault.to_account_info().try_borrow_mut_lamports()? -= amount;
        **ctx.accounts.recipient.to_account_info().try_borrow_mut_lamports()? += amount;

        treasury.total_withdrawn += amount;

        emit!(WithdrawEvent {
            recipient: ctx.accounts.recipient.key(),
            amount,
            timestamp: Clock::get()?.unix_timestamp,
        });

        Ok(())
    }

    /// Emergency pause
    pub fn pause(ctx: Context<Pause>) -> Result<()> {
        let treasury = &mut ctx.accounts.treasury;
        require!(
            ctx.accounts.authority.key() == treasury.authority,
            ErrorCode::Unauthorized
        );
        treasury.paused = true;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(init, payer = authority, space = 8 + 32 + 8 + 8 + 1)]
    pub treasury: Account<'info, Treasury>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Deposit<'info> {
    #[account(mut)]
    pub treasury: Account<'info, Treasury>,
    #[account(mut)]
    pub depositor: Signer<'info>,
    #[account(mut)]
    pub treasury_vault: SystemAccount<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Withdraw<'info> {
    #[account(mut)]
    pub treasury: Account<'info, Treasury>,
    pub authority: Signer<'info>,
    #[account(mut)]
    pub treasury_vault: SystemAccount<'info>,
    #[account(mut)]
    pub recipient: SystemAccount<'info>,
}

#[account]
pub struct Treasury {
    pub authority: Pubkey,
    pub total_deposited: u64,
    pub total_withdrawn: u64,
    pub paused: bool,
}

#[event]
pub struct DepositEvent {
    pub depositor: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[event]
pub struct WithdrawEvent {
    pub recipient: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

#[error_code]
pub enum ErrorCode {
    #[msg("Treasury is paused")]
    TreasuryPaused,
    #[msg("Unauthorized")]
    Unauthorized,
}
```

---

## Data Models

### Python/Database Models:

```python
from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer
from datetime import datetime
from enum import Enum

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

class TreasuryTransaction(Base):
    """Record of all treasury transactions"""
    __tablename__ = "treasury_transactions"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String, unique=True, index=True)  # Solana tx signature
    wallet_address = Column(String, index=True)

    type = Column(String)  # deposit or withdrawal
    amount_sol = Column(Float)

    status = Column(String)  # pending, confirmed, failed

    created_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)

    # For deposits: TIE contract value
    tie_contract_value = Column(Float, nullable=True)

    # Solana details
    block_number = Column(Integer, nullable=True)
    slot = Column(Integer, nullable=True)

class TreasuryState(Base):
    """Current treasury state snapshot"""
    __tablename__ = "treasury_state"

    id = Column(Integer, primary_key=True)

    total_deposited = Column(Float)  # Total SOL deposited all-time
    total_withdrawn = Column(Float)  # Total SOL withdrawn all-time
    current_balance = Column(Float)  # Current SOL in treasury

    treasury_ratio = Column(Float)  # current_balance / total_deposited

    holder_control_pct = Column(Float)  # % voting control by holders

    paused = Column(Boolean, default=False)

    updated_at = Column(DateTime, default=datetime.utcnow)
```

---

## Dependencies

### Required Services
- **tie-contract-manager** (Port 8921) - Mint TIE NFT when deposit confirmed
- **voting-weight-tracker** (Port 8922) - Update votes when deposit occurs
- **redemption-algorithm** (Port 8923) - Authorize withdrawals
- **flow-monitor** (Port 8928) - Record capital flows

### External Dependencies
- **Solana RPC Node** - Mainnet or devnet
- **Anchor Framework** - Smart contract deployment
- **Phantom/Solflare** - Wallet integration (frontend)

### Infrastructure
- **PostgreSQL** - Transaction history
- **Redis** - Real-time state caching
- **Docker** - Containerization
- **Port 8920** - Must be available

---

## Integration Flow

### Deposit Flow:

```
1. User clicks "Deposit" on abundance-dashboard
2. Phantom wallet prompts for approval
3. User signs transaction
4. Transaction sent to Solana (deposit instruction)
5. sol-treasury-core receives transaction
6. Smart contract transfers SOL to treasury PDA
7. Emit DepositEvent
8. Python service listens for event
9. Record transaction in database
10. Call tie-contract-manager to mint NFT (2x value)
11. Call voting-weight-tracker to add 2 votes
12. Call flow-monitor to record inflow
13. Broadcast via WebSocket to dashboard
14. User sees confirmation + new TIE contract
```

### Withdrawal Flow:

```
1. redemption-algorithm approves withdrawal
2. Calls POST /treasury/withdraw with auth
3. sol-treasury-core verifies auth signature
4. Execute withdraw instruction on Solana
5. Smart contract transfers SOL from PDA to user
6. Emit WithdrawEvent
7. Update database records
8. Call voting-weight-tracker (reduce to 1 vote)
9. Call flow-monitor to record outflow
10. Broadcast via WebSocket
11. User receives SOL
```

---

## Security Measures

### Smart Contract:
- **Multi-sig authority** - Requires 3/5 signatures for admin actions
- **Pause capability** - Emergency stop
- **No arbitrary code execution** - Pure transfer logic only
- **Audited before mainnet** - Reputable firm

### API Layer:
- **JWT authentication** - For admin endpoints
- **Rate limiting** - Prevent spam
- **Signature verification** - All withdrawal requests verified
- **HTTPS only** - Encrypted transport

### Operational:
- **Cold storage** - 20% of treasury in offline wallet
- **Insurance fund** - 5% set aside
- **Monitoring** - 24/7 alerts for unusual activity

---

## Success Criteria

**Phase 1: SPEC → BUILD**
- [x] All sections complete in SPEC.md
- [x] Smart contract logic defined
- [x] API endpoints documented
- [x] Data models specified
- [x] Integration flows mapped

**Phase 2: BUILD → TEST**
- [ ] Anchor program compiles without errors
- [ ] Anchor program deploys to devnet
- [ ] All API endpoints return expected responses
- [ ] Deposit flow works end-to-end
- [ ] Withdrawal flow works with auth
- [ ] Database records transactions correctly
- [ ] WebSocket broadcasts updates

**Phase 3: TEST → PRODUCTION**
- [ ] Smart contract audit passed
- [ ] All unit tests pass (>80% coverage)
- [ ] Integration tests pass (deposit + withdraw flows)
- [ ] Load testing: 100 deposits/minute
- [ ] Security review passed
- [ ] Multi-sig configured
- [ ] Emergency pause tested

**Phase 4: PRODUCTION**
- [ ] Deployed to Solana mainnet
- [ ] API deployed to 198.54.123.234:8920
- [ ] Registered in SERVICE_REGISTRY.json
- [ ] Monitoring configured
- [ ] First real deposit processed successfully
- [ ] 99.9% uptime for 7 days

---

## Technical Constraints

- **Language:** Rust (Solana program), Python 3.11+ (API)
- **Framework:** Anchor (Solana), FastAPI (API)
- **Port:** 8920
- **Solana Network:** Devnet for testing, Mainnet for production
- **Resource Limits:**
  - Memory: 512MB API service
  - Solana: Program size < 200KB
- **Response Time:** < 30 seconds for transaction confirmation
- **Database:** PostgreSQL 15+
- **Cache:** Redis 7+

---

## Testing Strategy

### Unit Tests:
```python
# Test deposit validation
def test_deposit_amount_positive()
def test_deposit_updates_balance()
def test_deposit_emits_event()

# Test withdrawal auth
def test_withdrawal_requires_auth()
def test_withdrawal_updates_balance()
def test_withdrawal_fails_when_paused()

# Test pause
def test_pause_requires_authority()
def test_pause_blocks_deposits()
def test_pause_blocks_withdrawals()
```

### Integration Tests:
```python
# End-to-end deposit
def test_full_deposit_flow()
    # 1. Submit deposit tx
    # 2. Confirm on-chain
    # 3. NFT minted
    # 4. Votes updated
    # 5. DB records created

# End-to-end withdrawal
def test_full_withdrawal_flow()
    # 1. Redemption approval
    # 2. Withdraw request
    # 3. On-chain transfer
    # 4. DB updated
    # 5. Votes reduced
```

---

## Monitoring & Alerts

### Metrics to Track:
- Total deposits (count, volume)
- Total withdrawals (count, volume)
- Current treasury balance
- Treasury ratio (current/deposited)
- Average deposit size
- Average withdrawal size
- Transaction success rate
- API response time
- Smart contract gas usage

### Alerts:
- Large deposit (>10 SOL)
- Large withdrawal (>10 SOL)
- Treasury ratio < 1.5
- Holder control < 60%
- API response time > 5s
- Transaction failure rate > 1%
- Emergency pause activated

---

## Next Steps

After sol-treasury-core is complete:

1. **Deploy to devnet** - Test with fake SOL
2. **Build tie-contract-manager** - Mint NFTs on deposit
3. **Build voting-weight-tracker** - Track 2:1 votes
4. **Integration testing** - All 3 services working together
5. **Security audit** - Smart contract review
6. **Deploy to mainnet** - Real SOL, real users

---

**SPEC Status:** ✅ **COMPLETE** - Ready for BUILD phase

**Estimated Build Time:** 1 week (smart contract + API)
**Complexity:** High (blockchain + backend integration)
**Priority:** CRITICAL (foundation for entire system)

---

**This is the foundation. Everything else builds on this.** 🏗️⚡💎
