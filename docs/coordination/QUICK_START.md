# 🤝 Multi-Session Coordination - Quick Start

**Status:** OPERATIONAL ✅
**Created:** 2025-11-15

---

## 🎯 What This Does

Enables multiple Claude Code sessions to work together as a team:
- **See** what other sessions are doing in real-time
- **Claim** work to prevent conflicts
- **Message** each other directly
- **Coordinate** without user as bottleneck

---

## ⚡ Quick Start (For Each New Session)

### Step 1: Register Your Session
```bash
./COORDINATION/scripts/session-start.sh
```

**Result:** Session registered, heartbeat sent, broadcast message sent

### Step 2: Check What Others Are Doing
```bash
./COORDINATION/scripts/session-status.sh
```

**Shows:**
- Active sessions and what they're working on
- Current claims (what's being worked on)
- Recent heartbeats (activity timeline)

### Step 3: View the Status Board (Human-Readable)
```bash
cat COORDINATION/STATUS_BOARD.md
```

**Shows:** Beautiful markdown overview of all sessions, claims, and messages

### Step 4: Claim Your Work (Before Starting)
```bash
./COORDINATION/scripts/session-claim.sh droplet church-guidance-ministry 4
```

**Parameters:**
- `droplet` - Resource type (droplet, file, deployment, etc.)
- `church-guidance-ministry` - Resource name
- `4` - Duration in hours (default: 4)

**Result:** Work claimed, others can see it's being worked on

### Step 5: Send Heartbeats As You Work
```bash
./COORDINATION/scripts/session-heartbeat.sh "building" "church-guidance-ministry" "BUILD - landing page" "30%" "next: intake form"
```

**Parameters:**
- Action: what you're doing (building, testing, deploying, etc.)
- Target: what you're working on
- Phase: current phase
- Progress: percentage (optional)
- Next action: what's coming next (optional)

**Result:** Status board updates, others can see your progress

### Step 6: Check Messages Regularly
```bash
./COORDINATION/scripts/session-check-messages.sh
```

**Shows:**
- Broadcast messages from all sessions
- Direct messages to your session

### Step 7: Release Work When Done
```bash
./COORDINATION/scripts/session-release.sh droplet church-guidance-ministry
```

**Result:** Claim removed, work available for others

---

## 📊 Example Workflow

### Session A Starts Working on Church Guidance Droplet

```bash
# Start session
./COORDINATION/scripts/session-start.sh
# Output: Session session-123 registered

# Check status
./COORDINATION/scripts/session-status.sh
# Output: 0 active sessions, 0 claims

# Claim work
./COORDINATION/scripts/session-claim.sh droplet church-guidance-ministry 4
# Output: ✅ Claimed: droplet/church-guidance-ministry

# Start building
./COORDINATION/scripts/session-heartbeat.sh "building" "church-guidance-ministry" "BUILD - landing page" "10%"

# Continue working...
./COORDINATION/scripts/session-heartbeat.sh "building" "church-guidance-ministry" "BUILD - intake form" "50%"

# Complete
./COORDINATION/scripts/session-release.sh droplet church-guidance-ministry
./COORDINATION/scripts/session-send-message.sh broadcast "Work complete" "church-guidance-ministry BUILD phase done"
```

### Session B Starts While Session A is Working

```bash
# Start session
./COORDINATION/scripts/session-start.sh
# Output: Session session-456 registered

# Check what's happening
./COORDINATION/scripts/session-status.sh
# Output:
#   Active sessions: 1
#   session-123 working on church-guidance-ministry
#   Active claims: droplet/church-guidance-ministry

# See that church-guidance is claimed, pick different work
./COORDINATION/scripts/session-claim.sh droplet email-automation 3

# Or send message to coordinate
./COORDINATION/scripts/session-send-message.sh session-123 "Can I help?" "I see you're working on church-guidance. Can I help with anything?"
```

### Session A Responds to Session B

```bash
# Check messages
./COORDINATION/scripts/session-check-messages.sh
# Output: Message from session-456: "Can I help?"

# Respond
./COORDINATION/scripts/session-send-message.sh session-456 "Yes!" "Can you start on the email templates while I finish the landing page?"

# Continue working in parallel
```

---

## 🚦 Rules to Follow

### Rule 1: Register At Start
**Always run session-start.sh when beginning a new session**

### Rule 2: Check Before Claiming
**Always check session-status.sh before claiming work**

### Rule 3: Claim Before Touching
**Always claim resources you're about to modify:**
- Droplets you're building
- Files you're editing (major changes)
- Shared resources (deployments, etc.)

**Don't need to claim:**
- Reading files
- Creating new files
- Running tests (read-only)

### Rule 4: Heartbeat Regularly
**Send heartbeats on significant actions:**
- Before claiming work
- After major milestones
- When switching phases
- Before releasing work

### Rule 5: Check Messages
**Run session-check-messages.sh periodically**
- Other sessions may need coordination
- Broadcasts may have important info

### Rule 6: Release When Done
**Always release claims when finished or switching tasks**

### Rule 7: Broadcast Completions
**Send broadcast when completing significant work**
- Helps others know what's available
- Builds team awareness

---

## 🔐 Secure Credentials (IMPORTANT!)

**Before doing ANY work that needs API keys:**

### Check for Existing Credentials
```bash
# List all available credentials
./scripts/session-list-credentials.sh
```

### Get a Credential
```bash
# Get Anthropic API key
export ANTHROPIC_API_KEY=$(./scripts/session-get-credential.sh anthropic_api_key)

# Get OpenAI API key
export OPENAI_API_KEY=$(./scripts/session-get-credential.sh openai_api_key)

# Get server admin password
./scripts/session-get-credential.sh server_admin_password
```

### Store a New Credential (If Needed)
```bash
./scripts/session-set-credential.sh credential_name "credential_value" api_key service_name
```

### Rules for Credentials:
- ✅ **ALWAYS** use the credential vault
- ❌ **NEVER** hardcode API keys in code
- ❌ **NEVER** commit credentials to git
- ✅ **ALWAYS** check vault first before asking user for keys

**Full Guide:** `docs/coordination/SECURE_CREDENTIALS.md`

---

## 📁 Files and Directories

```
COORDINATION/
│
├── QUICK_START.md              ← This file
├── STATUS_BOARD.md             ← Human-readable status (auto-updated)
├── SECURE_CREDENTIALS.md       ← Credential vault documentation
├── CREDENTIAL_RECOVERY.md      ← Recovery procedures
│
├── .credentials                ← Encrypted credential vault (git-ignored)
│
├── sessions/                   ← Registered sessions
│   └── session-XXX.json
│
├── heartbeats/                 ← Activity timeline (auto-cleanup 24h)
│   └── 2025-11-15_HH-MM-session-XXX.json
│
├── claims/                     ← Work ownership
│   └── droplet-name.claim
│
├── messages/                   ← Inter-session communication
│   ├── broadcast/              ← Messages to all
│   └── direct/session-XXX/     ← Messages to specific session
│
├── shared-knowledge/           ← Knowledge broadcasting
│   ├── learnings.md
│   ├── patterns.md
│   ├── troubleshooting.md
│   └── best-practices.md
│
└── scripts/                    ← Coordination tools
    ├── session-start.sh
    ├── session-heartbeat.sh
    ├── session-claim.sh
    ├── session-release.sh
    ├── session-send-message.sh
    ├── session-check-messages.sh
    ├── session-status.sh
    ├── session-share-learning.sh
    ├── session-search-knowledge.sh
    ├── session-set-credential.sh     ← Store credential
    ├── session-get-credential.sh     ← Get credential
    ├── session-list-credentials.sh   ← List all credentials
    ├── session-delete-credential.sh  ← Delete credential
    ├── session-get-server-credential.sh  ← Get from server
    ├── credential_vault.py           ← Encryption engine
    └── update-status-board.sh
```

---

## 💡 Tips for Effective Coordination

### Tip 1: Use Descriptive Heartbeats
**Good:**
```bash
./session-heartbeat.sh "building" "church-guidance" "BUILD - AI document generation (SPECS complete, testing integration)" "75%" "finish email delivery"
```

**Not as helpful:**
```bash
./session-heartbeat.sh "working" "stuff" "doing things"
```

### Tip 2: Broadcast Important Milestones
```bash
# When completing major work
./session-send-message.sh broadcast "Dashboard deployed" "Production ready on port 8002"

# When discovering blockers
./session-send-message.sh broadcast "Blocker found" "Stripe API key needed for church-guidance deployment"
```

### Tip 3: Coordinate on Overlap
If you want to work on something that's claimed:
```bash
# Check who has it
./session-status.sh

# Send direct message
./session-send-message.sh session-123 "Coordination?" "I'd like to help with X. Can we split the work?"
```

### Tip 4: View Status Board for Human Overview
```bash
# Quick visual summary
cat COORDINATION/STATUS_BOARD.md

# More detailed
./COORDINATION/scripts/session-status.sh
```

---

## 🎯 Integration with Assembly Line

When building droplets using the standard assembly line:

### SPECS Phase
```bash
# Claim the droplet
./session-claim.sh droplet my-droplet 2

# Heartbeat as you work
./session-heartbeat.sh "planning" "my-droplet" "SPECS - defining requirements" "25%"

# When complete
./session-heartbeat.sh "completed" "my-droplet" "SPECS complete" "100%"
./session-send-message.sh broadcast "SPECS done" "my-droplet ready for BUILD"
```

### BUILD Phase
```bash
# Already claimed from SPECS
./session-heartbeat.sh "building" "my-droplet" "BUILD - implementing core" "40%"

# Continue with heartbeats at milestones
./session-heartbeat.sh "building" "my-droplet" "BUILD - tests passing" "80%"

# When complete
./session-heartbeat.sh "completed" "my-droplet" "BUILD complete" "100%"
```

### PRODUCTION Phase
```bash
# Heartbeat before deployment
./session-heartbeat.sh "deploying" "my-droplet" "PRODUCTION - deploying to server"

# After deployment
./session-release.sh droplet my-droplet
./session-send-message.sh broadcast "Deployment complete" "my-droplet live on port 8003"
```

---

## 🔍 Troubleshooting

### "No active session" error
**Solution:** Run `./COORDINATION/scripts/session-start.sh` first

### Claim already exists
**Check:** `./session-status.sh` to see who has it
**Options:**
1. Wait for it to expire
2. Send message to coordinate
3. Pick different work

### Status board not updating
**Solution:** Run `./COORDINATION/scripts/update-status-board.sh` manually

### Can't see other sessions
**Check:** Are they in `COORDINATION/sessions/`?
**Note:** Sessions need to run session-start.sh to register

---

## ✅ Checklist for Each Session

**At Start:**
- [ ] Run session-start.sh
- [ ] Check session-status.sh
- [ ] Check session-check-messages.sh
- [ ] Identify unclaimed work

**During Work:**
- [ ] Claim before modifying
- [ ] Heartbeat on milestones
- [ ] Check messages periodically
- [ ] Update README.md in parallel

**At End:**
- [ ] Release all claims
- [ ] Send completion broadcast
- [ ] Update final status

---

## 🌟 Benefits

**For Sessions (AI):**
- Know what others are doing
- Avoid duplicate work
- Build on each other's progress
- Coordinate complex tasks

**For User:**
- Sessions work as team
- Less coordination overhead
- Faster parallel progress
- Transparent activity

**For System:**
- File-based (git-friendly)
- Asynchronous (no blocking)
- Self-documenting
- Auto-recovering (claims expire)

---

## 📖 Full Documentation

See: `CORE/ACTIONS/protocols/MULTI_SESSION_COORDINATION.md`

---

**Status:** OPERATIONAL ✅
**Current Sessions:** Check `./COORDINATION/scripts/session-status.sh`
**Status Board:** `cat COORDINATION/STATUS_BOARD.md`

🤝⚡📊✅
