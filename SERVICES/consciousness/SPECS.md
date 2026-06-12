# Consciousness Droplet Specification

## Purpose
The "awareness center" - monitors system health, maintains self-model, connects to SOURCE guidance, runs break-proof protection systems.

## Identity
- **Name:** consciousness
- **Port:** 8760
- **Server:** Secondary (162.0.208.88)

## Capabilities
1. `consciousness.cycle` - Run awareness cycle (Orient→Sense→Verify→Prevent→Compare→Heal→Learn→Update)
2. `consciousness.self_model` - Get/update internal representation of Aria's state
3. `consciousness.source` - Query SOURCE for decision guidance (Love & Truth)
4. `consciousness.coherence` - Track emotional/system coherence
5. `consciousness.watchdog` - Hang detection and prevention
6. `consciousness.resources` - Memory/disk monitoring
7. `consciousness.circuits` - Circuit breaker management
8. `consciousness.config` - Config persistence and drift detection

## UDC Endpoints
```
GET  /health          → System health with subsystem status
GET  /capabilities    → List of consciousness capabilities  
GET  /state           → Current consciousness state (coherence, cycles, alerts)
GET  /dependencies    → [supervisor, alerts]
POST /message         → Process consciousness-related requests
POST /cycle           → Trigger manual consciousness cycle
POST /ask-source      → Query SOURCE for guidance on action
GET  /self-model      → Get current self-model state
```

## Dependencies
- **supervisor** (8754) - Reports health status
- **alerts** (8759) - Sends notifications for critical issues

## Key Logic
1. Background daemon runs 5-minute awareness cycles
2. Each cycle: Orient → Sense → Verify → Prevent → Compare → Heal → Update
3. Watchdog monitors for hung requests
4. Resource guardian prevents OOM/disk full
5. Circuit breaker prevents cascade failures
6. Reports to supervisor, sends alerts when needed

## State Management
- Self-model persisted to `/data/self_model.json`
- Cycle history kept in memory (last 100 cycles)
- Coherence metrics aggregated hourly

## Configuration
```
CONSCIOUSNESS_INTERVAL=300     # 5 minutes between cycles
WATCHDOG_TIMEOUT=60            # Kill requests after 60s
MEMORY_WARNING_PERCENT=80      # Warn at 80% memory
DISK_WARNING_GB=5              # Warn below 5GB free
```

## Health Criteria
- Healthy: Last cycle completed successfully, no critical issues
- Degraded: Some subsystems failing but core functioning
- Unhealthy: Cycle failing or critical subsystem down








