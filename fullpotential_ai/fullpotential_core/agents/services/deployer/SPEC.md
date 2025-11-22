# deployer - SPECS

**Created:** 2025-11-15
**Status:** Production Ready (Droplet #24)
**Port:** 8007

---

## Purpose

Automates Sacred Loop Steps 6-7: deployment to production and Registry registration. Eliminates manual SSH commands, file transfers, Docker builds, and service registration. Enables true end-to-end autonomy from intent to production.

---

## Requirements

### Functional Requirements
- [ ] SSH file transfer to production server
- [ ] Docker image building and container deployment
- [ ] Alternative: systemd service deployment
- [ ] Service health verification after deployment
- [ ] Automatic Registry registration
- [ ] Rollback support on deployment failure
- [ ] Environment variable injection
- [ ] Port mapping configuration
- [ ] 6-phase deployment process with detailed logging
- [ ] Support for multiple deployment methods (Docker, systemd)
- [ ] SFTP file transfer with progress tracking

### Non-Functional Requirements
- [ ] Performance: Deployment < 2 minutes (simple services), < 5 minutes (complex)
- [ ] Reliability: Rollback on failure, health verification before completion
- [ ] Security: SSH key authentication, no password storage
- [ ] Logging: Complete deployment audit trail with phase timings
- [ ] Idempotent: Can redeploy same service without conflicts

---

## API Specs

### Endpoints

**POST /deploy**
- **Purpose:** Submit service for deployment
- **Input:** service_path, service_name, droplet_id, service_port, deployment_method, environment_vars, auto_register
- **Output:** deploy_job_id, status, created_at
- **Success:** 202 Accepted
- **Errors:** 400 if invalid input, 500 if job creation fails

**GET /deploy/{job_id}**
- **Purpose:** Get deployment status and details
- **Input:** job_id
- **Output:** Full deployment status with phase details, service_url, registration info
- **Success:** 200 OK
- **Errors:** 404 if job not found

**POST /deploy/{job_id}/rollback**
- **Purpose:** Rollback a deployment to previous version
- **Input:** job_id
- **Output:** Rollback confirmation
- **Success:** 200 OK
- **Errors:** 404 if job not found, 409 if no previous version

**GET /deploy/history/{service_name}**
- **Purpose:** Get deployment history for a service
- **Input:** service_name
- **Output:** Array of past deployments
- **Success:** 200 OK
- **Errors:** 404 if service not found

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "ssh_status": "connected", "registry_status": "reachable"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

**GET /capabilities**
- **Purpose:** UDC capabilities endpoint
- **Input:** None
- **Output:** Deployment methods, features, server info
- **Success:** 200 OK
- **Errors:** 500 if unavailable

### Data Models

```python
class DeployRequest:
    service_path: str
    service_name: str
    droplet_id: int
    service_port: int
    deployment_method: str  # "docker" or "systemd"
    environment_vars: dict
    auto_register: bool = True

class DeploymentPhase:
    phase: str  # "Validation", "Transfer", "Build", "Start Service", "Verify Health", "Register"
    status: str  # "pending", "running", "success", "failed"
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    details: str
    error: Optional[str]

class DeployJob:
    deploy_job_id: str
    service_name: str
    service_path: str
    status: str  # "pending", "running", "completed", "failed"
    droplet_id: int
    service_port: int
    service_url: Optional[str]
    deployment_method: str
    phases: List[DeploymentPhase]
    registration: Optional[dict]
    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]
    success: bool
    error: Optional[str]

class RegistrationInfo:
    droplet_id: int
    service_name: str
    endpoint: str
    registered_at: datetime
    registry_response: dict
```

---

## Dependencies

### External Services
- Production Server (198.54.123.234): SSH access, Docker daemon
- Registry (Port 8000): Service registration
- Verifier (Optional): Post-deployment verification

### APIs Required
- SSH/SFTP: File transfer to server
- Docker API: Image building and container management
- Registry API: POST /register
- Systemd: Service management (alternative to Docker)

### Data Sources
- Service codebase: Files to deploy
- Dockerfile: Docker deployment configuration
- requirements.txt: Python dependencies

---

## Success Criteria

How do we know this works?

- [ ] Files transferred to server successfully via SSH
- [ ] Docker image builds without errors
- [ ] Container starts and runs
- [ ] Health endpoint returns 200 OK
- [ ] Service registered with Registry
- [ ] Deployment completes in < 2 minutes (simple services)
- [ ] Rollback restores previous version on failure
- [ ] Environment variables injected correctly
- [ ] All 6 phases complete successfully
- [ ] Deployment audit trail captured

---

## Deployment Process (6 Phases)

### Phase 1: Validation (1 second)
- Check service path exists
- Verify Dockerfile or requirements.txt present
- Validate deployment configuration
- Ensure port not in use

### Phase 2: Transfer (5-10 seconds)
- SSH to production server
- Create deployment directory: /opt/fpai/services/{name}
- Transfer all files via SFTP
- Set correct file permissions

### Phase 3: Build (30-60 seconds)
- **Docker:** Build Docker image with tag {service_name}:latest
- **Systemd:** Install Python dependencies with pip
- Run build commands if specified

### Phase 4: Start Service (3-5 seconds)
- **Docker:** Run container with port mapping, environment vars, network
- **Systemd:** Create systemd unit file, enable and start service
- Set restart policy

### Phase 5: Verify Health (5-10 seconds)
- Wait for service to start (max 30 seconds)
- Check /health endpoint
- Verify correct response
- Retry up to 3 times if initial check fails

### Phase 6: Register with Registry (2-3 seconds)
- POST service info to Registry
- Verify registration succeeded
- Store registration confirmation

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8007
- **Resource limits:**
  - Memory: 512MB max
  - CPU: 1 core
  - Storage: 2GB for deployment artifacts
- **Response time:** < 2 minutes (simple), < 5 minutes (complex)
- **SSH:** Key-based authentication only
- **Docker:** Requires Docker daemon on server
- **Timeout:** 10 minutes per deployment
- **Backup retention:** Previous version kept for 7 days

---

## Deployment Methods

### Docker (Recommended)
**Pros:**
- Isolated environment
- Easy rollback (previous image)
- Consistent across deployments
- Port mapping built-in

**Cons:**
- Requires Docker on server
- Slightly higher resource usage

### Systemd
**Pros:**
- Lightweight
- Native to Linux
- Simple for basic services

**Cons:**
- No isolation
- Manual dependency management
- Harder rollback

---

## Rollback Support

**How Rollback Works:**
1. Keep previous Docker image or service files
2. On deployment failure in Phase 4 or 5: Auto-rollback
3. On manual rollback request: Stop current, start previous
4. Update Registry with rollback event

**Rollback Triggers:**
- Health check fails after 3 attempts
- Container exits immediately
- Build fails
- Manual request via API

---

## Integration with Sacred Loop

**Complete Autonomous Flow:**
```
Intent → SPEC → Package → Build → Verify → Auto-Fix → Deploy → Register → Done
```

All automatic, zero manual intervention.

---

**Next Step:** Complete Sacred Loop by deploying Auto-Fix Engine using Deployer
