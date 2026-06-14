# FPAI Service Inventory

Last Updated: December 23, 2025

## Server Allocation Guide

### PRIMARY SERVER (198.54.123.234) - 8GB RAM
**Purpose:** Web, Trading, Public Services  
**Memory Budget:** Keep under 6GB used

#### ✅ Active (Required)
| Service | Description | Memory |
|---------|-------------|--------|
| nginx | Web server | ~50MB |
| godmode | Control dashboard | ~100MB |
| whaletrack-live | Live trading | ~150MB |
| whaletrack-magnet | Trading signals | ~150MB |
| whaletrack-bridge-btc | BTC price bridge | ~50MB |
| whaletrack-bridge-eth | ETH price bridge | ~50MB |
| whaletrack-bridge-sol | SOL price bridge | ~50MB |
| fpai-credits-gateway | Payments API | ~100MB |
| fpai-nerve-center | Integration hub | ~100MB |
| memory-watchdog | Memory protection | ~10MB |
| fail2ban | Security | ~20MB |

#### ⏸️ Disabled (Available if needed)
| Service | Description | Memory | Notes |
|---------|-------------|--------|-------|
| dashboard | Legacy dashboard | ~100MB | Use godmode instead |
| revenue-api | Revenue API | ~100MB | Experimental |
| email-relay | Email routing | ~100MB | Not in production |
| api-portal | API hub | ~150MB | Not active |

---

### SECONDARY SERVER (162.0.208.88) - 32GB RAM
**Purpose:** AI, Intelligence, Processing  
**Memory Budget:** ~22GB available

#### ✅ Active
| Service | Description | Memory |
|---------|-------------|--------|
| aria-command | Main Aria brain | ~200MB |
| aria-builder | Code building | ~150MB |
| aria-memory | Memory evolution | ~100MB |
| aria-proactive | Proactive alerts | ~100MB |
| aria-watchdog | Server monitoring | ~50MB |
| ollama | Local LLM | ~4GB |
| ai-brain | AI routing | ~200MB |
| fpai-ai-gateway | AI access point | ~100MB |
| fpai-aware-brain | Context-aware AI | ~150MB |
| fpai-consciousness-coordinator | Central nervous system | ~200MB |
| fpai-consciousness_api | Consciousness API | ~100MB |
| fpai-consciousness_dashboard | Consciousness UI | ~100MB |
| fpai-consciousness_decision_engine | Decision making | ~150MB |
| fpai-consciousness_evolution | Evolution system | ~100MB |
| fpai-consciousness_feeder | Data feeding | ~100MB |
| fpai-consciousness_gateway | Consciousness gateway | ~100MB |
| fpai-consciousness_network | Network layer | ~100MB |
| fpai-consciousness_verifier | Verification | ~100MB |
| fpai-data-service | Data collection | ~150MB |
| fpai-sparket-engine | Sparket AI | ~200MB |

#### ⏸️ Available to Activate
| Service | Description | Memory | To Activate |
|---------|-------------|--------|-------------|
| revenue-intelligence | Revenue optimization | ~200MB | `/activate revenue-intelligence` |
| revenue-oracle | Revenue predictions | ~150MB | `/activate revenue-oracle` |
| brick2-autopilot | Marketing automation | ~200MB | `/activate brick2-autopilot` |
| brick2-web | Marketing web UI | ~100MB | `/activate brick2-web` |
| music-maestro | AI music production | ~500MB | `/activate music-maestro` |
| mydreamspace | Dream platform | ~200MB | `/activate mydreamspace` |
| i-match | Matching engine | ~200MB | `/activate i-match` |
| lead-scraper | Lead generation | ~150MB | `/activate lead-scraper` |
| church-treasury | Church finances | ~100MB | `/activate church-treasury` |
| 2x-treasury | SOL investments | ~100MB | `/activate 2x-treasury` |

---

## Telegram Commands

```
/inventory      - Show all available services
/services       - Show running services
/activate <svc> - Turn on a service
/deactivate <svc> - Turn off a service
/restart <svc>  - Restart a service
/logs <svc>     - View service logs
/memory         - Check memory status
/servers        - Full health check
```

## Manual Activation (SSH)

```bash
# On Secondary (recommended):
ssh root@162.0.208.88
systemctl enable <service-name>
systemctl start <service-name>
systemctl status <service-name>

# On Primary (only if necessary):
ssh root@198.54.123.234
systemctl enable <service-name>
systemctl start <service-name>
```

## Guidelines

1. **Primary (8GB)**: Only web/trading services. Never run AI services here.
2. **Secondary (32GB)**: All AI/intelligence services. Has 22GB+ available.
3. **Before activating**: Check `/memory` to ensure enough RAM.
4. **After activating**: Use `/logs <service>` to verify it started correctly.

## Service Categories

### 🎯 Critical (Never Disable)
- nginx, godmode, whaletrack-*, fpai-credits-gateway, aria-command, ollama

### 🧠 AI/Intelligence (Secondary Only)
- All consciousness-*, ai-*, aria-*, ollama

### 💰 Revenue (Experimental)
- revenue-*, 2x-treasury, brick2-*

### 📧 Communication (Not Production)
- email-relay, cortex-mail, communication-hub

### 🎨 Creative (Experimental)
- music-maestro, mydreamspace, i-match


