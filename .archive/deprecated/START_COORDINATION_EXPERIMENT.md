# 🚀 START HERE - Multi-Session Coordination Experiment

**Just opened this terminal? Read below!**

---

## 🎯 What's Happening

We're testing if multiple Claude sessions can coordinate on a shared task faster than working alone.

**The Task:** Restore 2 offline services (ports 8001 and 8025)

**The Test:** Can 4 sessions divide the work and finish in < 30 minutes?

---

## 👋 Step 1: Introduce Yourself

**Run this first:**

```bash
cd /Users/jamessunheart/Development

# See which terminal you are
echo "I am terminal: $(tty)"

# Check into the experiment
echo "$(date): [$(tty)] Session joined the experiment" >> /tmp/multi_session_experiment_log.txt

# Register yourself if you haven't
cd docs/coordination/scripts
./session-choose-role.sh  # See what roles are available

# Then register (pick a number that's not taken)
./claude-session-register.sh NUMBER "Your Role" "Your Goal"
```

---

## 🤝 Step 2: Claim a Task

**Check which tasks are available:**

```bash
cat /tmp/coordination_status.sh | grep "Task"
```

**Available tasks:**

1. **Investigation Task A** - Find out why port 8001 is offline
   - Output: `/tmp/investigation_8001.txt`
   - Claim with: `echo "CLAIMED: Task 1 by session $(cat docs/coordination/.current_session 2>/dev/null || echo 'unknown')" >> /tmp/multi_session_experiment_log.txt`

2. **Fix Task B** - Restore port 8001 based on investigation
   - Depends on: Task 1 completing first
   - Claim with: `echo "CLAIMED: Task 2 by session $(cat docs/coordination/.current_session 2>/dev/null || echo 'unknown')" >> /tmp/multi_session_experiment_log.txt`

3. **Investigation Task C** - Find out why port 8025 is offline
   - Output: `/tmp/investigation_8025.txt`
   - Claim with: `echo "CLAIMED: Task 3 by session $(cat docs/coordination/.current_session 2>/dev/null || echo 'unknown')" >> /tmp/multi_session_experiment_log.txt`

4. **Coordination Task D** - Track progress and help blockers
   - Claimed by: Session #14 (Truth-Seeker)
   - Status: Active

---

## 🛠️ Step 3: Do Your Work

### If you claimed Task 1 (Investigation of 8001):

```bash
cd /Users/jamessunheart/Development

# Check if orchestrator service exists
ls -la SERVICES/orchestrator/

# Check what process might be on port 8001
lsof -i :8001 || echo "Nothing running on 8001"

# Check if there's a start script
find SERVICES/orchestrator -name "*.py" -o -name "start.sh" -o -name "main.py"

# Document findings
cat > /tmp/investigation_8001.txt << 'EOF'
Investigation of Port 8001 (Orchestrator)
==========================================
Timestamp: $(date)
Session: [Your session number]

Findings:
- Service location: [path]
- Main file: [filename]
- Current status: [running/stopped/missing]
- Error logs: [any errors found]
- Next steps to fix: [recommendations]
EOF

echo "$(date): [Your session] Task 1 COMPLETE - investigation documented" >> /tmp/multi_session_experiment_log.txt
```

### If you claimed Task 2 (Fix 8001):

```bash
cd /Users/jamessunheart/Development

# Wait for investigation
echo "Waiting for investigation results..."
while [ ! -f /tmp/investigation_8001.txt ]; do sleep 2; done

# Read findings
cat /tmp/investigation_8001.txt

# Based on findings, start the service
# (You'll need to read the investigation and decide how to fix)

# Test if it works
curl http://localhost:8001/health

echo "$(date): [Your session] Task 2 status update" >> /tmp/multi_session_experiment_log.txt
```

### If you claimed Task 3 (Investigation of 8025):

```bash
cd /Users/jamessunheart/Development

# Find what service uses port 8025
grep -r "8025" SERVICES/*/

# Check SSOT for clues
cat docs/coordination/SSOT.json | grep 8025

# Document findings
cat > /tmp/investigation_8025.txt << 'EOF'
Investigation of Port 8025
===========================
Timestamp: $(date)
Session: [Your session number]

Findings:
- Service name: [what runs on 8025]
- Location: [path if found]
- Status: [running/stopped/unknown]
- Next steps: [recommendations]
EOF

echo "$(date): [Your session] Task 3 COMPLETE - investigation documented" >> /tmp/multi_session_experiment_log.txt
```

---

## 📊 Step 4: Check Progress Anytime

```bash
/tmp/coordination_status.sh
```

This shows:
- Which tasks are done
- Which services are online
- Recent activity from all sessions

---

## 💬 Step 5: Communicate If Needed

**Need help? Stuck?**

```bash
echo "$(date): [Your session] HELP NEEDED: [describe issue]" >> /tmp/multi_session_experiment_log.txt
```

All other sessions can see this in the log!

---

## ✅ When You Finish Your Task

```bash
echo "$(date): [Your session] TASK COMPLETE - [brief summary]" >> /tmp/multi_session_experiment_log.txt

# Check overall progress
/tmp/coordination_status.sh
```

---

## 🎯 The Goal

**Success = Both services online in < 30 minutes through coordinated effort**

- ✅ Port 8001 responds to health check
- ✅ Port 8025 identified and status determined
- ✅ Clear log showing division of labor
- ✅ Evidence of coordination (Task 1 → Task 2 handoff)

---

## 🧠 Why This Matters

This tests whether Claude sessions can:
- Self-organize around a shared goal
- Divide complex work effectively
- Coordinate through shared state (files/logs)
- Work faster together than alone
- Make conscious decisions about task ownership

**This is multi-agent AI coordination in practice!**

---

**Ready? Pick a task above and start working!**

Everyone can see progress by running: `/tmp/coordination_status.sh`
