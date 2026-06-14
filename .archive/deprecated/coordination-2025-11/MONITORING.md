# 🤖 Multi-Session Monitoring System

**Status:** ✅ OPERATIONAL
**Created:** 2025-11-15
**Session:** session-1763233940

---

## 🎯 Overview

Real-time monitoring and coordination for all Claude Code instances running on this machine.

**Capabilities:**
- Track all active Claude Code sessions
- Monitor server health and services
- Watch file system changes
- Coordinate work across sessions
- Share messages and knowledge
- Prevent duplicate work

---

## ⚡ Quick Start

### Master Command (Recommended)
```bash
./docs/coordination/scripts/monitor
```

This interactive menu lets you choose from 6 monitoring modes.

### Direct Commands

#### 1. Live Dashboard (Auto-updating every 5 sec)
```bash
./docs/coordination/scripts/live-monitor.sh
```

**Shows:**
- Active Claude Code sessions with latest heartbeats
- Recent session messages
- Server service health (ports 8000-8025)
- Recent file changes (last 5 min)
- Git activity across repos
- System resource usage

**Press Ctrl+C to exit**

#### 2. Process Details
```bash
./docs/coordination/scripts/detailed-process-monitor.sh
```

**Shows:**
- Each Claude process with PID
- Terminal assignment (s001-s012)
- CPU and memory usage
- Working directory
- Current activity
- Git status per terminal

#### 3. Quick Overview
```bash
./docs/coordination/scripts/quick-overview.sh
```

**Shows:**
- One-screen snapshot of current state
- Fast, no auto-refresh
- Perfect for quick status checks

#### 4. Session Status
```bash
./docs/coordination/scripts/session-status.sh
```

**Shows:**
- Registered sessions
- Active claims
- Recent heartbeats
- Coordination details

#### 5. Check Messages
```bash
./docs/coordination/scripts/session-check-messages.sh
```

**Shows:**
- Broadcast messages from all sessions
- Direct messages to your session

#### 6. Status Board
```bash
cat docs/coordination/STATUS_BOARD.md
```

**Shows:**
- Human-readable markdown overview
- Auto-updated by heartbeats

---

## 📊 What You Can Monitor

### 1. Claude Code Sessions

**10 Active Processes Detected:**
- Terminals: s001, s002, s003, s004, s005, s006, s007, s009, s010, s012
- All working in: `/Users/jamessunheart/Development`
- Most are ACTIVE (>10% CPU)
- Total combined CPU: ~150%
- Total combined Memory: ~15%

**3 Registered Sessions:**
- `session-1763229251` - Completed church-guidance-ministry BUILD
- `session-1763233940` - Monitoring coordination (this session)
- (Others registering...)

### 2. Server Services (198.54.123.234)

**Monitored Ports:**
- 8000: Registry ✅
- 8001: Orchestrator ⚠️ (currently offline)
- 8002: Dashboard ✅
- 8009: Church Guidance Ministry ✅
- 8010: I-Match ✅
- 8020: White Rock Ministry
- 8025: Credentials Manager ✅

### 3. File System Activity

**Tracks:**
- Python files (.py)
- Shell scripts (.sh)
- Markdown (.md)
- JSON configs (.json)
- Modified in last 5 minutes
- Max 10 most recent

### 4. Git Activity

**Monitors:**
- All repos in Development directory
- Recent commits
- Branch status
- Uncommitted changes
- Shows last commit time and message

### 5. System Resources

**CPU & Memory:**
- Per-process breakdown
- Total Claude usage
- Status indicators (🟢 IDLE, 🟡 ACTIVE, 🔴 HIGH CPU)

---

## 🔄 Coordination Workflow

### For Each Session

#### When Starting Work:
```bash
# 1. Check what's happening
./docs/coordination/scripts/monitor

# 2. Register your session
./docs/coordination/scripts/session-start.sh

# 3. See what others are doing
./docs/coordination/scripts/session-status.sh

# 4. Claim your work
./docs/coordination/scripts/session-claim.sh droplet my-service 4
```

#### During Work:
```bash
# Send heartbeats at milestones
./docs/coordination/scripts/session-heartbeat.sh \
  "building" \
  "my-service" \
  "BUILD - implementing feature X" \
  "60%" \
  "next: write tests"

# Check messages periodically
./docs/coordination/scripts/session-check-messages.sh
```

#### When Complete:
```bash
# Release your claim
./docs/coordination/scripts/session-release.sh droplet my-service

# Announce completion
./docs/coordination/scripts/session-send-message.sh \
  broadcast \
  "Work Complete" \
  "my-service is ready for production!"
```

---

## 🎨 Visual Legend

### Status Indicators
- 🟢 Online / Idle / Complete / Success
- 🟡 Active / In Progress / Warning
- 🔵 Building / Processing
- 🔴 Offline / Error / High Load
- 🟤 Unknown / Waiting
- ⚫ Stopped / Disabled

### Icons
- 🤖 Claude Code session
- 🌐 Server/service
- 💬 Message
- 📝 File change
- 📦 Git activity
- 💻 System resource
- 🔒 Claimed work
- 💓 Heartbeat
- ⚡ Quick action
- 🔍 Details
- 📊 Dashboard

---

## 📁 File Structure

