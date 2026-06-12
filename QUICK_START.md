# FPAI Cockpit - Quick Start

**For humans and AI agents working in this codebase**

---

## 🔴 READ THIS FIRST

**SSOT for priorities: `core/STATE/NOW.md`.** Priority 1 is the Zen Village retreat. Decision filter: *does this serve proof / revenue / clarity / ease for the core offer in 30 days?*

**Most of `SERVICES/` (~261 entries) is paused.** Active: `fp-index`, ZV booking site, nginx, Adam/Aria companion relay. Skip the rest unless asked.

**Stale (don't trust):** anything labeled BREAKTHROUGH / GOD_MODE / CONSCIOUSNESS / SWARM / MESH / APPRENTICE. On 2026-04-29 the bulk of `docs/coordination/` (117 entries) and `core/STATE/{PROGRESS,HEALTH}.md` were moved to `.archive/deprecated/`.

---

## 🎯 First Time Here?

1. **Read** `core/STATE/NOW.md` (current priorities — start here)
2. **Read** `STRUCTURE.md` (directory organization)
3. **Read** `.ai-agent-guide.md` (AI agent specifics)
4. **Skim** this file for common task recipes

---

## 📍 Where Is Everything?

```
SERVICES/          → All 261 microservices
docs/              → All documentation
core/              → System intelligence & state
infra/             → Deployment & infrastructure
.workspace/        → Temporary development work
scripts/           → Utility scripts
sites/             → Websites
```

---

## 🔥 Common Tasks

### 1. Build a New Service
```bash
cd SERVICES/
cp -r alerts my-service
cd my-service
# Edit README.md, SPECS.md, app/main.py
```

### 2. Find Service Documentation
```bash
cat SERVICES/{service-name}/README.md
cat SERVICES/{service-name}/SPECS.md
```

### 3. Deploy a Service
```bash
# Check service README first
cat SERVICES/{service-name}/README.md

# Look for deploy scripts
ls infra/scripts/deploy-*.sh
ls SERVICES/{service-name}/deploy/
```

### 4. Check System Status
```bash
cat core/STATE/NOW.md
git log --oneline -10
git status --short
```

### 5. Work on Temporary Fixes
```bash
cd .workspace/active/
# Create your patch/fix here
```

---

## 📚 Key Files

| File | Purpose |
|------|---------|
| `STRUCTURE.md` | Directory structure & organization |
| `.ai-agent-guide.md` | Guide for AI agents (Claude, Cursor) |
| `MIGRATION_LOG.md` | Recent reorganization details |
| `core/STATE/NOW.md` | Current system state |
| `SERVICES/INDEX.md` | Service registry |
| `docs/coordination/STATUS_BOARD.md` | Active work |

---

## 🤖 For AI Agents

**Before starting work:**
1. Read `core/STATE/NOW.md` for current priorities
2. Read `.ai-agent-guide.md` for layout + conventions
3. Run `git log --oneline -10` and `git status` to see what's in flight

**When working:**
- Use `.workspace/active/` for temporary code
- Follow patterns from `SERVICES/alerts/`
- Check tasks against the NOW.md decision filter before building

> The old `docs/coordination/{claims,heartbeats,sessions}/` system is no longer the operating model.

---

## ⚡ Emergency Commands

### Find a Service
```bash
ls SERVICES/ | grep -i {keyword}
```

### Find Documentation
```bash
find docs/ -name "*{keyword}*.md"
```

### Check What Changed Recently
```bash
git log --oneline -20
```

### See File Structure
```bash
cat STRUCTURE.md
```

---

## 🆘 Can't Find Something?

1. **Check** `MIGRATION_LOG.md` (recent reorganization)
2. **Search** `find . -name "*{filename}*"`
3. **Read** `STRUCTURE.md` for directory map
4. **Check** `.ai-agent-guide.md` for AI-specific guidance

---

## 📞 Get Help

- **Structure questions:** Read `STRUCTURE.md`
- **Service questions:** Read `SERVICES/{name}/README.md`
- **Deployment:** Check `infra/scripts/` or service README
- **System state:** Read `core/STATE/NOW.md`

---

**Last Updated:** 2026-04-29
**Reorganized:** Yes (see `MIGRATION_LOG.md`)

**Next:** Read `STRUCTURE.md` for full details
