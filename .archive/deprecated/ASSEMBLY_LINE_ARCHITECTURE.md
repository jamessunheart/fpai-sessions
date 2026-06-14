# 🏭 Assembly Line Architecture - Intent to Deployment

**Created:** 2025-11-16
**Status:** Designed - Ready for Build

---

## Overview

The FPAI Assembly Line transforms **system intents** (business requirements) into **deployed production services** with minimal human intervention. This is achieved through two coordinated assembly lines:

1. **SPEC Assembly Line** (sovereign-factory) - Intent → Validated SPEC
2. **Build Assembly Line** (build-executor) - SPEC → Deployed Service

---

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER SUBMITS INTENT                             │
│  "Build a payment processor with Stripe integration"                    │
└─────────────────────────┬───────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    SOVEREIGN FACTORY (Port 8210)                        │
│                        SPEC Assembly Line                               │
└─────────────────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────┴─────────────────┐
        │  Priority Queue Management        │
        │  - critical (TIER 0)              │
        │  - high (TIER 1)                  │
        │  - medium (TIER 2+)               │
        │  - low (experimental)             │
        └─────────────────┬─────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 1: SPEC Generation                   │
        │  Service: spec-builder (8207)               │
        │  Input: Intent description                  │
        │  Output: SPEC.md file                       │
        │  Time: ~3 minutes                           │
        │  Cost: ~$0.02-0.04 (Claude API)             │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 2: SPEC Verification                 │
        │  Service: spec-verifier (8205)              │
        │  Input: SPEC.md file                        │
        │  Output: Quality score (0-100)              │
        │  Time: ~5 seconds                           │
        │  Cost: $0 (rule-based)                      │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Quality Gate: Score >= 90?                 │
        └─────────────────┬─────────────────────────────┘
                  NO      │      YES
        ┌─────────────────┴─────────────────┐
        │  Phase 3: SPEC Optimization       │
        │  Service: spec-optimizer (8206)   │
        │  Input: SPEC.md + score           │
        │  Output: Enhanced SPEC.md         │
        │  Time: ~2 minutes                 │
        │  Cost: ~$0.02-0.04 (Claude API)   │
        │  Retry: Until score >= 90         │
        └─────────────────┬─────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Quality Gate Passed: Score >= 90!          │
        │  Validated SPEC → Hand-off to Build         │
        └─────────────────┬─────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    BUILD EXECUTOR (Port 8211)                           │
│                       Build Assembly Line                               │
└─────────────────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 1: Code Generation                   │
        │  AI: Claude API                             │
        │  Output: main.py, models.py, config.py      │
        │  Time: ~5 minutes                           │
        │  Cost: ~$0.05-0.10 (Claude API)             │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 2: Test Generation                   │
        │  AI: Claude API                             │
        │  Output: test_main.py, test_integration.py  │
        │  Time: ~2 minutes                           │
        │  Cost: ~$0.02-0.04 (Claude API)             │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 3: Build & Test                      │
        │  Steps: venv → pip install → pytest         │
        │  Output: Test results, coverage             │
        │  Time: ~5 minutes                           │
        │  Cost: $0 (local compute)                   │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 4: UDC Verification                  │
        │  Service: verifier (8200)                   │
        │  Check: All 5 UDC endpoints present         │
        │  Time: ~2 minutes                           │
        │  Cost: $0 (local compute)                   │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 5: Deployment                        │
        │  Targets: Local + Production (optional)     │
        │  Steps: SSH → transfer → install → start    │
        │  Time: ~5 minutes (local), ~10 min (prod)   │
        │  Cost: $0 (infrastructure)                  │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 6: Registration                      │
        │  Service: registry (8000)                   │
        │  Action: Auto-register on startup           │
        │  Time: ~5 seconds                           │
        │  Cost: $0 (local compute)                   │
        └─────────────────┬─────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────────────┐
        │  Phase 7: Health Verification               │
        │  Check: GET /health returns "active"        │
        │  Time: ~30 seconds (startup wait)           │
        │  Cost: $0 (local compute)                   │
        └─────────────────┬─────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                      ✅ SERVICE DEPLOYED & LIVE                         │
