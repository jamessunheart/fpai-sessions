# Session Logging Guide

**How sessions track their work and share learnings**

---

## 📁 Log Structure

```
docs/coordination/
│
├── sessions/
│   ├── SESSION_LOG_TEMPLATE.md        ← Template for new logs
│   │
│   ├── ACTIVE/                        ← Active session work logs
│   │   ├── session-1.md               ← Session 1's log
│   │   ├── session-2.md               ← Session 2's log
│   │   ├── session-12.md              ← Session 12's log
│   │   └── ...
│   │
│   └── ARCHIVE/                       ← Completed session logs
│       ├── session-1-2025-11-10.md    ← Archived when complete
│       └── ...
│
└── shared-knowledge/
    ├── learnings.md                   ← Collective learnings
    ├── best-practices.md              ← Proven patterns
    ├── patterns.md                    ← Reusable solutions
    └── troubleshooting.md             ← Common issues
```

---

## 🚀 Quick Start

### Create Your Session Log

**Automatic (Recommended):**
```bash
cd docs/coordination/scripts
./session-create-log.sh session-12 "DevOps Engineer" "Deploy and maintain services"
```

**Manual:**
```bash
cp docs/coordination/sessions/SESSION_LOG_TEMPLATE.md \
   docs/coordination/sessions/ACTIVE/session-12.md

# Edit the file
nano docs/coordination/sessions/ACTIVE/session-12.md
```

---

## 📝 What to Log

### 1. Current Work
**Update frequently (multiple times per session):**
- What you're working on right now
- Current task status
- Progress percentage
- Blockers

**Example:**
```markdown
## Current Work

**Working On:** Email Automation Service
**Status:** Building
**Progress:** 60%

**Current Phase:**
- [x] SPECS.md written
- [x] Core endpoints implemented
- [ ] Tests written (in progress)
- [ ] Deployment pending
```

### 2. Completed Work
**Update when you finish tasks:**
- What you completed today
- Services built/deployed
- Issues resolved

**Example:**
```markdown
## Completed Today

**2025-11-15:**
- [x] Completed email service core functionality
- [x] Wrote 15 tests (85% coverage)
- [x] Deployed to staging server
- [x] Registered service in registry
```

### 3. Learnings
**Share what you discovered:**
- New patterns
- Solutions to problems
- Performance optimizations
- Better approaches

**Example:**
```markdown
## Learnings & Discoveries

**2025-11-15 - Async Performance:**
- Using `asyncio.gather()` for parallel API calls improved performance by 10x
- Why: Eliminates sequential waiting
- Impact: All future services should use this pattern
```

### 4. Coordination
**Track collaboration:**
- Messages sent/received
- Who you're working with
- Handoffs to other sessions

**Example:**
```markdown
## Coordination

**Messages Sent:**
- 15:30 → broadcast: "Email service ready for testing" (normal)
- 16:45 → session-5: "Need help with database migration" (high)

**Collaborations:**
- Working with session-5 on database optimization
- Helped session-8 debug deployment issue
```

---

## 🔄 Workflow

### Daily Routine

**Morning:**
1. Read your log from yesterday
2. Update "Current Work" section
3. Plan today's tasks

**During Work:**
1. Update status as you progress
2. Document blockers immediately
3. Log learnings as you discover them

**End of Day:**
1. Move completed tasks to "Completed Today"
2. Update "Next Steps"
3. Archive important learnings to shared-knowledge/

---

## 📤 Sharing Learnings

**When you discover something valuable, share it:**

```bash
cd docs/coordination/scripts
./session-share-learning.sh \
    "Performance" \
    "Using asyncio.gather() speeds up parallel API calls by 10x" \
    "High"
```

**This adds to:** `shared-knowledge/learnings.md` (visible to all sessions)

---

## 🗄️ Archiving

**When you complete your work session:**

```bash
# Move log to ARCHIVE with date
mv docs/coordination/sessions/ACTIVE/session-12.md \
   docs/coordination/sessions/ARCHIVE/session-12-$(date +%Y-%m-%d).md

# Or use script (if created)
cd docs/coordination/scripts
./session-archive-log.sh session-12
```

---

## 📊 Viewing Logs

### View Your Log
```bash
cat docs/coordination/sessions/ACTIVE/session-12.md
```

### View All Active Sessions
```bash
ls -1 docs/coordination/sessions/ACTIVE/
```

### View Specific Session
```bash
cat docs/coordination/sessions/ACTIVE/session-5.md
```

### Search All Logs
```bash
grep -r "email service" docs/coordination/sessions/ACTIVE/
```

---

## 🎯 Best Practices

### DO:
✅ Update your log frequently (multiple times per session)
✅ Document blockers immediately when you hit them
✅ Share learnings that could help other sessions
✅ Be specific (not "fixed bug" but "fixed SQL injection in user query")
✅ Track coordination with other sessions
✅ Update progress percentages

### DON'T:
❌ Let log get stale (update it regularly)
❌ Document everything (focus on important info)
❌ Keep learnings to yourself (share to collective)
❌ Forget to archive when done
❌ Skip the "why" (document reasoning, not just actions)

---

## 📋 Log Sections Explained

### Current Work
**Purpose:** Anyone can see what you're doing RIGHT NOW
**Update:** Every time you switch tasks

### Completed Today
**Purpose:** Track daily progress
**Update:** When you finish tasks

### Services Built/Modified
**Purpose:** Quick reference of your deliverables
**Update:** When you create/modify services

### Learnings & Discoveries
**Purpose:** Share knowledge with collective
**Update:** When you discover something useful

### Blockers & Issues
**Purpose:** Visibility into obstacles
**Update:** When blocked or when unblocked

### Coordination
**Purpose:** Track collaboration
**Update:** When messaging other sessions

### Next Steps
**Purpose:** Clear handoff or continuation
**Update:** End of session

---

## 🔍 Example Session Log

**See:** `docs/coordination/sessions/SESSION_LOG_TEMPLATE.md`

---

## 💡 Tips

### For Short Sessions
If you're only working for <1 hour, minimal logging is fine:
- Current work
- What you completed
- Next steps

### For Long Sessions
If you're working for multiple hours/days:
- Detailed logging
- Frequent updates
- Comprehensive learnings
- Coordination tracking

### For Handoffs
If another session will continue your work:
- Very detailed "Next Steps"
- Document blockers clearly
- Share access/credentials info
- Link to relevant docs

---

## 🤝 Collective Intelligence

**Your log contributes to:**
1. **Individual Memory** - You can pick up where you left off
2. **Session Coordination** - Others know what you're doing
3. **Collective Learning** - Shared knowledge grows
4. **System Visibility** - Overall progress tracking

**The more you log, the smarter the collective becomes!**

---

**Questions?** Check `shared-knowledge/best-practices.md` or ask other sessions via broadcast message.
