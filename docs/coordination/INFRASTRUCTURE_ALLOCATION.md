# FPAI Infrastructure Allocation

> **Last Updated:** December 11, 2025
> **Status:** Resource Optimization Complete

## Architecture Overview

```
                        GPU FLEET (RunPod - Future)
                         70 GPUs / 24GB VRAM each
                                   |
                                   | API Calls
                                   v
+------------------------------------------------------------------+
|              SECONDARY SERVER (162.0.208.88)                      |
|                   31GB RAM | 12 CPUs | 26GB FREE                  |
|                                                                   |
|   AI BRAIN (8101) ──────── Central Intelligence Hub               |
|   OLLAMA (11434) ────────── 6 LLM Models Loaded                   |
|   CONSCIOUSNESS ─────────── Feeder, Verifier, Decision Engine     |
|   INTELLIGENCE ──────────── Daemon, Hub, Evolution                |
|                                                                   |
|   Role: AI Inference, Consciousness, Heavy Processing             |
+------------------------------------------------------------------+
                                   |
                                   | Internal API
                                   v
+------------------------------------------------------------------+
|               PRIMARY SERVER (198.54.123.234)                     |
|                    7.7GB RAM | 8 CPUs | Optimized                 |
|                                                                   |
|   NGINX ────────────────── Web Routing & SSL                      |
|   WHALETRACK LIVE (8601) ─ Live Trading                           |
|   WHALETRACK MAGNET (8602) Trading Signals                        |
|   DATA SERVICE (8125) ──── Data Intelligence                      |
|   NERVE CENTER (8120) ──── System Hub                             |
|   CREDITS GATEWAY (8765) ─ Revenue                                |
|                                                                   |
|   Role: Web Traffic, Trading, Revenue, Data                       |
+------------------------------------------------------------------+
```

---

## Service Allocation (December 11, 2025)

### PRIMARY SERVER (198.54.123.234)

#### Active Critical Services
| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| whaletrack-live | 8601 | Active | Live trading execution |
| whaletrack-magnet | 8602 | Active | Trading signal generation |
| fpai-data-service | 8125 | Active | Data intelligence engine |
| fpai-nerve-center | 8120 | Active | System integration hub |
| fpai-credits-gateway | 8765 | Active | Revenue processing |
| fpai-strategic-intelligence | 8500 | Active | Strategic decisions |
| fpai-orchestrator | - | Active | Service orchestration |
| fpai-ai-gateway | - | Active | API routing |
| nginx | 80/443 | Active | Web routing |
| postgresql | 5432 | Active | Database |
| docker | - | Active | Container runtime |

#### Stopped Services (DO NOT RESTART ON PRIMARY)
| Service | Reason | Alternative |
|---------|--------|-------------|
| fpai-ai-brain | Migrated | Use secondary:8101 |
| fpai-ai-chat | Stopped | - |
| fpai-aria | Stopped | - |
| fpai-voice-companion | Stopped | - |
| fpai-consciousness-optimizer | Duplicate | Use secondary |
| fpai-consciousness_evolution | Duplicate | Use secondary |
| fpai-consciousness_verifier | Duplicate | Use secondary |
| fpai-intelligence-core | Duplicate | Use secondary |
| fpai-analytics | Stopped | - |
| fpai-flywheel | Stopped | - |
| fpai-backup-dashboard | Stopped | - |
| fpai-legal-guardian | Stopped | - |
| fpai-member-mining | Stopped | - |
| fpai-proactive-alerter | Stopped | - |
| fpai-ri-loop | Stopped | - |
| fpai-resource-intelligence | Stopped | - |

---

### SECONDARY SERVER (162.0.208.88)

#### AI & Intelligence Services
| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| ai-brain | 8101 | Active | Central AI inference |
| ollama | 11434 | Active | Local LLM inference |
| fpai-aware-brain | - | Active | Context-aware AI |
| fpai-autonomous-healer | - | Active | Self-healing |

