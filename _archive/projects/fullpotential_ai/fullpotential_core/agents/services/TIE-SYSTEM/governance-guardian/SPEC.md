# governance-guardian

**TIE Governance Control Monitoring & Circuit Breaker**

**Port:** 8926
**Status:** SPEC COMPLETE → BUILD PHASE
**Version:** 1.0.0

---

## Purpose

**Monitors holder control percentage and prevents system instability.**

Core responsibilities:
- Monitor voting-weight-tracker for holder control %
- Enforce >51% holder control requirement
- Implement circuit breakers at critical thresholds
- Alert on governance violations
- Pause system if control drops below 51% (emergency failsafe)
- Provide audit log of all governance events

---

## Monitoring Strategy

### Polling Intervals:
- **Every 30 seconds:** Check governance status from voting-weight-tracker
- **On alert:** Increase to every 5 seconds
- **Emergency:** Continuous monitoring (1 second)

### Threshold Levels:
```
>70%  - Excellent (Green)   ✅ Normal operations
60-70% - Good (Green)       ✅ Normal operations
55-60% - Acceptable (Green) ✅ Normal operations
51-55% - Caution (Yellow)   ⚠️  Increased monitoring
49-51% - Warning (Orange)   ⚠️  Alert & prepare pause
<49%  - Critical (Red)      🚨 PAUSE SYSTEM
```

### Circuit Breaker Actions:

**55% Threshold (Yellow Alert):**
- Log warning
- Increase monitoring frequency (30s → 5s)
- Send notification to admin
- Continue normal operations

**52% Threshold (Orange Warning):**
- Log urgent warning
- Increase monitoring to 1 second
- Send urgent notification
- Prepare pause mechanism
- Continue normal operations (but watch closely)

**51% Threshold (Red Critical):**
- **PAUSE REDEMPTIONS** - Stop new redemptions
- Alert all administrators
- Log emergency event
- Allow deposits only
- Require manual review to resume

**49% Threshold (Emergency):**
- **PAUSE ENTIRE SYSTEM** - Stop all operations
- Emergency alert to all admins
- Require governance vote to resume
- Forensic audit required

---

## API Endpoints

### 1. Get Guardian Status
```bash
GET /guardian/status

Returns:
{
  "monitoring_active": true,
  "last_check": "2025-11-16T10:00:00Z",
  "check_interval_seconds": 30,
  "current_holder_control": 70.5,
  "governance_level": "excellent",
  "system_status": "operational",
  "paused": false,
  "alerts_active": 0
}
```

### 2. Get Current Governance Metrics
```bash
GET /guardian/governance

Returns:
{
  "holder_control_percentage": 70.5,
  "total_votes": 1000,
  "holder_votes": 705,
  "seller_votes": 295,
  "threshold_level": "excellent",
  "margin_above_critical": 19.5,
  "is_stable": true,
  "last_updated": "2025-11-16T10:00:00Z"
}
```

### 3. Get Alert History
```bash
GET /guardian/alerts?limit=20

Returns:
{
  "alerts": [
    {
      "id": 1,
      "timestamp": "2025-11-16T09:30:00Z",
      "alert_type": "caution",
      "holder_control": 54.2,
      "message": "Holder control dropped below 55%",
      "action_taken": "increased_monitoring",
      "resolved": true,
      "resolved_at": "2025-11-16T09:45:00Z"
    }
  ]
}
```

### 4. Get Governance Events (Audit Log)
```bash
GET /guardian/events?limit=50

Returns:
{
  "events": [
    {
      "timestamp": "2025-11-16T10:00:00Z",
      "event_type": "governance_check",
      "holder_control": 70.5,
      "threshold_level": "excellent",
      "action": "none"
    },
    {
      "timestamp": "2025-11-16T09:55:00Z",
      "event_type": "threshold_crossed",
      "holder_control": 55.1,
      "threshold_level": "acceptable",
      "action": "cleared_caution_alert"
    }
  ]
}
```

### 5. Pause System (Admin Only)
```bash
POST /guardian/pause
{
  "reason": "Manual intervention required",
  "authorization": "admin_signature"
}

Returns:
{
  "paused": true,
  "paused_at": "2025-11-16T10:00:00Z",
  "reason": "Manual intervention required",
  "resume_requires": "admin_approval"
}
```

