# 🗂️ Full Potential AI - Unified Directory Structure

**Version:** 1.0
**Last Updated:** 2025-11-15

This document defines the standard directory structure used across **both** development and production environments.

---

## 🎯 Design Principles

1. **Mirror Structure** - Local and server use identical organization
2. **Clear Separation** - Services, docs, infrastructure, and data are clearly separated
3. **Easy Navigation** - Humans can quickly find what they need
4. **Scalable** - Structure supports growth from 10 to 1000 services

---

## 📁 Unified Structure

### Development: `/Users/jamessunheart/Development/`
### Production: `/opt/fpai/`

```
fpai/
├── apps/                    # All deployed services (droplets)
│   ├── registry/           # Service: Registry (port 8000)
│   ├── orchestrator/       # Service: Orchestrator (port 8001)
│   ├── dashboard/          # Service: Dashboard (port 8002)
│   ├── verifier/           # Service: Verifier (port 8003)
│   ├── proxy-manager/      # Service: Proxy Manager (port 8004)
│   ├── landing-page/       # Service: Landing Page (port 8005→80)
│   ├── membership/         # Service: Membership (port 8006)
│   ├── jobs/               # Service: Jobs Board (port 8008)
│   ├── i-match/            # Service: I Match (port TBD)
│   ├── i-proactive/        # Service: I Proactive (port 8400)
│   ├── auto-fix-engine/    # Service: Auto Fix Engine
│   ├── autonomous-executor/# Service: Autonomous Executor
│   ├── church-guidance-ministry/  # Service: Church Guidance
│   ├── credentials-manager/# Service: Credentials Manager
│   ├── deployer/           # Service: Deployer
│   ├── helper-management/  # Service: Helper Management
│   ├── ops/                # Service: Operations Dashboard
│   └── treasury-manager/   # Service: Treasury Manager
│
├── docs/                    # All documentation
│   ├── architecture/       # Architecture documents
│   ├── coordination/       # Coordination protocols
│   ├── intents/            # Intent documents
│   ├── sessions/           # Session history & learnings
│   ├── resources/          # Shared resources & tools
│   └── guides/             # How-to guides
│
├── infra/                   # Infrastructure as code
│   ├── docker/             # Docker configs
│   ├── nginx/              # Nginx configs
│   ├── scripts/            # Deployment scripts
│   └── monitoring/         # Monitoring configs
│
├── config/                  # Global configuration
│   ├── .env.example        # Environment template
│   ├── services.yaml       # Service registry config
│   └── ports.yaml          # Port assignments
│
├── data/                    # Persistent data
│   ├── registry/           # Registry data
│   ├── jobs/               # Jobs data
│   ├── membership/         # Membership data
│   └── shared/             # Shared data
│
├── logs/                    # Centralized logs
│   ├── services/           # Service logs
│   ├── deployment/         # Deployment logs
│   └── system/             # System logs
│
├── core/                    # Core system files
│   ├── actions/            # Sacred Loop actions
│   ├── intelligence/       # AI intelligence
│   ├── intent/             # Intent processing
│   └── state/              # System state
│
└── README.md               # Main navigation document
```

---

## 🔍 Quick Navigation Guide

### For Humans:

**Looking for a service?**
→ `apps/{service-name}/`

**Looking for documentation?**
→ `docs/{category}/`

**Looking for deployment scripts?**
→ `infra/scripts/`

**Looking for logs?**
→ `logs/services/{service-name}/`

**Looking for configuration?**
→ `config/`

### For AI Agents:

**Current system state?**
→ `core/state/`

**Available actions?**
→ `core/actions/`

**Session history?**
→ `docs/sessions/`

**Service capabilities?**
→ `apps/{service}/README.md`

---

## 📋 Directory Responsibilities

### `/apps/` - All Services
- Each service has its own directory
- Standard structure within each service:
  ```
  service-name/
  ├── app/                 # Application code
  ├── tests/              # Tests
  ├── Dockerfile          # Container definition
  ├── requirements.txt    # Dependencies
  ├── README.md          # Service documentation
  └── .env.example       # Environment template
  ```

### `/docs/` - Documentation
- Organized by category
- Markdown files for easy reading
- Version controlled

### `/infra/` - Infrastructure
- Deployment automation
- Server configuration
- Monitoring setup

### `/config/` - Configuration
- Environment variables
- Service registry
- Port mappings

### `/data/` - Persistent Data
- Database files
- Uploaded files
- Cache data

### `/logs/` - Logging
- Service logs (stdout/stderr)
- Deployment logs
- System logs

### `/core/` - Core System
- Sacred Loop implementation
- AI intelligence layer
- Intent processing
- System state management

---

## 🚀 Migration Plan

### Phase 1: Server Reorganization ✅
1. Move `i-match` from `/opt/fpai/i-match/` to `/opt/fpai/apps/i-match/`
2. Move `i-proactive` from `/opt/fpai/i-proactive/` to `/opt/fpai/apps/i-proactive/`
3. Create missing directories (`docs/`, `infra/`)

### Phase 2: Local Reorganization
1. Move all `.md` files from root to `docs/`
2. Rename `SERVICES/` to `apps/`
3. Create consistent directory structure
4. Update all scripts to use new paths

### Phase 3: Synchronization
1. Deploy remaining services to server
2. Sync documentation
3. Create master README.md for navigation

---

## 📌 Port Registry

Services and their assigned ports:

| Service | Port | Status |
|---------|------|--------|
| registry | 8000 | Active |
| orchestrator | 8001 | Active |
| dashboard | 8002 | Active |
| verifier | 8003 | Active |
| proxy-manager | 8004 | Active |
| landing-page | 8005→80 | Active |
| membership | 8006 | Active |
| delegation-monitor | 8007 | Active |
| jobs | 8008 | Active |
| i-proactive | 8400 | Active |

**Available Ports:** 8009-8399, 8401+

---

## 🔄 Maintenance

This structure should be maintained by:
1. Always placing new services in `apps/`
2. Always documenting in `docs/`
3. Keeping local and server in sync
4. Updating this document when structure changes

---

**Questions?** Check `docs/guides/navigation.md` or ask in the coordination channel.

🌐⚡💎 One Structure - Easy Navigation - Infinite Potential