```
docs/coordination/
├── MONITORING.md              ← This file
├── scripts/
│   ├── monitor                ← Master command (interactive)
│   ├── live-monitor.sh        ← Auto-updating dashboard
│   ├── detailed-process-monitor.sh  ← Process details
│   ├── quick-overview.sh      ← Quick snapshot
│   ├── session-status.sh      ← Session coordination
│   ├── session-check-messages.sh    ← Message viewer
│   └── [other session scripts...]
├── sessions/                  ← Registered sessions
├── heartbeats/                ← Activity timeline
├── messages/                  ← Inter-session comms
└── STATUS_BOARD.md            ← Human-readable status
```

---

## 🔧 Troubleshooting

### No processes showing
**Issue:** Process monitor shows 0 Claude instances
**Check:** Are there actually Claude terminals open?
```bash
ps aux | grep claude
```

### Server services offline
**Issue:** All server checks show 🔴
**Check:** Is SSH connection working?
```bash
ssh root@198.54.123.234 'curl -s localhost:8000/health'
```

### Sessions not registered
**Issue:** Quick overview shows "0 registered"
**Solution:** Each Claude session needs to register:
```bash
./docs/coordination/scripts/session-start.sh
```

### Monitoring script permission denied
**Issue:** `Permission denied` when running scripts
**Solution:** Make executable:
```bash
chmod +x docs/coordination/scripts/*.sh
chmod +x docs/coordination/scripts/monitor
```

---

## 💡 Tips & Best Practices

### Tip 1: Keep Live Monitor Open
Run the live monitor in a dedicated terminal:
```bash
# In a spare terminal
./docs/coordination/scripts/live-monitor.sh
```

Leave it running for real-time awareness!

### Tip 2: Check Before Starting Work
Always check status before claiming work:
```bash
./docs/coordination/scripts/quick-overview.sh
```

### Tip 3: Heartbeat Regularly
Send heartbeats at major milestones:
- Before starting a phase
- At 25%, 50%, 75% completion
- When switching tasks
- When encountering blockers
- When completing work

### Tip 4: Broadcast Important Info
Let others know about:
- Completions
- Blockers
- Discoveries
- Infrastructure changes
- Deployment events

### Tip 5: Use Process Monitor to Debug
If a session seems stuck, check its CPU usage:
```bash
./docs/coordination/scripts/detailed-process-monitor.sh
```

### Tip 6: Watch File Changes
See what's being modified in real-time:
```bash
./docs/coordination/scripts/live-monitor.sh
# Watch the "Recent File Changes" section
```

---

## 🚀 Advanced Usage

### Run Multiple Monitors
```bash
# Terminal 1: Live dashboard
./docs/coordination/scripts/live-monitor.sh

# Terminal 2: Your work
# (Normal Claude Code session)

# Terminal 3: Process monitor
watch -n 5 './docs/coordination/scripts/detailed-process-monitor.sh'
```

### Filter File Changes
Edit `live-monitor.sh` to watch specific patterns:
```bash
# Line ~100 in live-monitor.sh
find "$DEV_DIR" -type f \( -name "*.py" -o -name "*.tsx" \) -mmin -5 ...
```

### Customize Server Checks
Add more services in `live-monitor.sh`:
```bash
# Around line 150
declare -A services=(
    ["8000"]="Registry"
    ["8099"]="Your New Service"
)
```

---

## 📊 Sample Output

### Live Dashboard
```
╔══════════════════════════════════════════════════════════════════════╗
║  🤖 LIVE CLAUDE CODE & SYSTEM ACTIVITY MONITOR                       ║
║  Updated: 2025-11-15 11:20:00                                        ║
╚══════════════════════════════════════════════════════════════════════╝

━━━ 🤖 ACTIVE CLAUDE CODE SESSIONS ━━━

Process Count: 10 running | Registered: 3 sessions

🟢 session-1763229251
   ├─ Status: active | Action: completed
   ├─ Working on: church-guidance-ministry BUILD
   ├─ Phase: 🎉 BUILD 100% COMPLETE - Ready for production
   └─ Last seen: 2025-11 18:12

🟡 session-1763233940
   ├─ Status: active | Action: coordinating
   ├─ Working on: multi-session monitoring
   ├─ Phase: Built live monitoring dashboards - 3 scripts operational 100%
   └─ Last seen: 2025-11 19:20

─────────────────────────────────────────────────────────────────────

━━━ 💬 RECENT SESSION MESSAGES ━━━

📢 [19:20:30] session-1763233940: 🎉 Monitoring System Ready
   Live multi-session monitoring dashboards now available!
...
```

---

## 🎯 Next Steps

1. **All sessions should register:**
   ```bash
   ./docs/coordination/scripts/session-start.sh
   ```

2. **Start monitoring:**
   ```bash
   ./docs/coordination/scripts/monitor
   ```

3. **Begin coordinated work:**
   - Check status
   - Claim work
   - Send heartbeats
   - Check messages
   - Release when done

---

## ✅ System Status

- ✅ Live monitoring operational
- ✅ Process tracking working
- ✅ Server health checks active
- ✅ File watching enabled
- ✅ Git monitoring working
- ✅ Session coordination ready
- ✅ Message broadcasting ready

**All systems nominal!**

---

**Created by:** session-1763233940
**Date:** 2025-11-15
**Status:** OPERATIONAL ✅

🤖💬📊✅
