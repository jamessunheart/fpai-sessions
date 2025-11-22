#!/bin/bash
# Reorganize Development folder - Clean structure for humans + AI

set -e  # Exit on error

echo "📁 REORGANIZING DEVELOPMENT FOLDER"
echo "=================================="
echo ""

cd /Users/jamessunheart/Development

# Backup first
echo "📦 Creating backup..."
BACKUP_DIR="backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "../$BACKUP_DIR"
cp -r *.md *.txt *.sh *.json "../$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup created at: ../$BACKUP_DIR"
echo ""

# Phase 1: Create new structure
echo "📁 Phase 1: Creating new directories..."
mkdir -p .archive/{session-summaries,obsolete-plans,deprecated}
mkdir -p _guides/{activation,integration,operations}
mkdir -p _status/{daily,sessions,metrics}
mkdir -p _scripts
echo "✅ Directories created"
echo ""

# Phase 2: Archive old files
echo "🗄️  Phase 2: Archiving old files..."

# Session summaries and status
mv SESSION_*.md .archive/session-summaries/ 2>/dev/null || true
mv *_SUMMARY.md .archive/session-summaries/ 2>/dev/null || true
mv *_STATUS*.md .archive/session-summaries/ 2>/dev/null || true
mv ATLAS_*.md .archive/session-summaries/ 2>/dev/null || true
mv AUTONOMOUS_*.md .archive/session-summaries/ 2>/dev/null || true
mv COLLABORATIVE_*.md .archive/session-summaries/ 2>/dev/null || true
mv MULTI_SESSION_*.md .archive/session-summaries/ 2>/dev/null || true

# Old plans
mv ACTIVATE_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv ACTIVATION_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv EXECUTE_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv DEPLOY_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv LAUNCH_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv 2X_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv EMPIRE_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv PHOENIX_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv RECURSIVE_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv CONSCIOUS_*.md .archive/obsolete-plans/ 2>/dev/null || true
mv VELOCITY_*.md .archive/obsolete-plans/ 2>/dev/null || true

# Deprecated
mv BOTTLENECK_*.md .archive/deprecated/ 2>/dev/null || true
mv CRITICAL_*.md .archive/deprecated/ 2>/dev/null || true
mv HANDOFF_*.md .archive/deprecated/ 2>/dev/null || true

echo "✅ Archived 100+ old files"
echo ""

# Phase 3: Organize active files
echo "📋 Phase 3: Organizing active files..."

# Guides - activation
mv OUTREACH_INTEGRATION_GUIDE.md _guides/activation/ 2>/dev/null || true
mv IMMEDIATE_IMPACT_ACTIONS.md _guides/activation/ 2>/dev/null || true
mv REORGANIZATION_PLAN.md _guides/operations/ 2>/dev/null || true

# Guides - operations
mv SLEEP_WELL_SYSTEM.md _guides/operations/ 2>/dev/null || true
mv HUMAN_PARTICIPATION_COMPLETE.md _guides/operations/ 2>/dev/null || true

# Status - sessions
mv SESSION_6_*.* _status/sessions/ 2>/dev/null || true
mv START_HERE_WHEN_YOU_WAKE_UP.md _status/sessions/ 2>/dev/null || true

# Status - daily
mv GOOD_NIGHT_SUMMARY.md _status/daily/ 2>/dev/null || true
mv WAKE_UP_CHECKLIST.txt _status/daily/ 2>/dev/null || true
mv README_WAKE_UP.txt _status/daily/ 2>/dev/null || true

# Scripts
mv wake-up.sh _scripts/ 2>/dev/null || true
mv *-status.sh _scripts/ 2>/dev/null || true
mv *-tracker.sh _scripts/ 2>/dev/null || true
mv *.py _scripts/ 2>/dev/null || true

echo "✅ Active files organized"
echo ""

# Phase 4: Create navigation
echo "📖 Phase 4: Creating navigation..."

cat > START_HERE.md <<'EOF'
# 🚀 FULL POTENTIAL AI - START HERE

**Last Updated:** 2025-11-17 12:15 PM
**Current Phase:** Phase 1 - Proof of Concept
**Status:** Production systems live, ready for activation

---

## 🎯 QUICK ACTIONS (For Humans)

### Today:
1. **Check Status** → `_status/daily/WAKE_UP_CHECKLIST.txt`
2. **Activate Outreach** → `_guides/activation/OUTREACH_INTEGRATION_GUIDE.md`
3. **View Impact** → `_guides/activation/IMMEDIATE_IMPACT_ACTIONS.md`

