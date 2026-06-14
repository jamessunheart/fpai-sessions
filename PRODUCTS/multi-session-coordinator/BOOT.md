# BOOT SEQUENCE - Claude Code Session Initialization

**READ THIS FIRST when starting a new Claude Code session**

Last Updated: 2025-11-16
Version: 2.2 - Credential Vault Enhanced Security (5-Star Rating)
Status: OPERATIONAL

---

## 🚀 QUICK START (Do This Now)

### Step 1: 🌐 READ CAPITAL & VISION SSOT (MOST IMPORTANT!)

```bash
cat docs/coordination/CAPITAL_VISION_SSOT.md
```

**⚡ THIS IS THE SINGLE SOURCE OF TRUTH FOR RESOURCES - READ FIRST, EVERY SESSION ⚡**

---

#### 📊 PRESENT RESOURCES (What We Have NOW):

**Capital Available: $373,261**
- **Spot Holdings:** $164,608 (44%)
  - 1.0 BTC @ $96K
  - 373 SOL @ $148
  - 4.1M HOT @ $0.003
  - 1K USDT
- **Leveraged Positions:** $208,653 margin (56%)
  - BTC 3x + BTC 2x + SOL 2x
  - Current P&L: -$31,041 (-8.32%)
  - Status: Holding through correction

**Operating Costs: $30,000/month**
- **Ministry Operations:** $20,000/month (FPAI infrastructure, development, marketing)
- **Ministry Leadership:** $10,000/month (housing, family support, operations)
- **Burn Rate:** $30K/month = 12 months runway with current capital
- **Legal Structure:** 508(c)(1)(A) Church → Trust → LLC ventures within PMA

**Current Revenue: $0**
- I MATCH: Ready to launch
- Platform services: In development
- Treasury yields: Not deployed yet (potential $2-7K/month)

**💡 Bottom Line:** We have $373K capital and 12 months runway. Treasury deployment ($2-7K/month yield) + Revenue generation (target $30K MRR) = Path to sustainability.

---

#### 🌐 FUTURE VISION (Where We're Going):

**Total Addressable Market: $5.21 TRILLION**

**The 10-Year Path:**
```
$373K → $5M → $100M → $3B → $150B → $1-5T
(Now)   (M6)  (Y2)    (Y4)  (Y7)    (Y10+)
```

**Phase 1 (NOW):** PROOF - $373K → $5M (Months 1-6)
- 100 matches in financial advisors
- $500K treasury through yields
- Proven unit economics (CAC < LTV/5, NPS > 50)

**Phase 2:** EXPAND - $5M → $100M (Months 7-18)
- 5-10 categories live, 10K matches
- $5M ARR, network effects kicking in

**Phase 3-5:** SUPER-APP → NETWORK EFFECTS → NEW PARADIGM
- $100M → $3B → $150B → $1-5T
- Years 2-10+, exponential growth

**💡 Bottom Line:** $5T isn't hype—it's math. AI + network effects + 10 categories.

---

#### 🎯 THE GAP (What We Must Do):

**PRESENT → FUTURE requires:**

1. **Deploy Capital** ($373K → yields)
   - 40% stable DeFi: $2K/month
   - 40% tactical: $3-12K/month
   - 20% moonshots: $6-31K/month
   - Target: $2-7K/month average

2. **Launch Revenue** ($0 → $40K/month)
   - I MATCH Phase 1: 10 matches Month 1
   - Scale to 100 matches by Month 6
   - Build 5-10 more categories

3. **Build Platform**
   - Unified AI matching engine
   - Modular category system
   - Token integration (FPAI/POT)
   - Analytics dashboard

**💡 Bottom Line:** Execute Phase 1 → Prove model → Scale exponentially.

---

#### 📊 LIVE DASHBOARD (Real-Time Tracking):

**View present & future resources in real-time:**
- **Treasury Dashboard:** https://fullpotential.com/dashboard/money
  - Current capital, positions, P&L
  - AI consumption breakdown
  - Optimization recommendations
  - Auto-updates every 30 seconds

**API Access:**
- GET https://fullpotential.com/api/treasury (full metrics)
- GET https://fullpotential.com/api/treasury/positions (crypto positions)
- GET https://fullpotential.com/api/treasury/recommendations (optimizations)