### 6. Resume System (Admin Only)
```bash
POST /guardian/resume
{
  "authorization": "admin_signature",
  "governance_verified": true
}

Returns:
{
  "paused": false,
  "resumed_at": "2025-11-16T10:05:00Z",
  "current_holder_control": 70.5,
  "safe_to_resume": true
}
```

### 7. Get System Rules
```bash
GET /guardian/rules

Returns:
{
  "critical_threshold": 51.0,
  "caution_threshold": 55.0,
  "warning_threshold": 52.0,
  "pause_redemptions_at": 51.0,
  "pause_system_at": 49.0,
  "monitoring_interval_normal": 30,
  "monitoring_interval_caution": 5,
  "monitoring_interval_critical": 1
}
```

### 8. Health Check
```bash
GET /health

Returns:
{
  "status": "healthy",
  "monitoring_active": true,
  "voting_tracker_connected": true,
  "database": "connected",
  "last_governance_check": "2025-11-16T10:00:00Z",
  "seconds_since_last_check": 5
}
```

---

## Data Models

### GuardianStatus (Runtime State)
```python
{
  "monitoring_active": true,
  "last_check": "2025-11-16T10:00:00Z",
  "check_interval_seconds": 30,
  "current_holder_control": 70.5,
  "governance_level": "excellent",  # excellent|good|acceptable|caution|warning|critical
  "system_status": "operational",   # operational|redemptions_paused|fully_paused
  "paused": false,
  "alerts_active": 0
}
```

### GovernanceAlert (Database)
```python
{
  "id": 1,
  "timestamp": "2025-11-16T09:30:00Z",
  "alert_type": "caution",  # caution|warning|critical|emergency
  "holder_control": 54.2,
  "message": "Holder control dropped below 55%",
  "action_taken": "increased_monitoring",
  "resolved": true,
  "resolved_at": "2025-11-16T09:45:00Z"
}
```

### GovernanceEvent (Database - Audit Log)
```python
{
  "id": 1,
  "timestamp": "2025-11-16T10:00:00Z",
  "event_type": "governance_check",  # governance_check|threshold_crossed|pause|resume
  "holder_control": 70.5,
  "threshold_level": "excellent",
  "action": "none",  # none|alert|pause|resume
  "details": "Routine governance check"
}
```

### SystemPause (Database)
```python
{
  "id": 1,
  "paused_at": "2025-11-16T10:00:00Z",
  "resumed_at": null,
  "pause_reason": "Holder control below 51%",
  "pause_type": "automatic",  # automatic|manual
  "holder_control_at_pause": 50.8,
  "resumed_by": null,
  "resume_reason": null
}
```

---

## Monitoring Loop (Background Task)

### Main Monitoring Task:
```python
async def monitor_governance():
    while True:
        try:
            # 1. Fetch governance status from voting-weight-tracker
            governance = await fetch_governance_status()

            # 2. Determine threshold level
            level = determine_threshold_level(governance.holder_control_percentage)

            # 3. Log governance check event
            await log_governance_event(governance, level)

            # 4. Check for threshold violations
            if governance.holder_control_percentage < 51.0:
                await handle_critical_threshold(governance)
            elif governance.holder_control_percentage < 52.0:
                await handle_warning_threshold(governance)
            elif governance.holder_control_percentage < 55.0:
                await handle_caution_threshold(governance)
            else:
                await clear_alerts_if_safe(governance)

            # 5. Adjust monitoring interval based on level
            interval = get_monitoring_interval(level)

            # 6. Wait for next check
            await asyncio.sleep(interval)

        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            await asyncio.sleep(30)  # Retry in 30 seconds
```

---

## Integration Flow

### Normal Operations:
```
governance-guardian (every 30 seconds)
  ↓
GET voting-weight-tracker /voting/governance
  ↓
governance-guardian:
  1. Check holder_control_percentage
  2. Verify > 51%
  3. Log governance check event
  4. Continue monitoring
```

### Caution Threshold (55%):
```
governance-guardian (detects holder_control < 55%)
  ↓
governance-guardian:
  1. Create caution alert
  2. Increase monitoring to 5 seconds
  3. Send notification to admin
  4. Log threshold_crossed event
  5. Continue normal operations
```

### Critical Threshold (51%):
```
governance-guardian (detects holder_control < 51%)
  ↓
governance-guardian:
  1. Create critical alert
  2. PAUSE REDEMPTIONS (call redemption-algorithm)
  3. Send urgent notifications
  4. Increase monitoring to 1 second
  5. Log pause event
  6. Require manual review to resume
```

