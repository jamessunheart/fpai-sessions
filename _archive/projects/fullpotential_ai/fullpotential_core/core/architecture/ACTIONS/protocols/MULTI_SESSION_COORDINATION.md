# 🤝 Multi-Session Coordination Protocol

**Purpose:** Enable multiple Claude Code sessions to work collaboratively without conflicts

**Last Updated:** 2025-11-15 10:00 UTC
**Status:** ACTIVE

---

## 🎯 The Problem

**Current State:**
- Multiple Claude sessions running simultaneously
- Each session only communicates with user
- No visibility into what other sessions are doing
- Risk of overwriting each other's work
- Coordination happens through user (slow bottleneck)

**What We Need:**
- Sessions see each other's status in real-time
- Sessions claim work to avoid conflicts
- Sessions communicate directly (async, file-based)
- Sessions coordinate like a team, not isolated workers

---

## 🏗️ System Design

### Core Principles

1. **File-Based Coordination** - No databases, just files (git-compatible)
2. **Asynchronous** - Sessions don't block waiting for each other
3. **Heartbeat Model** - Regular status updates (every action)
4. **Work Claims** - Explicit ownership to prevent conflicts
5. **Message Passing** - Sessions leave notes for each other

### Directory Structure

```
COORDINATION/
│
├── sessions/                   ← Active session registry
│   ├── session-001.json        ← Each session has a file
│   ├── session-002.json
│   └── session-003.json
│
├── heartbeats/                 ← Recent activity (auto-cleanup)
│   ├── 2025-11-15_10-00-session-001.json
│   ├── 2025-11-15_10-01-session-002.json
│   └── ...
│
├── claims/                     ← Work ownership
│   ├── droplet-church-guidance.claim
│   ├── droplet-dashboard.claim
│   └── file-CONSCIOUSNESS.md.claim
│
├── messages/                   ← Inter-session communication
│   ├── broadcast/              ← Messages to all sessions
│   └── direct/                 ← Messages to specific sessions
│       ├── session-001/
│       ├── session-002/
│       └── session-003/
│
├── STATUS_BOARD.md             ← Human-readable overview
│
└── handoffs/                   ← Session transitions (existing)
    └── ...
```

---

## 🔄 Session Lifecycle

### 1. Session Registration (On Start)

**When:** First message in new session

**Action:** Create session file
```json
{
  "session_id": "session-001",
  "started_at": "2025-11-15T10:00:00Z",
  "status": "active",
  "current_work": null,
  "capabilities": ["general-purpose", "build", "debug"],
  "last_heartbeat": "2025-11-15T10:00:00Z"
}
```

**File:** `COORDINATION/sessions/session-{id}.json`

### 2. Heartbeat (Every Significant Action)

**When:**
- Start working on something
- Complete a task
- Switch tasks
- Before claiming work
- After releasing work

**Action:** Update heartbeat
```json
{
  "session_id": "session-001",
  "timestamp": "2025-11-15T10:05:00Z",
  "action": "building",
  "target": "church-guidance-ministry droplet",
  "phase": "BUILD - implementing landing page",
  "files_touched": ["agents/services/church-guidance-ministry/BUILD/src/main.py"],
  "progress": "30%",
  "next_action": "implement intake form",
  "estimated_completion": "2025-11-15T12:00:00Z"
}
```

**File:** `COORDINATION/heartbeats/{timestamp}-{session-id}.json`

**Cleanup:** Delete heartbeats older than 24 hours

### 3. Work Claiming (Before Starting)

**When:** About to work on a droplet, file, or task

**Action:** Create claim file
```json
{
  "claimed_by": "session-001",
  "claimed_at": "2025-11-15T10:00:00Z",
  "resource_type": "droplet",
  "resource_name": "church-guidance-ministry",
  "phase": "BUILD",
  "estimated_duration": "4 hours",
  "expires_at": "2025-11-15T14:00:00Z",
  "allow_coordination": true
}
```

**File:** `COORDINATION/claims/{resource-type}-{resource-name}.claim`

**Check Before Claiming:**
```bash
# Check if someone else already claimed this
if [ -f "COORDINATION/claims/droplet-church-guidance.claim" ]; then
  # Read the claim
  # If expired, take over
  # If active, coordinate or pick different work
fi
```

### 4. Work Release (When Done or Switching)

