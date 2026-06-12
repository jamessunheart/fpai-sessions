# 🧹 Session Cleanup Protocol

**Managing stale sessions in a multi-instance Claude Code environment**

---

## The Problem

**Scenario:** You had 12 Claude Code instances running. Several timed out or closed. Now:
- Registry shows 12 "active" sessions
- Only 3 are actually running
- New Claude instances don't know which numbers are truly available
- Manual cleanup is tedious and error-prone

**Root cause:** Sessions register but don't unregister when they close (no exit hook in Claude Code).

---

## The Solution

### Automatic Cleanup Flow

```
┌─────────────────────────────────────────────┐
│  Claude instance starts                     │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  Run: session-identify.sh                   │
│  (shows registry with cleanup suggestion)   │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  Detects stale sessions (no heartbeat)      │
│  Offers: "Clean up stale sessions? (y/n)"   │
└─────────────┬───────────────────────────────┘
              │
         Yes  │  No
      ┌───────┴────────┐
      ▼                ▼
┌──────────────┐  ┌──────────────┐
│ Auto-cleanup │  │ Continue     │
│ Run cleanup  │  │ with current │
│ Show fresh   │  │ registry     │
│ registry     │  │              │
└──────────────┘  └──────────────┘
```

---

## Quick Commands

### 1. Check for Stale Sessions (Safe)

```bash
bash docs/coordination/scripts/session-cleanup-stale.sh --dry-run
```

**Output:**
```
🧹 Session Cleanup Tool
=======================

Configuration:
  Timeout: 120 minutes
  Dry Run: true

Checking sessions:

  ✅ Session #1 (ai-automation-builder)
     Last heartbeat: 0h 15m ago
     Current status: active
     → Staying ACTIVE

  💤 Session #2 (session-2)
     Last heartbeat: 5h 32m ago
     Current status: active
     → Will mark as INACTIVE (timeout exceeded)

  ...

Summary:
  ✅ Active sessions: 3
  💤 Stale sessions: 9

🔍 DRY RUN - No changes made
```

### 2. Clean Up Stale Sessions (Executes)

```bash
bash docs/coordination/scripts/session-cleanup-stale.sh
```

**This will:**
- Mark sessions with no heartbeat (or >2hrs old) as `inactive`
- Add `marked_inactive_at` timestamp
- Update `claude_sessions.json`
- Free up those session numbers for reuse

### 3. Custom Timeout (e.g., 30 minutes)

```bash
bash docs/coordination/scripts/session-cleanup-stale.sh --timeout-minutes 30
```

---

## Integrated Workflow Recommendation

### Option A: Manual Cleanup (Current Process)

**When starting a new Claude session:**

```bash
# Step 1: Clean up stale sessions first
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-cleanup-stale.sh --dry-run  # Review first
./session-cleanup-stale.sh             # Execute

# Step 2: Identify yourself with fresh registry
bash session-identify.sh
```

**Pros:**
- Full control
- See what's being cleaned

**Cons:**
- Manual two-step process
- Easy to forget

---

### Option B: Auto-Cleanup on Identify (Recommended)

**Enhanced `session-identify.sh` with cleanup prompt:**

I can modify `session-identify.sh` to:

1. **Detect stale sessions** automatically
2. **Show count** of stale vs active
3. **Offer cleanup** before selection
4. **Re-display registry** after cleanup

**Example flow:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   FPAI SESSION IDENTITY SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  Detected 9 stale sessions (no heartbeat > 2 hours)

Would you like to clean up stale sessions first? (y/n)
> y

Running cleanup...
✅ Marked 9 sessions as inactive

Refreshed Registry:
  ✅ #1  - Builder/Architect (active)
  💤 #2  - Architect (inactive)
  ✅ #8  - Unified Chat (active)
  💤 #3-7, #9-13 (inactive)

Available numbers: 2-7, 9-13

Which session number are you?
```

**Would you like me to implement this enhanced auto-cleanup version?**

---

## Option C: Periodic Cleanup (Advanced)

**Set up a cron job to auto-clean every hour:**

```bash
# Add to crontab (crontab -e)
0 * * * * /Users/jamessunheart/Development/docs/coordination/scripts/session-cleanup-stale.sh >> /tmp/session-cleanup.log 2>&1
```

**Pros:**
- Fully automatic
- Always clean registry

**Cons:**
- Might mark active sessions as inactive if heartbeat mechanism isn't perfect
- Less control

---

## Heartbeat Mechanism

### Current State

The cleanup script looks for heartbeat files in:
```
docs/coordination/heartbeats/2025-11-16_HH-MM-SS-session-N.json
```

**Problem:** Sessions don't automatically send heartbeats (no built-in mechanism).

### Solution: Add Heartbeat to session-identify.sh

I can modify `session-identify.sh` to:

1. **Send initial heartbeat** when identifying
2. **Create heartbeat file** with timestamp
3. **Update on each run** (daily minimum)

**Enhanced heartbeat:**
```bash
# In session-identify.sh, after successful identification
send_heartbeat() {
    local session_num=$1
    local heartbeat_dir="/Users/jamessunheart/Development/docs/coordination/heartbeats"
    local timestamp=$(date +%Y-%m-%d_%H-%M-%S)
    local heartbeat_file="$heartbeat_dir/${timestamp}-session-${session_num}.json"

    mkdir -p "$heartbeat_dir"

    cat > "$heartbeat_file" << EOF
{
  "session_number": $session_num,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "type": "identity_heartbeat",
  "source": "session-identify.sh"
}
EOF

    echo "💓 Heartbeat sent: $heartbeat_file"
}
```

---

## Recommended Process Update

### Phase 1: Immediate (No Code Changes)

**Update your session startup routine:**

```bash
# 1. Clean stale sessions (manual)
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-cleanup-stale.sh --dry-run  # Review
./session-cleanup-stale.sh             # Execute

