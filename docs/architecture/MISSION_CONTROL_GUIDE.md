# 🎯 Mission Control v2.0 - Complete User Flow

## For Mission Builders (Apprentices)

### 1. Browse Missions
Visit **`https://fullpotential.ai/missions`**

You'll see a **live tactical grid** showing:
- Mission ID (e.g., M001, M002)
- Priority badges (P0 = urgent, P1 = high, P2 = strategic)
- Current status (OPEN, CLAIMED, IN PROGRESS, SUBMITTED, COMPLETED)
- Who's working on it (if claimed)
- Constitutional principle alignment
- Auto-refreshes every 30 seconds

### 2. View Mission Details
Click on any mission card → **Full mission spec page** opens

You'll see:
- ✅ Complete technical specification (markdown rendered beautifully)
- ✅ Requirements, architecture, API specs, testing strategy
- ✅ Starter kit instructions
- ✅ Claim button (if not already claimed)
- ✅ Status history timeline

### 3. Claim a Mission
On the detail page, fill out the **claim form**:
- Your name
- Email (optional)
- Notes (optional, e.g., "Starting this week")

Click **"CLAIM & START MISSION"**

**What happens:**
- Mission status → `CLAIMED`
- Your name appears on the card
- Other users see it's taken
- A "SUBMIT CODE" button appears for you

### 4. Work on the Code
Follow the starter kit instructions in the mission spec:
```bash
# Create repo
mkdir mission-m001
cd mission-m001
git init

# Build according to spec
# (Full instructions in mission doc)

# Test locally
pytest tests/ -v
```

### 5. Submit Your Work
When ready, click **"SUBMIT CODE"** on the mission detail page

This takes you to **Harvester** with mission pre-filled:
- Mission ID auto-selected
- Form ready for your GitHub repo URL
- Just paste your repo link and submit

### 6. Watch the Harvest
Real-time terminal shows:
- 📦 Cloning your repo
- ✅ Verifying structure
- 🧪 Running tests
- 🔐 Security scan
- 📊 Quality score (0-100)

**Auto-Updates Happen:**
- Mission status → `SUBMITTED` (harvest starts)
- Mission status → `COMPLETED` (if score ≥ 60%)
- Mission status → `BLOCKED` (if tests fail)

### 7. See Results on Board
Go back to `/missions` → Your mission shows:
- Status badge: **COMPLETED** ✅
- Your name as contributor
- Final harvest score in history

---

## For System Operators

### View All Mission States
```bash
# API: Get all missions with live status
curl https://fullpotential.ai/missions/api/missions

# Response includes:
{
  "missions": [
    {
      "id": "M001",
      "title": "...",
      "live_status": {
        "status": "completed",
        "last_updated": "2025-11-26T15:45:00",
        "history": [...]
      },
      "claim_info": {
        "claimer_name": "Alex Chen",
        "claimed_at": "..."
      }
    }
  ]
}
```

### Manual Status Update
```bash
curl -X POST https://fullpotential.ai/missions/api/status \
  -H "Content-Type: application/json" \
  -d '{
    "mission_id": "M001",
    "status": "in_progress",
    "updated_by": "Alex Chen",
    "notes": "Making good progress on tests"
  }'
```

### Check Claims
```bash
# On server
ls -la /root/FPAI_Cockpit/SERVICES/mission-control/data/claims/
cat data/claims/M001.json
```

### Monitor Logs
```bash
# Mission Control logs
tail -f /root/FPAI_Cockpit/SERVICES/mission-control/mission-control.log

# Harvester logs (shows when submissions come in)
tail -f /root/FPAI_Cockpit/SERVICES/harvester/feedback.log
```

---

## Complete System Flow Diagram