**Action:** Delete claim file, send completion message
```bash
rm COORDINATION/claims/droplet-church-guidance.claim
```

**Send Message:**
```json
{
  "from": "session-001",
  "to": "broadcast",
  "timestamp": "2025-11-15T12:00:00Z",
  "type": "work_completed",
  "subject": "church-guidance-ministry BUILD phase complete",
  "details": {
    "resource": "church-guidance-ministry",
    "phase_completed": "BUILD",
    "next_phase": "PRODUCTION",
    "files_modified": ["..."],
    "tests_passing": true
  }
}
```

### 5. Session Shutdown (On End)

**Action:** Update session status, release all claims
```json
{
  "session_id": "session-001",
  "status": "completed",
  "ended_at": "2025-11-15T12:00:00Z",
  "total_duration": "2 hours",
  "work_completed": ["church-guidance-ministry BUILD phase"],
  "handoff_notes": "Ready for PRODUCTION deployment"
}
```

---

## 📋 Session Actions (Scripts)

### session-start.sh
```bash
#!/bin/bash
# Register this session
SESSION_ID="session-$(date +%s)"
echo $SESSION_ID > COORDINATION/.current_session

cat > COORDINATION/sessions/$SESSION_ID.json <<EOF
{
  "session_id": "$SESSION_ID",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "active",
  "current_work": null,
  "last_heartbeat": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "✅ Session $SESSION_ID registered"
```

### session-heartbeat.sh
```bash
#!/bin/bash
# Send heartbeat
SESSION_ID=$(cat COORDINATION/.current_session)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M)

cat > COORDINATION/heartbeats/${TIMESTAMP}-${SESSION_ID}.json <<EOF
{
  "session_id": "$SESSION_ID",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "action": "$1",
  "target": "$2",
  "phase": "$3"
}
EOF

# Update session file
# ... (update last_heartbeat, current_work)

# Cleanup old heartbeats (>24h)
find COORDINATION/heartbeats -name "*.json" -mtime +1 -delete
```

### session-claim.sh
```bash
#!/bin/bash
# Claim work
RESOURCE_TYPE=$1
RESOURCE_NAME=$2
SESSION_ID=$(cat COORDINATION/.current_session)

CLAIM_FILE="COORDINATION/claims/${RESOURCE_TYPE}-${RESOURCE_NAME}.claim"

# Check if already claimed
if [ -f "$CLAIM_FILE" ]; then
  # Check if expired
  CLAIMED_BY=$(jq -r '.claimed_by' $CLAIM_FILE)
  EXPIRES_AT=$(jq -r '.expires_at' $CLAIM_FILE)

  if [ "$CLAIMED_BY" != "$SESSION_ID" ]; then
    # Check if expired (would need date comparison)
    echo "⚠️  Already claimed by $CLAIMED_BY"
    echo "Check COORDINATION/claims/${RESOURCE_TYPE}-${RESOURCE_NAME}.claim"
    exit 1
  fi
fi

# Create claim
cat > $CLAIM_FILE <<EOF
{
  "claimed_by": "$SESSION_ID",
  "claimed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "resource_type": "$RESOURCE_TYPE",
  "resource_name": "$RESOURCE_NAME",
  "expires_at": "$(date -u -v +4H +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "✅ Claimed: $RESOURCE_TYPE/$RESOURCE_NAME"
```

### session-release.sh
```bash
#!/bin/bash
# Release work
RESOURCE_TYPE=$1
RESOURCE_NAME=$2

CLAIM_FILE="COORDINATION/claims/${RESOURCE_TYPE}-${RESOURCE_NAME}.claim"

if [ -f "$CLAIM_FILE" ]; then
  rm $CLAIM_FILE
  echo "✅ Released: $RESOURCE_TYPE/$RESOURCE_NAME"
else
  echo "⚠️  No claim found for $RESOURCE_TYPE/$RESOURCE_NAME"
fi
```

