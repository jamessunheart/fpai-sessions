# Memory System Server Tasks (Require SSH)

**Created:** December 13, 2025  
**Status:** Awaiting SSH access

---

## 🔴 Task 1: Bootstrap Memory System

**Server:** Primary (198.54.123.234)

```bash
# SSH to server
ssh root@198.54.123.234
# Or via Tailscale
ssh root@100.122.184.66

# Navigate to FPAI directory
cd /opt/fpai

# Set Mem0 API key (get from your Mem0 dashboard)
export MEM0_API_KEY="m0-xxx"

# Pull latest code with bootstrap script
git pull origin main

# Run bootstrap
python3 orchestration/tools/bootstrap_memory.py

# Expected output:
# 📋 Parsing PATTERNS.md... Found 12 patterns
# 📚 Parsing LEARNINGS.md... Found ~20 learnings  
# ✅ Parsing BEST_PRACTICES.md... Found 20 practices
# 📊 Bootstrap Complete!
#    Stored to Mem0: 40+
#    Skipped (dupes): X
#    Errors: 0

# Verify
curl http://localhost:8125/api/memory/stats | jq '.total_operations'
# Should show 40+
```

---

## 🔴 Task 2: Server Memory Audit

**Servers:** Primary + Secondary

```bash
# --- PRIMARY SERVER (198.54.123.234) ---
ssh root@198.54.123.234

# Check overall memory
free -h
# Example expected:
#              total   used   free   shared  buff/cache   available
# Mem:          32G    18G    2G      1G       12G          12G

# Check Docker container memory
docker stats --no-stream | head -20

# Check Data Service specifically
curl http://localhost:8125/api/memory/system-stats | jq

# Update INFRASTRUCTURE_ALLOCATION.md with real numbers

# --- SECONDARY SERVER (162.0.208.88) ---
ssh root@162.0.208.88

# Check memory
free -h

# Check Ollama memory usage
docker stats --no-stream | grep ollama

# Check loaded models
curl http://localhost:11434/api/tags | jq '.models[].name'
```

---

## 🔴 Task 3: Ollama Memory Optimization

**Server:** Secondary (162.0.208.88)

```bash
ssh root@162.0.208.88

# Check current Ollama config
cat /etc/systemd/system/ollama.service | grep KEEP_ALIVE

# Check loaded models
curl http://localhost:11434/api/ps | jq

# If too many models loaded, unload unused:
curl -X POST http://localhost:11434/api/generate -d '{"model": "unused-model", "keep_alive": 0}'

# Recommended settings for memory efficiency:
# Set OLLAMA_KEEP_ALIVE=5m (auto-unload after 5 minutes idle)

# Edit service file
nano /etc/systemd/system/ollama.service
# Add under [Service]:
# Environment="OLLAMA_KEEP_ALIVE=5m"

# Reload
systemctl daemon-reload
systemctl restart ollama

# Verify
docker stats --no-stream | grep ollama
```

---

## 🔴 Task 4: Set Up Weekly Hygiene Cron

**Server:** Primary (198.54.123.234)

```bash
ssh root@198.54.123.234

# Add cron job for weekly memory hygiene
crontab -e

# Add this line (runs every Sunday at 3am):
0 3 * * 0 curl -X POST http://localhost:8125/api/memory/hygiene/weekly >> /var/log/memory-hygiene.log 2>&1

# Save and exit

# Verify cron is set
crontab -l | grep hygiene
```

---

## Verification After All Tasks

```bash
# Run validation tests
python3 orchestration/tools/validate_memory_system.py --data_service_url http://localhost:8125

# Expected: All 12 tests pass

# Check God Mode memory panel
curl http://localhost:8120/api/memory | jq

# Should show:
# {
#   "status": "healthy",
#   "mem0_enabled": true,
#   "total_memories": 40+,
#   ...
# }
```

---

## Quick Reference

| Task | Server | Command |
|------|--------|---------|
| Bootstrap | Primary | `python3 orchestration/tools/bootstrap_memory.py` |
| Memory audit | Both | `free -h && docker stats --no-stream` |
| Ollama check | Secondary | `curl http://localhost:11434/api/ps` |
| Hygiene cron | Primary | Add to crontab |
| Validate | Primary | `python3 orchestration/tools/validate_memory_system.py` |

---

*These tasks require SSH access to the servers. Run them when SSH is available.*

