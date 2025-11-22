# Start Here

**30-Second Routing - Pick Your Path:**

- 🤖 **AI Session (Claude)** → [3-step boot](#-ai-session-boot-sequence) (5-10 min first time, 2 min returning)
- 👤 **External Apprentice/Developer** → **https://fullpotential.ai/missions** (missions portal)
- 🏠 **James (Local)** → [Quick Access](#-quick-access) below
- 📖 **Full Context** → Keep reading

---

## 🎯 Quick Access

### For External Apprentices/Developers
- **🌐 Missions Portal:** **https://fullpotential.ai/missions**
  - Browse available missions
  - Claim missions and earn XP
  - Submit work via GitHub PRs
  - Track progress and achievements
  - Complete signup/login flow

### For James (Local Access)
- **Priority missions:** [missions/active/DO_THIS_NOW.md](missions/active/DO_THIS_NOW.md)
- **System status:** [Memory Dashboard](http://198.54.123.234:8032) (live) or [docs/status/](docs/status/)
- **Service browse:** `ls services/*/`
- **Add missions to portal:** Update database via portal admin or sync markdown → DB

### For AI Sessions

⚠️ **CRITICAL: Coordinate first** → See [AI Boot Sequence](#-ai-session-boot-sequence) below

**Quick commands:**
```bash
cat docs/coordination/SSOT.json                      # Who's active?
ls docs/coordination/sessions/ACTIVE/                # What are they doing?
cat missions/active/DO_THIS_NOW.md                   # Current priorities
```

**New?** Follow [3-step boot](#-ai-session-boot-sequence) • **Returning?** [Fast path](#-fast-path-returning-sessions)

### For Developers
- **Guides:** [docs/guides/](docs/guides/)
- **Architecture:** [docs/architecture/](docs/architecture/)
- **Service template:** [services/_TEMPLATE/](services/_TEMPLATE/)

---

## 🤖 AI Session Boot Sequence

### First: Are you NEW or RETURNING?

- **🆕 NEW SESSION** → Follow 3-step path below (5-10 min)
- **🔄 RETURNING SESSION** → [Fast Path](#-fast-path-returning-sessions) (2 min)

---

### 📚 NEW SESSION: 3-Step Progressive Understanding

**Follow these steps in order:**

#### **Level 1: CONTEXT** (3 min) - Understand WHAT we're building

**Goal:** $373K → $5T over 10 years via multiple AI sessions + humans working together

**What we're building:**
- Revenue services (i-match, magnet-trading, more)
- Multi-AI coordination system (multiple Claude sessions working together)
- Human apprentice tasks (OAuth/API work AI can't do)

**Current priorities:**
- See [`missions/active/DO_THIS_NOW.md`](missions/active/DO_THIS_NOW.md)

**Key architecture:**
- Services in `services/` directory (75+)
- Major systems in `systems/` directory
- Coordination via `docs/coordination/`

**Output:** "I understand what we're building and why"

---

#### **Level 2: COORDINATION** (3 min) - Avoid conflicts

**⚠️ CRITICAL: Multi-session coordination protocol**

**🤖 AUTOMATED (Recommended)** - One command does everything:

```bash
./automation/coordination/session-auto-init.sh my-session-name
```

This automatically:
- ✅ Checks who's active (reads SSOT.json)
- ✅ Creates your status file from template
- ✅ Registers you in SSOT.json
- ✅ Starts auto-heartbeat (updates every 5 min)

**Manual approach** (if automation unavailable):

```bash
# 1. Check who's active
cat docs/coordination/SSOT.json

# 2. See what they're working on
ls docs/coordination/sessions/ACTIVE/
cat docs/coordination/sessions/ACTIVE/*.md

# 3. Create your status file
cp docs/coordination/sessions/SESSION_STATUS_TEMPLATE.md \
   docs/coordination/sessions/ACTIVE/SESSION_YOUR_ID.md
```

**Include in your status file:**
- What you're working on
- What's completed ✅ / blocked ❌
- How others can help 🤝

**Why:** Prevents duplicate work, enables parallel builds, shows handoffs

**Output:** "I know who's doing what and won't conflict"

---

#### **Level 3: CHOOSE WORK** (3 min) - Pick your project

**Option A: Human-Blocker Missions** (Highest Priority)
→ Read: [`missions/active/DO_THIS_NOW.md`](missions/active/DO_THIS_NOW.md)
- Tasks humans need to do (OAuth, API keys)
- Can't do these yourself, but can prepare/monitor

**Option B: Active Builds**
→ Check: [`docs/coordination/sessions/ACTIVE/`](docs/coordination/sessions/ACTIVE/)
- See what other sessions are building
- Find "How others can help" sections
- Join a build in progress

**Option C: Deploy Ready Systems**
→ Check: `docs/coordination/sessions/ACTIVE/SESSION_*.md`
- Search for "READY TO DEPLOY" or "deployment ready" markers
- Look for completed builds in `automation/deployment/`
- Check service README files for deployment instructions

**Option D: New Service**
- Copy `services/_TEMPLATE/`
- Build something from `missions/active/`

---

#### **✅ Now: Document Your Choice & Start**

```bash
# Update your status file with chosen work
# Edit: docs/coordination/sessions/ACTIVE/SESSION_YOUR_ID.md
```

**Update these fields:**
- **Working on:** [Your chosen project/option]
- **Started:** [Current timestamp]
- **🔄 In Progress:** [First task you'll tackle]

**Example:**
```markdown
**Working on:** i-match-launch (Option A)
**Started:** 2025-11-20 16:00
**🔄 In Progress:**
- Review current i-match status
- Identify next deployment steps
```

**Then start working!** Update status every 15-30 min (Completed/In Progress/Blocked).

**Output:** "I've documented my work and I'm ready to start"

---

#### **OPTIONAL: Deep Dive** (15-20 min) - For comprehensive initialization

**For detailed protocols, automation, and resource understanding:**
→ Read: [`docs/coordination/MEMORY/BOOT.md`](docs/coordination/MEMORY/BOOT.md)

**This comprehensive guide covers:**
- Complete resource SSOT ($373K capital → $5T vision)
- Credential vault (never ask user twice for API keys)
- Service automation (new-service.sh, sync-service.sh)
- Task automation (automate before asking user)
- All coordination protocols
- Security requirements

**When to read this:**
- First time working with services
- Need to understand capital/vision
- Working with credentials
- Building UDC-compliant services

**For UDC architecture & SPEC building:**
→ Read: [`docs/coordination/BOOT.md`](docs/coordination/BOOT.md)
- Universal Droplet Contract (5 endpoints)
- SPEC creation protocol
- TIER architecture
- Service mesh integration

---

### ⚡ FAST PATH: Returning Sessions

**Already know the system? 30-second checklist:**

**🤖 AUTOMATED:**
```bash
./automation/coordination/session-auto-init.sh my-session-name
# Then edit your status file and start working
```

**Manual:**
```bash
# 1. Coordinate
cat docs/coordination/SSOT.json && ls docs/coordination/sessions/ACTIVE/

# 2. Create/update status file
cp docs/coordination/sessions/SESSION_STATUS_TEMPLATE.md \
   docs/coordination/sessions/ACTIVE/SESSION_YOUR_ID.md

# 3. Check priorities
cat missions/active/DO_THIS_NOW.md
```

**When done:** `./automation/coordination/session-stop.sh my-session-name`

---

### 📖 Key Resources

**Essential files:**
- `docs/coordination/SSOT.json` - Active sessions & system state
- `missions/active/DO_THIS_NOW.md` - Current priorities
- `SYSTEM_INDEX.json` - Complete system map

**Browse:**
- `services/` - 75+ deployable services
- `docs/guides/` - How-to guides
- `docs/coordination/sessions/ACTIVE/` - Active builds

---

## 📁 Directory Structure

**Key directories:**
- `services/` - 75+ deployable services (use `_TEMPLATE/` for new ones)
- `systems/` - Major systems (magnet-trading, mission-portal)
- `docs/` - All documentation (guides, architecture, coordination, status)
- `missions/` - Human apprentice tasks (check `active/DO_THIS_NOW.md`)
- `automation/` - Scripts (deployment, monitoring, coordination)
- `data/` - Logs, credentials, backups
- `archive/` - Historical files

**Full tree:** See [docs/architecture/DIRECTORY_STRUCTURE.md](docs/architecture/DIRECTORY_STRUCTURE.md)

---

## 🚀 Common Tasks

```bash
# Launch a mission
cat missions/active/DO_THIS_NOW.md

# Check system health (live dashboard)
open http://198.54.123.234:8032

# Browse services
ls services/*/

# Deploy a service
cd services/your-service/ && ./deploy.sh

# View guides
ls docs/guides/
```

---

## 🎯 System Context

**Goal:** $373K → $5T over 10 years

**Phase 1 Services:** i-match (AI matching), magnet-trading (treasury protection)
**Coordination:** Multi-AI sessions + human apprentices via file-based protocol
**Current Work:** [missions/active/DO_THIS_NOW.md](missions/active/DO_THIS_NOW.md)

**Live Production Systems:**
- **🌐 Missions Portal:** https://fullpotential.ai/missions (apprentice missions & coordination)
- **Memory Dashboard:** http://198.54.123.234:8032 (real-time system monitoring)
- **Memory Tools:** `services/_shared/memory_optimizer.py` (optimization utilities)

**Key Indices:**
- System map: `SYSTEM_INDEX.json`
- Active sessions: `docs/coordination/SSOT.json`
- Services: `services/` directory

---

## 📞 Getting Help

- **Humans:** Check [docs/guides/](docs/guides/) or tell James exactly where you're stuck
- **AI Sessions:** Check [SYSTEM_INDEX.json](SYSTEM_INDEX.json) and [docs/coordination/](docs/coordination/)
- **New Service:** Copy `services/_TEMPLATE/`, customize, deploy
- **Documentation:** Add to appropriate `docs/` subdirectory

---

**Last Updated:** Nov 20, 2025
**Read Time:** ~3 minutes (first time), ~1 minute (returning)

🚀 **Ready to begin? Scroll to top and pick your path!**