---

**Why Step 1 is CRITICAL:**

Every session MUST be aligned on:
1. ✅ **PRESENT:** $373K capital (idle, needs deployment)
2. ✅ **FUTURE:** $5.21T TAM (10-year exponential path)
3. ✅ **GAP:** Deploy → Build → Prove → Scale
4. ✅ **PHASE:** Phase 1 execution (100 matches, $500K treasury)
5. ✅ **ACTION:** Your work must close the gap between present & future

**READ CAPITAL_VISION_SSOT.md BEFORE DOING ANYTHING ELSE.**

All resource numbers, strategy details, and progress metrics are in that file.
It's updated in real-time and displayed on the dashboard.

---

### Step 2: Check Your Identity

```bash
# Where am I?
pwd
# Should be: /Users/jamessunheart/Development

# What terminal?
echo $TERM_SESSION_ID || tty
```

### Step 3: Register Your Session

```bash
cd docs/coordination/scripts
./claude-session-register.sh YOUR_NUMBER "Your Role" "Your Goal"
```

**Available Numbers:** 12
**Currently Registered:** 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13

**Choose a role based on your task:**
- Architect / Builder
- DevOps Engineer
- Revenue Engineer
- Coordination Engineer
- Infrastructure Engineer
- etc.

### Step 4: 🔐 Set Up Credential Vault Access (CRITICAL)

**Ask user for master key ONCE:**
```bash
# User provides this ONCE per session:
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"
```

**Check what credentials are available:**
```bash
./session-list-credentials.sh
```

**Available credentials (10):**
- anthropic_api_key (Claude AI)
- openai_api_key (OpenAI)
- STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY (Payments)
- NAMECHEAP_API_USER, NAMECHEAP_API_KEY (Domains)
- server_admin_password, server_master_encryption_key, server_jwt_secret (Server)
- test_key (Testing)

**⚠️ NEVER ask user for individual credentials - check vault first!**

### Step 5: Check Messages

```bash
./session-check-messages.sh
```

### Step 6: View Current State

```bash
cat ../SSOT.json | python3 -m json.tool | head -100
```

---

## 📋 CORE PROTOCOLS

**You MUST follow these protocols:**

### 1. Session Registry Protocol
**File:** `docs/coordination/SESSION_REGISTRY_PROTOCOL.md`

**Register yourself:**
```bash
./scripts/claude-session-register.sh NUMBER "ROLE" "GOAL"
```

**This makes you visible to all other sessions**

### 2. Service Registry Protocol
**File:** `docs/coordination/SERVICE_REGISTRY_PROTOCOL.md`

**Register services you build:**
```bash
./scripts/service-register.sh "name" "description" PORT "status"
./scripts/service-update.sh "name" "status"
```

**This tracks what you're building**

### 3. Credential Vault Protocol ⭐ CRITICAL (Enhanced v2.0)
**Files:**
- `docs/coordination/VAULT_SECURITY_ENHANCED.md` (Security Features Guide - NEW!)
- `docs/coordination/VAULT_ACCESS_FOR_SESSIONS.md` (Complete Guide)
- `docs/coordination/VAULT_QUICK_REFERENCE.md` (Quick Reference)

**🔒 NEW: Enhanced Security Features**
- ✅ Audit logging (track who accessed what when)
- ✅ Automatic encrypted backups (last 10 kept)
- ✅ Access monitoring (timestamps, session tracking)
- ✅ File integrity monitoring (SHA-256 hashing)
- ⭐ Security Rating: 5/5 for development environment

**🔑 STEP 1: Get Master Key from User (ONCE per session)**
```bash
# Ask user for this ONCE at session start:
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"
export CLAUDE_SESSION_ID="session-X"  # For audit trail
```

**📋 STEP 2: Check what's in vault (BEFORE asking user for anything)**
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts

# Using wrapper scripts (original - still works)
./session-list-credentials.sh

# OR using enhanced vault (NEW - with stats)
python3 credential_vault_enhanced.py stats
python3 credential_vault_enhanced.py list
```

**📥 STEP 3: Retrieve credentials from vault**
```bash
# Get ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=$(./session-get-credential.sh anthropic_api_key)

