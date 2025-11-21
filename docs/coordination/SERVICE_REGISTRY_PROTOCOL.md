# Service Registry Protocol

**For all Claude Code sessions to register and manage services**

## Quick Start - Register New Service

```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./service-register.sh "service-name" "Description" 8XXX "status"
```

## Example

```bash
./service-register.sh "email-automation" "Automated email campaigns" 8500 "development"
```

## What Happens

1. Service added to `SERVICES/SERVICE_REGISTRY.json`
2. Auto-synced to GitHub (if git push enabled)
3. Auto-synced to server registry (http://198.54.123.234:8000)
4. Appears in SSOT.json within 5 seconds
5. All sessions can see it

## View All Services

```bash
# From SSOT (all sessions see this)
cat /Users/jamessunheart/Development/docs/coordination/SSOT.json | python3 -m json.tool | grep -A 50 services

# From source
cat /Users/jamessunheart/Development/SERVICES/SERVICE_REGISTRY.json | python3 -m json.tool
```

## Update Service Status

```bash
./service-update.sh "service-name" "production"
```

## Sync to Server

```bash
# Automatic via integrated-registry-system.py (runs every 60s)
# Or manual:
cd /Users/jamessunheart/Development/SERVICES
python3 integrated-registry-system.py
```

## Sync to GitHub

```bash
cd /Users/jamessunheart/Development/SERVICES
git add SERVICE_REGISTRY.json
git commit -m "Updated service registry"
git push origin main
```

## Current Services

- **ai-automation** (port 8700) - Development
- **i-match** (port 8401) - Production

## Service Statuses

- `development` - Being built
- `testing` - In QA
- `production` - Live
- `planned` - Not started
- `deprecated` - No longer used

## That's It!

Simple protocol:
- Register → Sync to GitHub → Sync to Server → Visible to all
- One command to add
- Auto-synced everywhere
