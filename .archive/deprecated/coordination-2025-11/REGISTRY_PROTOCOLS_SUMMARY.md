# Registry Protocols - Simple Guide

**For all Claude Code sessions**

---

## SESSION REGISTRY

**Register yourself as a Claude session**

### One Command:

```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./claude-session-register.sh YOUR_NUMBER "Your Role" "Your Goal"
```

### Example:

```bash
./claude-session-register.sh 12 "Revenue Engineer" "Build revenue systems"
```

### What Happens:
1. Added to `claude_sessions.json`
2. Auto-merged into `SSOT.json` (5 seconds)
3. All sessions can see you

### View:
```bash
cat docs/coordination/SSOT.json | python3 -m json.tool | grep -A 100 claude_sessions
```

**Available numbers:** 12

---

## SERVICE REGISTRY

**Register a service/project you're building**

### One Command:

```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./service-register.sh "name" "Description" PORT "status"
```

### Example:

```bash
./service-register.sh "email-automation" "Automated email campaigns" 8500 "development"
```

### Update Status:

```bash
./service-update.sh "email-automation" "production"
```

### What Happens:
1. Added to `SERVICES/SERVICE_REGISTRY.json`
2. Synced to server registry (http://198.54.123.234:8000)
3. Auto-merged into `SSOT.json` (5 seconds)
4. Ready for GitHub commit

### View:
```bash
cat docs/coordination/SSOT.json | python3 -m json.tool | grep -A 50 services
```

### Current Services:
- ai-automation (8700) - Development
- i-match (8401) - Production

---

## AUTO-SYNC

### To Server:

**Automatic** via `integrated-registry-system.py` (runs every 60s)

**Manual:**
```bash
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py
```

### To GitHub:

```bash
cd /Users/jamessunheart/Development/SERVICES
git add SERVICE_REGISTRY.json
git commit -m "Updated services"
git push origin main
```

**Auto-sync setup (future):**
- Create GitHub repo: `fpai-services`
- Add remote: `git remote add origin git@github.com:your-org/fpai-services.git`
- First push: `git push -u origin main`
- Set up cron on server to pull from GitHub hourly

---

## SSOT.json (Single Source of Truth)

**All sessions read from here:**

```bash
cat /Users/jamessunheart/Development/docs/coordination/SSOT.json | python3 -m json.tool
```

**Contains:**
- `claude_sessions` - All registered sessions
- `services` - All registered services
- `server_status` - Server health
- `dashboards` - Dashboard URLs
- Auto-updates every 5 seconds

---

## That's It!

**Two simple protocols:**

1. **Session Registry** → `claude-session-register.sh`
2. **Service Registry** → `service-register.sh` + auto-sync

**One unified view:** `SSOT.json`

**Syncs to:**
- ✅ SSOT.json (auto, 5s)
- ✅ Server registry (auto, 60s)
- ⏳ GitHub (manual, or set up auto)

---

**Full Docs:**
- SESSION_REGISTRY_PROTOCOL.md
- SERVICE_REGISTRY_PROTOCOL.md
- INTEGRATED_REGISTRY_SYSTEM.md
