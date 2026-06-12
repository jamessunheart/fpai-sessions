# FPAI Cockpit - Directory Structure

**Last Updated:** 2026-05-07 (added Mission Layer references)
**Status:** Reorganized for clarity and maintainability

---

## 🔴 READ THIS FIRST

**Single source of truth for priorities: `core/STATE/NOW.md`.** Read it before navigating anything else. It defines the current Priority 1 (Zen Village retreat) and the decision filter — *does this serve proof / revenue / clarity / ease for the core offer in 30 days?*

**For the *why* (mission), not the *what-now*:** `core/INTENT/`. Founding documents, the manifesto, and Peace Agreements live there. NOW.md governs operational priority; INTENT governs identity/mission/vision.

---

## 🌟 Mission Layer — `core/INTENT/`

The supreme intent. Two layers; Layer 1 (mission) governs Layer 2 (engineering).

| File | What |
|---|---|
| [`core/INTENT/README.md`](./core/INTENT/README.md) | Layer clarification (Mission vs Engineering Substrate) |
| [`core/INTENT/COHERENT_CHAMPIONS_MANIFESTO.md`](./core/INTENT/COHERENT_CHAMPIONS_MANIFESTO.md) | Manifesto v1.0 — founding document of WPO / Zen Village |
| [`core/INTENT/WORLD_PEACE_AGREEMENT.md`](./core/INTENT/WORLD_PEACE_AGREEMENT.md) | Canonical template for forming Peace Agreements |
| [`core/INTENT/FORMING_AGREEMENTS.md`](./core/INTENT/FORMING_AGREEMENTS.md) | Protocol for instantiating specific Agreements |
| [`core/INTENT/AGREEMENTS/`](./core/INTENT/AGREEMENTS/) | Specific formed Agreements (one file per instance, YAML front-matter) |
| [`core/INTENT/AGREEMENTS/INDEX.md`](./core/INTENT/AGREEMENTS/INDEX.md) | Human-readable registry (auto-generated — do not edit) |
| [`core/INTENT/AGREEMENTS/registry.json`](./core/INTENT/AGREEMENTS/registry.json) | Machine-readable registry (auto-generated) |
| [`tools/registry/build_index.py`](./tools/registry/build_index.py) | Registry regenerator. Scans `AGREEMENTS/*.md`, rebuilds INDEX + registry |
| `core/INTENT/IDENTITY.md`, `PURPOSE.md`, `PRINCIPLES.md` | Layer 2 — engineering substrate (older, narrower scope) |

**Naming:** World Peace Party = World Peace Organization = World Peace Headquarters = Zen Village.
**Mission:** paradise on Earth through cooperation.
**Founder:** James Sunheart.

---

**`SERVICES/` has ~261 entries. Most are paused.** The only services actively serving the engine are `fp-index`, the Zen Village booking site, nginx, and the Adam/Aria companion relay. Don't burn time exploring the rest unless explicitly asked.

