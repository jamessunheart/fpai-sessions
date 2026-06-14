# Proactive Monitor Service

## Purpose
Actively monitors critical services and metrics, sending signals to Chief of Staff when issues are detected.

## What It Monitors

### 1. Service Health
- fp-index (8550) - Main service
- alerts (8766) - Notification system
- chief-of-staff (8107) - Intelligence layer
- credits-gateway (8765) - Revenue
- whaletrack-magnet (8600) - Trading

### 2. Key Metrics
- Service uptime/availability
- Response time (detect slowness)
- Error rates (if exposed)
- Revenue metrics (if available)

### 3. System Health
- Disk space (alert if >90% full)
- Memory usage (alert if >90%)
- CPU load (alert if sustained high load)

## How It Works

```
Every 5 minutes:
  1. Check each service health endpoint
  2. Compare current state vs previous state
  3. Detect anomalies (service down, slow response, errors)
  4. Send signal to Chief of Staff
  5. Chief of Staff filters and routes
  6. You get alert if urgent
```

## Signal Examples

**Service Down:**
```json
{
  "source": "proactive-monitor",
  "type": "error",
  "title": "fp-index service is down",
  "description": "Health check failed - service not responding",
  "data": {
    "service": "fp-index",
    "port": 8550,
    "error": "Connection refused",
    "last_seen": "2026-04-30 19:35:00"
  }
}
```

**Slow Response:**
```json
{
  "source": "proactive-monitor",
  "type": "metric",
  "title": "credits-gateway responding slowly",
  "description": "Response time increased 300% in last hour",
  "data": {
    "service": "credits-gateway",
    "current_response_time": 2.5,
    "normal_response_time": 0.5,
    "increase_pct": 300
  }
}
```

## Configuration

- **Check Interval:** 5 minutes
- **Timeout:** 10 seconds per health check
- **Alerting:** Via Chief of Staff
- **Retention:** Last 24 hours of checks
