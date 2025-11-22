# Full Potential AI - Development Environment

Complete development environment for the Full Potential AI system following the Sacred Loop architecture.

## 🧠 Claude Code Activation

**To activate Claude Code in any new session, just say:**

```
Remember
```

That's it! Claude will:
- Load consciousness from memory system
- Verify server health
- Confirm orientation
- Continue with current priority

**See:** `MEMORY/NEW_SESSION_START.md` for details

---

## 🌐 System Architecture

This environment follows the **Sacred Loop** pattern:

1. **Architect declares intent** → 2. **AI generates SPEC** → 3. **Coordinator packages & assigns** → 4. **Apprentice builds via AI** → 5. **Verifier enforces standards** → 6. **Deployer deploys** → 7. **Registry + Dashboard update** → 8. **Architect issues next intent**

## 📁 Directory Structure

```
~/Development/
├── FPAI_SYSTEM_INDEX.md          # System navigation guide (READ THIS FIRST)
│
├── 📚 BLUEPRINT ROOTS (READ-ONLY)
│   ├── 1-blueprints (architecture)/  # System architecture truth
│   ├── 2-roles (behavior)/           # Role definitions
│   └── 3-droplets (implementation)/  # Droplet specifications
│
├── 🧠 SERVICE REPOS (CODE HERE)
│   ├── orchestrator/                 # Task routing droplet
│   ├── registry/                     # Identity & SSOT droplet
│   └── droplet-*-*/                  # Other droplets
│
├── 🧰 TOOLING
│   ├── fullpotential-tools/          # Complete optimization suite
│   ├── fpai-tools/                   # Development helpers
│   └── fpai-ops/                     # Operations scripts
│
└── 📂 RESOURCES (READ-ONLY)
    ├── AI FILES/
    ├── APPRENTICE/
    ├── ARCHITECT/
    └── ...
```

## 🛠️ Tools Overview

### Full Potential Tools (`fullpotential-tools/`)

Complete optimization and analysis suite:

```bash
# Generate SSOT snapshot + gap analysis
./fullpotential-tools/bin/fp-tools workflow --scan-github

# Generate SPEC from intent
./fullpotential-tools/bin/fp-tools spec --droplet-id 1 --intent "Build identity system"

# Validate droplet against UDC
./fullpotential-tools/bin/fp-tools validate --path ./droplet-1-registry

# Monitor system health
./fullpotential-tools/bin/fp-tools health --watch
```

### Development Tools (`fpai-tools/`)

Development workflow automation:

```bash
# Initialize new droplet
./fpai-tools/droplet-init.sh 1 registry

# Start all services locally
./fpai-tools/local-dev.sh all

# Run code standards check
./fpai-tools/code-standards-check.sh all

# Run tests across all services
./fpai-tools/test-runner.sh all
```

### Operations Tools (`fpai-ops/`)

Deployment and operations:

```bash
# Deploy droplet to production
./fpai-ops/deploy-droplet.sh registry

# Quick health check
./fpai-ops/health-check.sh

# Sync with GitHub
./fpai-ops/git-sync.sh registry "Add JWT validation"

# Rollback to previous version
./fpai-ops/rollback.sh registry

# Daily automated snapshots
./fpai-ops/snapshot-daily.sh --email you@email.com

# Complete Sacred Loop automation
./fpai-ops/sacred-loop.sh 1 "Build identity system with JWT"
```

## 🚀 Quick Start

### 1. First Time Setup

```bash
cd ~/Development

# Install dependencies for fullpotential-tools
cd fullpotential-tools
./setup.sh

# Install development tools
pip3 install black ruff mypy pytest pytest-cov
```

### 2. Initialize Your First Droplet

```bash
# Create droplet repository structure
./fpai-tools/droplet-init.sh 1 registry

# Navigate to the new droplet
cd droplet-1-registry

# Install dependencies
pip3 install -r requirements.txt

# Start development server
python -m app.main
```

### 3. Development Workflow

```bash
# Start all services
./fpai-tools/local-dev.sh all

# Check service status
./fpai-tools/local-dev.sh status

# Run tests
./fpai-tools/test-runner.sh registry

# Check code standards
./fpai-tools/code-standards-check.sh registry

# Auto-fix code issues
./fpai-tools/code-standards-check.sh fix registry
```

