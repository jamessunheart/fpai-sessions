# Fund Flow Architecture: SQLite vs Hyperliquid

## 🔍 Critical Architecture Clarification

### **The Current Gap:**

**SQLite Database** = **Virtual Accounting System** (NOT actual fund storage)
- Tracks allocation limits
- Records transaction history
- Manages strategy assignments
- **Does NOT hold real funds**

**Hyperliquid** = **Actual Fund Storage & Execution**
- Real crypto/USD funds stored here
- Trades execute directly on Hyperliquid
- User connects via API secret
- **This is where real money lives**

---

## 📊 Current Flow (How It Actually Works)

### Step 1: User Connects Hyperliquid Account
```
User provides Hyperliquid API secret
    ↓
System creates Hyperliquid adapter
    ↓
Can now execute trades with user's Hyperliquid funds
```

### Step 2: User "Deposits" in SQLite (Virtual Allocation)
```
User: "Deposit $10,000"
    ↓
SQLite: idle_balance = $10,000 ✅
    ↓
BUT: No actual funds moved!
    ↓
This is just a "virtual allocation limit"
```

### Step 3: User Allocates to Strategy
```
User: "Allocate $5,000 to Signal Shark"
    ↓
SQLite: trading_balance = $5,000 ✅
    ↓
BUT: Still no actual funds moved!
    ↓
This sets a "spending limit" for the strategy
```

### Step 4: Auto-Trader Executes Trade
```
Strategy detects signal
    ↓
Checks SQLite: "Do I have allocation?" ✅ ($5,000 available)
    ↓
Calls Hyperliquid adapter
    ↓
Executes trade using REAL funds from Hyperliquid
    ↓
SQLite records trade (for accounting)
```

---

## ⚠️ The Problem

**SQLite "deposits" don't actually move funds!**

Current implementation:
- ✅ SQLite tracks allocations (virtual)
- ✅ Hyperliquid holds real funds
- ❌ **No connection between them**
- ❌ User must manually deposit to Hyperliquid
- ❌ SQLite balance ≠ Hyperliquid balance

---

## 🔧 How It Should Work

### Option 1: SQLite as Allocation Limits Only (Current)

**Flow:**
1. User deposits funds **directly to Hyperliquid** (external)
2. User connects Hyperliquid account to system
3. SQLite tracks "allocation limits" (how much to use per strategy)
4. Trades execute using Hyperliquid funds
5. SQLite records trades for accounting

**Pros:**
- ✅ Simple
- ✅ User controls their Hyperliquid account
- ✅ No fund custody risk

**Cons:**
- ❌ SQLite balance is "fake" (just a limit)
- ❌ User must manually sync balances
- ❌ Confusing UX

### Option 2: Add Hyperliquid Balance Sync

**Flow:**
1. User connects Hyperliquid account
2. System reads actual Hyperliquid balance
3. SQLite syncs with Hyperliquid balance
4. "Deposit" command updates Hyperliquid allocation limit
5. Trades execute using Hyperliquid funds

**Implementation:**
```python
async def sync_hyperliquid_balance(user_id: str):
    """Sync SQLite balance with actual Hyperliquid balance."""
    adapter = get_hyperliquid_adapter(user_id)
    if not adapter:
        return
    
    # Get actual balance from Hyperliquid
    user_state = adapter["info"].user_state(cfg["main_account"])
    actual_balance = float(user_state.get("marginSummary", {}).get("accountValue", 0))
    
    # Update SQLite to match
    account_manager = get_account_manager()
    account = account_manager.get_balance(user_id)
    
    # Sync idle_balance with Hyperliquid balance
    if account.idle_balance != actual_balance:
        # Adjust SQLite to match reality
        account_manager._sync_balance(user_id, actual_balance)
```

### Option 3: Full Custody Model (Not Recommended)

**Flow:**
1. User deposits funds to system
2. System holds funds in Hyperliquid sub-account
3. System manages all fund movements
4. User can't directly access Hyperliquid

**Pros:**
- ✅ Unified balance system
- ✅ Simple UX

**Cons:**
- ❌ Custody risk
- ❌ Regulatory complexity
- ❌ User loses control

---

## 💡 Recommended Solution: Option 2 (Balance Sync)

### Implementation Plan