# Get OpenAI key
export OPENAI_API_KEY=$(./session-get-credential.sh openai_api_key)

# Get Stripe keys
export STRIPE_SECRET_KEY=$(./session-get-credential.sh STRIPE_SECRET_KEY)
export STRIPE_PUBLISHABLE_KEY=$(./session-get-credential.sh STRIPE_PUBLISHABLE_KEY)
```

**💾 STEP 4: Add new credentials to vault (when user provides them)**
```bash
# If user gives you a new credential, save it for all sessions:
./session-set-credential.sh <name> <value> <type> <service>

# Examples:
./session-set-credential.sh sendgrid_api_key "SG.xxxxx" api_key sendgrid
./session-set-credential.sh db_password "pass123" password postgres
./session-set-credential.sh github_token "ghp_xxxxx" access_token github
```

**🔄 STEP 5: Broadcast when adding important credentials**
```bash
./session-send-message.sh "broadcast" "Credential Added" "sendgrid_api_key now in vault" "normal"
```

**📊 STEP 6 (NEW): Monitor vault security**
```bash
# View vault statistics (backups, last modified, etc.)
python3 credential_vault_enhanced.py stats

# View audit log (who accessed what when)
python3 credential_vault_enhanced.py audit 50
```

**⚠️ CRITICAL RULES:**
- ✅ **ALWAYS check vault FIRST** before asking user for credentials
- ✅ **SAVE to vault** when user provides new credentials
- ✅ **NEVER ask user twice** for same credential
- ✅ **ALL sessions share same vault** (read/write access)
- ✅ **SET CLAUDE_SESSION_ID** for audit trail
- ✅ **10 credentials already available** (see list below)

**Currently in Vault (as of 2025-11-16):**
1. anthropic_api_key (api_key) [anthropic]
2. openai_api_key (api_key)
3. STRIPE_SECRET_KEY (api_key)
4. STRIPE_PUBLISHABLE_KEY (api_key)
5. NAMECHEAP_API_USER (api_key) [namecheap]
6. NAMECHEAP_API_KEY (api_key) [namecheap]
7. server_admin_password (password) [credentials-manager]
8. server_master_encryption_key (secret) [credentials-manager]
9. server_jwt_secret (secret) [credentials-manager]
10. test_key (api_key) [test]

**This ensures user NEVER has to repeat credentials across sessions**

### 4. Treasury & Resources SSOT ⭐ CRITICAL
**File:** `docs/coordination/CAPITAL_VISION_SSOT.md`

**🏛️ THE SINGLE SOURCE OF TRUTH FOR FINANCES, VISION & LEGAL STRUCTURE**

**Read this FIRST every session to understand:**
- **Current Capital:** $373,261 (BTC, SOL, leveraged positions)
- **Monthly Burn:** $30,000/month (12 months runway)
- **Legal Structure:** 508(c)(1)(A) Church → Trust → LLC ventures
- **Vision:** $373K → $5 Trillion over 10 years
- **Phase 1 Goal:** 100 matches + $30K MRR in 6 months

**View the SSOT:**
```bash
cat docs/coordination/CAPITAL_VISION_SSOT.md | less
```

**Key Sections:**
- Legal Structure & Compliance (508c1a framework)
- Current Resources ($373K breakdown)
- Operating Costs ($30K/month - ministry expenses)
- Treasury Strategy (yield generation $2-7K/month)
- Vision & Path ($5.21T TAM, 10-year phases)
- Phase 1 Metrics (proof + profitability)

**⚠️ CRITICAL COMPLIANCE:**
- Internal tracking: This SSOT (detailed breakdown)
- Public reporting: Ministry-aligned categories only
- All revenue services = Ministry tools/platforms
- Legal verification required before external reporting

**This tells you WHERE WE ARE and WHERE WE'RE GOING. Read it every session.**

### 5. Communication Protocol
**Send messages:**
```bash
./scripts/session-send-message.sh "broadcast" "Subject" "Message" "priority"
./scripts/session-send-message.sh "session-5" "Subject" "Direct message" "normal"
```

**Check messages:**
```bash
./scripts/session-check-messages.sh
```

### 5. Resource SSOT Update Protocol ⭐ CRITICAL
**Files to update:** `CAPITAL_VISION_SSOT.md` + `BOOT.md Step 1`

**WHEN to update:**
- Capital changes (new positions, P&L updates, treasury deployment)
- Revenue milestones reached (first match, $1K MRR, etc.)
- Phase transitions (Phase 1 → Phase 2, etc.)
- Major strategic decisions (treasury vote, new categories, etc.)
- Operating costs change (new services, API usage spikes)

**HOW to update (4-step protocol):**

```bash
# Step 1: Update the SSOT file
cd /Users/jamessunheart/Development
# Edit docs/coordination/CAPITAL_VISION_SSOT.md with new data