```
┌────────────────────────────────────────────────────────────┐
│                    USER JOURNEY                             │
└────────────────────────────────────────────────────────────┘

1️⃣  Browse
    │
    ↓
┌─────────────────────────┐
│  fullpotential.ai       │
│       /missions         │  ← Live tactical grid
│                         │  ← Real-time status badges
│  [M001 | P0 | OPEN]    │
│  [M002 | P1 | CLAIMED] │
└─────────┬───────────────┘
          │ (click mission)
          ↓
2️⃣  View Details
    │
    ↓
┌─────────────────────────┐
│  Mission M001 Detail    │
│  ─────────────────────  │
│  📋 Full Spec           │
│  🎯 Requirements        │
│  🏗️ Architecture        │
│  ✅ Testing Strategy    │
│                         │
│  [CLAIM & START] ←─────┼─── Not claimed yet
└─────────┬───────────────┘
          │ (claim)
          ↓
3️⃣  Work Locally
    │
    ↓
┌─────────────────────────┐
│  Your Local Machine     │
│  ─────────────────────  │
│  $ git init             │
│  $ # build code         │
│  $ pytest tests/ -v     │
│  $ git push origin main │
└─────────┬───────────────┘
          │ (click SUBMIT CODE)
          ↓
4️⃣  Submit & Harvest
    │
    ↓
┌─────────────────────────┐
│  Harvester Form         │
│  ─────────────────────  │
│  Mission: M001 ✓        │  ← Pre-filled
│  Repo: [paste URL]      │
│  [SUBMIT] ──────────────┼──→ Triggers harvest
└─────────┬───────────────┘
          │
          ↓
┌─────────────────────────┐
│  Real-time Terminal     │
│  ─────────────────────  │
│  > Cloning repo... ✓    │
│  > Running tests... ✓   │
│  > Security scan... ✓   │
│  > Score: 85/100 ✅     │
└─────────┬───────────────┘
          │
          ↓
5️⃣  Auto-Update Mission
    │
    ↓
┌─────────────────────────┐
│  Mission Control API    │
│  POST /api/status       │
│  {                      │
│    status: "completed", │
│    harvest_score: 85    │
│  }                      │
└─────────┬───────────────┘
          │
          ↓
6️⃣  See Results
    │
    ↓
┌─────────────────────────┐
│  Mission Board          │
│  ─────────────────────  │
│  [M001 | P0 | ✅ DONE] │  ← Updated!
│   👤 Alex Chen          │
│   Score: 85/100         │
└─────────────────────────┘
```

---

## Status State Machine

```
OPEN
  ↓ (user clicks CLAIM)
CLAIMED
  ↓ (user working locally)
IN_PROGRESS
  ↓ (user clicks SUBMIT CODE)
SUBMITTED
  ↓
  ├─→ COMPLETED (harvest score ≥ 60%)
  └─→ BLOCKED (tests failed / errors)
```

---

## Key Features

### ✅ Real-Time Tracking
- Board auto-refreshes every 30 seconds
- Status updates appear immediately
- No manual coordination needed

### ✅ Claim Protection
- Can't claim if already taken
- Clear visibility of who's working on what
- Prevents duplicate work

### ✅ Seamless Integration
- Mission → Detail → Claim → Code → Submit → Harvest → Complete
- All in one smooth flow
- No context switching

### ✅ Full Transparency
- Status history shows every update
- Harvest scores visible
- Timeline of all changes

### ✅ No Database Required
- JSON files for simplicity
- Easy to inspect and debug
- Git-friendly (can be committed)

---

## Quick Commands

### Deploy
```bash
# On server
cd /root/FPAI_Cockpit
git pull origin main
bash DEPLOY_MISSION_CONTROL.sh
```

### Test Locally
```bash
# Start Mission Control
cd SERVICES/mission-control
python3 app.py &

# Start Harvester
cd SERVICES/harvester
python3 app.py &

# Visit
open http://localhost:8700
```

### Check Health
```bash
curl http://127.0.0.1:8700/health
curl http://127.0.0.1:8055/health
```

---

## Next Steps

Now that Mission Control is live:

1. **Generate More Missions:** Use `generate_mission_package.py` to create new specs
2. **Invite Builders:** Share `/missions` URL with apprentices
3. **Monitor Progress:** Watch the board fill with claimed/completed missions
4. **Iterate:** Collect feedback and enhance the system

🎯 **Mission Control is now the operational center of Full Potential AI.**

