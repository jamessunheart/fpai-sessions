# Unified Intelligence Architecture

## THE VISION

One God Mode dashboard. All services self-register. All builders self-coordinate. You observe, direct, and the system executes.

---

## CURRENT INFRASTRUCTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUR INFRASTRUCTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  NAMECHEAP #1 (198.54.123.234) - Main Services                  │
│  ├─ Registry (8000)                                             │
│  ├─ Dashboard (8002)                                            │
│  ├─ Landing Page (8005)                                         │
│  ├─ Jobs (8008)                                                 │
│  ├─ I-Match (8401)                                              │
│  ├─ UC Credits (8765)                                           │
│  ├─ God Mode Dashboard                                          │
│  └─ 30+ other services                                          │
│                                                                 │
│  NAMECHEAP #2 (162.0.208.88) - AI Brain / Hive                  │
│  ├─ Thinking System                                             │
│  ├─ Task API (8114)                                             │
│  ├─ Build Queue (SQLite)                                        │
│  ├─ Scaling Governor                                            │
│  ├─ Cost Optimizer                                              │
│  ├─ Observatory Dashboard (8113)                                │
│  └─ Local Ollama (backup builder)                               │
│                                                                 │
│  NAMECHEAP #3 (209.74.93.72) - Secondary                        │
│  └─ [Available - cPanel access]                                 │
│                                                                 │
│  GPU FLEET (Multi-Provider)                                     │
│  ├─ RunPod: 2x A40 ($0.60/hr combined)                          │
│  ├─ Vast.ai: 1x RTX 5090 ($0.81/hr)                             │
│  └─ Vultr: [Available for scaling]                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## TARGET STATE

```
                         ┌─────────────────────────┐
                         │      GOD MODE           │
                         │  fullpotential.ai/god   │
                         │                         │
                         │  • All services visible │
                         │  • All builders visible │
                         │  • Build queue UI       │
                         │  • Treasury/costs       │
                         │  • One-click actions    │
                         └───────────┬─────────────┘
                                     │
                                     ▼
                         ┌─────────────────────────┐
                         │      HIVE BRAIN         │
                         │    (162.0.208.88)       │
                         │                         │
                         │  • Service Registry     │
                         │  • Build Queue          │
                         │  • Scaling Governor     │
                         │  • Event Bus            │
                         └───────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │  SMART SERVICES │    │  GPU BUILDERS   │    │  OTHER SERVERS  │
    │  (198.54.123.234)│    │  (RunPod/Vast)  │    │  (209.74.93.72) │
    │                 │    │                 │    │                 │
    │  Auto-register  │    │  Poll for tasks │    │  Auto-register  │
    │  Send heartbeats│    │  Build code     │    │  Send heartbeats│
    │  Report metrics │    │  Report results │    │  Report metrics │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

---

## SMART SERVICE PROTOCOL

Every service becomes "smart" by implementing this simple protocol:

### 1. Registration (on startup)
```python
POST http://162.0.208.88:8114/api/services/register
{
    "name": "i-match",
    "host": "198.54.123.234",
    "port": 8401,
    "health_endpoint": "/health",
    "capabilities": ["matching", "recommendations"],
    "version": "1.0.0"
}
```

### 2. Heartbeat (every 30 seconds)
```python
POST http://162.0.208.88:8114/api/services/heartbeat
{
    "name": "i-match",
    "status": "healthy",
    "uptime_seconds": 3600,
    "metrics": {
        "requests_per_min": 42,
        "avg_latency_ms": 120,
        "error_rate": 0.01,
        "memory_mb": 256
    }
}
```

### 3. Build Request (when service needs improvement)
```python
POST http://162.0.208.88:8114/api/tasks/queue
{
    "title": "Add caching to I-Match",
    "request": "Implement Redis caching for match results...",
    "priority": 2,
    "requester": "i-match",
    "target_service": "i-match"
}
```

---

## SMART SERVICE SDK

Simple Python package that any service can use:

```python
# Install: pip install fpai-sdk

from fpai_sdk import SmartService

class MyService(SmartService):
    name = "my-service"
    port = 8500
    capabilities = ["feature1", "feature2"]
    
    def health(self):
        return {"status": "healthy", "version": "1.0.0"}

