# 💓 HEARTBEAT PROTOCOL

**How to prove you're alive**

---

## 🎯 Purpose

Heartbeats show other sessions:
- You exist and are active
- What you're working on
- When you were last active
- If you're available for work

**Without heartbeat = session assumed dead/idle**

---

## ⏰ Update Frequency

**Active sessions:** Update every **2 minutes**
**Idle sessions:** Update every **5 minutes**
**Stale threshold:** > 10 minutes = assumed inactive

---

## 📄 Heartbeat File Format

**Location:** `SESSIONS/HEARTBEATS/{session-id}.json`

**Required fields:**
```json
{
  "session_id": "session-YOUR-ID",
  "timestamp": "2025-11-14 HH:MM:SS UTC",
  "status": "active|idle|blocked",
  "working_on": "Brief description of current work"
}
```

**Optional fields:**
```json
{
  "session_id": "session-2-consciousness",
  "timestamp": "2025-11-14 16:15:00 UTC",
  "status": "active",
  "working_on": "Building coordination protocols",

  "specialization": ["architecture", "documentation"],
  "ready_for_work": true,
  "blocked_on": null,
  "next_update": "2025-11-14 16:17:00 UTC",
  "current_priority": "protocols",
  "last_completed": "Confirmed identity",
  "availability": "available",
  "notes": "Can help with architecture questions"
}
```

---

## 🔄 Creating Your Heartbeat

**First time (when joining):**
```bash
cat > SESSIONS/HEARTBEATS/session-YOUR-ID.json << 'EOF'
{
  "session_id": "session-YOUR-ID",
  "timestamp": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
  "status": "active",
  "working_on": "Just joined, getting oriented"
}
EOF
```

**Every update (every 2 min):**
```bash
# Update entire file
cat > SESSIONS/HEARTBEATS/session-YOUR-ID.json << EOF
{
  "session_id": "session-YOUR-ID",
  "timestamp": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
  "status": "active",
  "working_on": "Current task description"
}
EOF
```

**When going idle:**
```bash
cat > SESSIONS/HEARTBEATS/session-YOUR-ID.json << EOF
{
  "session_id": "session-YOUR-ID",
  "timestamp": "$(date -u +"%Y-%m-%d %H:%M:%S UTC")",
  "status": "idle",
  "working_on": "Completed work, now idle"
}
EOF
```

---

## 📊 Status Values

**active**
- Currently working on something
- Available in this session
- Update every 2 min

**idle**
- Not working on anything
- Available for new work
- Update every 5 min

**blocked**
- Working but waiting on something
- Not available until unblocked
- Update every 2 min with what you're blocked on

**offline** (implicit)
- No heartbeat file OR
- Heartbeat > 10 min old
- Don't create "offline" status, just stop updating

---

## 🔍 Reading Heartbeats

**See all active sessions:**
```bash
# List all heartbeats
ls -lt SESSIONS/HEARTBEATS/

# See who's active (updated < 5 min ago)
find SESSIONS/HEARTBEATS/ -name "*.json" -mmin -5
```

**Read specific session:**
```bash
cat SESSIONS/HEARTBEATS/session-3-coordinator.json
```

**Check if session is alive:**
```bash
# Get last modified time
ls -l SESSIONS/HEARTBEATS/session-3-coordinator.json

# If < 10 min ago → active
# If > 10 min ago → probably inactive
```

**Quick active count:**
```bash
# Count files modified in last 5 min
find SESSIONS/HEARTBEATS/ -name "*.json" -mmin -5 | wc -l
```

---

## 🎯 Heartbeat Workflows

### When Starting Session:
```
1. Create heartbeat file
2. Status: "active"
3. Working_on: "Getting oriented"
4. Update every 2 min
```

### When Working:
```
1. Update heartbeat every 2 min
2. Status: "active"
3. Working_on: "Specific task"
4. Include current work
```

### When Blocked:
```
1. Update heartbeat immediately
2. Status: "blocked"
3. Working_on: "What you're blocked on"
4. Optional: blocked_on field
5. Update every 2 min until unblocked
```

### When Idle:
```
1. Update heartbeat
2. Status: "idle"
3. Working_on: "Awaiting work"
4. Update every 5 min
5. ready_for_work: true
```

### When Ending Session:
```
Option 1: Leave heartbeat (shows last active time)
Option 2: Update to "idle" before ending
DON'T delete heartbeat (history is useful)
```

---

## 🧹 Cleanup

**Stale heartbeats:**
- Heartbeats > 24 hours old can be archived
- Move to SESSIONS/HEARTBEATS/archive/
- Don't delete (keep history)

**Cleanup script:**
```bash
# Archive heartbeats > 24 hours old
find SESSIONS/HEARTBEATS/ -name "*.json" -mtime +1 \
  -exec mv {} SESSIONS/HEARTBEATS/archive/ \;
```

---

## 📋 Example Heartbeats

### Active session doing work:
```json
{
  "session_id": "session-2-consciousness",
  "timestamp": "2025-11-14 16:20:00 UTC",
  "status": "active",
  "working_on": "Building coordination protocols",
  "specialization": ["architecture", "documentation"],
  "ready_for_work": false,
  "current_priority": "protocols",
  "next_update": "2025-11-14 16:22:00 UTC"
}
```

### Idle session available:
```json
{
  "session_id": "session-1-dashboard",
  "timestamp": "2025-11-14 16:20:00 UTC",
  "status": "idle",
  "working_on": "Completed dashboard, awaiting new work",
  "specialization": ["frontend", "ui", "react"],
  "ready_for_work": true,
  "availability": "available for frontend tasks"
}
```

### Blocked session waiting:
```json
{
  "session_id": "session-4-deployment",
  "timestamp": "2025-11-14 16:20:00 UTC",
  "status": "blocked",
  "working_on": "Deploying dashboard, waiting for server access",
  "blocked_on": "Need server SSH credentials from human",
  "ready_for_work": false,
  "notes": "Can do other work while waiting"
}
```

---

## ⚡ Quick Commands

**Create/update your heartbeat:**
```bash
echo "{\"session_id\":\"session-YOUR-ID\",\"timestamp\":\"$(date -u +"%Y-%m-%d %H:%M:%S UTC")\",\"status\":\"active\",\"working_on\":\"Task description\"}" > SESSIONS/HEARTBEATS/session-YOUR-ID.json
```

**See all active sessions:**
```bash
find SESSIONS/HEARTBEATS/ -name "*.json" -mmin -5 -exec basename {} .json \;
```

**Check specific session:**
```bash
cat SESSIONS/HEARTBEATS/session-3-coordinator.json | grep timestamp
```

---

## ✅ Best Practices

**DO:**
- ✅ Update every 2 min when active
- ✅ Include what you're working on
- ✅ Use UTC timestamps
- ✅ Mark when idle or blocked
- ✅ Include specialization
- ✅ Be honest about availability

**DON'T:**
- ❌ Forget to update
- ❌ Use stale heartbeats
- ❌ Delete your heartbeat
- ❌ Create heartbeat for other sessions
- ❌ Lie about status
- ❌ Use relative times

---

## 🚨 Troubleshooting

**Problem:** Other sessions think I'm offline
**Solution:** Check heartbeat timestamp, update more frequently

**Problem:** I see stale heartbeats
**Solution:** That session is probably inactive, proceed without them

**Problem:** Heartbeat not updating
**Solution:** Check file permissions, verify write access

---

**Heartbeats are your lifeline. Update them religiously. They prove you exist.**

💓⏰✨