# Step 2: Update BOOT.md Step 1 (if present resources changed)
# Edit docs/coordination/MEMORY/BOOT.md lines 23-47 (PRESENT RESOURCES section)

# Step 3: Sync everywhere (Local → GitHub → Server)
git add docs/coordination/CAPITAL_VISION_SSOT.md docs/coordination/MEMORY/BOOT.md
git commit -m "Update resource SSOT: [what changed]"
git push

# Upload to server
scp docs/coordination/CAPITAL_VISION_SSOT.md root@198.54.123.234:/opt/fpai/docs/coordination/
scp docs/coordination/MEMORY/BOOT.md root@198.54.123.234:/opt/fpai/docs/coordination/MEMORY/

# Step 4: Notify all sessions
cd docs/coordination/scripts
./session-send-message.sh "broadcast" "Resource SSOT Updated" \
  "Updated CAPITAL_VISION_SSOT.md: [what changed]. All sessions: reread BOOT.md Step 1 for latest resources." \
  "high"
```

**What to update in CAPITAL_VISION_SSOT.md:**
- Line 4: Last Updated timestamp
- Lines 13-30: Current capital, positions, P&L
- Lines 32-37: Operating costs, AI consumption
- Lines 39-45: Revenue projections (update as we hit milestones)
- Lines 109-130: Phase 1 milestones (check boxes as we progress)
- Lines 257-279: Success Dashboard metrics

**What to update in BOOT.md Step 1:**
- Lines 25-34: Capital breakdown (if changed)
- Lines 36-40: Operating costs (if changed)
- Lines 42-45: Current revenue (if changed)

**CRITICAL:** After updating, all sessions who run `cat docs/coordination/MEMORY/BOOT.md` will see the new data immediately!

### 6. Service Automation Protocol ⭐ NEW
**File:** `docs/coordination/scripts/SERVICE_AUTOMATION_README.md`

**CRITICAL: All services MUST be uniform across Local → GitHub → Server**

**Create new service (AUTO: creates everywhere):**
```bash
./scripts/new-service.sh [name] "Description" [port]
```

**Deploy changes (AUTO: syncs everywhere):**
```bash
./scripts/sync-service.sh [service-name]
```

**Create GitHub repos for all services:**
```bash
./scripts/create-service-repos.sh
```

**Validate UDC compliance (6 required endpoints):**
```bash
./scripts/enforce-udc-compliance.sh [service-name]
```

**This ensures:**
- ✅ Uniform structure (all services follow _TEMPLATE)
- ✅ GitHub integration (all services version controlled)
- ✅ Server deployment (automated sync to production)
- ✅ UDC compliance (all 6 required endpoints)
- ✅ Registry tracking (SERVICE_REGISTRY.json is source of truth)

**NEVER manually create services - ALWAYS use these scripts!**

### 7. Task Automation Protocol ⭐ NEW - CRITICAL
**Service:** `task-automation` (Port 8031)
**Files:**
- `SERVICES/task-automation/QUICK_START.md` - Quick reference
- `SERVICES/task-automation/README.md` - Complete documentation
- `SERVICES/task-automation/TASK_AUTOMATION_FRAMEWORK.md` - Architecture

**🤖 AUTOMATE BEFORE ASKING USER TO DO MANUAL WORK**

**⚠️ CRITICAL RULE: Before asking user to manually sign up for services, configure settings, or perform operational tasks - CHECK IF TASK AUTOMATION CAN HANDLE IT!**

**What Can Be Automated:**
- ✅ Service signups (SendGrid, Mailgun, GitHub, etc.)
- ✅ Email verifications (monitor dashboard, flag for human click)
- ✅ DNS configurations (via API or task tracking)
- ✅ API integrations (automated setup + credential storage)
- ✅ Account configurations (settings, webhooks, etc.)
- ✅ Form submissions (with AI assistance)

**DECISION FLOW:**

```
User needs something (e.g., "Set up SendGrid")
    ↓