**1. Add Balance Sync Endpoint**
```python
@app.post("/api/account/sync-hyperliquid")
async def sync_hyperliquid_balance(
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Sync SQLite balance with actual Hyperliquid balance."""
    user_id = user["user_id"]
    
    # Get Hyperliquid adapter
    adapter = get_hyperliquid_adapter(user_id)
    if not adapter:
        raise HTTPException(400, "Hyperliquid not connected")
    
    # Get actual balance
    cfg = get_user_live_trading_config(user_id)
    user_state = adapter["info"].user_state(cfg["main_account"])
    hyperliquid_balance = float(
        user_state.get("marginSummary", {}).get("accountValue", 0)
    )
    
    # Sync SQLite
    account_manager = get_account_manager()
    account = account_manager.get_balance(user_id)
    
    # Calculate difference
    total_allocated = sum(account.allocated_to_strategies.values())
    expected_idle = hyperliquid_balance - total_allocated
    
    # Update SQLite idle_balance to match Hyperliquid
    if account.idle_balance != expected_idle:
        # Adjust SQLite balance
        diff = expected_idle - account.idle_balance
        if diff > 0:
            # Add difference
            account_manager.deposit(user_id, diff, source="hyperliquid_sync")
        # Note: Don't subtract if Hyperliquid has less (might be in positions)
    
    return {
        "hyperliquid_balance": hyperliquid_balance,
        "sqlite_idle_balance": account.idle_balance,
        "synced": True
    }
```

**2. Auto-Sync on Trade Execution**
```python
# In strategy_auto_trader.py, after trade execution:
async def _record_trade_open(self, position: Position):
    """Record trade and sync balances."""
    # Record trade (existing code)
    
    # Sync Hyperliquid balance
    await self._sync_hyperliquid_balance()
```

**3. Update Deposit Command**
```python
# In trading_commands.py
if "deposit" in msg_lower:
    # Check if Hyperliquid connected
    resp = await self.client.get(f"{TRADING_API_BASE}/api/live/status")
    if resp.status_code == 200:
        status = resp.json()
        if status.get("connected"):
            return (
                "💡 Your Hyperliquid account is connected.\n"
                "Funds are managed through your Hyperliquid account.\n"
                "Use 'Sync balance' to update allocation limits.\n\n"
                "To add funds:\n"
                "1. Deposit to your Hyperliquid account (external)\n"
                "2. Say 'Sync balance' to update limits"
            )
```

---

## 📋 Current State Summary

### What SQLite Does:
- ✅ Tracks allocation limits per strategy
- ✅ Records transaction history
- ✅ Manages strategy assignments
- ✅ Provides accounting/audit trail

### What SQLite Does NOT Do:
- ❌ Hold actual funds
- ❌ Move funds to Hyperliquid
- ❌ Sync with Hyperliquid balance automatically

### What Hyperliquid Does:
- ✅ Holds real crypto/USD funds
- ✅ Executes trades
- ✅ Manages positions
- ✅ Provides real-time balance

### The Connection:
- User connects Hyperliquid account → System can trade
- SQLite sets allocation limits → Controls how much to use
- Trades execute on Hyperliquid → Using real funds
- SQLite records trades → For accounting

---

## 🚀 Next Steps

1. **Add Balance Sync** - Sync SQLite with Hyperliquid balance
2. **Update Deposit Flow** - Clarify that deposits go to Hyperliquid
3. **Add Sync Command** - "Sync balance" to update SQLite from Hyperliquid
4. **Update Documentation** - Clarify that SQLite is allocation tracking, not fund storage

---

## 💬 User Communication

**Current (Confusing):**
```
User: "Deposit $10,000"
Aria: "✅ Deposited $10,000 to your account"
[But no actual funds moved!]
```

**Better (Clear):**
```
User: "Deposit $10,000"
Aria: "💡 To add funds for trading:
      1. Deposit $10,000 to your Hyperliquid account
      2. Say 'Sync balance' to update allocation limits
      
      Your Hyperliquid account is connected: ✅"
```

**Or with Auto-Sync:**
```
User: "Sync balance"
Aria: "✅ Synced with Hyperliquid
      Hyperliquid Balance: $10,000
      Available for Allocation: $10,000
      Allocated to Strategies: $0"
```

---

## ✅ Conclusion

**SQLite = Virtual Allocation System**
- Tracks how much capital to allocate per strategy
- Provides accounting and audit trail
- Does NOT hold real funds

**Hyperliquid = Real Fund Storage**
- Holds actual crypto/USD
- Executes trades
- This is where real money lives

**The Connection:**
- User connects Hyperliquid → System can trade
- SQLite sets limits → Controls allocation
- Trades execute on Hyperliquid → Using real funds
- SQLite records → For accounting

**Missing Piece:**
- Need balance sync to keep SQLite aligned with Hyperliquid reality