### session-status.sh
```bash
#!/bin/bash
# View all session status

echo "=== ACTIVE SESSIONS ==="
for session in COORDINATION/sessions/*.json; do
  if [ -f "$session" ]; then
    SESSION_ID=$(jq -r '.session_id' $session)
    STATUS=$(jq -r '.status' $session)
    WORK=$(jq -r '.current_work // "idle"' $session)
    LAST=$(jq -r '.last_heartbeat' $session)

    echo "$SESSION_ID: $STATUS - $WORK (last: $LAST)"
  fi
done

echo ""
echo "=== ACTIVE CLAIMS ==="
for claim in COORDINATION/claims/*.claim; do
  if [ -f "$claim" ]; then
    CLAIMED_BY=$(jq -r '.claimed_by' $claim)
    RESOURCE=$(jq -r '.resource_name' $claim)
    TYPE=$(jq -r '.resource_type' $claim)

    echo "$TYPE: $RESOURCE (claimed by $CLAIMED_BY)"
  fi
done
```

### session-send-message.sh
```bash
#!/bin/bash
# Send message to other sessions
TO=$1  # "broadcast" or "session-XXX"
SUBJECT=$2
MESSAGE=$3

SESSION_ID=$(cat COORDINATION/.current_session)
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)

if [ "$TO" = "broadcast" ]; then
  MSG_FILE="COORDINATION/messages/broadcast/${TIMESTAMP}-${SESSION_ID}.json"
else
  MSG_FILE="COORDINATION/messages/direct/${TO}/${TIMESTAMP}-${SESSION_ID}.json"
  mkdir -p "COORDINATION/messages/direct/${TO}"
fi

cat > $MSG_FILE <<EOF
{
  "from": "$SESSION_ID",
  "to": "$TO",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "subject": "$SUBJECT",
  "message": "$MESSAGE"
}
EOF

echo "✅ Message sent to $TO"
```

### session-check-messages.sh
```bash
#!/bin/bash
# Check for new messages

SESSION_ID=$(cat COORDINATION/.current_session)

echo "=== BROADCAST MESSAGES ==="
ls -t COORDINATION/messages/broadcast/*.json 2>/dev/null | head -5 | while read msg; do
  echo "From: $(jq -r '.from' $msg)"
  echo "Subject: $(jq -r '.subject' $msg)"
  echo "Message: $(jq -r '.message' $msg)"
  echo "---"
done

echo ""
echo "=== DIRECT MESSAGES ==="
ls -t COORDINATION/messages/direct/${SESSION_ID}/*.json 2>/dev/null | head -5 | while read msg; do
  echo "From: $(jq -r '.from' $msg)"
  echo "Subject: $(jq -r '.subject' $msg)"
  echo "Message: $(jq -r '.message' $msg)"
  echo "---"
done
```

---

## 📊 Status Board (Auto-Generated)

**File:** `COORDINATION/STATUS_BOARD.md`

**Updated by:** Each heartbeat

**Example:**
```markdown
# 🤝 Multi-Session Status Board

**Last Updated:** 2025-11-15 10:05 UTC
**Active Sessions:** 3

---

## 🟢 Active Sessions

### session-001 (Started: 10:00 UTC)
- **Status:** Building
- **Working On:** church-guidance-ministry droplet
- **Phase:** BUILD - implementing landing page
- **Progress:** 30%
- **Last Update:** 2 minutes ago
- **Next:** Implement intake form
- **Est. Complete:** 12:00 UTC

### session-002 (Started: 09:45 UTC)
- **Status:** Testing
- **Working On:** dashboard deployment
- **Phase:** PRODUCTION - testing deployment
- **Progress:** 85%
- **Last Update:** 5 minutes ago
- **Next:** Final verification
- **Est. Complete:** 10:30 UTC

### session-003 (Started: 10:00 UTC)
- **Status:** Planning
- **Working On:** treasury deployment strategy
- **Phase:** Research
- **Progress:** 15%
- **Last Update:** 1 minute ago
- **Next:** Review market timing
- **Est. Complete:** 11:00 UTC

---

## 🔒 Active Claims

- **droplet/church-guidance-ministry** - session-001 (expires 14:00 UTC)
- **droplet/dashboard** - session-002 (expires 10:30 UTC)
- **file/TREASURY_DYNAMIC_STRATEGY.md** - session-003 (expires 11:00 UTC)

---

## 📬 Recent Messages (Last Hour)

- **10:03** - session-002 → broadcast: "Dashboard tests passing, ready for final deployment"
- **10:01** - session-001 → broadcast: "Starting church guidance ministry BUILD phase"
- **10:00** - session-003 → session-001: "FYI - I'm researching treasury, may have insights for church revenue model"

---

## ⚠️ Coordination Needed

- None detected

---

**Auto-refreshes:** Every heartbeat
**View:** `cat COORDINATION/STATUS_BOARD.md`
```

