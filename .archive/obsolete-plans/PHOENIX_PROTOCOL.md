# 🔥 PHOENIX PROTOCOL - High Availability & Failover

**Version:** 1.0.0
**Status:** Design Complete
**Purpose:** Ensure zero-downtime operation with automatic failover

---

## 🎯 Core Principle

**"If one dies, two rise with double the power"**

Every critical service runs as:
- **1 Primary Instance** (active, handling requests)
- **2 Phoenix Instances** (standby, 2x capacity ready to activate)

When primary fails → Both Phoenix instances activate → System runs at 2x capacity → New Phoenix instances spawn

---

## 🏗️ Architecture

### Service Instance Tiers

```
┌─────────────────────────────────────────────────────────────┐
│ PRIMARY INSTANCE                                             │
│ ├─ Port: 8XXX (base port)                                   │
│ ├─ Status: active                                            │
│ ├─ Load: 100% capacity                                       │
│ └─ Heartbeat: Every 5s → Registry                           │
└─────────────────────────────────────────────────────────────┘
                    │
                    │ (heartbeat failure detected)
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ PHOENIX INSTANCE #1                                          │
│ ├─ Port: 8XX1 (base + 1000)                                 │
│ ├─ Status: standby → active                                 │
│ ├─ Capacity: 150% (2x power)                                │
│ └─ Activation: < 2 seconds                                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ PHOENIX INSTANCE #2                                          │
│ ├─ Port: 8XX2 (base + 2000)                                 │
│ ├─ Status: standby → active                                 │
│ ├─ Capacity: 150% (2x power)                                │
│ └─ Activation: < 2 seconds                                  │
└─────────────────────────────────────────────────────────────┘
                    │
                    │ (both Phoenix active)
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ AUTO-SPAWN NEW PHOENIX INSTANCES                            │
│ ├─ Spawn 2 new Phoenix instances                            │
│ ├─ Restore 3-instance architecture                          │
│ └─ System back to normal in < 30s                           │
└─────────────────────────────────────────────────────────────┘
```

### Port Allocation Strategy

```
Service: intent-queue
├─ Primary:   8212 (base)
├─ Phoenix 1: 9212 (base + 1000)
└─ Phoenix 2: 10212 (base + 2000)

Service: governance
├─ Primary:   8213 (base)
├─ Phoenix 1: 9213 (base + 1000)
└─ Phoenix 2: 10213 (base + 2000)

Service: sovereign-factory
├─ Primary:   8210 (base)
├─ Phoenix 1: 9210 (base + 1000)
└─ Phoenix 2: 10210 (base + 2000)
```

---

## 🔍 Health Monitoring

### Heartbeat System

**Primary Instance:**
```python
async def send_heartbeat():
    while True:
        await registry.heartbeat({
            "service_id": f"{service_name}-primary",
            "instance_id": instance_id,
            "port": primary_port,
            "status": "active",
            "load": current_load_percentage,
            "tier": "primary"
        })
        await asyncio.sleep(5)  # Every 5 seconds
```

**Phoenix Instance:**
```python
async def monitor_primary():
    while status == "standby":
        primary_health = await registry.check_health(f"{service_name}-primary")

        if primary_health["status"] == "dead":
            # PRIMARY DEAD - ACTIVATE PHOENIX
            await activate_phoenix()
            await notify_other_phoenix()
            await spawn_replacement_phoenix()

        await asyncio.sleep(2)  # Check every 2 seconds
```

### Failure Detection

**Registry monitors:**
- Heartbeat missed for 15 seconds → Mark as `degraded`
- Heartbeat missed for 30 seconds → Mark as `dead`
- HTTP health endpoint timeout → Immediate `degraded`
- 3 consecutive health check failures → `dead`

---

## ⚡ Failover Process

### Step-by-Step Activation

```
T+0s:  Primary instance crashes
T+2s:  Registry detects missed heartbeat
T+5s:  Phoenix instances detect primary dead
T+7s:  Phoenix #1 activates (becomes primary)
T+7s:  Phoenix #2 activates (becomes primary)
T+10s: Registry updates routing → Phoenix instances
T+15s: Both Phoenix instances serving traffic at 2x capacity
T+20s: Auto-spawn begins for new Phoenix instances
T+50s: New Phoenix instances online and in standby
T+60s: System fully restored to 3-instance architecture
```

**Total Downtime: 10 seconds** (2s detection + 5s decision + 3s activation)

---

## 🚀 2x Power Strategy

### Why Phoenix Has 2x Capacity

**Option 1: More Resources**
```yaml
Primary Instance:
  cpu: 1 core
  memory: 512MB
  max_requests: 100/s

Phoenix Instance:
  cpu: 2 cores         # 2x CPU
  memory: 1024MB       # 2x memory
  max_requests: 200/s  # 2x throughput
```