### Resume Operations:
```
Admin (verifies governance restored)
  ↓
POST /guardian/resume
  ↓
governance-guardian:
  1. Verify current holder_control > 51%
  2. Resume redemptions
  3. Log resume event
  4. Clear alerts
  5. Return to normal monitoring
```

---

## Circuit Breaker Integration

### Services to Pause on Critical Threshold:

**Immediate pause (holder_control < 51%):**
- redemption-algorithm - Stop new redemptions
- Allow deposits to continue (helps restore holder control)

**Full pause (holder_control < 49%):**
- redemption-algorithm - Stop redemptions
- sol-treasury-core - Stop withdrawals
- Allow deposits only

---

## Database Schema

### Table: governance_alerts
```sql
CREATE TABLE governance_alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    alert_type VARCHAR(20) NOT NULL,
    holder_control DECIMAL(5,2) NOT NULL,
    message TEXT NOT NULL,
    action_taken VARCHAR(50) NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMP
);

CREATE INDEX idx_alert_timestamp ON governance_alerts(timestamp DESC);
CREATE INDEX idx_alert_resolved ON governance_alerts(resolved);
```

### Table: governance_events
```sql
CREATE TABLE governance_events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    event_type VARCHAR(30) NOT NULL,
    holder_control DECIMAL(5,2) NOT NULL,
    threshold_level VARCHAR(20) NOT NULL,
    action VARCHAR(50) NOT NULL,
    details TEXT
);

CREATE INDEX idx_event_timestamp ON governance_events(timestamp DESC);
CREATE INDEX idx_event_type ON governance_events(event_type);
```

### Table: system_pauses
```sql
CREATE TABLE system_pauses (
    id SERIAL PRIMARY KEY,
    paused_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resumed_at TIMESTAMP,
    pause_reason TEXT NOT NULL,
    pause_type VARCHAR(20) NOT NULL,
    holder_control_at_pause DECIMAL(5,2) NOT NULL,
    resumed_by VARCHAR(100),
    resume_reason TEXT
);

CREATE INDEX idx_pause_timestamp ON system_pauses(paused_at DESC);
```

---

## Alert Notification Channels

### Notification Methods:
1. **Slack/Discord Webhook** - Real-time alerts
2. **Email** - Critical alerts to admins
3. **Dashboard** - Visual indicators
4. **Audit Log** - Permanent record

### Alert Message Template:
```
🚨 TIE GOVERNANCE ALERT

Level: {alert_type}
Holder Control: {holder_control}%
Threshold: {threshold}%
Action Taken: {action}

Timestamp: {timestamp}
System Status: {system_status}
```

---

## Testing Requirements

### Unit Tests:
- Threshold level determination
- Alert creation logic
- Pause/resume mechanism
- Monitoring interval adjustment

### Integration Tests:
- Fetch governance status from voting-weight-tracker
- Pause redemption-algorithm on critical threshold
- Alert notification delivery
- Database audit log

### Scenario Tests:
- Gradual decline from 70% → 51% → 49%
- Rapid drop below critical threshold
- Recovery from pause state
- Multiple threshold crossings

---

## Configuration

### Environment Variables:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/tie_governance

# Service
SERVICE_PORT=8926

# Integration
VOTING_TRACKER_URL=http://localhost:8922
REDEMPTION_ALGORITHM_URL=http://localhost:8923
TREASURY_CORE_URL=http://localhost:8920

# Monitoring
MONITORING_INTERVAL_NORMAL=30      # seconds
MONITORING_INTERVAL_CAUTION=5      # seconds
MONITORING_INTERVAL_CRITICAL=1     # seconds

# Thresholds
CRITICAL_THRESHOLD=51.0
WARNING_THRESHOLD=52.0
CAUTION_THRESHOLD=55.0

# Alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
ADMIN_EMAIL=admin@fullpotential.com
```

---

## Next Steps

After governance-guardian:
1. Integration testing (all 4 core services together)
2. Load testing (simulate governance stress scenarios)
3. Build redemption-algorithm (Port 8923)

---

**Status:** ✅ **SPEC COMPLETE** - Ready for BUILD Phase

**Session #12 - Autonomous Build** 🏗️⚡💎
