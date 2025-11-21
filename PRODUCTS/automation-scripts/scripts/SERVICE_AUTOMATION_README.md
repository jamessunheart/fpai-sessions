# Service Automation Suite
**Uniform service management across Local → GitHub → Server**

Created by: Session #2 (Coordination & Infrastructure)
Date: 2025-11-15

---

## 🎯 Purpose

These scripts ensure **complete uniformity** across:
- ✅ Local development (`~/Development/SERVICES/`)
- ✅ GitHub repos (`github.com/fullpotentialai/`)
- ✅ Server deployment (`/opt/fpai/` on 198.54.123.234)

Every service follows:
- **UDC (Universal Droplet Contract)** - 6 required endpoints
- **Standard structure** - src/, tests/, deploy/, docs/
- **Registry tracking** - All services in SERVICE_REGISTRY.json

---

## 📜 Available Scripts

### 1. `create-service-repos.sh`
**Create GitHub repos for all existing services**

```bash
./create-service-repos.sh
```

**What it does:**
- Reads `SERVICE_REGISTRY.json`
- For each service without a GitHub repo:
  - Creates repo at `github.com/fullpotentialai/[service-name]`
  - Pushes existing code
  - Updates registry with repo URL

**When to use:** When you have local services that need GitHub repos

---

### 2. `new-service.sh`
**Scaffold a new service from scratch**

```bash
./new-service.sh [service-name] "Description" [port]
```

**Example:**
```bash
./new-service.sh payment-processor "Handle payment processing" 8500
```

**What it does:**
1. Copies `_TEMPLATE/` structure
2. Creates GitHub repo
3. Initializes git and pushes
4. Creates FastAPI app with **all 6 UDC endpoints**
5. Registers in `SERVICE_REGISTRY.json`
6. Creates server directory
7. Ready to develop!

**When to use:** Starting a brand new service

**Output:**
- Local: `~/Development/SERVICES/payment-processor/`
- GitHub: `github.com/fullpotentialai/payment-processor`
- Server: `/opt/fpai/payment-processor/` (directory created)

---

### 3. `sync-service.sh`
**Three-way sync: Local → GitHub → Server**

```bash
./sync-service.sh [service-name]
```

**Example:**
```bash
./sync-service.sh i-proactive
```

**What it does:**
1. Commits local changes
2. Pushes to GitHub
3. Syncs to server via rsync
4. Restarts service

**When to use:** After making changes to a service

**Perfect for:**
- Deploying updates
- Keeping all 3 locations in sync
- Quick iterations

---

### 4. `enforce-udc-compliance.sh`
**Validate services have all 6 required endpoints**

```bash
# Check all services
./enforce-udc-compliance.sh

# Check specific service
./enforce-udc-compliance.sh i-proactive
```

**Required endpoints:**
1. `/health` - Service status
2. `/capabilities` - What it provides
3. `/state` - Resource usage
4. `/dependencies` - Required services
5. `/message` - Inter-service communication

**Output:**
```
✅ Fully compliant: 2
⚠️  Non-compliant: 1
⏸️  Not running: 1
```

**When to use:** Before deploying to production

---

## 🔄 Complete Workflow Examples

### Starting a New Service

```bash
# 1. Create service (creates everywhere)
./new-service.sh my-service "My awesome service" 8600

# 2. Develop locally
cd ~/Development/SERVICES/my-service
./start.sh

# 3. Test it works
curl http://localhost:8600/health

# 4. Deploy to server
./sync-service.sh my-service

# 5. Test on server
curl http://198.54.123.234:8600/health

# 6. Verify UDC compliance
./enforce-udc-compliance.sh my-service
```

### Updating an Existing Service

```bash
# 1. Make changes locally
cd ~/Development/SERVICES/i-proactive
# ... edit code ...

# 2. Sync everywhere
cd ~/Development/docs/coordination/scripts
./sync-service.sh i-proactive

# Done! Changes are now:
#   - Committed to git
#   - Pushed to GitHub
#   - Deployed to server
#   - Service restarted
```

### Creating GitHub Repos for All Services

```bash
# One command to create all missing repos
./create-service-repos.sh
```

---

## 📋 SERVICE_REGISTRY.json Structure

Every service is tracked with:

```json
{
  "name": "service-name",
  "description": "What it does",
  "status": "development|production",
  "port": 8400,
  "path_local": "/Users/jamessunheart/Development/SERVICES/service-name",
  "path_production": "/opt/fpai/service-name",
  "repo": "https://github.com/fullpotentialai/service-name",
  "tech_stack": ["Python", "FastAPI"],
  "dependencies": ["fastapi", "uvicorn"]
}
```

**All scripts read this registry** - it's the single source of truth.

---

## 🏗️ Standard Service Structure

Every service must follow this structure:

```
service-name/
├── src/                    # Source code
│   └── main.py            # FastAPI app with UDC endpoints
├── tests/                  # Test files
├── deploy/                 # Deployment configs
├── docs/                   # Documentation
├── README.md              # Service overview
├── SPEC.md                # Technical specification
├── PROGRESS.md            # Development tracking
├── requirements.txt       # Python dependencies
├── start.sh               # Start script
└── .git/                  # Git repository
```

**This structure is:**
- ✅ Created by `new-service.sh`
- ✅ Enforced by `_TEMPLATE/`
- ✅ Synced by `sync-service.sh`
- ✅ Same on local, GitHub, and server

---

## 🔐 Server Access

All scripts use:
- **Server:** `root@198.54.123.234`
- **Path:** `/opt/fpai/[service-name]`
- **Method:** SSH + rsync

**SSH keys must be set up** for passwordless access.

---

## 🎓 For Claude Sessions

**To create a new service:**
```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./new-service.sh [name] "Description" [port]
```

**To deploy changes:**
```bash
./sync-service.sh [service-name]
```

**To check compliance:**
```bash
./enforce-udc-compliance.sh [service-name]
```

**All services are uniform** - same structure, same endpoints, same deployment process.

---

## ✅ Benefits

1. **Uniformity** - All services follow the same structure
2. **Speed** - Create new service in seconds with all infrastructure
3. **Compliance** - UDC endpoints enforced automatically
4. **Sync** - Local, GitHub, Server always in sync
5. **Tracking** - Everything registered in SERVICE_REGISTRY.json
6. **Coordination** - All Claude sessions use the same scripts

---

## 🆘 Troubleshooting

**"Service not found in registry"**
- Run: `cat ~/Development/SERVICES/SERVICE_REGISTRY.json | grep -A5 "name"`
- Your service must be in the registry

**"GitHub repo creation failed"**
- Check: `gh auth status`
- Reauth: `gh auth login`

**"Server sync failed"**
- Check: `ssh root@198.54.123.234 'ls /opt/fpai'`
- Verify SSH access works

**"UDC compliance failed"**
- See: `/Users/jamessunheart/Development/docs/coordination/MEMORY/UDC_COMPLIANCE.md`
- Add missing endpoints to your service

---

**Created by Session #2 - Coordination & Infrastructure**
**Part of the Collective Mind coordination system**

🌐⚡💎
