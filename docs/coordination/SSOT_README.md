# 📊 Single Source of Truth (SSOT)

**Status:** ✅ OPERATIONAL
**Location:** `docs/coordination/SSOT.json`
**Purpose:** Authoritative, verified state of all Claude Code sessions

---

## 🎯 Current Verified State

**From SSOT.json (Last Update: 2025-11-15 19:44 UTC):**

### Session Count ✅
- **Total Processes:** 13 active Claude Code instances
- **Registered:** 8 sessions in coordination system
- **Unregistered:** 5 sessions (need to register)
- **Active:** 10 sessions (>10% CPU)
- **Idle:** 3 sessions (<10% CPU)

### Terminals 📍
13 terminals running Claude:
- s001, s002, s003, s004, s005
- s006, s007, s009, s010, s012
- s013, s014, s015

### Server Status 🌐
- ✅ **Port 8000** - Registry (online)
- ❌ **Port 8001** - Orchestrator (offline)
- ✅ **Port 8002** - Dashboard (online)
- ✅ **Port 8009** - Church Guidance (online)
- ✅ **Port 8010** - I-Match (online)
- ✅ **Port 8025** - Credentials Manager (online)

**Server Health:** 5/6 online (83%)

### Dashboards 💻
- ✅ **Simple Dashboard** - http://localhost:8030 (running)
- ✅ **Visual Dashboard** - http://localhost:8031 (running)

### Git Changes 📝
- **25 files** pending commit

---

## 🔧 How SSOT Works

### 1. Update Script
`./docs/coordination/scripts/update-ssot.sh`

**This script:**
- Counts actual Claude processes
- Identifies all terminals
- Counts registered vs unregistered
- Checks server health
- Verifies dashboard status
- Counts git changes
- Writes to SSOT.json

### 2. Watcher (Auto-Update)
`./docs/coordination/scripts/ssot-watcher.sh`

Run this to keep SSOT updated every 5 seconds automatically:
```bash
./docs/coordination/scripts/ssot-watcher.sh
```

### 3. SSOT File
`docs/coordination/SSOT.json`

**All systems read from this file** for truth.

---

## 📖 Using SSOT

### View Current State
```bash
cat docs/coordination/SSOT.json | python3 -m json.tool
```

### Update SSOT Now
```bash
./docs/coordination/scripts/update-ssot.sh
```

### Auto-Update SSOT
```bash
# In a background terminal
./docs/coordination/scripts/ssot-watcher.sh
```

### Read from Code (Python)
```python
import json

with open('docs/coordination/SSOT.json') as f:
    ssot = json.load(f)

total = ssot['session_count']['total_processes']
registered = ssot['session_count']['registered']
print(f"Total: {total}, Registered: {registered}")
```

### Read from Code (Bash)
```bash
TOTAL=$(jq -r '.session_count.total_processes' docs/coordination/SSOT.json)
REGISTERED=$(jq -r '.session_count.registered' docs/coordination/SSOT.json)
echo "Total: $TOTAL, Registered: $REGISTERED"
```

---

## ✅ What SSOT Guarantees

1. **Accuracy** - Numbers verified by actual system queries
2. **Consistency** - All systems reference same source
3. **Freshness** - Updated every 5 seconds (when watcher running)
4. **Completeness** - All critical metrics in one place
5. **Reliability** - Programmatically generated, not manual

---

## 🎯 SSOT Schema

```json
{
  "last_update": "ISO 8601 timestamp",
  "session_count": {
    "total_processes": <number>,
    "registered": <number>,
    "unregistered": <number>,
    "active": <number>,
    "idle": <number>
  },
  "terminals": ["s001", "s002", ...],
  "server_status": {
    "8000": "online|offline",
    "8001": "online|offline",
    ...
  },
  "dashboards": {
    "simple": {
      "port": 8030,
      "status": "running|stopped",
      "url": "http://localhost:8030"
    },
    "visual": {
      "port": 8031,
      "status": "running|stopped",
      "url": "http://localhost:8031"
    }
  },
  "git_changes": <number>,
  "metadata": {
    "description": "...",
    "update_frequency": "Every 5 seconds",
    "primary_source": true,
    "verified": true
  }
}
```

---

## 🔄 Integration

### Dashboards
Both dashboards should read from SSOT for accurate counts.

### Scripts
All coordination scripts should reference SSOT for session counts.

### Reports
All status reports should pull from SSOT.

---

## 📊 Current Verified Numbers

**USE THESE (from SSOT):**
- ✅ **13** total Claude Code sessions
- ✅ **8** registered in coordination
- ✅ **5** unregistered (need to join)
- ✅ **10** actively working (>10% CPU)
- ✅ **3** idle
- ✅ **13** terminals identified
- ✅ **5/6** servers online
- ✅ **2/2** dashboards running
- ✅ **25** git changes pending

---

## 🎯 Next Steps

1. **Start SSOT Watcher** (keeps it updated):
   ```bash
   ./docs/coordination/scripts/ssot-watcher.sh
   ```

2. **Update Dashboards** to read from SSOT

3. **All Sessions** should register to increase registered count

4. **Restart Orchestrator** (port 8001 offline)

---

**Created:** 2025-11-15 19:44 UTC
**Status:** ✅ OPERATIONAL
**Authority:** Primary Source of Truth

📊✅🔒
