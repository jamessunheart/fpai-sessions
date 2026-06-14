# ARIA Trading Integration Plan
**Goal:** Establish Signal Shark as top-performing auto-trading strategy connected to Aria for multi-user money management

**Date:** December 14, 2025

---

## 🎯 Current State Analysis

### Top Performing Strategy: Signal Shark ✅
- **Win Rate:** 95.7% (69 trades)
- **Total PnL:** $2,222.65
- **Status:** Actively trading (last trade 17.7 hours ago)
- **Assessment:** Best performing, most reliable strategy

### Aria Current Capabilities ✅
- Chat interface (`/chat` endpoint)
- Trading intelligence module (`aria_trading_intel.py`)
- Can answer trading questions
- Can track positions manually
- **Missing:** Automated trading, money management, multi-user allocation

### User System ✅
- Per-user treasury management (`get_user_treasury`)
- User data isolation (`USER_DATA_ROOT`)
- Starting capital: $100,000 default
- **Missing:** Aria commands for money movement

---

## 🚀 Implementation Plan

### Phase 1: Signal Shark Auto-Trading Setup (Priority 1)

#### 1.1 Create Signal Shark Auto-Trader
**File:** `whaletrack-magnetic-trader/backend/core/signal_shark_auto_trader.py`

**Features:**
- Uses Signal Shark strategy (95.7% win rate)
- Auto-executes trades when confidence >= 70%
- Per-user capital allocation
- Automatic position management
- Risk management (stop-loss, take-profit)

**Configuration:**
```python
SIGNAL_SHARK_CONFIG = {
    "min_confidence": 70.0,  # Signal Shark threshold
    "min_probability": 65.0,
    "leverage": 1.25,  # Signal Shark leverage
    "position_size_pct": 10.0,  # 10% of allocated capital per trade
    "max_positions": 3,
    "stop_loss_pct": 2.0,
    "take_profit_pct": 0.0,  # Exit at magnet target
    "max_daily_loss_pct": 5.0,
    "enabled_symbols": ["BTC", "ETH", "SOL"]
}
```

#### 1.2 Enable Auto-Trading Per User
**File:** `whaletrack-magnetic-trader/backend/api/main.py`

**New Endpoint:**
```python
@app.post("/api/auto-trade/enable")
async def enable_auto_trade(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user),
    strategy: str = "signal-shark",
    capital_allocation: float = 10000.0
):
    """Enable auto-trading for user with Signal Shark strategy."""
    # Enable auto-trading
    # Allocate capital
    # Start trading loop
```

---

### Phase 2: Aria Money Management Integration (Priority 1)

#### 2.1 Add Money Management to Aria
**File:** `SERVICES/aria/app/main.py`

**New Capabilities:**
- Deposit money to trading account
- Withdraw money from trading account
- Allocate capital to strategies
- Check balance
- View performance

**New Endpoints:**
```python
@app.post("/trading/deposit")
async def deposit_money(user_id: str, amount: float):
    """Deposit money to user's trading account via Aria."""
    
@app.post("/trading/withdraw")
async def withdraw_money(user_id: str, amount: float):
    """Withdraw money from user's trading account via Aria."""
    
@app.post("/trading/allocate")
async def allocate_to_strategy(user_id: str, strategy: str, amount: float):
    """Allocate capital to a specific trading strategy."""
    
@app.get("/trading/balance")
async def get_balance(user_id: str):
    """Get user's trading account balance."""
```

#### 2.2 Natural Language Commands in Aria
**File:** `aria_trading_intel.py` (extend existing)

**New Commands:**
- "Deposit $1000 to trading"
- "Withdraw $500 from trading"
- "Allocate $5000 to Signal Shark"
- "Move $2000 to idle"
- "What's my trading balance?"
- "Enable auto-trading with Signal Shark"
- "Stop auto-trading"

**Implementation:**
```python
async def process_money_command(message: str, user_id: str) -> str:
    """Process money management commands."""
    msg_lower = message.lower()
    
    # Deposit
    if "deposit" in msg_lower:
        amount = extract_amount(msg_lower)
        return await deposit_to_trading(user_id, amount)
    
    # Withdraw
    if "withdraw" in msg_lower:
        amount = extract_amount(msg_lower)
        return await withdraw_from_trading(user_id, amount)
    
    # Allocate to strategy
    if "allocate" in msg_lower or "move to" in msg_lower:
        amount = extract_amount(msg_lower)
        strategy = extract_strategy(msg_lower)
        return await allocate_to_strategy(user_id, strategy, amount)
    
    # Check balance
    if "balance" in msg_lower or "how much" in msg_lower:
        return await get_trading_balance(user_id)
    
    # Enable auto-trading
    if "enable" in msg_lower and "auto" in msg_lower:
        strategy = extract_strategy(msg_lower) or "signal-shark"
        return await enable_auto_trading(user_id, strategy)
```

---

### Phase 3: Multi-User Auto-Trading System (Priority 2)

#### 3.1 User Account Structure
**Database Schema:**
```sql
CREATE TABLE user_accounts (
    user_id TEXT PRIMARY KEY,
    total_balance REAL DEFAULT 0.0,
    trading_balance REAL DEFAULT 0.0,
    idle_balance REAL DEFAULT 0.0,
    auto_trade_enabled BOOLEAN DEFAULT FALSE,
    active_strategy TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE strategy_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    strategy_name TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_accounts(user_id)
);
```

#### 3.2 Auto-Trading Loop
**File:** `whaletrack-magnetic-trader/backend/core/auto_trading_loop.py`

**Features:**
- Runs continuously for each user with auto-trade enabled
- Monitors market signals
- Executes trades when Signal Shark conditions met
- Updates user balances
- Logs all trades

