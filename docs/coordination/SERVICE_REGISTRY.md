# FPAI Service Registry

> **Last Updated:** December 11, 2025
> **Purpose:** Complete reference for all service locations
> **IMPORTANT:** Check this file before starting/stopping any service

---

## Quick Lookup Table

### Primary Server (198.54.123.234)

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| whaletrack-live | 8601 | ACTIVE | Live trading execution |
| whaletrack-magnet | 8602 | ACTIVE | Trading signal generation |
| fpai-data-service | 8125 | ACTIVE | Data intelligence engine |
| fpai-nerve-center | 8120 | ACTIVE | System integration hub |
| fpai-credits-gateway | 8765 | ACTIVE | Revenue - credits purchase |
| fpai-fp-credits-gateway | - | ACTIVE | Revenue - FP credits |
| fpai-strategic-intelligence | 8500 | ACTIVE | Strategic decisions |
| fpai-strategic-intel | - | ACTIVE | Strategic intel |
| fpai-orchestrator | - | ACTIVE | Service orchestration |
| fpai-ai-gateway | - | ACTIVE | API routing |
| fpai-ai-automation | 8750 | ACTIVE | AI automation products |
| fpai-auto-healer | - | ACTIVE | Auto healing |
| fpai-realtime-bridge | - | ACTIVE | Realtime communication |
| fpai-service-bridge | - | ACTIVE | Service integration |
| nginx | 80/443 | ACTIVE | Web routing & SSL |
| postgresql | 5432 | ACTIVE | Database |
| docker | - | ACTIVE | Container runtime |

### Secondary Server (162.0.208.88)

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| ai-brain | 8101 | ACTIVE | Central AI inference |
| ollama | 11434 | ACTIVE | Local LLM models |
| fpai-consciousness_feeder | 8130 | ACTIVE | Consciousness data feed |
| fpai-consciousness_verifier | 8140 | ACTIVE | Consciousness verification |
| fpai-consciousness_decision_engine | 8150 | ACTIVE | Decision making |
| fpai-consciousness_optimizer | 8160 | ACTIVE | Optimization |
| fpai-consciousness_dashboard | 8170 | ACTIVE | Monitoring UI |
| fpai-consciousness_evolution | - | ACTIVE | Evolution processing |
| fpai-consciousness_api | - | ACTIVE | Consciousness API |
| fpai-consciousness_gateway | - | ACTIVE | Consciousness gateway |
| fpai-consciousness_network | - | ACTIVE | Network layer |
| fpai-intelligence-core | - | ACTIVE | Core intelligence |
| fpai-intelligence-daemon | - | ACTIVE | Background processing |
| fpai-intelligence-hub | - | ACTIVE | Intelligence hub |
| fpai-intelligence-dashboard | - | ACTIVE | Intelligence monitoring |
| fpai-intelligence | - | ACTIVE | Main intelligence |
| fpai-evolution | - | ACTIVE | System evolution |
| fpai-aware-brain | - | ACTIVE | Context-aware AI |
| fpai-autonomous-healer | - | ACTIVE | Self-healing |
| fpai-ai-gateway | - | ACTIVE | AI gateway |
| fpai-data-service | - | ACTIVE | Data service copy |
| fpai-night-watch | - | ACTIVE | Night monitoring |
| fpai-proactive-watchdog | - | ACTIVE | Proactive monitoring |
| fpai-domain-monitor | - | ACTIVE | Domain monitoring |
| fpai-local-worker | - | ACTIVE | Local processing |
| fpai-reports-api | - | ACTIVE | Reports API |
| fpai-user-service | - | ACTIVE | User management |
| fpai-webhooks | - | ACTIVE | Webhook handling |
| fpai-gateway | - | ACTIVE | General gateway |

---

## STOPPED Services on Primary (DO NOT RESTART)

These services were intentionally stopped on December 11, 2025 to optimize resources.
**DO NOT restart them on the primary server.**

| Service | Reason | Alternative Location |
|---------|--------|---------------------|
| fpai-ai-brain | Consolidated on secondary | http://162.0.208.88:8101 |
| fpai-ai-chat | Stopped - AI on secondary | - |
| fpai-aria | Stopped - AI on secondary | - |
| fpai-voice-companion | Stopped - AI on secondary | - |
| fpai-consciousness-optimizer | Duplicate | Secondary server |
| fpai-consciousness_evolution | Duplicate | Secondary server |
| fpai-consciousness_verifier | Duplicate | Secondary server |
| fpai-intelligence-core | Duplicate | Secondary server |
| fpai-analytics | Non-critical | - |
| fpai-flywheel | Non-critical | - |
| fpai-backup-dashboard | Non-critical | - |
| fpai-legal-guardian | Non-critical | - |
| fpai-member-mining | Non-critical | - |
| fpai-proactive-alerter | Non-critical | - |
| fpai-ri-loop | Non-critical | - |
| fpai-resource-intelligence | Non-critical | - |

