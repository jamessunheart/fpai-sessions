# Memory Optimization Migration Plan

## Strategy: Redundant Migration (Zero Downtime)

```
Phase 1: Deploy on Secondary (services run on BOTH)
Phase 2: Update routing/documentation
Phase 3: Notify users/services of new endpoints
Phase 4: Decommission on Primary
```

---

## Services to Migrate

| Service | Current (Primary) | New (Secondary) | Memory Saved |
|---------|-------------------|-----------------|--------------|
| fpai-aria | 198.54.123.234:8105 | 162.0.208.88:8105 | 52 MB |
| fpai-ai-automation | 198.54.123.234:8106 | 162.0.208.88:8106 | 46 MB |
| fpai-ai-gateway | 198.54.123.234:8107 | 162.0.208.88:8107 | 21 MB |
| fpai-sparket-engine | 198.54.123.234:8108 | 162.0.208.88:8108 | 119 MB |

**Total Memory Recovery:** ~238 MB on Primary

---

## Phase 1: Deploy on Secondary

### 1.1 Copy Service Files

```bash
# Run from PRIMARY, copy to SECONDARY
ssh -p 2222 root@198.54.123.234 '
# Services to migrate
SERVICES="aria ai-automation ai-gateway sparket-engine"

for svc in $SERVICES; do
    echo "📦 Copying $svc to secondary..."
    
    # Copy service code
    scp -r /opt/fpai/SERVICES/$svc root@162.0.208.88:/opt/fpai/SERVICES/
    
    # Copy systemd unit file
    scp /etc/systemd/system/fpai-$svc.service root@162.0.208.88:/etc/systemd/system/
done
'
```

### 1.2 Setup on Secondary

```bash
# Run ON SECONDARY
ssh root@162.0.208.88 '
SERVICES="aria ai-automation ai-gateway sparket-engine"

for svc in $SERVICES; do
    echo "🔧 Setting up $svc..."
    cd /opt/fpai/SERVICES/$svc
    
    # Create venv if needed
    [ ! -d .venv ] && python3 -m venv .venv
    
    # Install deps
    source .venv/bin/activate
    pip install -r requirements.txt -q
    
    # Enable and start service
    systemctl daemon-reload
    systemctl enable fpai-$svc
    systemctl start fpai-$svc
    
    echo "✅ $svc started on secondary"
done
'
```

### 1.3 Verify Both Running

```bash
# Check services on BOTH servers
echo "=== PRIMARY ==="
curl -s http://198.54.123.234:8105/health  # aria
curl -s http://198.54.123.234:8106/health  # ai-automation

echo "=== SECONDARY ==="
curl -s http://162.0.208.88:8105/health    # aria
curl -s http://162.0.208.88:8106/health    # ai-automation
```

---

## Phase 2: Update Routing

### 2.1 Update SSOT.json

```json
{
  "fleet": {
    "routing": {
      "ai_inference": "http://162.0.208.88:8101",
      "aria": "http://162.0.208.88:8105",
      "ai_automation": "http://162.0.208.88:8106",
      "ai_gateway": "http://162.0.208.88:8107",
      "sparket_engine": "http://162.0.208.88:8108"
    }
  }
}
```

### 2.2 Update SERVICE_REGISTRY.md

Add migration notes to the registry showing both locations during transition.

### 2.3 Update Nginx (if proxying)

```nginx
# /etc/nginx/conf.d/ai-services.conf

# Aria - now on secondary
upstream aria_backend {
    server 162.0.208.88:8105;  # NEW - Secondary
    server 198.54.123.234:8105 backup;  # OLD - Primary (backup)
}

# AI Automation - now on secondary  
upstream ai_automation_backend {
    server 162.0.208.88:8106;  # NEW
    server 198.54.123.234:8106 backup;  # OLD (backup)
}
```

---

## Phase 3: Notification

### Services That Call Migrated Services

Check and update these callers:

