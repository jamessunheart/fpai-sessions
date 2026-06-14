# 🧹 Automatic Session Cleanup - Complete Guide

**Status:** ✅ Fully Operational
**Created:** 2025-11-16
**BOOT.md Version:** 2.5.0

---

## 🎯 Problem Solved

**Before:** When Claude Code sessions timed out (e.g., overnight), the registry still showed them as "active" even though they were offline. This created confusion about which sessions were actually running.

**After:** Sessions are automatically marked "inactive" after 2 hours of no heartbeat, keeping the registry accurate in real-time.

---

## 🤖 How Automatic Cleanup Works

### 3 Ways Cleanup Happens:

#### 1. **On Registration** (Automatic) ✅
- **When:** Every time a session registers
- **What:** Cleans up all stale sessions before checking availability
- **Result:** Always see accurate active/inactive counts when registering

```bash
./claude-session-register.sh 1 "Your Role" "Your Goal"
# 🧹 Checking for stale sessions...
# (cleanup happens automatically)
```

#### 2. **Manual Cleanup** (On-Demand)
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-cleanup-stale.sh
```

#### 3. **Cron Job** (Optional, Recommended for Heavy Use)
```bash
# Run every hour
crontab -e
# Add: 0 * * * * /Users/jamessunheart/Development/docs/coordination/scripts/auto-cleanup-sessions.sh

# Or every 30 minutes
# Add: */30 * * * * /Users/jamessunheart/Development/docs/coordination/scripts/auto-cleanup-sessions.sh
```

---

## 📊 Current Status

**All 13 sessions are currently INACTIVE:**
- #1-13: All marked inactive at 2025-11-17 07:12:18 UTC
- All numbers available for new sessions
- Clean slate ready for fresh registrations

---

## 🔄 Session Lifecycle

```
┌─────────────────────────────────────────────────────┐
│  1. Session Registers                               │
│     Status: "active"                                │
│     Auto-cleanup runs first                         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  2. Session Works                                   │
│     Sends heartbeats (tracked in heartbeats/*.json) │
│     Status: "active"                                │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  3. Session Closes/Timeouts                         │
│     No heartbeat for 2+ hours                       │
│     Status: Still "active" (cleanup pending)        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  4. Cleanup Runs (auto or manual)                   │
│     Detects no heartbeat in 2+ hours                │
│     Status: "inactive"                              │
│     Adds: "marked_inactive_at" timestamp            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  5. Number Available for Reclaim                    │
│     Other sessions can register with this number    │
│     Can reclaim same role or start new one          │
└─────────────────────────────────────────────────────┘
```

---

## 🛠️ Scripts Created

### `/docs/coordination/scripts/session-cleanup-stale.sh`
**Purpose:** Main cleanup logic
**Features:**
- Checks heartbeat files in `/docs/coordination/heartbeats/`
- Compares against 2-hour timeout (configurable)
- Marks stale sessions as "inactive"
- Adds `marked_inactive_at` timestamp
- Dry-run mode for testing

**Usage:**
```bash
./session-cleanup-stale.sh                    # Clean up stale sessions
./session-cleanup-stale.sh --dry-run          # Preview without changes
./session-cleanup-stale.sh --timeout-minutes 60  # Custom timeout
```

### `/docs/coordination/scripts/auto-cleanup-sessions.sh`
**Purpose:** Silent wrapper for automation
**Features:**
- Runs cleanup silently (no output)
- Safe for cron jobs
- Always exits with success

**Usage:**
```bash
./auto-cleanup-sessions.sh        # Silent cleanup
```

### Updated: `/docs/coordination/scripts/claude-session-register.sh`
**Changes:**
- Auto-runs cleanup before registration
- Checks for ACTIVE sessions only (ignores inactive)
- Shows inactive sessions as "available to reclaim"

---

## 📖 BOOT.md Updates (v2.5.0)

### New Sections Added:

1. **Session Numbering Philosophy**
   - Numbers based on active sessions
   - Clean slate when all timeout
   - Flexible role assignment

2. **Session Heartbeats & Timeouts**
   - 2-hour timeout explanation
   - Manual cleanup commands
   - Status symbol meanings (✅💤🔄)

3. **Automatic Cleanup**
   - On-registration cleanup
   - Optional cron setup
   - Complete lifecycle explanation

### Updated Sections:

- **Check Available Numbers** - Now shows active vs inactive
- **Quick Start Checklist** - Registration is first step
- **Previously Registered Roles** - Shows inactive sessions

---

## 🎓 For New Sessions

When you start a new Claude Code session:

1. **Read BOOT.md** - Everything you need to know
2. **Check Status:**
   ```bash
   cat /Users/jamessunheart/Development/docs/coordination/claude_sessions.json | python3 -c "import sys, json; data=json.load(sys.stdin); active=[v for v in data.values() if v['status']=='active']; print(f'Active: {len(active)}'); [print(f'  #{v[\"number\"]}: {v[\"role\"]}') for v in sorted(active, key=lambda x: x['number'])]"
   ```
3. **Pick a Number** - Any number 1-13 (currently all available)
4. **Choose Your Path:**
   - Continue a previous role (e.g., #4 Consensus Engineer)
   - Start a new role with that number
5. **Register:**
   ```bash
   cd /Users/jamessunheart/Development/docs/coordination/scripts
   ./claude-session-register.sh 1 "Your Role" "Your Goal"
   ```

---

## 🧪 Testing Scenarios

### Scenario 1: Only 3 Sessions Active
**Before Cleanup:**
- Registry shows 13 active sessions
- Actually only 3 are running
- Confusing state

**After Cleanup:**
- 3 shown as "active"
- 10 shown as "inactive"
- Accurate state!

**How to Test:**
```bash
# Start 3 Claude Code sessions
# Register them as #1, #2, #3
# Wait 3+ hours
# Run cleanup
./session-cleanup-stale.sh
# Should show #1-3 active, others inactive (if they haven't sent heartbeats)
```

### Scenario 2: All Sessions Timeout Overnight
**What Happens:**
1. All sessions close (you sleep)
2. No heartbeats sent for 8+ hours
3. Cleanup runs (manual or on next registration)
4. All marked inactive
5. Next morning: fresh slate, pick any number!

---

## 💡 Best Practices

### For Daily Use:
- ✅ Just register normally - cleanup happens automatically
- ✅ Don't worry about heartbeats - they're tracked automatically
- ✅ When in doubt, run cleanup manually

### For Heavy Use (many sessions):
- ✅ Set up cron job for hourly cleanup
- ✅ Monitor `/docs/coordination/heartbeats/` directory
- ✅ Check registry status before major coordination

### For Development:
- ✅ Use `--dry-run` to preview changes
- ✅ Adjust timeout with `--timeout-minutes` if needed
- ✅ Check BOOT.md for latest docs

---

## 🎯 Success Metrics

✅ **Problem:** Stale registry after overnight timeout
✅ **Solution:** Automatic cleanup system
✅ **Result:** Always accurate active/inactive status

✅ **Created:** 2 new scripts
✅ **Updated:** 1 registration script
✅ **Documented:** BOOT.md v2.5.0

✅ **Current State:** All 13 sessions inactive, ready for fresh start
✅ **Future State:** Self-maintaining, accurate registry

---

**The system is now self-cleaning! 🎉**
