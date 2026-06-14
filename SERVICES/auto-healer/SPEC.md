# Auto-Healer Service

**Version:** 1.0.0  
**Port:** 8180  
**Status:** Production Ready

## Overview

The Auto-Healer is a smart service healing system that goes beyond simple restarts. It diagnoses WHY services fail, applies appropriate fixes, learns from outcomes, and escalates when human intervention is needed.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Auto-Healer                               │
├─────────────────────────────────────────────────────────────────┤
│  Detection Layer                                                 │
│  ├── HealthChecker (HTTP + Systemd monitoring)                  │
│  └── Continuous loop every 30 seconds                           │
├─────────────────────────────────────────────────────────────────┤
│  Diagnosis Layer                                                 │
│  ├── FailureAnalyzer (log parsing, pattern matching)            │
│  └── 8 failure types: missing_deps, port_in_use, etc.           │
├─────────────────────────────────────────────────────────────────┤
│  Healing Layer                                                   │
│  ├── HealingExecutor (action orchestration)                     │
│  └── Actions: create_venv, install_deps, kill_port, restart     │
├─────────────────────────────────────────────────────────────────┤
│  Learning Layer                                                  │
│  ├── KnowledgeBase (SQLite persistence)                         │
│  └── Tracks success rates, recurring patterns                   │
├─────────────────────────────────────────────────────────────────┤
│  Escalation Layer                                                │
│  ├── EscalationManager (alerting)                               │
│  └── Email + God Mode notifications                             │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Detection
- HTTP health endpoint checks
- Systemd service status monitoring
- Consecutive failure tracking
- Response time measurement

### Diagnosis
- **MISSING_VENV**: Venv directory doesn't exist
- **MISSING_DEPS**: Python module not installed
- **MISSING_IMPORT**: Code import error
- **PORT_IN_USE**: Address already in use
- **CONFIG_ERROR**: Missing env vars / config issues
- **DATABASE_ERROR**: DB connection problems
- **MEMORY_OOM**: Out of memory
- **UNKNOWN**: Requires human review

### Healing Actions
| Action | Risk | Description |
|--------|------|-------------|
| `restart_service` | Low | Simple systemd restart |
| `create_venv` | Low | Create venv + install deps |
| `install_deps` | Low | pip install missing module |
| `kill_port` | Medium | Kill process using port |

### Learning
- Historical success rates per (failure_type, action) pair
- Recurring pattern detection (5+ failures in 24h = flagged)
- MTTR (Mean Time To Recovery) tracking

### Escalation
- Max 3 auto-restart attempts before alerting
- Critical services: alert if down > 5 minutes
- Recurring patterns flagged for human review
- Alert channels: Email, God Mode dashboard

## API Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /api/status` - Comprehensive status

### Services
- `GET /api/services` - List all monitored services
- `GET /api/services/{name}` - Service details
- `POST /api/services` - Add service to monitor
- `DELETE /api/services/{name}` - Remove service

### Health Checks
- `GET /api/services/{name}/health` - Check specific service
- `POST /api/health/check-all` - Trigger full health check

### Healing
- `POST /api/services/{name}/heal` - Manually trigger healing
- `GET /api/services/{name}/diagnose` - Diagnose without healing

### Knowledge Base
- `GET /api/outcomes` - Healing history
- `GET /api/diagnoses` - Recent diagnoses
- `GET /api/patterns` - Recurring patterns
- `GET /api/metrics` - Statistics

### Escalation
- `GET /api/alerts` - Recent alerts
- `POST /api/services/{name}/suppress` - Suppress alerts
- `POST /api/services/{name}/unsuppress` - Unsuppress alerts

### God Mode Integration
- `GET /api/god-mode-status` - Summary for dashboard

## Configuration

Environment variables:
- `PORT` - Service port (default: 8180)
- `LOG_LEVEL` - Logging level (default: INFO)
- `HEALTH_CHECK_INTERVAL` - Seconds between checks (default: 30)
- `MAX_AUTO_RESTARTS` - Max attempts before escalate (default: 3)
- `RESTART_COOLDOWN` - Seconds between attempts (default: 60)
- `CRITICAL_DOWN_THRESHOLD` - Seconds before critical alert (default: 300)
- `ALERT_EMAIL` - Email for alerts
- `COMMUNICATION_HUB_URL` - For sending emails
- `GOD_MODE_URL` - For dashboard notifications

## Monitored Services (Default)

| Service | Port | Critical |
|---------|------|----------|
| genesis | 8150 | Yes |
| team-hub | 8355 | Yes |
| fp-credits-gateway | 8765 | Yes |
| ai-brain | 8101 | Yes |
| intelligence-core | 8142 | Yes |
| data-service | 8125 | Yes |
| whaletrack-magnet | 8600 | No |
| i-match | 8401 | No |
| ai-automation | 8700 | No |
| god-mode-v3 | 8300 | No |

## Deployment

```bash
# Create systemd service
cat > /etc/systemd/system/fpai-auto-healer.service << EOF
[Unit]
Description=FPAI Auto-Healer - Smart Service Healing
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/auto-healer
Environment="PATH=/opt/fpai/auto-healer/.venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/fpai/auto-healer/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8180
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Setup
cd /opt/fpai/auto-healer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Enable and start
systemctl daemon-reload
systemctl enable fpai-auto-healer
systemctl start fpai-auto-healer
```

## Success Metrics

| Metric | Target |
|--------|--------|
| MTTR | < 2 minutes |
| Auto-heal success rate | > 80% |
| False positive alerts | < 5% |
| Service coverage | 100% critical |