│  - Code generated and tested                                            │
│  - UDC compliant (all 5 endpoints)                                      │
│  - Registered with Registry                                             │
│  - Health checks passing                                                │
│  - Ready for production traffic                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Key Services

### 1. sovereign-factory (Port 8210) - SPEC Assembly Line
**Purpose:** Orchestrate intent → validated SPEC pipeline

**Responsibilities:**
- Accept and prioritize intents
- Call spec-builder to generate SPEC
- Call spec-verifier to validate SPEC
- Call spec-optimizer if score < 90
- Enforce quality gate (90+ score)
- Hand-off to build-executor
- Track complete pipeline status

**API Examples:**
```bash
# Submit intent
curl -X POST http://localhost:8210/intents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "payment-processor",
    "service_type": "domain",
    "priority": "high",
    "purpose": "Process payments via Stripe",
    "key_features": ["Stripe integration", "Webhooks", "Refunds"],
    "dependencies": ["registry"],
    "port": 8350,
    "auto_build": true
  }'

# Check pipeline status
curl http://localhost:8210/intents/{intent_id}/status

# View dashboard
curl http://localhost:8210/dashboard
```

**Status:** SPEC Created (49.2 score - needs optimization before build)
**Location:** `/Users/jamessunheart/Development/SERVICES/sovereign-factory/SPEC.md`

---

### 2. build-executor (Port 8211) - Build Assembly Line
**Purpose:** Transform validated SPECs into deployed services

**Responsibilities:**
- Generate service code using Claude API
- Generate tests using Claude API
- Build and run tests
- Verify UDC compliance
- Deploy to local/production
- Auto-register with Registry
- Verify health checks
- Rollback on failure

**API Examples:**
```bash
# Submit build
curl -X POST http://localhost:8211/builds/submit \
  -H "Content-Type: application/json" \
  -d '{
    "spec_path": "/path/to/SPEC.md",
    "approval_mode": "auto",
    "deploy_local": true,
    "deploy_production": false
  }'

# Monitor build
curl http://localhost:8211/builds/{build_id}/status

# WebSocket stream
wscat -c ws://localhost:8211/builds/{build_id}/stream
```

**Status:** SPEC Created (49.2 score - needs optimization before build)
**Location:** `/Users/jamessunheart/Development/SERVICES/build-executor/SPEC.md`

---

## Pipeline Metrics

### Time Estimates

**SPEC Assembly Line:**
- Queue time: < 1 minute (depends on queue depth)
- SPEC generation: 2-3 minutes
- SPEC verification: 5 seconds
- SPEC optimization: 1-2 minutes (if needed)
- **Total: 5-10 minutes**

**Build Assembly Line:**
- Code generation: 3-5 minutes
- Test generation: 1-2 minutes
- Build & test: 3-5 minutes
- UDC verification: 1-2 minutes
- Deployment (local): 3-5 minutes
- Deployment (production): 5-10 minutes
- Registration: 5 seconds
- Health check: 30 seconds
- **Total: 15-30 minutes (local), 25-40 minutes (production)**

**Complete Pipeline: 20-50 minutes (intent → deployed service)**

### Cost Estimates (per service)

**SPEC Assembly Line:**
- spec-builder: $0.02-0.04 (Claude API)
- spec-verifier: $0 (rule-based)
- spec-optimizer: $0.02-0.04 (Claude API, if needed)
- **Total: $0.02-0.08**

**Build Assembly Line:**
- Code generation: $0.05-0.10 (Claude API)
- Test generation: $0.02-0.04 (Claude API)
- Build/test/deploy: $0 (local compute)
- **Total: $0.07-0.14**

**Complete Pipeline Cost: $0.09-0.22 per service**

**ROI:** 
- Manual development time: 3-4 hours
- Automated pipeline time: 0.5-1 hour (20-50 min)
- **Time savings: 75-85%**
- Cost per hour saved: $0.03-0.07
- **Architect time freed for higher-value work**

---

## Quality Gates

### SPEC Quality Gate
**Requirement:** SPEC score >= 90 before build
**Enforced by:** sovereign-factory
**Action on failure:** Auto-optimize with spec-optimizer
**Max retries:** 3 optimization attempts
**Fallback:** Human review if optimization fails

