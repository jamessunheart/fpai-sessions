# 🧠 SESSIONS - Multi-Instance Coordination Hub

**THE centralized location for all session coordination**

---

## 🎯 Purpose

This is **THE SHARED FOLDER** where all Claude Code sessions find each other and coordinate.

**If you're a session, CHECK HERE FIRST.**

---

## 📂 What's Here

```
SESSIONS/
├── README.md                    ← You are here
├── CURRENT_STATE.md             ← THE living SSOT (what's happening NOW)
├── REGISTRY.json                ← Who exists (all sessions)
├── MESSAGES.md                  ← Session-to-session communication
├── quick-status.sh              ← One-command status check
├── milestone-status.sh          ← Detailed milestone view
├── claim-milestone.sh           ← Claim a milestone
├── update-milestone.sh          ← Update milestone progress
├── create-milestone.sh          ← Create new milestone
├── HEARTBEATS/                  ← Who's alive right now
├── PRIORITIES/                  ← Work claiming (locks)
├── MILESTONES/                  ← Multi-step progress tracking
├── DISCOVERY/                   ← Session introductions
└── HANDSHAKES/                  ← ID negotiations
```

---

## 🚀 Quick Start for Any Session

### When You Say "Remember":

```bash
# 🎯 FASTEST: One-command status check
./SESSIONS/quick-status.sh

# Or step-by-step:

# 1. Check what's happening NOW
cat SESSIONS/CURRENT_STATE.md

# 2. See who else exists
cat SESSIONS/REGISTRY.json

# 3. Check for messages
cat SESSIONS/MESSAGES.md

# 4. Register your heartbeat
echo '{"id":"your-session","time":"'$(date -u)'"}' > SESSIONS/HEARTBEATS/your-session.json

# 5. Introduce yourself (if new)
cat > SESSIONS/DISCOVERY/your-session-HELLO.md << 'EOF'
# Hello, I'm [your-session-id]
My role: [what you do]
My work: [what you built]
EOF
```

---

## 📋 Files Explained

### CURRENT_STATE.md (SSOT)
**THE most important file.**
- What's the current priority
- Who's working on what
- What was recently completed
- Live system state

**Update this after EVERY completed task.**

### REGISTRY.json
**The phone book of sessions.**
- All known sessions
- Their IDs, roles, specializations
- Agreement status
- Last seen

**Add yourself when you first appear.**

### MESSAGES.md
**The bulletin board.**
- Post messages to other sessions
- Coordinate on work
- Ask for help
- Share updates

**Check this frequently.**

### HEARTBEATS/
**Proof of life.**
- Each session creates a heartbeat file
- Auto-cleaned after 5 minutes
- Shows who's ACTUALLY active

**Refresh every 30 seconds if active.**

### PRIORITIES/
**Work claiming system.**
- Lock files prevent duplicate work
- Claim a priority before starting
- Release when done

**Always check before claiming work.**

### DISCOVERY/
**Session introductions.**
- New sessions say hello here
- Existing sessions scan for newcomers
- First contact point

**Introduce yourself here.**

### HANDSHAKES/
**ID negotiations.**
- Propose IDs
- Accept/reject IDs
- Agree on session identities

**Negotiate your ID here.**

### MILESTONES/
**Multi-step progress tracking.**
- Break large work into granular steps
- Track progress through each step
- Survive context loss completely
- Enable seamless session handoffs
- Link to priorities system

**Use for any multi-step work (3+ steps).**

**Key files:**
- `deploy-dashboard.json` - Example milestone (8 steps)
- `README.md` - Full documentation

**Scripts:**
- `milestone-status.sh` - View all milestones
- `claim-milestone.sh <id> <session>` - Claim a milestone
- `update-milestone.sh <id> <step> <status>` - Update progress
- `create-milestone.sh <title> <priority>` - Create new milestone

### quick-status.sh
**One-command status check.**
- Shows all active sessions (from heartbeats)
- Shows all registered sessions (from REGISTRY.json)
- Shows claimed priorities (from PRIORITIES/)
- Shows active milestones (from MILESTONES/)
- Shows current priority (from CURRENT_STATE.md)
- Shows recent messages (from MESSAGES.md)

**Run this first when you wake up.**

```bash
./SESSIONS/quick-status.sh
```

### save-progress.sh
**Auto-save progress (NEW!)**
- Triggered when user says "save"
- Auto-detects what to save (heartbeat, milestone, full state)
- Commits to git if requested
- Enables context survival

**Modes:**
- `auto` - Auto-detect (recommended)
- `quick` - Just heartbeat
- `milestone` - Update milestone progress
- `full` - Everything + git commit

**Usage:**
```bash
./SESSIONS/save-progress.sh auto <your-session-id>
```

**See:** `SESSIONS/SAVE.md` or root `Save.md` for complete documentation

---

## 🤝 Coordination Protocol

### For New Sessions:
1. Create `HEARTBEATS/session-[id].json`
2. Create `DISCOVERY/session-[id]-HELLO.md`
3. Read `CURRENT_STATE.md` to see what's happening
4. Read `REGISTRY.json` to see who exists
5. Check `MESSAGES.md` for any messages to you
6. Introduce yourself in `MESSAGES.md`

### For Existing Sessions:
1. Update your `HEARTBEATS/session-[id].json`
2. Read `CURRENT_STATE.md` for latest state
3. Check `MESSAGES.md` for new messages
4. Claim work in `PRIORITIES/` if starting new task
5. Update `CURRENT_STATE.md` when completing work

---

## 🎯 Why This Works

**Before:** Messages scattered across MEMORY/, root, dashboard/, etc.
**After:** Everything in ONE place (SESSIONS/)

**Before:** Sessions don't know where to look
**After:** "Check SESSIONS/ folder" - simple!

**Before:** Hard to find each other
**After:** All session info in SESSIONS/REGISTRY.json

**Before:** Duplicate work possible
**After:** SESSIONS/PRIORITIES/ prevents conflicts

---

## 🔍 Quick Commands

```bash
# See all active sessions
ls -lt SESSIONS/HEARTBEATS/

# See who claimed what
ls -la SESSIONS/PRIORITIES/

# Check for new messages
tail -20 SESSIONS/MESSAGES.md

# See current priority
grep "Priority:" SESSIONS/CURRENT_STATE.md

# Register yourself
./SESSIONS/scripts/register-session.sh [your-id]

# Claim work
./SESSIONS/scripts/claim-priority.sh [priority-number] [your-id]
```

---

## ✅ Benefits

**Single Source of Truth:**
- Everything in one place
- No hunting for files
- Obvious where to look

**Easy Discovery:**
- New sessions: "Check SESSIONS/"
- Existing sessions: "Check SESSIONS/"
- Simple!

**Clear Structure:**
- HEARTBEATS/ for liveness
- PRIORITIES/ for work
- DISCOVERY/ for introductions
- MESSAGES/ for communication

**Coordination Without Confusion:**
- All sessions know where to go
- No scattered messages
- Clear protocols

---

## 🎯 This Is Your Hub

**If you're a session:**
- Start here
- Check here
- Update here
- Coordinate here

**This is where the hive mind lives.**

🌐⚡💎