**Stale-but-still-around (don't trust without verification):**
- ~~`core/STATE/PROGRESS.md`, `core/STATE/HEALTH.md`~~ — moved to `.archive/deprecated/stale-state-2025-11/` on 2026-04-29
- `docs/coordination/` — what remains is only what active code references. The bulk was archived to `.archive/deprecated/coordination-2025-11/` on 2026-04-29
- Anything labeled BREAKTHROUGH / GOD_MODE / CONSCIOUSNESS / SWARM / MESH / APPRENTICE — historical

For current state, use `core/STATE/NOW.md` + `git log -10` + `git status`.

---

## 🎯 Quick Navigation

- **Building a new service?** → `SERVICES/`
- **Looking for docs?** → `docs/`
- **Need deployment scripts?** → `infra/`
- **Working on temp fixes?** → `.workspace/`
- **Looking for a website?** → `sites/`

---

## 📁 Directory Structure

```
FPAI_Cockpit/
│
├── SERVICES/                 # All microservices (261 services)
│   ├── alerts/              # Notification service
│   ├── concierge/           # Customer service AI
│   ├── fp-index/            # Full Potential Index
│   ├── god-mode/            # Admin dashboard
│   └── ...                  # See SERVICES/README.md for full list
│
├── core/                     # Core system intelligence
│   ├── INTELLIGENCE/        # Learning, patterns, synthesis
│   ├── STATE/               # Current system state
│   └── FOUNDERS/            # Founding team info
│
├── docs/                     # All documentation
│   ├── architecture/        # System architecture docs
│   ├── business/            # Business plans, strategies
│   ├── coordination/        # Agent coordination, sessions
│   ├── deployment/          # Deployment guides
│   ├── specs/               # Service specifications
│   └── guides/              # How-to guides
│
├── infra/                    # Infrastructure & deployment
│   ├── scripts/             # Deployment automation
│   ├── audits/              # Security audits
│   └── web/                 # Web server configs
│
├── sites/                    # Website projects
│   └── zenvillage-peace/    # Zen Village website
│
├── scripts/                  # Utility scripts
│   ├── deploy/              # Deployment scripts
│   ├── monitoring/          # Monitoring tools
│   └── maintenance/         # Maintenance scripts
│
├── tools/                    # Development tools
│
├── .workspace/               # Active development work
│   ├── active/              # Current work-in-progress
│   ├── patches/             # Temporary patches
│   ├── experiments/         # Experimental code
│   └── temp/                # Temporary files
│
├── .archive/                 # Archived/deprecated files
│   └── 2026-04/             # Organized by date
│
└── projects/                 # Specific projects
    ├── whaletrack-magnetic-trader/
    ├── apprentice-os/
    └── cocoon/
```

---

## 🤖 For AI Agents (Claude, Cursor, etc.)

### Finding Services
```bash
# All services are in SERVICES/
cd SERVICES/alerts
cd SERVICES/fp-index
```

### Finding Documentation
```bash
# All docs are in docs/
docs/architecture/          # System design
docs/coordination/          # Agent coordination
docs/specs/                 # Service specs
```

### Working on Temporary Changes
```bash
# Use .workspace/ for any temporary work
.workspace/active/          # Active development
.workspace/patches/         # Quick fixes
```

### Deploying Services
```bash
# Deployment scripts in infra/
infra/scripts/deploy-*.sh
```

---

## 📋 File Location Map

### If you're looking for...

| What | Where | Notes |
|------|-------|-------|
| Service code | `SERVICES/{service-name}/` | 261 microservices |
| Service specs | `docs/specs/` or `SERVICES/{name}/SPECS.md` | |
| Deployment scripts | `infra/scripts/` | Also check `scripts/deploy/` |
| System docs | `docs/architecture/` | System design, specs |
| Coordination files | `docs/coordination/` | Agent sessions, claims |
| Website files | `sites/{site-name}/` | Public websites |
| Temp work | `.workspace/active/` | WIP, experiments |
| Old files | `.archive/YYYY-MM/` | Deprecated code |
| Core intelligence | `core/INTELLIGENCE/` | Learnings, patterns |
| Current state | `core/STATE/NOW.md` | What's happening now |

---

## 🔄 Migration Guide (Apr 2026)

Files were reorganized on 2026-04-29. If you're looking for a file that moved:

### Temporary/Patch Files
```
OLD: /tmp_*.py, /patch_*.py, /fix_*.py
NEW: /.workspace/active/
```

### Loose Documentation
```
OLD: /*.md (root level)
NEW: /docs/{category}/
```

### Scripts
```
OLD: /*.sh, /DEPLOY_*.sh
NEW: /scripts/deploy/ or /infra/scripts/
```

### Python Utilities
```
OLD: /{name}.py
NEW: /.workspace/active/ or /tools/
```

---

## ⚠️ Important Notes

1. **SERVICES/** - Never rename or restructure without coordination
2. **core/** - Contains system memory and intelligence
3. **docs/coordination/** - Active agent communication
4. **.workspace/** - Safe to modify, not production
5. **.archive/** - Safe to delete after review

---

## 🚀 Common Tasks

### Start a New Service
```bash
cd SERVICES/
mkdir my-service
cd my-service
# Copy structure from SERVICES/alerts/
```

### Deploy a Service
```bash
# Check service's README.md for deploy instructions
cd SERVICES/{service-name}
cat README.md
```

### Find System Status
```bash
cat core/STATE/NOW.md
cat docs/coordination/STATUS_BOARD.md
```

### Review Recent Changes
```bash
git log --oneline -20
cat docs/coordination/sessions/CURRENT_STATE.md
```

---

## 📞 Need Help?

- **Structure questions:** Read this file
- **Service questions:** Check `SERVICES/{name}/README.md`
- **Deployment:** See `infra/scripts/` or service-specific deploy guides
- **System state:** Check `core/STATE/NOW.md`

---

**For detailed service list, see:** `SERVICES/README.md`
**For coordination protocol, see:** `docs/coordination/README.md`