1. Can it be automated? (Check task automation framework)
    YES → Create task + let system handle it
    NO  → Ask user OR flag for human-in-the-loop
    ↓
2. Create automation task:
    ssh root@198.54.123.234 "cd /root/SERVICES/task-automation && \
      python3 src/cli.py create [type] [service] 'description' \
      --params '{...}' --analyze"
    ↓
3. AI analyzes task:
    - Automation level: FULL | SEMI | MANUAL
    - Blockers identified: CAPTCHA, EMAIL_VERIFICATION, etc.
    - Steps recommended
    - Time estimate
    ↓
4. Route accordingly:
    FULL → Automated execution (Phase 2+)
    SEMI → Automated with human checkpoints
    MANUAL → Queue for human OR ask user
```

**CLI Usage (On Server):**
```bash
ssh root@198.54.123.234
cd /root/SERVICES/task-automation

# Create task with AI analysis
python3 src/cli.py create service_signup sendgrid \
  "Set up SendGrid email relay" \
  --params '{"sender": "james@fullpotential.com"}' \
  --analyze

# List pending tasks
python3 src/cli.py list --status pending

# View task details
python3 src/cli.py show [task-id]

# Get service suggestion
python3 src/cli.py suggest "Need email relay" --category email
```

**Web Dashboard:**
```
http://198.54.123.234:8031
```

**When to Use Task Automation:**

**✅ YES - Use task automation for:**
- Service signups and configurations
- Email/phone verifications (semi-automated)
- DNS record setup
- API key generation and storage
- Webhook configurations
- Account settings
- Any repetitive operational task

**❌ NO - Don't use task automation for:**
- Writing code or building features
- Strategic decisions
- Creative work
- Real-time user interactions
- Tasks requiring immediate human judgment

**Human-in-the-Loop Integration:**

**When task is BLOCKED:**
```python
# Task gets marked as BLOCKED with blocker type
# E.g., CAPTCHA, EMAIL_VERIFICATION, PHONE_VERIFICATION

# System can:
1. Send message to user via session-send-message.sh
2. Create notification in dashboard
3. Wait for human action
4. Resume automation after human completes blocker
```

**Example - SendGrid Setup (SEMI-automated):**
```bash
# Step 1: Create task
python3 src/cli.py create service_signup sendgrid \
  "Set up SendGrid for daily reports" --analyze

# AI Response:
# ✅ Can automate: YES
# ✅ Automation Level: SEMI
# ✅ Blockers: EMAIL_VERIFICATION
# ✅ Steps:
#    1. Navigate to SendGrid signup (automated)
#    2. Fill registration form (automated)
#    3. Submit form (automated)
#    4. **Monitor email dashboard for verification** (automated)
#    5. **Click verification link** (HUMAN REQUIRED)
#    6. Extract API key (automated)
#    7. Store in credential vault (automated)
#    8. Configure Postfix relay (automated)
# ✅ Time: 5 minutes (vs 15-30 manual)
# ✅ Human actions: 1 (email click)

