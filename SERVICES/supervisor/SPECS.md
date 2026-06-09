# Supervisor Droplet - SPECS

**Droplet ID:** #101
**Version:** 1.0.0
**Status:** Planning

---

## Purpose

Monitor all system droplets, automatically restart failures, and dispatch alerts when issues are detected. The Supervisor is the "watchdog" of the droplet ecosystem.

---

## Requirements

### Functional Requirements
- [ ] Monitor health of all registered droplets every 30 seconds
- [ ] Automatically restart unhealthy droplets via systemd
- [ ] Track failure history per droplet
- [ ] Dispatch alerts to Alerts droplet when issues occur
- [ ] Provide dashboard of droplet health status
- [ ] Implement exponential backoff for repeated failures

### Non-Functional Requirements
- [ ] Must respond to /health in <50ms
- [ ] Must not consume >50MB memory
- [ ] Must handle droplet timeouts gracefully (5s max)
- [ ] Must continue operating if individual droplets are unreachable

---

## API Specs

### UDC Endpoints (Required)

```
GET /health
Response: {"status": "healthy", "timestamp": "...", "uptime_seconds": N, "version": "1.0.0"}

GET /capabilities
Response: {"service_name": "supervisor", "droplet_id": 101, "capabilities": [...]}

GET /state
Response: {"status": "active", "monitored_droplets": N, "last_check": "..."}

GET /dependencies
Response: {"required_services": [...], "optional_services": [...]}

POST /message
Request: {"from_service": "...", "message_type": "...", "payload": {...}}
```

### Business Endpoints

```
GET /droplets
Response: List of all monitored droplets and their status

GET /droplets/{name}/history
Response: Health history for specific droplet

POST /droplets/{name}/restart
Response: Manually trigger restart of a droplet

POST /register
Request: {"name": "...", "url": "...", "port": N}
Response: Register a new droplet for monitoring
```

---

## Dependencies

### Required Services
- systemd (for restart commands)

### Optional Services
- alerts (for notifications - degrades gracefully if unavailable)

### External APIs
- None

---

## Success Criteria

- [ ] Can detect unhealthy droplet within 30 seconds
- [ ] Can restart droplet via systemd
- [ ] Continues monitoring if one droplet is down
- [ ] Sends alert when droplet fails
- [ ] Passes all UDC compliance tests
- [ ] Has >80% test coverage

---

## Configuration

```bash
# Environment Variables
SUPERVISOR_PORT=8760
CHECK_INTERVAL_SECONDS=30
RESTART_COOLDOWN_SECONDS=60
MAX_RESTART_ATTEMPTS=3
ALERTS_URL=http://localhost:8765
```

---

## Compliance Notes

- This is an internal infrastructure service
- No user data is processed
- Logs may contain service names and health status