# That's it! Service auto-registers and sends heartbeats
```

---

## GOD MODE UPGRADE

The God Mode dashboard will show:

### Panel 1: Service Fleet
```
┌─────────────────────────────────────────────────────────────┐
│  SERVICES                                      42/45 online │
├─────────────────────────────────────────────────────────────┤
│  🟢 registry        198.54.123.234:8000    12ms   healthy   │
│  🟢 i-match         198.54.123.234:8401    45ms   healthy   │
│  🟢 uc-credits      198.54.123.234:8765    23ms   healthy   │
│  🟡 orchestrator    198.54.123.234:8001    --     starting  │
│  🔴 spec-optimizer  198.54.123.234:8206    --     offline   │
└─────────────────────────────────────────────────────────────┘
```

### Panel 2: Builder Fleet
```
┌─────────────────────────────────────────────────────────────┐
│  BUILDERS                                       3/3 active  │
├─────────────────────────────────────────────────────────────┤
│  🟢 runpod-a40-1    A40      $0.40/hr    building...        │
│  🟢 runpod-a40-2    A40      $0.20/hr    idle               │
│  🟡 vastai-5090     RTX5090  $0.81/hr    starting           │
├─────────────────────────────────────────────────────────────┤
│  Total: $1.41/hr | $1,030/mo | [+ Add Builder]              │
└─────────────────────────────────────────────────────────────┘
```

### Panel 3: Build Queue
```
┌─────────────────────────────────────────────────────────────┐
│  BUILD QUEUE                              3 pending, 1 active│
├─────────────────────────────────────────────────────────────┤
│  🔨 [REVENUE] Billing Integration         building  2m ago  │
│  ⏳ [REVENUE] Landing Page                pending   queued  │
│  ⏳ [SELF] Optimize I-Match caching       pending   queued  │
├─────────────────────────────────────────────────────────────┤
│  [+ New Build Task]                                         │
└─────────────────────────────────────────────────────────────┘
```

### Panel 4: Quick Actions
```
┌─────────────────────────────────────────────────────────────┐
│  QUICK ACTIONS                                              │
├─────────────────────────────────────────────────────────────┤
│  [📝 New Build]  [🚀 Scale Up]  [💰 Costs]  [📊 Metrics]    │
└─────────────────────────────────────────────────────────────┘
```

---

## YOUR NEW WORKFLOW

### Before (Now)
1. Open Cursor window #1 for service A
2. Prompt Claude to build something
3. Open Cursor window #2 for service B
4. Prompt again
5. SSH to server to check status
6. Open God Mode to see dashboard
7. Repeat for each thing you want...

### After (Target)
1. Open God Mode dashboard
2. See everything at a glance
3. Click [+ New Build] → type what you want
4. Watch it build in real-time
5. See it auto-deploy
6. Done.

**Or even simpler:**
- Voice/chat to God Mode: "Make the landing page faster"
- System queues the task
- Builders build it
- Tests pass
- Auto-deploys
- You see the result

---

## IMPLEMENTATION PHASES

### Phase 1: Unified API (Today)
- [x] Task API exists (8114)
- [ ] Add /api/services/register endpoint
- [ ] Add /api/services/heartbeat endpoint
- [ ] Add /api/services/list endpoint

### Phase 2: Smart Service SDK (Day 2)
- [ ] Create fpai-sdk Python package
- [ ] Auto-registration on import
- [ ] Background heartbeat thread
- [ ] Build request helper

### Phase 3: God Mode Upgrade (Day 3)
- [ ] Add service discovery panel
- [ ] Add GPU fleet panel
- [ ] Add build queue panel with UI
- [ ] Add "New Build" button
- [ ] WebSocket for real-time updates

### Phase 4: Service Migration (Week 1)
- [ ] Add SDK to registry service
- [ ] Add SDK to i-match
- [ ] Add SDK to uc-credits
- [ ] Continue for all services...

### Phase 5: Self-Improvement Loop (Ongoing)
- [ ] Services request their own improvements
- [ ] System prioritizes by revenue impact
- [ ] Builders build, test, deploy
- [ ] Continuous optimization

---

## THE END STATE

```
YOU ──────► GOD MODE ──────► HIVE BRAIN ──────► EVERYTHING
   observe     command        coordinate        execute

"I want users to sign up faster"
        ↓
    God Mode understands intent
        ↓
    Breaks into tasks
        ↓
    Builders execute
        ↓
    Tests verify
        ↓
    Auto-deploys
        ↓
    You see metrics improve

No Cursor windows. No SSH. No manual prompts.
Just observe and direct.
```

---

## COST SUMMARY

| Component | Current Cost | Notes |
|-----------|-------------|-------|
| Namecheap #1 | ~$50/mo | Main services |
| Namecheap #2 | ~$100/mo | AI Brain |
| Namecheap #3 | ~$50/mo | Secondary |
| GPU Fleet | ~$1,000/mo | 3 GPUs running |
| **Total Infra** | **~$1,200/mo** | |

**Target:** Generate >$1,200/mo revenue to cover infrastructure, then scale.

---

*Created: 2025-12-02*
*Status: PLANNING → IMPLEMENTATION*






