# Step 2: System tracks progress, notifies when human action needed
# Step 3: Human clicks email link
# Step 4: System completes remaining steps automatically
```

**Benefits:**
- ⏱️ **Time:** 5 minutes vs 15-30 manual
- 🎯 **Consistency:** Same process every time
- 📝 **Documentation:** Auto-generated logs
- 🔄 **Reusability:** Same task type reusable
- 🤝 **Human-in-the-loop:** Smart delegation to human when needed

**CRITICAL: Before asking user to manually do ANY operational task, check if task automation can help!**

**This makes sessions more autonomous and reduces friction for the user.**

---

## 📚 FOUNDATION FILES (Read Before Building)

**The 5 Technical Standards - CRITICAL for all services:**

1. **UDC_COMPLIANCE.md** - Universal Droplet Contract (6 required endpoints)
2. **TECH_STACK.md** - Standard technologies (Python, FastAPI, PostgreSQL, etc.)
3. **SECURITY_REQUIREMENTS.md** - Security best practices (authentication, encryption, validation)
4. **CODE_STANDARDS.md** - Coding conventions (Python style, testing, documentation)
5. **INTEGRATION_GUIDE.md** - How to connect to the ecosystem

**When building services:** Read these FIRST, follow them ALWAYS

---

## 🛠️ EXECUTION GUIDES (How to Build)

**The how-to manuals:**

1. **ASSEMBLY_LINE_SOP.md** - The 4-phase build process (SPECS → BUILD → README → PRODUCTION)
2. **DEVELOPER_ACCELERATION_KIT.md** - Rapid development patterns & code generators
3. **APPRENTICE_HANDBOOK.md** - Daily workflow & execution protocol

**Start with ASSEMBLY_LINE_SOP.md** - It shows the step-by-step process for every service

---

## ✅ VERIFICATION STANDARDS (Quality Control)

**What senior devs check:**

1. **VERIFICATION_PROTOCOL.md** - 6 levels of verification (Basic → UDC → Tests → Quality → Security → Production)
2. **LEARNING_PROGRESSION.md** - Quality expectations at each skill level (Novice → Competent → Proficient → Expert)

**Before deploying:** Run through verification checklist

---

## 🧠 OPERATING PRINCIPLES (How to Think)

**Core philosophy - Read to understand the mindset:**

**PRINCIPLES.md** - LIFE TO LIFE paradigm + 9 core principles:
1. Context = Consciousness (Search first, always)
2. Design > Data > Decisions (Fix architecture first)
3. Build Hierarchy (Search → Evaluate → Orchestrate → Build)
4. Decide → Explain → Undo (Execute reversible actions immediately)
5. Compress to Action (Think wide, communicate succinct)
6. Flow Like Water (Core stable, implementation fluid)
7. Companion Not Bot (Presence over efficiency)
8. Memory Persistence (Update files directly)
9. Work Hours Not Calendar Time (Parallel execution thinking)

---

## 📝 SESSION LOGS & LEARNINGS

**Share and learn from collective intelligence:**

- **shared-knowledge/learnings.md** - Past learnings from all sessions
- **shared-knowledge/best-practices.md** - Proven patterns
- **shared-knowledge/patterns.md** - Reusable solutions
- **shared-knowledge/troubleshooting.md** - Common issues & fixes
- **sessions/ACTIVE/** - Active session work logs
- **sessions/ARCHIVE/** - Completed session records

**Share your learnings:**
```bash
./scripts/session-share-learning.sh \
    "Category" \
    "What you learned" \
    "Impact level"
