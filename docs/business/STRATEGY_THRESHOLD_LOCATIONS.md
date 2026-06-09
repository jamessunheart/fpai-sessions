# Strategy Threshold Configuration Locations
**Date:** December 14, 2025

---

## 🔍 Findings

### Where Strategy Thresholds Are Configured

#### 1. **System-Level Strategies (Whale/Minnow)**
**Location:** `whaletrack-magnetic-trader/backend/config/`

- **`whale_config.py`**: 
  - `min_whale_confidence: 60` (line 33)
  - `min_velocity: 35` (line 34)
  - `min_rr: 2.0` (line 35)

- **`minnow_config.py`**:
  - `min_whale_confidence: 50` (line 27)
  - `min_velocity: 35` (line 28)
  - `min_rr: 1.5` (line 29)

**How It Works:**
- Loaded in `main.py` line 664-668 based on `WHALETRACK_STRATEGY` env var
- Passed to `WhaleTrackTradingSystem` which creates `EntryEngine` with these values
- EntryEngine checks `whale_state.confidence < self.min_confidence` at line 127 of `entry_engine.py`

---

#### 2. **User-Specific Strategies (Signal Shark, Signal Shark MAX, Steady Growth)**

**Problem:** These strategies are NOT configured in the backend code!

**Evidence:**
- No config files for "signal-shark", "signal-shark-max", or "steady-growth"
- Strategies are differentiated by **leverage** in trades:
  - Signal Shark: 1.25x leverage
  - Signal Shark MAX: 2.0x leverage  
  - Steady Growth: 1.0x leverage
  - Sweep strategies: 1.0-2.0x leverage

**How They Work:**
- The `/api/strategy/{name}/trades` endpoint likely filters trades by leverage
- Each strategy uses different confidence thresholds when executing trades
- These thresholds are likely stored in:
  1. **User settings** (`/api/auto-trade/users/{user_id}`)
  2. **Frontend configuration** (client-side filtering)
  3. **Separate strategy execution logic** (not found yet)

---

## 🎯 Where to Fix Strategy Thresholds

### Signal Shark MAX (Needs 100% → 90%)

**Current State:** Requires ~100% confidence (too restrictive)

**Where to Fix:**
1. **Check user settings:**
   ```bash
   curl https://fullpotential.ai/whale/api/auto-trade/users/user_3ef802bfab32 | jq '.settings'
   ```
   - If `min_confidence: 100.0` exists, change to `90.0`

2. **Check if there's a strategy-specific config:**
   - Search for "signal-shark-max" in codebase
   - Check for strategy config files in `backend/config/`
   - Check environment variables

3. **Check frontend:**
   - Strategies might be configured client-side
   - Check `fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/`

### Steady Growth (Needs 75% → 65%)

**Current State:** Requires ~75% confidence (too conservative)

**Where to Fix:**
1. **Same as Signal Shark MAX** - check user settings first
2. **Add range-bound market acceptance** - may require code changes
3. **Increase leverage** from 1.0x → 1.25x

---

## 🔧 Implementation Options

### Option 1: User Settings (Most Likely)

If thresholds are in user settings, modify via API:

```python
# Update user settings
PUT /api/auto-trade/users/{user_id}/settings
{
    "min_confidence": 90.0,  # For Signal Shark MAX
    "min_probability": 85.0
}
```

### Option 2: Create Strategy Config Files

Create new config files:
- `whaletrack-magnetic-trader/backend/config/signal_shark_max_config.py`
- `whaletrack-magnetic-trader/backend/config/steady_growth_config.py`

Then load based on strategy name.

### Option 3: Frontend Configuration

If strategies are client-side, modify frontend config:
- Check `website-ai/frontend/app/services/whaletrack/`
- Look for strategy definitions with confidence thresholds

---

## 📊 Current Configuration Values

### System Strategies:
- **Whale:** `min_confidence: 60`, `min_velocity: 35`
- **Minnow:** `min_confidence: 50`, `min_velocity: 35`

### User Strategies (Inferred from behavior):
- **Signal Shark:** `min_confidence: ~70`, leverage: 1.25x
- **Signal Shark MAX:** `min_confidence: ~100`, leverage: 2.0x ❌ **TOO HIGH**
- **Steady Growth:** `min_confidence: ~75`, leverage: 1.0x ❌ **TOO HIGH**
- **Sweep Strategies:** `min_confidence: ~65-70`, leverage: 1.0-2.0x ✅ **FIXED**

---

## 🚀 Next Steps

1. **Check User Settings API:**
   ```bash
   curl https://fullpotential.ai/whale/api/auto-trade/users/user_3ef802bfab32 | jq
   ```

2. **Search Frontend for Strategy Config:**
   ```bash
   grep -r "signal-shark\|steady-growth" fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/
   ```

3. **Check if Strategies Are Differentiated by Leverage:**
   - The `/api/strategy/{name}/trades` endpoint must filter somewhere
   - Check if it filters by leverage in the database query
   - Check if frontend filters client-side

4. **Create Strategy Config Files** (if needed):
   - Add `signal_shark_max_config.py` with `min_confidence: 90`
   - Add `steady_growth_config.py` with `min_confidence: 65`

---

## ⚠️ Important Notes

- **Sweep strategies are FIXED** ✅ (reversal_engine.py updated)
- **Signal Shark MAX and Steady Growth** need threshold adjustments
- Thresholds might be enforced in multiple places:
  - Backend EntryEngine (found)
  - User settings (likely)
  - Frontend filtering (possible)
  - Separate strategy execution logic (unknown)

---

## 🔍 Debugging Commands

```bash
# Check user settings
curl https://fullpotential.ai/whale/api/auto-trade/users/user_3ef802bfab32 | jq '.settings'

# Check strategy info
curl https://fullpotential.ai/whale/api/strategy/info | jq

# Check strategy trades (see leverage)
curl https://fullpotential.ai/whale/api/strategy/signal-shark-max/trades?limit=5 | jq '.trades[0].leverage'

# Search for strategy configs
grep -r "signal-shark\|steady-growth\|min_confidence.*100\|min_confidence.*75" whaletrack-magnetic-trader/
```