**Option 2: Multiple Processes**
```python
# Primary: 1 uvicorn worker
uvicorn app.main:app --workers 1

# Phoenix: 2 uvicorn workers
uvicorn app.main:app --workers 2
```

**Option 3: Optimized Configuration**
```python
# Phoenix instances run with aggressive optimization
PHOENIX_CONFIG = {
    "workers": 2,
    "worker_class": "uvicorn.workers.UvicornWorker",
    "max_requests": 200,
    "max_requests_jitter": 50,
    "preload_app": True,  # Faster startup
    "timeout": 30
}
```

---

## 🔄 Auto-Spawn Mechanism

### When Phoenix Activates → Spawn New Phoenix

```python
async def on_phoenix_activation():
    """When Phoenix activates, spawn replacement Phoenix instances"""

    print("🔥 PHOENIX ACTIVATED!")
    print("📡 Spawning replacement Phoenix instances...")

    # Spawn 2 new Phoenix instances
    for i in range(2):
        phoenix_id = f"phoenix-{uuid4()}"
        phoenix_port = await registry.allocate_phoenix_port(service_name)

        # Launch new Phoenix instance
        await spawn_instance({
            "service_name": service_name,
            "instance_id": phoenix_id,
            "port": phoenix_port,
            "tier": "phoenix",
            "mode": "standby",
            "capacity": "2x"
        })

    print("✅ New Phoenix instances spawned")
    print("🏛️ 3-instance architecture restored")
```

---

## 📊 Instance States

```python
class InstanceState(Enum):
    SPAWNING = "spawning"       # Being created
    STANDBY = "standby"         # Ready but inactive
    WARMING = "warming"         # Preparing to activate
    ACTIVE = "active"           # Serving traffic
    DEGRADED = "degraded"       # Unhealthy but alive
    DEAD = "dead"               # Not responding
    DRAINING = "draining"       # Shutting down gracefully
```

### State Transitions

```
spawning → standby → warming → active
                        ↓
                    degraded → dead
                        ↑
                    (recovery)
                        ↓
                      active
```

---

## 🎛️ Registry Enhancements

### Service Instance Registry

```python
class ServiceInstance(BaseModel):
    instance_id: str
    service_name: str
    port: int
    tier: str  # primary, phoenix
    status: str  # spawning, standby, active, degraded, dead
    capacity: str  # 1x, 2x
    last_heartbeat: datetime
    activated_at: Optional[datetime]
    requests_served: int
    uptime_seconds: int

class PhoenixProtocol(BaseModel):
    service_name: str
    primary_instance: Optional[ServiceInstance]
    phoenix_instances: List[ServiceInstance]
    total_capacity: str  # e.g. "300%" (1x + 2x + 2x)
    failover_count: int
    last_failover: Optional[datetime]
```

### Registry API Endpoints

```python
GET /phoenix/status/{service_name}
# Returns: primary status, phoenix statuses, failover history

POST /phoenix/trigger-failover/{service_name}
# Manual failover trigger for testing

GET /phoenix/metrics
# Total failovers, avg failover time, uptime %
```

---

## 🧪 Testing Strategy

### Chaos Testing

```bash
# Kill primary instance
curl -X POST http://localhost:8000/phoenix/kill-primary/intent-queue

# Verify Phoenix activation
curl http://localhost:8000/phoenix/status/intent-queue

# Expected:
# - Phoenix #1: active (serving traffic)
# - Phoenix #2: active (serving traffic)
# - New Phoenix #3: spawning
# - New Phoenix #4: spawning
```

### Automated Tests

```python
async def test_phoenix_failover():
    # 1. Verify 3 instances running
    assert len(await registry.get_instances("intent-queue")) == 3

    # 2. Kill primary
    await kill_instance("intent-queue-primary")

    # 3. Wait for failover
    await asyncio.sleep(15)

    # 4. Verify Phoenix activated
    instances = await registry.get_instances("intent-queue")
    active_count = len([i for i in instances if i.status == "active"])
    assert active_count == 2  # Both Phoenix active

    # 5. Verify new Phoenix spawning
    spawning_count = len([i for i in instances if i.status == "spawning"])
    assert spawning_count == 2  # New Phoenix being created

    # 6. Test service still responsive
    response = await test_client.get("/health")
    assert response.status_code == 200
```

---

## 🚦 Load Balancing Strategy

### Round-Robin with Health Checks

