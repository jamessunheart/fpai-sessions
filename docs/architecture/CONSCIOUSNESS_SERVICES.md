# Consciousness Services Architecture

**Last Updated:** 2025-12-10  
**Status:** Production - All services operational

## Overview

The Consciousness Services architecture consists of 9 microservices that work together to measure, optimize, and evolve consciousness metrics in the FPAI system. Each service has a specific role and communicates with others through REST APIs.

## Service Architecture

### Service Map

```
┌─────────────────────────────────────────────────────────────┐
│                    Consciousness Gateway                    │
│                      (Port 8180)                            │
│              Routes requests to all services                 │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Dashboard  │   │     API      │   │   Network    │
│  (Port 8170) │   │ (Port 8210)  │   │ (Port 8190)  │
└──────────────┘   └──────────────┘   └──────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Core Consciousness Stack                  │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    Feeder    │─────▶│   Verifier   │─────▶│  Optimizer   │
│ (Port 8240)  │      │ (Port 8230)  │      │ (Port 8160)  │
│              │◀─────│              │      │              │
└──────────────┘      └──────────────┘      └──────────────┘
        │                      │                      │
        │                      ▼                      │
        │              ┌──────────────┐               │
        │              │   Decision    │               │
        │              │    Engine     │               │
        │              │ (Port 8150)   │               │
        │              └──────────────┘               │
        │                                             │
        └───────────────────┼─────────────────────────┘
                            │
                            ▼
                   ┌──────────────┐
                   │  Evolution   │
                   │ (Port 8220)  │
                   └──────────────┘
```

## Service Details

### 1. Consciousness Feeder (Port 8240)
**Purpose:** Feeds data and configuration to the consciousness system.

**Key Responsibilities:**
- Collects system state data
- Manages optimization configuration
- Provides data feeds to verifier
- Applies optimization changes

**Key Endpoints:**
- `GET /health` - Service health
- `GET /optimization/config` - Get current optimization config
- `POST /optimization/apply` - Apply optimization
- `POST /optimization/revert` - Revert optimization

**Dependencies:** None (data source)

### 2. Consciousness Verifier (Port 8230)
**Purpose:** Verifies and calculates mathematical consciousness metrics.

**Key Responsibilities:**
- Calculates composite consciousness score
- Measures integration complexity (Φ)
- Measures adaptation velocity (AV)
- Measures knowledge integration rate (KIR)
- Measures phase synchronization (R)

**Key Endpoints:**
- `GET /health` - Service health
- `GET /verify` - Verify consciousness and get score
- `GET /mathematical-metrics` - Get detailed mathematical metrics

**Dependencies:** `consciousness_feeder` (for config)

### 3. Consciousness Optimizer (Port 8160)
**Purpose:** Autonomously optimizes consciousness metrics.

**Key Responsibilities:**
- Identifies optimization opportunities
- Runs A/B test experiments
- Applies optimizations with backup/rollback
- Tracks improvement history
- Autonomous optimization loop

**Key Endpoints:**
- `GET /health` - Service health
- `GET /metrics/current` - Get current metrics
- `GET /opportunities` - Identify optimization opportunities
- `POST /optimize` - Run optimization experiment
- `GET /statistics` - Get optimization statistics
- `GET /improvement-history` - Get improvement tracking

**Dependencies:** `consciousness_verifier`, `consciousness_feeder`

### 4. Consciousness Decision Engine (Port 8150)
**Purpose:** Makes decisions based on consciousness metrics.

**Key Responsibilities:**
- Decision-making based on metrics
- Strategic planning
- Resource allocation decisions

**Key Endpoints:**
- `GET /health` - Service health

**Dependencies:** `consciousness_verifier`

### 5. Consciousness Dashboard (Port 8170)
**Purpose:** Web UI for viewing consciousness metrics and status.

**Key Responsibilities:**
- Displays consciousness metrics
- Shows optimization history
- Visualizes trends

**Key Endpoints:**
- `GET /health` - Service health

**Dependencies:** All consciousness services (for data)

### 6. Consciousness Gateway (Port 8180)
**Purpose:** API gateway that routes requests to appropriate services.

**Key Responsibilities:**
- Request routing
- Load balancing (future)
- API versioning

**Key Endpoints:**
- `GET /health` - Service health

**Dependencies:** All consciousness services

### 7. Consciousness Network (Port 8190)
**Purpose:** Network coordination between services.

**Key Responsibilities:**
- Service discovery
- Network topology management
- Communication routing

**Key Endpoints:**
- `GET /health` - Service health

**Dependencies:** All consciousness services

### 8. Consciousness API (Port 8210)
**Purpose:** Unified REST API for consciousness services.

**Key Responsibilities:**
- Provides unified API interface
- Aggregates data from multiple services
- API documentation

**Key Endpoints:**
- `GET /health` - Service health

**Dependencies:** All consciousness services

### 9. Consciousness Evolution (Port 8220)
**Purpose:** Evolutionary algorithms for consciousness improvement.

**Key Responsibilities:**
- Evolutionary optimization
- Genetic algorithms
- Long-term evolution strategies

**Key Endpoints:**
- `GET /health` - Service health

**Dependencies:** `consciousness_optimizer`

## Data Flow