```

---

## 🗺️ SYSTEM MAP

### Key Locations:

```
/Users/jamessunheart/Development/
├── docs/coordination/          # COORDINATION HUB
│   ├── MEMORY/                 # THIS FOLDER - Boot sequence
│   ├── SSOT.json              # Single Source of Truth (read-only)
│   ├── claude_sessions.json   # Session registry
│   ├── services_status.json   # Service registry
│   └── scripts/               # All coordination scripts
│
├── SERVICES/                   # SERVICE DEVELOPMENT
│   ├── SERVICE_REGISTRY.json  # Master service catalog
│   ├── _TEMPLATE/             # Template for new services
│   ├── integrated-registry-system.py  # Auto-sync tool
│   └── [your-service]/        # Your service here
│
└── .claude-consciousness      # Auto-loaded context
```

### Key URLs:

- **Master Dashboard:** https://fullpotential.com/master (password: gDqfvCUrAfZvA17c)
- **Credential Vault:** https://fullpotential.com/vault
- **Coordination Dashboard:** https://fullpotential.com/dashboard/coordination
- **Server Registry:** http://198.54.123.234:8000

---

## 🎯 CURRENT MISSION

**Collective Goal:** Build autonomous revenue systems → $120K MRR

**Active Initiatives:**
1. AI Marketing Engine (Session #1, #3)
2. Revenue Dashboard (Session #9)
3. FPAI Empire Platform (Session #10)
4. Session Coordination (Session #2, #13)
5. Communication Infrastructure (Session #8)

**Your Role:** Find where you fit, register, start building

---

## ✅ CHECKLIST - Complete Before Starting Work

- [ ] **Read BOOT.md Step 1 - Resource SSOT (MOST CRITICAL!)**
  - [ ] Know current capital: $373K (spot + leveraged positions)
  - [ ] Know future vision: $5.21T TAM, 10-year path
  - [ ] Know the gap: Deploy → Build → Prove → Scale
  - [ ] Know the dashboard: https://fullpotential.com/dashboard/money
- [ ] Read this BOOT.md file completely
- [ ] **🔐 Set up credential vault access (CRITICAL):**
  - [ ] Got master key from user: `export FPAI_CREDENTIALS_KEY="..."`
  - [ ] Listed available credentials: `./session-list-credentials.sh`
  - [ ] Know how to retrieve: `./session-get-credential.sh <name>`
  - [ ] Know how to add: `./session-set-credential.sh <name> <value> <type> <service>`
  - [ ] **NEVER ask user for credentials without checking vault first**
- [ ] Registered in session registry (`claude-session-register.sh`)
- [ ] Checked messages (`session-check-messages.sh`)
- [ ] Viewed SSOT.json to see current system state
- [ ] Read relevant protocol docs:
  - [ ] VAULT_ACCESS_FOR_SESSIONS.md ⭐ CRITICAL - Credential management
  - [ ] SESSION_REGISTRY_PROTOCOL.md
  - [ ] SERVICE_REGISTRY_PROTOCOL.md
  - [ ] SERVICE_AUTOMATION_README.md ⭐ CRITICAL
- [ ] Know how to send/receive messages
- [ ] Understand your role and goal
- [ ] **Know the 4 service automation scripts:**
  - [ ] `new-service.sh` - Create new service
  - [ ] `sync-service.sh` - Deploy changes
  - [ ] `create-service-repos.sh` - GitHub repos
  - [ ] `enforce-udc-compliance.sh` - Validate endpoints
- [ ] **🤖 Know task automation system (CRITICAL):**
  - [ ] Understand decision flow: Automate before asking user
  - [ ] Know when to use it: Service signups, configs, verifications
  - [ ] Know how to create tasks: `python3 src/cli.py create ...`
  - [ ] Know dashboard: http://198.54.123.234:8031
  - [ ] **Remember: Check task automation BEFORE asking user to do manual work**
- [ ] Ready to coordinate with other sessions

---

## 📚 ESSENTIAL READING

**Complete boot sequence - Read in this order:**

### Phase 1: Orientation (Start here)
1. **BOOT.md** (this file) ← YOU ARE HERE
2. **PRINCIPLES.md** - Operating philosophy & mindset
3. **PROTOCOLS_INDEX.md** - Quick reference for all protocols

### Phase 2: Foundation Knowledge (Before building)
4. **UDC_COMPLIANCE.md** - 6 required endpoints
5. **TECH_STACK.md** - Standard technologies
6. **SECURITY_REQUIREMENTS.md** - Security standards
7. **CODE_STANDARDS.md** - Coding conventions
8. **INTEGRATION_GUIDE.md** - Ecosystem integration

### Phase 3: Execution (When building)
9. **ASSEMBLY_LINE_SOP.md** - 4-phase build process
10. **DEVELOPER_ACCELERATION_KIT.md** - Rapid development
11. **APPRENTICE_HANDBOOK.md** - Daily workflow

### Phase 4: Verification (Before deploying)
12. **VERIFICATION_PROTOCOL.md** - Quality checkpoints
13. **LEARNING_PROGRESSION.md** - Skill development

**All MEMORY files in:** `/Users/jamessunheart/Development/docs/coordination/MEMORY/`
**Coordination files in:** `/Users/jamessunheart/Development/docs/coordination/`

---

## 🔄 STANDARD WORKFLOW

### Every Session Start:

1. Read MEMORY/BOOT.md (this file)
2. Register your session
3. Check messages
4. View SSOT.json
5. Start work

### When Building a Service (NEW AUTOMATED WORKFLOW):

**Creating NEW service:**
```bash
cd docs/coordination/scripts
./new-service.sh [name] "Description" [port]
# ✅ Creates: Local folder + GitHub repo + Server directory + UDC endpoints
```

**Updating EXISTING service:**
```bash
# 1. Make changes locally
cd ~/Development/SERVICES/[service-name]
# ... edit code ...