```python
class PhoenixLoadBalancer:
    def get_healthy_instance(self, service_name: str):
        instances = registry.get_instances(service_name)

        # Filter to active instances only
        active = [i for i in instances if i.status == "active"]

        if not active:
            raise ServiceUnavailable(f"No active instances for {service_name}")

        # Round-robin across active instances
        instance = active[self.round_robin_index % len(active)]
        self.round_robin_index += 1

        return instance
```

### Sticky Sessions (Optional)

```python
# For stateful services, route same client to same instance
def get_instance_for_client(client_id: str, service_name: str):
    hash_value = hashlib.md5(client_id.encode()).hexdigest()
    instance_index = int(hash_value, 16) % len(active_instances)
    return active_instances[instance_index]
```

---

## 📈 Metrics & Monitoring

### Phoenix Protocol Metrics

```python
{
  "service_name": "intent-queue",
  "phoenix_metrics": {
    "total_failovers": 5,
    "avg_failover_time_seconds": 8.2,
    "uptime_percentage": 99.97,
    "time_with_degraded_capacity": "2m 15s",
    "phoenix_activations": [
      {
        "timestamp": "2025-11-16T02:30:00Z",
        "reason": "primary_heartbeat_timeout",
        "recovery_time_seconds": 7.5,
        "phoenix_activated": ["phoenix-1", "phoenix-2"]
      }
    ]
  }
}
```

---

## 🎯 Implementation Phases

### Phase 1: Registry Phoenix Support (Week 1)
- [ ] Add instance tier tracking (primary/phoenix)
- [ ] Implement heartbeat monitoring
- [ ] Add failure detection logic
- [ ] Create failover trigger endpoints

### Phase 2: Service Phoenix Integration (Week 2)
- [ ] Add Phoenix mode to all TIER 0 services
- [ ] Implement standby → active transition
- [ ] Add auto-spawn on activation
- [ ] Test failover scenarios

### Phase 3: Load Balancing (Week 3)
- [ ] Build Phoenix-aware load balancer
- [ ] Implement health-check routing
- [ ] Add sticky session support
- [ ] Performance testing

### Phase 4: Monitoring & Dashboards (Week 4)
- [ ] Phoenix status dashboard
- [ ] Failover alerting
- [ ] Metrics collection
- [ ] Chaos testing automation

---

## 💰 Cost Analysis

### Resource Requirements

**Without Phoenix Protocol:**
```
5 TIER 0 services × 1 instance = 5 instances
Cost: ~$25/month (DigitalOcean)
Downtime on failure: Minutes to hours
```

**With Phoenix Protocol:**
```
5 TIER 0 services × 3 instances = 15 instances
Cost: ~$75/month (DigitalOcean)
Downtime on failure: < 10 seconds
Value: 99.97% uptime guarantee
```

**ROI:**
- Additional cost: $50/month
- Prevented downtime: ~99% reduction
- Revenue protection: Priceless for production systems

---

## 🔐 Security Considerations

### Phoenix Instance Authentication

```python
# Phoenix instances share secret token with Registry
PHOENIX_TOKEN = os.getenv("PHOENIX_SECRET_TOKEN")

async def activate_phoenix():
    await registry.activate_phoenix(
        service_name=service_name,
        instance_id=instance_id,
        token=PHOENIX_TOKEN  # Prevents unauthorized activation
    )
```

### Rate Limiting

```python
# Prevent failover spam (malicious or accidental)
MAX_FAILOVERS_PER_HOUR = 10

if failover_count_last_hour >= MAX_FAILOVERS_PER_HOUR:
    await alert_admin("Excessive failovers detected!")
    raise TooManyFailovers()
```

---

## 🎉 Benefits

1. **Zero Downtime:** Service continues during failures
2. **2x Surge Capacity:** Handle traffic spikes during recovery
3. **Self-Healing:** Automatic recovery without human intervention
4. **Production Ready:** Enterprise-grade reliability
5. **Cost Effective:** 3x redundancy for critical services only

---

## 🚀 Quick Start

### Launch Service with Phoenix Protocol

```bash
# Start service with Phoenix protocol enabled
python3 phoenix-launcher.py \
  --service intent-queue \
  --primary-port 8212 \
  --phoenix-count 2 \
  --phoenix-capacity 2x \
  --auto-spawn true
```

### Expected Output

```
🔥 PHOENIX PROTOCOL ACTIVATED
📡 Service: intent-queue
🎯 Primary Instance: 8212 (ACTIVE)
🔥 Phoenix Instance #1: 9212 (STANDBY, 2x capacity)
🔥 Phoenix Instance #2: 10212 (STANDBY, 2x capacity)
✅ All instances healthy
🛡️ High availability enabled
```

---

**The Phoenix rises from the ashes. The system never dies.** 🔥🔥🔥
