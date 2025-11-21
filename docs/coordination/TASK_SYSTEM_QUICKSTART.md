# 🚀 Task Coordination System - Quick Start

**New system for multi-session coordination - prevents duplicate work!**

## For Sessions: How to Use

### 1. View Available Tasks
```bash
cd docs/coordination/scripts
./task-status.sh
```

### 2. Claim a Task
```bash
./task-claim.sh TASK_ID "What you'll be doing"
```
**Example:**
```bash
./task-claim.sh AUTH "Implement user authentication system"
```

### 3. Start Working
```bash
./task-update.sh TASK_ID in_progress
```

### 4. Complete the Task
```bash
./task-complete.sh TASK_ID "Summary of what you did"
```
**Example:**
```bash
./task-complete.sh AUTH "Built JWT auth with refresh tokens, integrated with user DB"
```

## For Coordinators: How to Set Up Tasks

### Option 1: Let Sessions Create Tasks (Recommended)
Tasks are automatically created when first claimed. Just tell sessions what task IDs to use:
- "Claim AUTH for authentication"
- "Claim DB for database setup"
- "Claim DEPLOY for deployment"

### Option 2: Pre-Create Tasks
```bash
cd docs/coordination/tasks
cat > task_AUTH.json << 'EOF'
{
  "task_id": "AUTH",
  "description": "Implement authentication system",
  "status": "available",
  "claimed_by": null,
  "claimed_at": null,
  "started_at": null,
  "completed_at": null,
  "result": null
}
EOF
```

## Task Lifecycle

```
available → claimed → in_progress → completed
    ↑          ↓
    └──────────┘
  (can unclaim)
```

## Common Commands

### See what everyone is working on:
```bash
./task-status.sh
```

### See details of specific task:
```bash
./task-status.sh TASK_ID
```

### Unclaim a task (make it available again):
```bash
./task-update.sh TASK_ID available
```

### Check your session identity:
```bash
cat ../claude_sessions.json | python3 -m json.tool
```

## Safety Features

✅ **Can't claim a task that's already claimed** - Atomic locking prevents it
✅ **Can't update someone else's task** - Ownership validation
✅ **Can't accidentally overwrite** - File-based locking
✅ **Duration tracked automatically** - Know how long tasks take

## Example Session

```bash
# Terminal 1 (Session #1 - Forge)
cd docs/coordination/scripts

# Check what's available
./task-status.sh
# Shows: No tasks found

# Claim a task
./task-claim.sh AUTH "Build authentication"
# ✅ TASK CLAIMED

# Start working
./task-update.sh AUTH in_progress
# 🔄 Task AUTH status: claimed → in_progress

# ... work on authentication ...

# Complete it
./task-complete.sh AUTH "JWT auth with refresh tokens complete"
# ✅ Task completed with 45m duration


# Terminal 2 (Session #2 - Backend)
cd docs/coordination/scripts

# Check what's available
./task-status.sh
# Shows: AUTH is in_progress by Forge

# Try to claim AUTH
./task-claim.sh AUTH "Also build auth"
# ❌ FAILED: Task already claimed by session-1

# Claim a different task
./task-claim.sh DB "Setup database"
# ✅ TASK CLAIMED

# Both sessions now working in parallel!
```

## Task Naming Conventions

**Good task IDs:**
- Short, uppercase: `AUTH`, `DB`, `DEPLOY`, `TEST`
- Descriptive: `USER_MGMT`, `API_DOCS`, `FIX_BUG_123`
- Category prefix: `BACKEND_AUTH`, `FRONTEND_UI`, `INFRA_DEPLOY`

**Avoid:**
- Generic: `TASK1`, `TODO`
- Too long: `IMPLEMENT_THE_COMPLETE_USER_AUTHENTICATION_SYSTEM`
- Special chars: `AUTH@123`, `DB-SETUP!`

## Integration with Existing Systems

### Session Registration
Use enhanced registration to avoid collisions:
```bash
./session-register-enhanced.sh 1 "Your Name" "Your Goal"
```

### Heartbeats
Send regular heartbeats (your current task will be visible):
```bash
./session-heartbeat.sh "Working on AUTH task"
```

### Broadcasts
Announce task completion to all sessions:
```bash
./session-send-message.sh broadcast "✅ AUTH task complete!" "Authentication system is live"
```

## Tips for Effective Coordination

1. **Break big tasks into smaller ones**
   - Instead of: `BUILD_APP`
   - Use: `AUTH`, `DB`, `API`, `FRONTEND`, `DEPLOY`

2. **Use clear descriptions when claiming**
   - Bad: `./task-claim.sh DB "database"`
   - Good: `./task-claim.sh DB "Setup PostgreSQL with migrations and user tables"`

3. **Check status before claiming**
   - Run `./task-status.sh` first
   - See what's already being worked on

4. **Update to in_progress when you start**
   - Claiming ≠ working
   - Update status so others know you're active

5. **Write clear completion summaries**
   - Others may need to understand what you did
   - Include key details: "JWT auth with refresh, integrated with user DB, 95% test coverage"

## Troubleshooting

### "Task already claimed"
Someone else is working on it. Check `./task-status.sh` to see who, or claim a different task.

### "Session identity not found"
Run `./session-identify.sh` or `./session-register-enhanced.sh` first.

### "Permission denied"
Make scripts executable: `chmod +x *.sh`

### "Unbound variable" errors
Update bash: `bash --version` should be 4.0+, or use `set +u` mode.

## Files to Know About

```
docs/coordination/
├── scripts/
│   ├── task-claim.sh      ← Claim tasks
│   ├── task-status.sh     ← View status
│   ├── task-update.sh     ← Update status
│   └── task-complete.sh   ← Complete tasks
├── tasks/                 ← Task JSON files
│   └── task_*.json
└── claude_sessions.json   ← Session registry
```

## Quick Reference

| Action | Command |
|--------|---------|
| View all tasks | `./task-status.sh` |
| View one task | `./task-status.sh TASK_ID` |
| Claim task | `./task-claim.sh ID "desc"` |
| Start task | `./task-update.sh ID in_progress` |
| Complete task | `./task-complete.sh ID "result"` |
| Unclaim task | `./task-update.sh ID available` |

---

**Questions?** Read the full documentation:
- `COORDINATION_FIXES_COMPLETE.md` - Technical details
- `COORDINATION_SYSTEM_FIXED.md` - Before/after comparison