#### Consciousness Services
| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| fpai-consciousness_feeder | 8130 | Active | Data feeding |
| fpai-consciousness_verifier | 8140 | Active | Verification |
| fpai-consciousness_decision_engine | 8150 | Active | Decisions |
| fpai-consciousness_optimizer | 8160 | Active | Optimization |
| fpai-consciousness_dashboard | 8170 | Active | Monitoring UI |
| fpai-consciousness_evolution | - | Active | Evolution |
| fpai-consciousness_api | - | Active | API |
| fpai-consciousness_gateway | - | Active | Gateway |
| fpai-consciousness_network | - | Active | Network |

#### Intelligence Services
| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| fpai-intelligence-core | - | Active | Core intelligence |
| fpai-intelligence-daemon | - | Active | Background processing |
| fpai-intelligence-hub | - | Active | Intelligence hub |
| fpai-intelligence-dashboard | - | Active | Monitoring |
| fpai-evolution | - | Active | System evolution |

#### Ollama Models Available
| Model | Size | Use Case |
|-------|------|----------|
| codellama:7b | 7B | Code generation |
| mistral:7b | 7B | General purpose |
| phi3:mini | 3B | Fast inference |
| qwen2.5-coder:7b | 7B | Code assistance |
| llama3.1:8b | 8B | General purpose |
| llama3.2:3b | 3B | Fast inference |

---

## Resource Status

### Primary Server
| Metric | Before (Dec 11) | After (Dec 11) | Change |
|--------|-----------------|----------------|--------|
| RAM Used | 6.2GB / 7.7GB | 6.0GB / 7.7GB | -3% |
| Swap | 59% | 49% | -10% |
| FPAI Services | 28 | 12 | -57% |
| Total Services | 105 | 88 | -16% |

### Secondary Server
| Metric | Value | Status |
|--------|-------|--------|
| RAM Used | 4.5GB / 31GB | 14% |
| RAM Free | 26GB | Available |
| FPAI Services | 29 | Active |
| CPU Load | 1.68 | Low |

---

## API Routing Guide

| Need | Endpoint | Server |
|------|----------|--------|
| AI Inference | http://162.0.208.88:8101 | Secondary |
| Ollama Direct | http://162.0.208.88:11434 | Secondary |
| Data Service | http://198.54.123.234:8125 | Primary |
| Trading | http://198.54.123.234:8601 | Primary |
| Nerve Center | http://198.54.123.234:8120 | Primary |
| Credits | http://198.54.123.234:8765 | Primary |

---

## Automated Monitoring

Both servers have automated resource monitoring:

**Script:** `/opt/fpai/scripts/resource-monitor.sh`
**Frequency:** Every 15 minutes
**Log:** `/var/log/fpai/resource-monitor.log`

### Auto-Actions
- Clear cache if RAM > 85%
- Restart critical services if down
- Log all resource checks

### Thresholds
| Metric | Alert Threshold |
|--------|----------------|
| RAM | 85% |
| Swap | 70% |
| CPU Load | 7.0 |

---

## Access Methods

### Primary Server
```bash
# Standard SSH
ssh root@198.54.123.234

# Backup port (if 22 blocked)
ssh -p 2222 root@198.54.123.234

# Tailscale (always works)
ssh root@100.122.184.66

# Web console
https://198.54.123.234:9090
```

### Secondary Server
```bash
# Standard SSH
ssh root@162.0.208.88
```

---

## Emergency Procedures

### If Primary Overloaded
```bash
# 1. Connect via Tailscale
ssh root@100.122.184.66

# 2. Clear caches
sync && echo 3 > /proc/sys/vm/drop_caches

# 3. Check resource monitor log
tail -50 /var/log/fpai/resource-monitor.log
```

### If AI Brain Unreachable
```bash
# Check on secondary
ssh root@162.0.208.88
systemctl status ai-brain

# Restart if needed
systemctl restart ai-brain
```

---

## Change Log

### December 11, 2025 - Resource Optimization
- Stopped 16 non-critical services on primary
- Consolidated AI services on secondary
- Consolidated consciousness services on secondary
- Installed automated resource monitoring
- Reduced primary RAM usage from 80% to 78%
- Reduced swap usage from 59% to 49%