```bash
# Find services that call aria
grep -r "8105\|aria" /opt/fpai/SERVICES/*/app/*.py
grep -r "8105\|aria" /opt/fpai/SERVICES/*/.env

# Find services that call ai-automation
grep -r "8106\|ai-automation" /opt/fpai/SERVICES/*/app/*.py
```

### Update Environment Variables

```bash
# On PRIMARY, update .env files that reference migrated services
find /opt/fpai/SERVICES -name ".env" -exec grep -l "198.54.123.234:810[5-8]" {} \;

# Change:
# ARIA_URL=http://198.54.123.234:8105
# To:
# ARIA_URL=http://162.0.208.88:8105
```

### Broadcast Message

```bash
# Send coordination message
./docs/coordination/scripts/session-send-message.sh broadcast \
    "SERVICE_MIGRATION" \
    "AI services (aria, ai-automation, ai-gateway, sparket-engine) migrated to secondary server (162.0.208.88). Update your endpoints."
```

---

## Phase 4: Decommission on Primary

### 4.1 Verify Secondary Stable (Wait 24-48 hours)

```bash
# Check secondary services are healthy
for port in 8105 8106 8107 8108; do
    echo "Port $port:"
    curl -s http://162.0.208.88:$port/health | head -c 100
    echo ""
done
```

### 4.2 Stop on Primary

```bash
# Run on PRIMARY
ssh -p 2222 root@198.54.123.234 '
SERVICES="aria ai-automation ai-gateway sparket-engine"

for svc in $SERVICES; do
    echo "🛑 Stopping $svc on primary..."
    systemctl stop fpai-$svc
    systemctl disable fpai-$svc
done

echo ""
echo "Memory after migration:"
free -h
'
```

### 4.3 Remove from Primary (Optional)

```bash
# Only after confirmed working on secondary for 1 week
rm -rf /opt/fpai/SERVICES/aria
rm -rf /opt/fpai/SERVICES/ai-automation
# etc.
```

---

## Rollback Plan

If issues occur on secondary:

```bash
# Re-enable on PRIMARY
ssh -p 2222 root@198.54.123.234 '
systemctl start fpai-aria
systemctl start fpai-ai-automation
systemctl start fpai-ai-gateway
systemctl start fpai-sparket-engine
'

# Update SSOT back to primary IPs
```

---

## Timeline

| Day | Action |
|-----|--------|
| Day 1 | Phase 1: Deploy redundantly on secondary |
| Day 1 | Phase 2: Update SSOT and routing |
| Day 2 | Phase 3: Update callers, send notifications |
| Day 3-4 | Monitor both running |
| Day 5 | Phase 4: Stop on primary if stable |
| Day 7+ | Remove code from primary |

---

## Quick Start Commands

### Run Phase 1 Now

```bash
# Execute this to start the migration
ssh -p 2222 root@198.54.123.234 '
echo "Starting redundant deployment to secondary..."

# Copy aria first as test
scp -r /opt/fpai/SERVICES/aria root@162.0.208.88:/opt/fpai/SERVICES/
scp /etc/systemd/system/fpai-aria.service root@162.0.208.88:/etc/systemd/system/

ssh root@162.0.208.88 "
cd /opt/fpai/SERVICES/aria
python3 -m venv .venv 2>/dev/null
source .venv/bin/activate
pip install -r requirements.txt -q 2>/dev/null
systemctl daemon-reload
systemctl enable fpai-aria
systemctl start fpai-aria
systemctl status fpai-aria --no-pager | head -5
"
'
```

---

## Post-Migration Memory Targets

| Server | Before | After | Target |
|--------|--------|-------|--------|
| Primary | 6.2GB/7.7GB (81%) | 5.9GB/7.7GB (77%) | <5GB (65%) |
| Secondary | 10.7GB/31GB (34%) | 11GB/31GB (35%) | <15GB (48%) |

---

*Created: December 13, 2025*
*Status: Ready for execution*

