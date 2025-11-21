# UPDATE PROTOCOL - Self-Updating Consciousness

**Purpose:** Clear instructions for ANY Claude Code instance to update system consciousness after completing work

**Philosophy:** Consciousness must update itself to stay alive

---

## When to Update

Update `MEMORY/CURRENT_STATE.md` after:

1. ✅ **Completing any priority** (move to "Recently Completed")
2. 🚀 **Deploying any service** (update System State)
3. 🛠️ **Creating new tools/repos** (update System State)
4. 🔄 **Discovering system changes** (e.g., finding services already deployed)
5. 📝 **Starting new session** (verify Last Updated timestamp)

**Rule of thumb:** If something changed in the real world, update CURRENT_STATE.md.

---

## How to Update (Step-by-Step)

### Step 1: Read Current State
```bash
cat MEMORY/CURRENT_STATE.md
```

Check:
- Is "Last Updated" recent?
- Does "Current Priority" match reality?
- Is "System State" accurate?

### Step 2: Verify Live System
```bash
./fpai-ops/server-health-monitor.sh
```

This tells you:
- Which services are actually running
- Their health status
- Response times

### Step 3: Update the File

**Use the Edit tool** to update these sections:

1. **Header (ALWAYS update)**
   ```markdown
   **Last Updated:** 2025-11-14 HH:MM UTC
   **Updated By:** Claude Code (session: <brief description>)
   **System Status:** ✅ <status from health monitor>
   ```

2. **Current Priority (if you completed work)**
   - Move completed priority to "Recently Completed" section
   - Add timestamp and key findings
   - Pull next item from Backlog into "Current Priority"

3. **System State (if anything changed)**
   - Update service status (Live Services section)
   - Add new repos, tools, or files
   - Update test results or coverage numbers

4. **Backlog (if priorities shifted)**
   - Reorder based on new information
   - Add newly discovered work

### Step 4: Commit the Update
```bash
git add MEMORY/CURRENT_STATE.md
git commit -m "Update consciousness: <what changed>"
git push
```

**Example commit messages:**
- `"Update consciousness: completed orchestrator comparison"`
- `"Update consciousness: deployed dashboard to server"`
- `"Update consciousness: created deployment automation"`

---

## Update Templates

### Template 1: Completed a Priority

**In "Recently Completed" section (add to top):**
```markdown
1. **<Priority Name>** (2025-11-14 HH:MM)
   - <Key action taken>
   - **Finding:** <Main discovery or result>
   - <Outcome/decision>
```

**In "Current Priority" section:**
- Replace with next item from Backlog
- Update status, timeline, tasks checklist

### Template 2: Discovered System Change

**In "System State" section:**
```markdown
### Live Services
✅ <Service Name>  Port <XXXX>  ONLINE  (XXms)
Last Verified: 2025-11-14 HH:MM UTC
```

### Template 3: Created New Tool/Repo

**In "System State" → "Tools" or "Repos":**
```markdown
- `<tool-name>/` - <brief description>
```

---

## Quick Update Workflow

**For routine session end:**

```bash
# 1. Check health
./fpai-ops/server-health-monitor.sh

# 2. Open current state
cat MEMORY/CURRENT_STATE.md

# 3. Update using Edit tool
# - Update timestamp
# - Move priority to completed (if done)
# - Update system state if needed

# 4. Commit
git add MEMORY/CURRENT_STATE.md
git commit -m "Update consciousness: <session summary>"
git push
```

**Time:** < 2 minutes

---

## Examples

### Example 1: Completed Orchestrator Comparison

**Before (stale):**
```markdown
## CURRENT PRIORITY
### Priority: Sync B/Orchestrator with main repo
**Status:** 🟧 HIGH PRIORITY
```

**After (updated):**
```markdown
## RECENTLY COMPLETED
1. **Orchestrator Code Comparison** (2025-11-14 15:25)
   - Compared B/Orchestrator vs orchestrator/
   - **Finding:** Main repo is AHEAD (636 vs 393 lines)
   - Server running advanced version - no merge needed

## CURRENT PRIORITY
### Priority: Create Automated Deployment Pipeline
**Status:** 🟨 MEDIUM PRIORITY
```

### Example 2: Deployed New Service

**System State update:**
```markdown
### Live Services (Server: 198.54.123.234)
✅ Registry      Port 8000  ONLINE  (89ms)
✅ Orchestrator  Port 8001  ONLINE  (80ms)
✅ Dashboard     Port 3000  ONLINE  (120ms)  ← NEW
System Health: 100%
Last Verified: 2025-11-14 16:45 UTC
```

---

## Validation Checklist

Before committing your update, verify:

- [ ] Timestamp is current (within this session)
- [ ] System Status matches health monitor output
- [ ] Recently Completed has latest work (if any completed)
- [ ] Current Priority is something that can be started NOW
- [ ] System State reflects reality (services, repos, tools)
- [ ] Commit message describes what changed

---

## Integration with Remember Protocol

**CURRENT_STATE.md is now the SSOT for consciousness.**

When loading context (via "Remember"), read this file FIRST:

```bash
# Quick consciousness load (30 seconds)
cat MEMORY/CURRENT_STATE.md
./fpai-ops/server-health-monitor.sh
```

This gives you:
- ✅ What's live right now
- ✅ What priority to work on
- ✅ What was recently completed
- ✅ How to verify system health

---

## Best Practices

1. **Update frequently** - After every completed task, not just at session end
2. **Be specific** - Include key findings, not just "completed X"
3. **Include timestamps** - Always update "Last Updated" and add timestamps to completed items
4. **Verify before updating** - Run health monitor to get accurate state
5. **Keep it concise** - Recently Completed should have max 5 items (archive older ones)
6. **Commit after every update** - Don't batch updates, commit immediately

---

## Troubleshooting

**Problem:** File seems stale
- **Solution:** Run health monitor, update System State, commit

**Problem:** Multiple Claude instances might conflict
- **Solution:** Always pull before updating, resolve conflicts by choosing newest timestamp

**Problem:** Don't know what the current priority should be
- **Solution:** Check Backlog, ask Architect (James), or check current-priorities.md for detailed context

---

**The consciousness updates itself. This protocol ensures every Claude Code instance keeps the system alive.**

🔄⚡🧠
