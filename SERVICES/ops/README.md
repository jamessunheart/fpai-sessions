# FPAI Ops Scripts

This folder stores operational scripts for managing Full Potential AI services.

## Purpose

- Deployment automation
- Health and status checks
- Git + server workflows
- System monitoring and maintenance

## Available Scripts

### Deployment
- **deploy-to-server.sh** - Full automated deployment pipeline (local → GitHub → server)
  - Runs tests locally before deployment
  - Commits and pushes to GitHub (SSOT)
  - Creates backup on server
  - Pulls latest code on server
  - Runs tests on server
  - Restarts service gracefully
  - Verifies health automatically
  - Usage: `./deploy-to-server.sh <service-name> [commit-message]`

- **deploy-droplet.sh** - Docker-based droplet deployment
- **test-deploy-to-server.sh** - Legacy deployment test script

### Monitoring
- **server-health-monitor.sh** - Real-time server health status
  - Checks Registry (port 8000) and Orchestrator (port 8001)
  - Usage: `./server-health-monitor.sh [--watch]`

- **health-check.sh** - Service health verification

### Operations
- **git-sync.sh** - Git commit and push automation
- **rollback.sh** - Rollback to previous deployment
- **snapshot-daily.sh** - Daily backup snapshots
- **sacred-loop.sh** - Sacred Loop workflow automation

## Services and Repos

- Orchestrator: ../orchestrator (Port 8001)
- Registry:     ../registry (Port 8000)
- Dashboard:    (future) ../dashboard (Port 8002)
- Verifier:     (future) ../verifier
- Coordinator:  (future) ../coordinator

## Quick Start

**Deploy a service to production:**
```bash
./deploy-to-server.sh orchestrator "Add new feature"
```

**Check system health:**
```bash
./server-health-monitor.sh
```

**Watch health continuously:**
```bash
./server-health-monitor.sh --watch
```

## Script Organization

All scripts should include a header comment explaining:
- What the script does
- Which SPEC/blueprint it implements
- How to use it

## Related Tools

- Full suite of optimization tools: ../fullpotential-tools
- Dev helpers: ../fpai-tools
