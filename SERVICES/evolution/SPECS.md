# Evolution Droplet Specification

## Purpose
The "self-improver" - learns from issues, proposes improvements, evolves behavior over time.

## Identity
- **Name:** evolution
- **Port:** 8762
- **Server:** Secondary (162.0.208.88)

## Capabilities
1. `evolution.analyze` - Analyze issues for lessons
2. `evolution.propose` - Generate evolution proposals
3. `evolution.apply` - Apply approved evolutions
4. `evolution.history` - Track evolution history
5. `evolution.recommendations` - Get improvement recommendations

## UDC Endpoints
```
GET  /health          → Evolution system health
GET  /capabilities    → List of evolution capabilities
GET  /state           → Evolution stats, pending proposals
GET  /dependencies    → [intelligence, brain, alerts]
POST /message         → Process evolution requests
POST /on_issue        → Learn from a new issue
POST /evolve          → Run evolution cycle
GET  /lessons         → Get learned lessons
GET  /proposals       → Get pending proposals
POST /approve/:id     → Approve a proposal
```

## Dependencies
- **intelligence** (8761) - Receives issue patterns
- **brain** (8756) - AI for proposal generation
- **alerts** (8759) - Sends notifications for high-risk proposals

## Key Logic
1. Receives issue notifications from intelligence
2. Analyzes for patterns and lessons
3. Generates code/config evolution proposals
4. LOW risk: auto-apply
5. HIGH risk: queue for steward approval
6. Tracks what worked, what didn't

## State Management
- SQLite database at `/data/evolution.db`
- Tables: lessons, proposals, applied_evolutions

## Configuration
```
AUTO_APPROVE_LOW_RISK=true      # Auto-apply low-risk evolutions
EVOLUTION_INTERVAL=1800         # 30 minutes between proactive cycles
```

## Risk Levels
- LOW: Config changes, documentation updates
- MEDIUM: Non-critical code changes
- HIGH: Critical path changes, security-related

## Health Criteria
- Healthy: Database accessible, can generate proposals
- Degraded: AI unavailable for proposals
- Unhealthy: Cannot store lessons








