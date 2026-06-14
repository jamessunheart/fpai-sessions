# ops - SPECS

**Created:** 2025-11-15
**Status:** Operational Scripts Collection

---

## Purpose

Collection of operational scripts for managing Full Potential AI services. Automates deployment, health monitoring, git workflows, and system maintenance. Provides command-line tools for common operations.

---

## Requirements

### Functional Requirements
- [ ] Automated deployment pipeline (local → GitHub → server)
- [ ] Pre-deployment testing (run tests before deploy)
- [ ] Server health monitoring with live status
- [ ] Git workflow automation (commit, push, sync)
- [ ] Rollback capabilities
- [ ] Daily backup snapshots
- [ ] Sacred Loop workflow automation
- [ ] Service restart and status checks
- [ ] Log aggregation and viewing
- [ ] Docker deployment automation

### Non-Functional Requirements
- [ ] Reliability: Backup before every deployment, rollback on failure
- [ ] Safety: Always run tests before deploying
- [ ] Logging: Complete audit trail of all operations
- [ ] Idempotency: Scripts can be run multiple times safely
- [ ] User-friendly: Clear output and error messages

---

## Available Scripts

### Deployment Scripts

**deploy-to-server.sh**
- **Purpose:** Full automated deployment pipeline
- **Usage:** `./deploy-to-server.sh <service-name> [commit-message]`
- **Steps:**
  1. Run tests locally
  2. Commit and push to GitHub (SSOT)
  3. Create backup on server
  4. Pull latest code on server
  5. Run tests on server
  6. Restart service gracefully
  7. Verify health automatically
  8. Rollback on failure

**deploy-droplet.sh**
- **Purpose:** Docker-based droplet deployment
- **Usage:** `./deploy-droplet.sh <droplet-name>`

**test-deploy-to-server.sh**
- **Purpose:** Legacy deployment test script
- **Usage:** `./test-deploy-to-server.sh`

### Monitoring Scripts

**server-health-monitor.sh**
- **Purpose:** Real-time server health status
- **Usage:** `./server-health-monitor.sh [--watch]`
- **Checks:**
  - Registry (port 8000)
  - Orchestrator (port 8001)
  - All registered services
  - System resources (CPU, memory, disk)

**health-check.sh**
- **Purpose:** Service health verification
- **Usage:** `./health-check.sh <service-name>`

### Operations Scripts

**git-sync.sh**
- **Purpose:** Git commit and push automation
- **Usage:** `./git-sync.sh [commit-message]`

**rollback.sh**
- **Purpose:** Rollback to previous deployment
- **Usage:** `./rollback.sh <service-name>`

**snapshot-daily.sh**
- **Purpose:** Daily backup snapshots
- **Usage:** `./snapshot-daily.sh`
- **Schedule:** Cron job daily at 2am

**sacred-loop.sh**
- **Purpose:** Sacred Loop workflow automation
- **Usage:** `./sacred-loop.sh <droplet-id> <intent>`

---

## Script Specifications

### deploy-to-server.sh

**Input:**
- service_name: Name of service to deploy
- commit_message: Optional git commit message

**Process:**
1. **Local Tests:** Run pytest in service directory
2. **Git Commit:** Commit changes with message
3. **GitHub Push:** Push to GitHub (SSOT)
4. **Server Backup:** Create timestamped backup
5. **Pull Code:** Git pull on server
6. **Server Tests:** Run pytest on server
7. **Restart Service:** Systemd or Docker restart
8. **Health Check:** Verify /health endpoint
9. **Rollback:** Restore backup if health check fails

**Output:**
- Deployment status
- Test results
- Health check status
- Rollback information if needed

**Exit Codes:**
- 0: Success
- 1: Local tests failed
- 2: Git operations failed
- 3: Server tests failed
- 4: Health check failed (after rollback)

### server-health-monitor.sh

**Input:**
- --watch: Optional flag for continuous monitoring

**Process:**
1. Check Registry health and list services
2. Check Orchestrator health
3. Query each registered service
4. Check system resources
5. Display color-coded status

**Output:**
```
Registry: ✓ Healthy (8000)
Orchestrator: ✓ Healthy (8001)
Dashboard: ✓ Healthy (8002)
Verifier: ✗ Unhealthy (8200)

System Resources:
  CPU: 45%
  Memory: 2.1GB / 4GB
  Disk: 15GB / 50GB
```

**Watch Mode:**
- Refresh every 5 seconds
- Clear screen between updates
- Highlight changes

---

## Dependencies

### External Services
- GitHub: Source of truth for code
- Production Server: Deployment target
- Registry: Service discovery
- Orchestrator: System coordination

### Tools Required
- git: Version control
- ssh: Server access
- pytest: Testing
- systemctl: Service management
- docker: Container management (optional)

---

## Success Criteria

How do we know these scripts work?

- [ ] Deployment script completes successfully
- [ ] Tests run before every deployment
- [ ] Backup created before deployment
- [ ] Rollback works on deployment failure
- [ ] Health monitoring shows accurate status
- [ ] Git sync commits and pushes correctly
- [ ] Sacred Loop automation works end-to-end
- [ ] All scripts have proper error handling
- [ ] Scripts are idempotent (safe to re-run)

---

## Services and Repos

**Managed Services:**
- Orchestrator: ../orchestrator (Port 8001)
- Registry: ../registry (Port 8000)
- Dashboard: ../dashboard (Port 8002)
- Verifier: ../verifier (Port 8200)
- Coordinator: ../coordinator
- All other agents/services/* droplets

---

## Technical Constraints

- **Language:** Bash
- **Requires:** SSH access to server, git configured, pytest installed
- **Permissions:** Execute permission on all scripts
- **Environment:** Works on macOS and Linux
- **Server:** Ubuntu 20.04+ with systemd

---

## Script Organization

**Header Comment Required:**
```bash
#!/bin/bash
# Script: deploy-to-server.sh
# Purpose: Full automated deployment pipeline
# SPEC: DEPLOYMENT_SPEC.md
# Usage: ./deploy-to-server.sh <service-name> [commit-message]
```

**Error Handling:**
```bash
set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure
```

**Logging:**
```bash
echo "=== Step: Testing locally ==="
echo "✓ Tests passed"
echo "✗ Tests failed"
```

---

## Cron Jobs

**Daily Snapshot:**
```cron
0 2 * * * /opt/fpai/ops/snapshot-daily.sh
```

**Health Monitor (Optional):**
```cron
*/5 * * * * /opt/fpai/ops/health-check.sh >> /var/log/fpai-health.log
```

---

## Integration Notes

**With Sacred Loop:**
Scripts support full Sacred Loop automation:
```bash
./sacred-loop.sh 25 "Build Credentials Manager for secure API key storage"
```

This triggers:
1. SPEC generation
2. Package creation
3. Build
4. Verification
5. Deployment
6. Registry registration

All automated via ops scripts.

---

**Next Step:** Add more automation scripts as needs arise, document all new scripts