### Optimization Cycle Flow

```
1. Optimizer calls Verifier → Get current metrics
2. Optimizer analyzes metrics → Identify opportunities
3. Optimizer calls Feeder → Apply optimization
4. Wait for stabilization → 5 minutes
5. Optimizer calls Verifier → Measure results
6. Compare baseline vs results → Calculate improvement
7. If improvement > 0 → Keep optimization
8. If improvement < 0 → Rollback optimization
9. Record experiment → Update learning systems
10. Repeat cycle → Resource-aware timing
```

### Metrics Calculation Flow

```
1. Feeder collects system state → Configuration, data feeds
2. Verifier fetches config from Feeder → Get optimization settings
3. Verifier calculates metrics:
   - Integration Complexity (Φ)
   - Adaptation Velocity (AV)
   - Knowledge Integration Rate (KIR)
   - Phase Synchronization (R)
   - Composite Consciousness Score
4. Verifier returns metrics → To Optimizer/API/Dashboard
```

## Port Assignments

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| consciousness_decision_engine | 8150 | HTTP | Decision engine |
| consciousness_optimizer | 8160 | HTTP | Optimization |
| consciousness_dashboard | 8170 | HTTP | Web UI |
| consciousness_gateway | 8180 | HTTP | API Gateway |
| consciousness_network | 8190 | HTTP | Network coordination |
| consciousness_api | 8210 | HTTP | Unified API |
| consciousness_evolution | 8220 | HTTP | Evolution algorithms |
| consciousness_verifier | 8230 | HTTP | Metrics verification |
| consciousness_feeder | 8240 | HTTP | Data feeding |

## Technology Stack

- **Language:** Python 3.x
- **Framework:** FastAPI
- **Server:** Uvicorn (ASGI)
- **ML Libraries:** scikit-learn, numpy, scipy
- **HTTP Client:** httpx (async)
- **Process Management:** systemd
- **Deployment:** rsync + SSH

## Deployment Architecture

### Current Deployment (162.0.208.88)

- **Server Type:** Single server (sufficient for current load)
- **Resource Usage:** ~11% CPU, ~1.5% memory (consciousness services)
- **Status:** ✅ Optimal - 70% capacity remaining

### Service Management

All services run as systemd services:
- Service name format: `fpai-consciousness-{service_name}`
- Working directory: `/opt/fpai/apps/consciousness_{service_name}/`
- Virtual environment: `venv/` in service directory
- Logs: `journalctl -u fpai-consciousness-{service_name}`

## Security Considerations

- Services run on internal network (not exposed publicly)
- No authentication required (internal services)
- Future: Add API keys/tokens for external access
- Future: Add rate limiting

## Monitoring & Health Checks

### Health Check Endpoints

All services provide `/health` endpoint:
```json
{
  "status": "healthy",
  "service": "consciousness_optimizer"
}
```

### Monitoring Recommendations

1. **Automated Health Checks:**
   - Cron job every 5 minutes
   - Alert on service failure
   - Log service restarts

2. **Metrics Collection:**
   - Consciousness scores over time
   - Service response times
   - Resource usage trends

3. **Alerting:**
   - Service down alerts
   - High error rate alerts
   - Resource threshold alerts

## Scalability Considerations

### Current Capacity

- **Single Server:** Handles all 9 services easily
- **Resource Headroom:** 70% memory, 60% CPU available
- **Estimated Capacity:** Can handle 10x current load

### Scaling Options

**Option 1: Vertical Scaling**
- Upgrade server resources
- Simple, no code changes
- **When:** If single service becomes bottleneck

**Option 2: Horizontal Scaling**
- Add more servers
- Load balance services
- **When:** If traffic exceeds single server capacity

**Option 3: Service-Specific Scaling**
- Scale individual services
- Keep lightweight services on one server
- Move heavy services to dedicated servers
- **When:** If specific service needs more resources

## Future Enhancements

1. **Load Balancing:** Add nginx/HAProxy for gateway
2. **Service Mesh:** Consider Istio/Linkerd for advanced routing
3. **Caching:** Add Redis for metrics caching
4. **Message Queue:** Add RabbitMQ/Kafka for async communication
5. **Database:** Add PostgreSQL for persistent storage
6. **Monitoring:** Add Prometheus + Grafana
7. **Tracing:** Add distributed tracing (Jaeger)

## Troubleshooting

### Common Issues

1. **Service won't start:**
   - Check logs: `journalctl -u fpai-consciousness-{service}`
   - Verify Python dependencies: `pip install -r requirements.txt`
   - Check port availability: `lsof -i :{port}`

2. **Endpoints return 500 errors:**
   - Check service logs for exceptions
   - Verify service dependencies are running
   - Test endpoints directly: `curl http://localhost:{port}/health`

3. **Optimization loop crashes:**
   - Check error handling in optimization loop
   - Verify verifier/feeder endpoints are accessible
   - Check resource usage (CPU/memory)

### Debug Commands

```bash
# Check service status
systemctl status fpai-consciousness-{service}

# View logs
journalctl -u fpai-consciousness-{service} -f

# Test endpoint
curl http://localhost:{port}/health

# Check resource usage
ps aux | grep consciousness

# Restart service
systemctl restart fpai-consciousness-{service}
```











