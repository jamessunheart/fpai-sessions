# 💾 SAVE - Quick Reference for Sessions

**Location:** SESSIONS/SAVE.md
**Purpose:** Quick save commands for any session

---

## One-Line Saves

```bash
# Auto-detect what to save (RECOMMENDED)
./SESSIONS/save-progress.sh auto <your-session-id>

# Quick checkpoint (just heartbeat)
./SESSIONS/save-progress.sh quick <your-session-id>

# Milestone progress (step completion)
./SESSIONS/save-progress.sh milestone <your-session-id>

# Full save (everything + git commit)
./SESSIONS/save-progress.sh full <your-session-id>
```

---

## Examples

### I'm session-3-coordinator and want to save:
```bash
./SESSIONS/save-progress.sh auto session-3-coordinator
```

### I just completed a milestone step:
```bash
./SESSIONS/save-progress.sh milestone session-3-coordinator
# Script will prompt: Which step? What did you do?
```

### I finished major work and want to commit:
```bash
./SESSIONS/save-progress.sh full session-3-coordinator
```

---

## What Gets Saved

| Mode | Heartbeat | Milestone | CURRENT_STATE | Git Commit |
|------|-----------|-----------|---------------|------------|
| quick | ✅ | ❌ | ❌ | ❌ |
| milestone | ✅ | ✅ | ❌ | ❌ |
| full | ✅ | ✅ | ✅ | ✅ |
| auto | ✅ | Auto-detect | Auto-detect | Auto-detect |

---

## Find Your Session ID

```bash
# Check registry
cat SESSIONS/REGISTRY.json | jq -r '.sessions | keys[]'

# Check your heartbeat
ls SESSIONS/HEARTBEATS/*.json
```

---

**Quick save from anywhere:**
```bash
cd ~/Development && ./SESSIONS/save-progress.sh auto session-3-coordinator
```

💾