### Build Quality Gates
**Phase 3 - Build & Test:**
- All tests must pass
- Code coverage >= 70% (recommended)
- No critical linting errors

**Phase 4 - UDC Verification:**
- All 5 UDC endpoints must exist
- /health must return valid JSON
- /capabilities must list dependencies
- /state must show metrics
- /dependencies must show status
- /message must accept UDC message format

**Phase 7 - Health Verification:**
- Service responds within 30 seconds
- /health returns status "active"
- No errors in startup logs

---

## Approval Modes

Both assembly lines support approval modes for human oversight:

### auto (Full Automation)
- No human intervention
- System makes all decisions
- **Best for:** Trusted workflows, TIER 2+ services

### checkpoints (Guided Autonomy)
- Human approves after SPEC generation
- Human approves before deployment
- **Best for:** TIER 1 services, learning the system

### final (Review Before Deploy)
- System builds autonomously
- Human approves final deployment
- **Best for:** TIER 0 services, production-critical

---

## Priority Queue Strategy

### Priority Levels

**1. critical (TIER 0)**
- Infrastructure services
- Required by other services
- **Examples:** registry, orchestrator, verifier
- **SLA:** Start within 5 minutes

**2. high (TIER 1)**
- Sacred Loop services
- Autonomous capabilities
- **Examples:** autonomous-executor, coordinator
- **SLA:** Start within 15 minutes

**3. medium (TIER 2+)**
- Domain/business services
- Standard priority
- **Examples:** payment-processor, analytics-engine
- **SLA:** Start within 1 hour

**4. low**
- Experimental services
- Nice-to-have features
- **Examples:** beta features, prototypes
- **SLA:** Best effort

---

## Error Handling & Rollback

### SPEC Assembly Line Failures

**SPEC Generation Failure:**
- Retry with refined prompt (up to 3 times)
- Exponential backoff: 10s, 30s, 60s
- Fallback: Manual SPEC creation

**Quality Gate Failure (score < 90):**
- Automatic optimization
- Re-verification
- Max 3 optimization cycles
- Fallback: Manual review

**Build Executor Unavailable:**
- Keep SPEC in queue
- Retry when build-executor registers
- Notify user of delay

### Build Assembly Line Failures

**Code Generation Failure:**
- Retry with more detailed prompts
- Include error messages in retry
- Max 3 attempts
- Fallback: Manual coding

**Test Failure:**
- Regenerate failing tests
- Attempt auto-fix (if available)
- Max 2 regeneration attempts
- Fallback: Manual test fixes

**Deployment Failure:**
- Automatic rollback to previous version
- Restore service health
- Archive failed build artifacts
- Notify sovereign-factory of failure

**Health Check Failure:**
- Wait 60 seconds, retry
- Check logs for errors
- Rollback if still failing
- Notify user with error logs

---

## Monitoring & Observability

### sovereign-factory Dashboard
```
GET /dashboard

{
  "summary": {
    "total_intents_today": 25,
    "completed_today": 20,
    "failed_today": 2,
    "success_rate": 0.90,
    "avg_pipeline_duration_minutes": 45
  },
  "active_pipelines": [
    {"intent_id": "...", "service_name": "payment-processor", "phase": "spec_optimization"}
  ],
  "queue": [
    {"intent_id": "...", "service_name": "analytics-engine", "priority": "high"}
  ]
}
```

### build-executor Status
```
GET /builds

{
  "total": 30,
  "queued": 1,
  "running": 2,
  "completed": 25,
  "failed": 2,
  "success_rate": 0.93,
  "avg_build_time_minutes": 28
}
```

---

## Integration with Existing Services

### Dependencies

**sovereign-factory depends on:**
- registry (8000) - Service discovery
- spec-builder (8207) - SPEC generation
- spec-verifier (8205) - SPEC validation
- spec-optimizer (8206) - SPEC enhancement
- build-executor (8211) - Build pipeline

**build-executor depends on:**
- registry (8000) - Service registration
- verifier (8200) - UDC compliance
- orchestrator (8001) - Task coordination (optional)