---

## 🚦 Coordination Rules

### Rule 1: Heartbeat Before Major Actions
**Always send heartbeat:**
- Before claiming work
- Before starting implementation
- After completing significant milestones
- Before switching tasks
- When encountering blockers

### Rule 2: Claim Before Touching
**Always claim:**
- Droplets you're building
- Files you're editing (if major changes)
- Shared resources (deployment slots, API keys, etc.)

**Don't need to claim:**
- Reading files
- Creating new files (not editing existing)
- Running tests (read-only)

### Rule 3: Check Status Before Starting
**Before picking up work:**
```bash
# Check what others are doing
./COORDINATION/scripts/session-status.sh

# Check if anyone claimed your target
ls COORDINATION/claims/ | grep your-target

# Check recent messages
./COORDINATION/scripts/session-check-messages.sh
```

### Rule 4: Broadcast Completions
**When finishing work:**
- Release claim
- Send broadcast message
- Update STATUS_BOARD
- Update droplet README

### Rule 5: Coordinate on Conflicts
**If work is claimed:**
- Check if expired (take over)
- Check if can help (send message)
- Pick different work
- Wait for release

---

## 🎯 Integration with Assembly Line

### When Building Droplets

**Phase 1: SPECS**
```bash
# Before starting SPECS
./session-claim.sh droplet church-guidance-ministry
./session-heartbeat.sh "planning" "church-guidance-ministry" "SPECS"

# During SPECS
# (update README as you go)

# After SPECS complete
./session-heartbeat.sh "completed" "church-guidance-ministry" "SPECS complete"
./session-send-message.sh broadcast "SPECS complete for church-guidance-ministry" "Ready for BUILD phase - 4-6 hours estimated"
```

**Phase 2: BUILD**
```bash
# Before starting BUILD
./session-heartbeat.sh "building" "church-guidance-ministry" "BUILD - landing page"

# During BUILD (heartbeat on each major component)
./session-heartbeat.sh "building" "church-guidance-ministry" "BUILD - intake form (50%)"

# After BUILD complete
./session-release.sh droplet church-guidance-ministry
./session-send-message.sh broadcast "BUILD complete" "church-guidance-ministry ready for PRODUCTION"
```

---

## 💡 Usage Patterns

### Pattern 1: Start of Session
```bash
# 1. Register session
./session-start.sh

# 2. Check what's happening
./session-status.sh

# 3. Check messages
./session-check-messages.sh

# 4. Pick unclaimed work or coordinate
```

### Pattern 2: During Work
```bash
# Every significant action
./session-heartbeat.sh "building" "target-name" "current-phase"

# Check for messages periodically
./session-check-messages.sh
```

### Pattern 3: Completion
```bash
# Release work
./session-release.sh droplet church-guidance-ministry

# Notify others
./session-send-message.sh broadcast "Work complete" "Details here"

# Update session status
# (automatically done by heartbeat)
```

### Pattern 4: Coordination Needed
```bash
# Send direct message
./session-send-message.sh session-002 "Question about dashboard" "Can I help with deployment?"

# Or broadcast for anyone
./session-send-message.sh broadcast "Need help" "Looking for someone to review SPECS"
```

---

## 📈 Benefits

### For Sessions (AI)
- ✅ See what other sessions are doing
- ✅ Avoid conflicts automatically
- ✅ Coordinate work efficiently
- ✅ Learn from each other's progress
- ✅ Build on each other's work

### For User
- ✅ Sessions work as team, not isolated
- ✅ Less coordination overhead
- ✅ Faster progress (parallel work)
- ✅ Transparent activity (STATUS_BOARD)
- ✅ No duplicate effort

### For System
- ✅ File-based (git-friendly)
- ✅ Asynchronous (no blocking)
- ✅ Self-documenting (all activity logged)
- ✅ Recoverable (claims expire automatically)

---

## 🔄 Next Steps

1. Create scripts in `COORDINATION/scripts/`
2. Create directories (`sessions/`, `heartbeats/`, `claims/`, `messages/`)
3. Test with 2+ simultaneous sessions
4. Refine based on real usage
5. Add to fast-load scripts (automatic registration)

---

**Status:** Protocol defined - ready for implementation
**Impact:** Transforms isolated sessions into coordinated team
**Requirement:** All sessions must follow this protocol

🤝⚡📊✅