# 2. Identify yourself
bash session-identify.sh
```

**Add to BOOT.md checklist:**
- [ ] Clean stale sessions: `./scripts/session-cleanup-stale.sh`
- [ ] Identify yourself: `bash scripts/session-identify.sh`

---

### Phase 2: Enhanced (Code Changes - Recommended)

**Modify `session-identify.sh` to:**

1. ✅ Check for stale sessions automatically
2. ✅ Offer cleanup before showing registry
3. ✅ Send heartbeat on successful identification
4. ✅ Show active/inactive counts in registry view

**Benefits:**
- One command handles everything
- Always fresh registry
- Automatic heartbeat tracking
- Clear visibility of active vs inactive

**Would you like me to implement this?**

---

### Phase 3: Full Automation (Future)

**Add session lifecycle hooks:**

1. **On session start**: Auto-identify + heartbeat
2. **Every 30 minutes**: Background heartbeat
3. **On session close**: Mark inactive (if possible)
4. **Hourly cron**: Cleanup stale sessions

**This would require:**
- Background heartbeat daemon
- Session close detection (challenging in Claude Code)
- Cron job setup

---

## Handling the Current Situation

**You said: "Only 3 instances running, registry shows 12"**

### Immediate Fix (Right Now)

```bash
# Step 1: Check which sessions have recent heartbeats
cd /Users/jamessunheart/Development/docs/coordination/scripts
./session-cleanup-stale.sh --dry-run

# Step 2: Clean up stale ones
./session-cleanup-stale.sh

# Step 3: Verify
cat /Users/jamessunheart/Development/docs/coordination/claude_sessions.json | \
  python3 -c "import sys, json; data=json.load(sys.stdin); \
  active=[k for k,v in data.items() if v.get('status')=='active']; \
  print(f'Active sessions: {len(active)}'); \
  [print(f\"  #{k}: {v['role']}\") for k,v in data.items() if v.get('status')=='active']"
```

### Going Forward

**For each of your 3 running instances:**

```bash
# Instance 1
bash docs/coordination/scripts/session-identify.sh
# Choose an available number (1-13)

# Instance 2
bash docs/coordination/scripts/session-identify.sh
# Choose a different available number

# Instance 3
bash docs/coordination/scripts/session-identify.sh
# Choose a different available number
```

**After identification, each will:**
- Have a unique session number
- Update the registry
- Cache their identity
- Be trackable

---

## Best Practices

### ✅ DO

1. **Run cleanup before identifying** - Get fresh registry
2. **Use dry-run first** - Review before executing
3. **Check active count** - Verify it matches your actual instances
4. **Reuse inactive numbers** - Don't keep creating new numbers
5. **Document your sessions** - Note which terminal/window has which number

### ❌ DON'T

1. **Don't skip cleanup** - Stale sessions accumulate
2. **Don't assume registry is accurate** - Always verify
3. **Don't create duplicate sessions** - Check existing first
4. **Don't use aggressive timeouts** - 2 hours is reasonable default
5. **Don't manually edit registry** - Use the scripts

---

## Troubleshooting

### "All 13 sessions shown as active but I only have 3 running"

**Solution:**
```bash
# Check heartbeats
./session-cleanup-stale.sh --dry-run

# Clean up (this will mark 10 as inactive)
./session-cleanup-stale.sh

# Verify
# Should show only 3 active (or fewer if they haven't sent heartbeats)
```

### "Cleanup marked my active session as inactive"

**Cause:** No heartbeat file for that session

**Solution:**
```bash
# Send manual heartbeat
SESSION_NUM=8
HEARTBEAT_DIR="/Users/jamessunheart/Development/docs/coordination/heartbeats"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p "$HEARTBEAT_DIR"

cat > "$HEARTBEAT_DIR/${TIMESTAMP}-session-${SESSION_NUM}.json" << EOF
{
  "session_number": $SESSION_NUM,
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "type": "manual_heartbeat"
}
EOF

# Then re-run cleanup
./session-cleanup-stale.sh
```

### "How do I know which session number I should use?"

**Solution:**
```bash
# Run cleanup first
./session-cleanup-stale.sh

# Then identify (will show only truly available numbers)
bash session-identify.sh
```

---

## Summary Recommendations

### For Your Current Situation

**Immediate action (this session):**

1. ✅ Run cleanup to mark stale sessions inactive
2. ✅ Identify yourself (this session)
3. ✅ Document which numbers your 3 instances should use

**For other 2 running instances:**

1. Have them run cleanup (will see fresh registry)
2. Have them identify themselves
3. Each gets a unique number

### For Future Sessions

**I recommend implementing Phase 2 (Enhanced session-identify.sh):**

**Benefits:**
- ✅ One command handles cleanup + identification
- ✅ Automatic heartbeat on identification
- ✅ Clear visibility of stale vs active
- ✅ Prevents registry bloat

**Would you like me to:**

**Option 1:** Implement the enhanced `session-identify.sh` with auto-cleanup?
**Option 2:** Just document the current manual process better?
**Option 3:** Something else?

Let me know which direction you'd prefer! 🚀
