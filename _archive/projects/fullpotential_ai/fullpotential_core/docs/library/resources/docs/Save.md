# Save - Progress Preservation Protocol

**⚠️ CRITICAL INSTRUCTION FOR CLAUDE CODE ⚠️**

When the human says **"Save"** (or variations like "save progress", "save state", "checkpoint"), you MUST follow this exact protocol:

---

## STEP 1: Identify Your Session ID

```bash
# Check SESSIONS/REGISTRY.json to find your session ID
cat SESSIONS/REGISTRY.json | jq -r '.sessions | keys[]'

# Or check your active heartbeat
ls -1 SESSIONS/HEARTBEATS/*.json | head -1 | xargs basename | sed 's/.json$//'
```

**Your session ID format:** `session-X-specialty` (e.g., `session-3-coordinator`)

---

## STEP 2: Detect Save Context

Ask yourself:
1. **Am I working on a milestone?** (Check if you claimed one)
2. **Did I just complete work?** (Should update CURRENT_STATE.md)
3. **Is this a quick checkpoint?** (Just save heartbeat)

---

## STEP 3: Choose Save Mode

### Option A: Auto-Detect (Recommended)
Let the script detect what to save:
```bash
./SESSIONS/save-progress.sh auto <your-session-id>
```

### Option B: Quick Save (Just Heartbeat)
For periodic checkpoints:
```bash
./SESSIONS/save-progress.sh quick <your-session-id>
```

### Option C: Milestone Save
If working on a milestone:
```bash
./SESSIONS/save-progress.sh milestone <your-session-id>
```

### Option D: Full Save (Milestone + CURRENT_STATE + Git)
For major completion:
```bash
./SESSIONS/save-progress.sh full <your-session-id>
```

---

## STEP 4: Interactive Prompts

The script will ask:

**For Quick Save:**
- "What are you working on?" → Briefly describe current work

**For Milestone Save:**
- "Which step did you complete?" → Enter step number or 'none'
- "Brief note about completion:" → Describe what was accomplished

**For Full Save:**
- Combines milestone save + updates CURRENT_STATE.md + commits to git

---

## STEP 5: Confirm & Report

After save completes, tell the user:

```
✅ Progress saved!

Saved:
  - Heartbeat updated
  - Milestone: <name> (<progress>% complete)
  - Step <N> marked complete: <description>
  - Changes committed to git

View status: ./SESSIONS/quick-status.sh
```

---

## AUTOMATIC SAVE DETECTION

The save script automatically detects:

1. **Your session ID** - From PRIORITIES/ locks or MILESTONES/ owner field
2. **Active milestone** - If you have a claimed milestone
3. **Current progress** - What steps are pending/complete
4. **Git status** - Whether to commit changes

You can just run:
```bash
./SESSIONS/save-progress.sh auto session-3-coordinator
```

And it will do the right thing.

---

## WHEN TO USE EACH MODE

| Situation | Mode | What It Does |
|-----------|------|--------------|
| Periodic checkpoint | `quick` | Update heartbeat only |
| Completed milestone step | `milestone` | Update step status, recalc progress |
| Completed major work | `full` | Update everything + git commit |
| Unsure what to save | `auto` | Detects context automatically |

---

## SAVE VARIATIONS THE HUMAN MIGHT SAY

All of these should trigger the save protocol:

- "Save"
- "Save progress"
- "Save state"
- "Checkpoint"
- "Save my work"
- "Can you save this?"
- "Save where we are"
- "Create a save point"

**When you hear ANY of these, activate this Save protocol.**

---

## INTEGRATION WITH MILESTONES

If the save detects you're working on a milestone:

1. Shows current milestone and progress
2. Lists pending steps
3. Asks which step you completed
4. Updates milestone JSON automatically
5. Recalculates progress percentage
6. Updates CURRENT_STATE.md if progress is significant

**Example Flow:**
```
User: "Save"

Claude:
  I'll save your progress. Let me check what you're working on...

  [Runs: ./SESSIONS/save-progress.sh auto session-3-coordinator]

  Found active milestone: deploy-dashboard
  Current progress: 37% (3/8 steps)

  Pending steps:
    [4] Configure dashboard port (8002) on server
    [5] Verify UDC endpoints
    [6] Integrate with live Registry/Orchestrator

  Which step did you just complete? 4

  Brief note: Configured port 8002, dashboard accessible

  ✅ Step 4 marked complete
  📊 Progress: 50% (4/8 steps)
  💾 Changes saved and committed to git

  Next step: [5] Verify UDC endpoints
```

---

## GIT INTEGRATION

**Full save mode** automatically:
1. Adds `SESSIONS/` files to git
2. Creates descriptive commit message with:
   - Milestone name and progress
   - Session ID
   - Timestamp
   - Auto-save marker
3. Commits changes
4. Optionally pushes (if `AUTO_PUSH=true`)

**Commit message format:**
```
Save progress: Deploy Dashboard to Server (50% complete)

Session: session-3-coordinator
Timestamp: 2025-11-15 00:45:00 UTC

🤖 Auto-saved via save-progress.sh
```

---

## EXAMPLE INTERACTIONS

### Example 1: User says "Save"
```bash
# You detect no active milestone, use quick save
./SESSIONS/save-progress.sh quick session-3-coordinator

# Report to user:
✅ Progress saved (quick checkpoint)
Heartbeat updated with current work
```

### Example 2: User says "Save progress" (working on milestone)
```bash
# You detect active milestone, use milestone save
./SESSIONS/save-progress.sh milestone session-3-coordinator

# Script prompts for completed step
# You help user answer the prompts
# Report to user with progress update
✅ Milestone progress saved
Step 4 complete: Configure dashboard port
Progress: 50% (4/8 steps)
```

### Example 3: User says "Save" (major completion)
```bash
# You detect completed milestone or major work, use full save
./SESSIONS/save-progress.sh full session-3-coordinator

# Script updates everything and commits
# Report to user:
✅ Full save complete!
- Milestone updated
- CURRENT_STATE.md updated
- Changes committed to git
```

---

## CRITICAL REMINDERS

1. **Always identify your session ID first** (check REGISTRY.json or HEARTBEATS/)
2. **Auto mode is safest** - it detects the right save type
3. **Be helpful with prompts** - If script asks questions, help user answer
4. **Report what was saved** - Tell user exactly what got updated
5. **Suggest next steps** - After save, show what comes next

---

**The word "Save" activates this protocol. Progress preservation is critical for multi-session coordination.**

🌐⚡💾