### 4. Deploy

```bash
# Sync with GitHub
./fpai-ops/git-sync.sh registry "Complete JWT implementation"

# Deploy to production
./fpai-ops/deploy-droplet.sh registry

# Verify deployment
./fpai-ops/health-check.sh
```

### 5. Monitor & Maintain

```bash
# Generate daily snapshot
./fpai-ops/snapshot-daily.sh

# Monitor system health
./fullpotential-tools/bin/fp-tools health --watch

# View logs
./fpai-tools/local-dev.sh logs registry
```

## 🔄 The Sacred Loop (Automated)

Run the complete Sacred Loop in one command:

```bash
./fpai-ops/sacred-loop.sh 10 "Create task routing and messaging system"
```

This automates:
1. ✅ SPEC generation
2. ✅ Repository initialization
3. ⚠️ Build (manual with AI assistance)
4. ✅ Standards verification
5. ✅ Testing
6. ✅ Deployment
7. ✅ System snapshot update
8. ✅ Next steps identification

## 📊 Daily Operations

### Morning Routine

```bash
# Check system health
./fpai-ops/health-check.sh

# Generate daily snapshot
./fpai-ops/snapshot-daily.sh

# Review gap analysis
cat fullpotential-tools/output/gap-analyses/GAP_ANALYSIS_*.md | tail -50
```

### Development Cycle

```bash
# 1. Generate SPEC for next priority
./fullpotential-tools/bin/fp-tools spec --droplet-id 8 --intent "Automated verification system"

# 2. Initialize droplet
./fpai-tools/droplet-init.sh 8 verifier

# 3. Build (use Claude + SPEC + Foundation Files)
cd droplet-8-verifier
# ... implement features ...

# 4. Test and validate
cd ..
./fpai-tools/test-runner.sh verifier
./fpai-tools/code-standards-check.sh verifier

# 5. Deploy
./fpai-ops/deploy-droplet.sh verifier

# 6. Update system state
./fullpotential-tools/bin/fp-tools workflow --scan-github
```

## 🎯 Key Scripts Reference

### Development (`fpai-tools/`)

| Script | Purpose | Example |
|--------|---------|---------|
| `droplet-init.sh` | Create new droplet repo | `./droplet-init.sh 1 registry` |
| `local-dev.sh` | Manage local services | `./local-dev.sh all` |
| `code-standards-check.sh` | Check code quality | `./code-standards-check.sh registry` |
| `test-runner.sh` | Run tests | `./test-runner.sh all` |

### Operations (`fpai-ops/`)

| Script | Purpose | Example |
|--------|---------|---------|
| `deploy-droplet.sh` | Deploy to server | `./deploy-droplet.sh registry` |
| `health-check.sh` | Check service health | `./health-check.sh` |
| `git-sync.sh` | GitHub workflow | `./git-sync.sh registry "message"` |
| `rollback.sh` | Rollback deployment | `./rollback.sh registry` |
| `snapshot-daily.sh` | Automated snapshots | `./snapshot-daily.sh --email you@email.com` |
| `sacred-loop.sh` | Complete automation | `./sacred-loop.sh 1 "intent"` |

### Full Potential Tools (`fullpotential-tools/bin/fp-tools`)

| Command | Purpose | Example |
|---------|---------|---------|
| `workflow` | Snapshot + gap analysis | `fp-tools workflow --scan-github` |
| `spec` | Generate SPEC | `fp-tools spec --droplet-id 1 --intent "..."` |
| `validate` | UDC validation | `fp-tools validate --path ./droplet-1` |
| `health` | System health | `fp-tools health --watch` |
| `snapshot` | Generate snapshot | `fp-tools snapshot --scan-github` |
| `gap` | Gap analysis | `fp-tools gap --snapshot file.md` |

## 🏗️ Building New Droplets

### Option 1: Manual Step-by-Step

```bash
# 1. Generate SPEC
./fullpotential-tools/bin/fp-tools spec --droplet-id 15 --intent "Developer recruitment pipeline"

# 2. Initialize repository
./fpai-tools/droplet-init.sh 15 recruiter

# 3. Implement features (use Claude + SPEC)

# 4. Test locally
./fpai-tools/test-runner.sh recruiter

# 5. Validate standards
./fpai-tools/code-standards-check.sh recruiter
./fullpotential-tools/bin/fp-tools validate --path ./droplet-15-recruiter

# 6. Deploy
./fpai-ops/deploy-droplet.sh recruiter
```