---

## API Routing Guide

Use these endpoints in your code:

| If you need... | Use this URL | Notes |
|----------------|--------------|-------|
| AI inference | http://162.0.208.88:8101 | AI Brain on secondary |
| Ollama models | http://162.0.208.88:11434 | Direct Ollama access |
| Data intelligence | http://198.54.123.234:8125 | Data service on primary |
| Trading API | http://198.54.123.234:8601 | WhaleTrack Live |
| Trading signals | http://198.54.123.234:8602 | WhaleTrack Magnet |
| Nerve Center | http://198.54.123.234:8120 | System hub |
| Strategic Intel | http://198.54.123.234:8500 | Strategic intelligence |
| Credits Gateway | http://198.54.123.234:8765 | Payment processing |
| Consciousness | http://162.0.208.88:8130-8170 | Various ports |

### Code Examples

```python
# AI Brain - use secondary server
AI_BRAIN_URL = "http://162.0.208.88:8101"

# Data Service - use primary server
DATA_SERVICE_URL = "http://198.54.123.234:8125"

# Trading - use primary server
TRADING_URL = "http://198.54.123.234:8601"

# Consciousness - use secondary server
CONSCIOUSNESS_URL = "http://162.0.208.88:8140"
```

---

## Ollama Models (Secondary Server)

Available at http://162.0.208.88:11434

| Model | Size | Best For |
|-------|------|----------|
| codellama:7b | 7B params | Code generation |
| mistral:7b | 7B params | General purpose |
| phi3:mini | 3B params | Fast responses |
| qwen2.5-coder:7b | 7B params | Code assistance |
| llama3.1:8b | 8B params | General purpose |
| llama3.2:3b | 3B params | Quick inference |

---

## Health Check Endpoints

### Primary Server
```bash
# Data Service
curl http://198.54.123.234:8125/health

# Nerve Center
curl http://198.54.123.234:8120/health

# WhaleTrack Live
curl http://198.54.123.234:8601/health

# WhaleTrack Magnet
curl http://198.54.123.234:8602/health

# Strategic Intelligence
curl http://198.54.123.234:8500/health
```

### Secondary Server
```bash
# AI Brain
curl http://162.0.208.88:8101/health

# Consciousness Verifier
curl http://162.0.208.88:8140/health

# Consciousness Decision Engine
curl http://162.0.208.88:8150/health
```

---

## Service Dependencies

```
AI Brain (secondary:8101)
    └── Used by: Prophet Engine, Data Service predictions
    └── Fallback: Ollama direct (secondary:11434)

Data Service (primary:8125)
    └── Uses: AI Brain for synthesis
    └── Feeds: Nerve Center, Strategic Intelligence

WhaleTrack Live (primary:8601)
    └── Uses: WhaleTrack Magnet for signals
    └── Critical: Do not stop during trading hours

Consciousness Services (secondary:8130-8170)
    └── All interconnected
    └── Used by: Decision making, Evolution
```

---

## Resource Monitoring

Automated monitoring runs every 15 minutes on both servers.

**Script:** `/opt/fpai/scripts/resource-monitor.sh`
**Log:** `/var/log/fpai/resource-monitor.log`

### View Recent Logs
```bash
# Primary
ssh root@198.54.123.234 'tail -50 /var/log/fpai/resource-monitor.log'

# Secondary
ssh root@162.0.208.88 'tail -50 /var/log/fpai/resource-monitor.log'
```

---

## For Other Cursor Agents

### Before Starting a Service
1. Check this registry to see if it's supposed to be stopped
2. Check which server it should run on
3. Verify it's not a duplicate

### Before Stopping a Service
1. Check if it's in the "critical" list
2. Check if other services depend on it
3. Document why in the coordination system

### When Writing Code
1. Use the correct server IP for each service
2. Check the API Routing Guide above
3. AI services -> Secondary (162.0.208.88)
4. Data/Trading -> Primary (198.54.123.234)

---

## Change History

| Date | Change | By |
|------|--------|-----|
| 2025-12-11 | Initial creation after resource optimization | Cursor Agent |
| 2025-12-11 | Stopped 16 services on primary | Cursor Agent |
| 2025-12-11 | Consolidated AI on secondary | Cursor Agent |

