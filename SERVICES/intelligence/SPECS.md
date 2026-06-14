# Intelligence Droplet Specification

## Purpose
The "smart healer" - verifies real functionality, analyzes root causes, remembers fixes, learns patterns.

## Identity
- **Name:** intelligence
- **Port:** 8761
- **Server:** Secondary (162.0.208.88)

## Capabilities
1. `intelligence.verify` - Real verification (not just health endpoints)
2. `intelligence.root_cause` - Analyze WHY something failed
3. `intelligence.remember` - Store/retrieve failure history and fixes
4. `intelligence.heal` - Intelligent healing with verification
5. `intelligence.patterns` - Detect patterns in failures
6. `intelligence.meta_learn` - Learn to learn better

## UDC Endpoints
```
GET  /health          → Intelligence system health
GET  /capabilities    → List of intelligence capabilities
GET  /state           → Learning stats, pattern count, success rate
GET  /dependencies    → [consciousness, alerts]
POST /message         → Process intelligence requests
POST /verify          → Run real verification on a capability
POST /heal            → Attempt intelligent healing
POST /analyze         → Root cause analysis
GET  /stats           → Get healing and learning statistics
```

## Dependencies
- **consciousness** (8760) - Receives issues from consciousness cycle
- **alerts** (8759) - Sends critical alerts

## Key Logic
1. Receives issues from consciousness or direct requests
2. Runs REAL verification (not just `/health`)
3. Analyzes root cause using history and patterns
4. Attempts fix from memory or generates new
5. Verifies fix worked
6. Records outcome for learning

## State Management
- SQLite database at `/data/intelligence.db`
- Tables: failures, fixes, patterns, learnings

## Configuration
```
ALERT_THRESHOLD=5           # Consecutive failures before alert
ALERT_COOLDOWN=43200        # 12 hours between alerts for same service
STARTUP_GRACE_PERIOD=600    # 10 minutes after restart
```

## Health Criteria
- Healthy: Database accessible, healing functional
- Degraded: Database issues but in-memory working
- Unhealthy: Cannot heal or verify