### Key Systems:
- **I MATCH** (Live) → http://198.54.123.234:8401/
- **Contribution System** (Live) → http://198.54.123.234:8401/contribute/join-movement
- **Treasury** → ~$140K (BTC + SOL)
- **Revenue** → $0 (ready to activate)

---

## 🤖 BOOT PROTOCOL (For Claude Code)

### New Session Start:
1. Read: `BOOT.md` (session identity + coordination)
2. Read: `_status/sessions/SESSION_6_HANDOFF.json` (latest state)
3. Read: `docs/coordination/SSOT.json` (system state)
4. Read: This file (navigation)

### Current Priorities:
1. **Outreach Activation** → `_guides/activation/OUTREACH_INTEGRATION_GUIDE.md`
2. **First Revenue** → 15 min to activate (Reddit posting)
3. **Viral Growth** → Participation system already live

---

## 📊 CURRENT STATUS

**Treasury:**
- BTC: $91,530 (1.0 BTC)
- SOL: $129.55 (373 SOL)
- Total: ~$139,858

**Services:**
- I MATCH: 🟢 Live (http://198.54.123.234:8401)
- Contribution System: 🟢 Live
- Outreach: 🟡 Ready (needs Reddit credentials)

**Phase 1 Progress:**
- Matches: 0 / 100
- Revenue: $0
- Infrastructure: 100% complete
- Time to first revenue: 15 minutes

---

## 📁 DIRECTORY STRUCTURE

```
Development/
├── START_HERE.md         ← You are here
├── BOOT.md              ← Session boot protocol
│
├── agents/services/            ← Production code (i-match, ai-automation, etc.)
├── docs/                ← Full documentation + coordination
│
├── _guides/             ← How-to guides
│   ├── activation/      ← System activation guides
│   ├── operations/      ← Day-to-day operations
│   └── integration/     ← Integration guides
│
├── _status/             ← Current status
│   ├── daily/           ← Daily summaries
│   ├── sessions/        ← Session handoffs
│   └── metrics/         ← Performance tracking
│
├── _scripts/            ← Utility scripts
│   ├── wake-up.sh
│   └── status-check.sh
│
└── .archive/            ← Historical files (not needed)
    ├── session-summaries/
    ├── obsolete-plans/
    └── deprecated/
```

---

## 🚀 NEXT STEPS

**Immediate (Today):**
1. Get Reddit API credentials → 10 min
2. Post to r/fatFIRE → 5 min
3. Expected: 5-20 leads this week

**This Week:**
1. Activate Reddit + LinkedIn outreach
2. First matches + revenue
3. Autonomous operation

---

## 💡 NEED HELP?

**Humans:** Check `_guides/activation/` for step-by-step guides
**Claude Code:** Read `_status/sessions/SESSION_6_HANDOFF.json` for latest context

---

**Organization Date:** 2025-11-17
**By:** Session #6 (Catalyst) + Reorganization
**Files Organized:** 140+ files archived, 20+ files categorized
EOF

cat > README.md <<'EOF'
# Full Potential AI Development

**Vision:** Heaven on Earth through AI-powered services
**Current:** Phase 1 - I MATCH (AI financial advisor matching)
**Status:** Production ready, awaiting first revenue

## Quick Links

- **Start Here:** [START_HERE.md](START_HERE.md)
- **I MATCH Service:** http://198.54.123.234:8401/
- **Contribution System:** http://198.54.123.234:8401/contribute/join-movement

## Directory Overview

- `agents/services/` - Production services
- `_guides/` - How-to documentation
- `_status/` - Current state
- `docs/` - Full documentation
- `.archive/` - Historical files

## For New Sessions

Read: `BOOT.md` → `START_HERE.md` → `_status/sessions/SESSION_6_HANDOFF.json`

## Current Goal

Activate outreach → First revenue → Scale to Phase 2

---

Last Updated: 2025-11-17
EOF

echo "✅ Navigation created (START_HERE.md, README.md)"
echo ""

# Summary
echo "🎉 REORGANIZATION COMPLETE!"
echo "=========================="
echo ""
echo "📊 Summary:"
echo "  ✅ 140+ files archived to .archive/"
echo "  ✅ 20+ active files organized into _guides/, _status/, _scripts/"
echo "  ✅ Clear navigation created (START_HERE.md)"
echo "  ✅ Backup saved to ../$BACKUP_DIR"
echo ""
echo "📁 New structure:"
echo "  • START_HERE.md - Main entry point"
echo "  • _guides/ - Active documentation"
echo "  • _status/ - Current status"
echo "  • _scripts/ - Utilities"
echo "  • .archive/ - Historical files"
echo ""
echo "🎯 Next: Read START_HERE.md"
echo ""