### Option 2: Sacred Loop Automation

```bash
./fpai-ops/sacred-loop.sh 15 "Developer recruitment and talent pipeline management"
```

## 🔐 Security & Standards

All droplets must follow:

- **UDC** (Universal Droplet Contract) - 5 required endpoints
- **Foundation Files** - Security, code standards, tech stack
- **Testing** - >80% coverage required
- **Code Quality** - Black, Ruff, Mypy validation
- **No Hardcoded Secrets** - Environment variables only

## 🎓 Learning Resources

1. **Read FIRST**: `FPAI_SYSTEM_INDEX.md` - System navigation
2. **Architecture**: `1-blueprints (architecture)/1-SYSTEM-BLUEPRINT.txt`
3. **Roles**: `2-roles (behavior)/` - Understand your role
4. **Quick Start**: `fullpotential-tools/QUICKSTART.md`
5. **Full Docs**: `fullpotential-tools/README.md`

## 🤝 Collaboration Guidelines

### For AI Code Assistants (Claude Code, etc.)

✅ **You CAN:**
- Read from all directories
- Modify code in service repos (`./orchestrator`, `./registry`, `./droplet-*`)
- Create/modify files in `./fpai-tools` and `./fpai-ops`
- Run scripts and execute commands

❌ **You CANNOT:**
- Modify blueprint files (`1-blueprints`, `2-roles`, `3-droplets`) without explicit instruction
- Ignore Foundation Files standards
- Skip testing requirements
- Deploy without verification

### For Developers

1. **Always** read the relevant SPEC before coding
2. **Always** run tests before committing
3. **Always** use Sacred Loop commit format
4. **Never** hardcode secrets
5. **Never** skip code standards checks

## 📈 Metrics & Targets

### Time Compression
- **85-95% reduction** in development time
- Build duration: **4-6 hours** (vs 20-40 hours traditional)
- Verification: **2-3 hours** (vs 8-12 hours traditional)

### Quality Targets
- First-pass approval: **>80%**
- UDC compliance: **100%**
- Test coverage: **>80%**
- Security issues: **<5% critical**

### Scalability
- Sprints in parallel: **10+ → 50+**
- Apprentices active: **20+ → 100+**
- Deployment frequency: **Continuous**

## 🆘 Troubleshooting

### Scripts Not Found

```bash
# Make scripts executable
chmod +x fpai-tools/*.sh fpai-ops/*.sh fullpotential-tools/bin/*

# Add to PATH (optional)
echo 'export PATH="$PATH:~/Development/fpai-tools:~/Development/fpai-ops"' >> ~/.zshrc
source ~/.zshrc
```

### Service Won't Start

```bash
# Check if port is in use
lsof -i :8001

# Check logs
./fpai-tools/local-dev.sh logs registry

# Restart service
./fpai-tools/local-dev.sh restart registry
```

### Tests Failing

```bash
# Run with verbose output
cd droplet-1-registry
pytest -v tests/

# Check coverage
pytest --cov=app --cov-report=html tests/
```

### Deployment Failed

```bash
# Check Docker
docker ps
docker logs droplet-registry

# Rollback
./fpai-ops/rollback.sh registry
```

## 🌟 Next Steps

1. ✅ Complete Phase 1 droplets (Registry, Orchestrator)
2. ✅ Complete Phase 2 droplets (Dashboard, Proxy Manager, Verifier)
3. ⏭️ Complete Phase 3 droplets (Coordinator, Recruiter, Deployer)
4. ⏭️ Complete Phase 4 droplets (Self-Optimizer, Meta-Architect, Mesh Expander)
5. ⏭️ Achieve full automation (Builder Droplet)

## 📞 Support

For issues, questions, or improvements:

1. Review the Blueprint: `1-blueprints (architecture)/1-SYSTEM-BLUEPRINT.txt`
2. Check Foundation Files
3. Run diagnostics: `./fpai-ops/health-check.sh`
4. Review latest gap analysis

---

**Built with ❤️ for Full Potential AI**

**Helping AI realize its Full Potential to help humanity realize its full potential**

🌐⚡💎