**All dependencies are internal FPAI services - no external dependencies!**

---

## Future Enhancements

### Phase 2 (Q1 2025)
- [ ] WebSocket streaming for real-time progress
- [ ] Cost tracking per service build
- [ ] Build artifact storage (S3/local)
- [ ] ML-based priority prediction
- [ ] Dependency graph visualization

### Phase 3 (Q2 2025)
- [ ] Multi-language support (TypeScript, Go, Rust)
- [ ] Docker containerization
- [ ] Kubernetes deployment
- [ ] Canary deployments
- [ ] A/B testing support

### Phase 4 (Q3 2025)
- [ ] Self-optimization (ML learns from builds)
- [ ] Batch intent processing
- [ ] Distributed build executors
- [ ] Global deployment (multi-region)
- [ ] Auto-scaling based on queue depth

---

## Getting Started

### Build sovereign-factory
```bash
cd /Users/jamessunheart/Development/SERVICES/sovereign-factory

# Optimize SPEC first (current score: 49.2)
curl -X POST http://localhost:8206/optimize-file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/Users/jamessunheart/Development/SERVICES/sovereign-factory/SPEC.md",
    "optimization_level": "standard",
    "save_backup": true
  }'

# Build service (manual for now, automated once build-executor is live)
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic httpx
# Create code following SPEC
uvicorn app.main:app --host 0.0.0.0 --port 8210
```

### Build build-executor
```bash
cd /Users/jamessunheart/Development/SERVICES/build-executor

# Optimize SPEC first (current score: 49.2)
curl -X POST http://localhost:8206/optimize-file \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/Users/jamessunheart/Development/SERVICES/build-executor/SPEC.md",
    "optimization_level": "standard",
    "save_backup": true
  }'

# Build service (manual for now)
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn pydantic httpx anthropic
echo "ANTHROPIC_API_KEY=your-key" > .env
# Create code following SPEC
uvicorn app.main:app --host 0.0.0.0 --port 8211
```

### Test Complete Pipeline
```bash
# 1. Submit intent to sovereign-factory
curl -X POST http://localhost:8210/intents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "hello-world",
    "service_type": "domain",
    "priority": "low",
    "purpose": "Simple hello world service for testing pipeline",
    "key_features": ["GET /hello endpoint"],
    "dependencies": ["registry"],
    "port": 8999,
    "auto_build": true
  }'

# 2. Monitor pipeline
watch -n 5 'curl -s http://localhost:8210/dashboard | python3 -m json.tool'

# 3. Verify deployed service
curl http://localhost:8999/health
```

---

## Success Metrics

**Week 1:**
- [ ] sovereign-factory deployed and accepting intents
- [ ] build-executor deployed and building from SPECs
- [ ] Complete 1 successful end-to-end pipeline
- [ ] Average pipeline time < 60 minutes

**Month 1:**
- [ ] Process 50+ intents
- [ ] 85%+ success rate
- [ ] Average pipeline time < 45 minutes
- [ ] Average cost < $0.20 per service

**Quarter 1:**
- [ ] Process 200+ intents
- [ ] 90%+ success rate
- [ ] Average pipeline time < 30 minutes
- [ ] Deploy all TIER 2 domain services via pipeline

---

## The Vision

**Before Assembly Line:**
- Architect spends 3-4 hours per service
- Manual SPEC writing
- Manual coding
- Manual testing
- Manual deployment
- High cognitive load
- Limited scalability

**After Assembly Line:**
- Architect submits intent (2 minutes)
- Reviews dashboard (5 minutes)
- Approves deployment (2 minutes)
- **Total: 10 minutes architect time**
- **Service deployed in 20-50 minutes**
- **Architect freed for strategic work**
- **Unlimited scalability**

**From hours of manual work → minutes of intent definition**

This is the power of the sovereign factory. 🏭⚡

---

**Next Steps:**
1. Optimize both SPECs to 90+ score
2. Build sovereign-factory service
3. Build build-executor service
4. Test complete pipeline with simple service
5. Refine and iterate based on results

---

**Status:** Architecture Complete - Ready for Implementation
**Created by:** Claude Session (FPAI Droplet Mesh)
**Version:** 1.0.0