---

### Phase 4: Aria Integration Points (Priority 2)

#### 4.1 Connect Aria to Trading System
**File:** `SERVICES/aria/app/main.py`

**Add Trading Context:**
```python
# In ARIA chat method, add trading context
trading_context = {
    "user_id": request.context.get("user_id"),
    "trading_enabled": await check_auto_trade_enabled(user_id),
    "balance": await get_trading_balance(user_id),
    "active_strategy": await get_active_strategy(user_id),
    "recent_performance": await get_recent_performance(user_id)
}

# Include in prompt
prompt = self._build_prompt(request.message, session["history"], {
    **request.context,
    "trading": trading_context
})
```

#### 4.2 Aria Trading Commands Handler
**File:** `aria_trading_intel.py` (extend)

**Add Money Management:**
```python
async def process_money_management(message: str, user_id: str) -> Optional[str]:
    """Process money management commands."""
    # Deposit, withdraw, allocate, balance checks
    # Connect to whaletrack-magnet API
    # Return user-friendly responses
```

---

## 📋 Implementation Checklist

### Immediate (Today)
- [ ] Create Signal Shark auto-trader configuration
- [ ] Add `/api/auto-trade/enable` endpoint
- [ ] Add `/api/trading/deposit` endpoint
- [ ] Add `/api/trading/withdraw` endpoint
- [ ] Add `/api/trading/balance` endpoint
- [ ] Extend Aria to handle money commands
- [ ] Test with single user

### Short-term (This Week)
- [ ] Create user accounts database schema
- [ ] Implement auto-trading loop
- [ ] Add strategy allocation tracking
- [ ] Add performance reporting to Aria
- [ ] Test multi-user scenarios

### Medium-term (Next 2 Weeks)
- [ ] Add risk management per user
- [ ] Add withdrawal limits/cooldowns
- [ ] Add performance dashboards
- [ ] Add email/SMS notifications
- [ ] Production deployment

---

## 🎯 User Experience Flow

### Example: User Enables Auto-Trading via Aria

**User:** "Hey Aria, I want to start auto-trading with Signal Shark"

**Aria:** "Great! Signal Shark has a 95.7% win rate. How much would you like to allocate?"

**User:** "Allocate $10,000"

**Aria:** "✅ Allocated $10,000 to Signal Shark auto-trading. Your account:
- Trading Balance: $10,000 (active)
- Idle Balance: $0
- Strategy: Signal Shark
- Auto-trading: Enabled

I'll monitor the markets and execute trades automatically when Signal Shark conditions are met. You can check your balance anytime by asking 'What's my trading balance?'"

### Example: User Checks Performance

**User:** "How's my trading doing?"

**Aria:** "📊 **Your Trading Performance:**
- Strategy: Signal Shark
- Allocated: $10,000
- Current Value: $10,245.50
- Total Return: +2.46%
- Win Rate: 96.2%
- Active Positions: 1 (SOL long)
- Today's PnL: +$45.50

Your account is performing well! Signal Shark is actively managing your capital."

### Example: User Moves Money

**User:** "Move $2000 to idle"

**Aria:** "✅ Moved $2,000 from trading to idle balance.
- Trading Balance: $8,000 (active)
- Idle Balance: $2,000
- Total Balance: $10,000

The $2,000 is now idle and won't be used for trading. Say 'move $2000 back to trading' to reactivate."

---

## 🔧 Technical Architecture

### Component Diagram
```
User → Aria Chat → Trading API → Signal Shark Auto-Trader → Market Execution
                ↓
         User Account DB
                ↓
         Balance Tracking
                ↓
         Performance Reporting
```

### Data Flow
1. User sends command to Aria
2. Aria parses command (deposit/withdraw/allocate)
3. Aria calls WhaleTrack Trading API
4. Trading API updates user account
5. Auto-trader monitors market (if enabled)
6. Auto-trader executes trades when conditions met
7. Performance updates sent to Aria
8. Aria reports back to user

---

## 📊 Success Metrics

### Performance Targets
- **Win Rate:** Maintain Signal Shark's 95%+ win rate
- **User Satisfaction:** >90% positive feedback
- **Uptime:** 99.9% availability
- **Response Time:** <2 seconds for Aria commands

### Business Metrics
- **User Adoption:** 10+ users in first month
- **Capital Deployed:** $100K+ total capital
- **Trading Volume:** $1M+ monthly volume
- **Revenue:** Track fees/commissions

---

## 🚨 Risk Management

### Per-User Limits
- Max allocation per strategy: $50,000
- Max daily loss: 5% of allocated capital
- Max positions: 3 concurrent
- Withdrawal cooldown: 24 hours

### System Limits
- Max total capital: $1M (scalable)
- Circuit breaker: Pause trading if system-wide loss >10%
- Monitoring: Real-time alerts for anomalies

---

## 📝 Next Steps

1. **Review this plan** - Confirm approach
2. **Start Phase 1** - Create Signal Shark auto-trader
3. **Test with single user** - Validate flow
4. **Deploy to production** - Enable for all users
5. **Monitor and optimize** - Continuous improvement

---

## 🔗 Related Files

- `whaletrack-magnetic-trader/backend/core/auto_trader.py` - Existing auto-trader (reference)
- `aria_trading_intel.py` - Existing trading intelligence (extend)
- `SERVICES/aria/app/main.py` - Aria main app (add endpoints)
- `whaletrack-magnetic-trader/backend/api/main.py` - Trading API (add endpoints)
- `whaletrack-magnetic-trader/backend/core/treasury.py` - Treasury management (extend)