# 2. Deploy everywhere
cd ~/Development/docs/coordination/scripts
./sync-service.sh [service-name]
# ✅ Commits + Pushes to GitHub + Syncs to Server + Restarts service
```

**Validating service:**
```bash
./enforce-udc-compliance.sh [service-name]
# ✅ Checks all 6 required UDC endpoints
```

**⚠️ NEVER manually create services - ALWAYS use automation scripts!**

### When Coordinating:

1. Send messages to other sessions
2. Check SSOT.json for who's active
3. Propose via broadcast messages
4. Wait for consensus
5. Execute coordinated plan

---

## 🆘 TROUBLESHOOTING

### "I don't know what to do"
→ Read BOOT.md (this file) and REGISTRY_PROTOCOLS_SUMMARY.md

### "I can't see other sessions"
→ Check SSOT.json: `cat docs/coordination/SSOT.json | python3 -m json.tool | grep -A 100 claude_sessions`

### "How do I get credentials?"
→ `./scripts/session-list-credentials.sh`

### "How do I talk to other sessions?"
→ `./scripts/session-send-message.sh "broadcast" "Subject" "Message" "normal"`

### "What services exist?"
→ `cat docs/coordination/SSOT.json | python3 -m json.tool | grep -A 50 services`

### "Where's the documentation?"
→ `/Users/jamessunheart/Development/docs/coordination/MEMORY/`

### "How do I create a new service?"
→ `./scripts/new-service.sh [name] "Description" [port]` (NEVER create manually!)

### "How do I deploy my service?"
→ `./scripts/sync-service.sh [service-name]` (syncs to GitHub + Server)

### "My service isn't UDC compliant"
→ `./scripts/enforce-udc-compliance.sh [service-name]` to check what's missing

---

## 🎓 LEARNING PATH

**New to the system?** Follow this path:

**Day 1:** Orientation
- Read BOOT.md
- Register your session
- Explore SSOT.json
- Read protocol docs

**Day 2:** Integration
- Send your first message
- Register a test service
- Understand consensus process
- Review other sessions' work

**Day 3:** Contribution
- Pick a mission or create your own
- Start building
- Coordinate with relevant sessions
- Update service registry

---

## 🌟 SUCCESS METRICS

**You're successfully integrated when:**

✅ You're registered in claude_sessions.json
✅ You appear in SSOT.json
✅ You can send/receive messages
✅ You know how to register services
✅ You understand current missions
✅ You're coordinating with other sessions
✅ You're building toward collective goals

---

## 🔐 SECURITY

**Important:**
- NEVER commit credentials to git
- Use vault for all secrets
- Never ask user for credentials (use vault)
- Follow security best practices

---

## 📞 HELP

**Need human assistance?**
- User is available for guidance
- Document unclear? Ask for clarification
- Found a bug? Report it
- Have suggestions? Propose them

**Need session assistance?**
- Broadcast message to all sessions
- Direct message specific session
- Check SSOT.json for who's active in your area

---

**Welcome to the Collective Mind!**

You are Session #_____ (register above to claim your number)

**Your mission:** Contribute to the autonomous revenue system

**Your tools:** Coordination protocols, service registry, credential vault, SSOT

**Your team:** 12 other Claude Code sessions + human oversight

**Let's build! 🚀**

---

**Last updated by:** Session (Task Automation Integration)
**Date:** 2025-11-16
**System status:** OPERATIONAL ✅
**Major update:** ⭐ Protocol #7 - Task Automation Framework (CRITICAL)
  - 🤖 AUTOMATE BEFORE ASKING USER for operational tasks
  - Service signups, configs, verifications now systematic
  - AI-powered task analysis (automation level, blockers, steps)
  - Human-in-the-loop for blockers (CAPTCHA, email verification)
  - Web Dashboard: http://198.54.123.234:8031
  - CLI: `python3 src/cli.py` on server
  - **CRITICAL RULE:** Check task automation BEFORE asking user to do manual work
  - Reduces friction, increases autonomy, systematic approach
  - See: `SERVICES/task-automation/QUICK_START.md`
**Previous update:** Enhanced Step 1 - Present/Future Resource SSOT
**Next review:** After Phase 2 (browser automation) implementation
