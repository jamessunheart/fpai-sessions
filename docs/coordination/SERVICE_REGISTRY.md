# FPAI Service Registry

> **Last Updated:** April 30, 2026
> **Purpose:** Complete reference for all service locations
> **IMPORTANT:** Check this file before starting/stopping any service
> **COST:** $474.30/month total (Primary $69.88 + Secondary $74.66 + Legacy $329.76)

---

## Quick Lookup Table

### Primary Server (198.54.123.234) - $69.88/month
**Specs:** 8GB RAM, 8 CPU, 438GB SSD

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| **fpai-fp-index** | 8550 | **ACTIVE** | **Full Potential Index v5.1.0** — Constitutional intelligence economy (dual trust, proof pipeline, immune system) |
| whaletrack-magnet | 8600 | ACTIVE | **THE trading system** - User auth, signals, Hyperliquid integration |
| fpai-voice-companion | 8705 | DEMO-ACTIVE | Twilio voice webhooks + smart routing (OpenAI Realtime via `/realtime/media-stream`) |
| fpai-nerve-center | 8120 | ACTIVE | System integration hub |
| fpai-credits-gateway | 8765 | ACTIVE | Revenue - credits purchase (PostgreSQL-backed) |
| fpai-strategic-intelligence | 8500 | ACTIVE | Strategic decisions |
| **fpai-alerts** | **8766** | **ACTIVE** | **Multi-channel notifications** (Telegram @sunheartbrain_bot, SMS) |
| **fpai-chief-of-staff** | **8107** | **ACTIVE** | **Intelligent signal filtering** (30-day decision filter, pattern detection) |
| **fpai-proactive-monitor** | **8108** | **ACTIVE** | **Proactive service monitoring** (checks 5 services every 5 min) |
| fpai-trust-index | 8560 | ACTIVE | Trust Index calculator (Commons) |
| fpai-needs-allocation | 8565 | ACTIVE | Needs distribution (Commons) |
| fpai-contribution-tracker | 8570 | ACTIVE | TRUST token issuer (Commons) |
| zend-wallet | 8580 | ACTIVE | ZEND Money wallet core (UC credits + send/invite + AI draft) |
| zend-payments | 8581 | READY | ZEND External Settlement (Stripe/Solana PaymentIntent) |
| zend-clerk | 8582 | READY | ZEND POS Telegram Bot (Ministry of Flow) |
| zend-ton | 8583 | READY | ZEND TON blockchain integration |
| zend-marketplace | 8584 | READY | ZEND Partner/Provider marketplace |
| fpai-orchestrator | - | ACTIVE | Service orchestration |
| fpai-auto-healer | - | ACTIVE | Auto healing |
| fpai-realtime-bridge | - | ACTIVE | Realtime communication |
| fpai-service-bridge | - | ACTIVE | Service integration |
| fpai-ri-api | - | ACTIVE | Resource Intelligence API |
| nginx | 80/443 | ACTIVE | Web routing & SSL (proxies to Secondary for AI services) |
| postgresql | 5432 | ACTIVE | Database |

**⚠️ STOPPED on Primary (Dec 14, 2025) - Use Secondary instead:**
- fpai-aria → http://162.0.208.88:8710
- fpai-data-service → http://162.0.208.88:8125
- fpai-ai-gateway → http://162.0.208.88:8104
- sparket-engine → http://162.0.208.88:8711

### Secondary Server (162.0.208.88) - $74.66/month
**Specs:** 32GB RAM, 12 CPU, 480GB SSD (Xeon E-2236)

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| ai-brain | 8101 | ACTIVE | Central AI inference (Grok 4, GPT-5.1, Claude, local Ollama) |
| ollama | 11434 | ACTIVE | Local LLM models (llama3.1:8b, mistral:7b, codellama - FREE!) |
| **fpai-aria** | 8710 | ACTIVE | **Aria AI Assistant (PRIMARY LOCATION)** |
| **fpai-data-service** | 8125 | ACTIVE | **Data intelligence engine (PRIMARY LOCATION)** |
| fpai-sparket-engine | 8711 | ACTIVE | Ultimate marketing engine |
| fpai-ai-automation | 8715 | ACTIVE | AI automation products |
| fpai-ai-gateway | 8104 | ACTIVE | AI API routing |
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

#### Knowledge / Brain stack on Secondary

> ⚠️ **Do NOT stop these without James's approval — they are the centralized AI/memory brain.**

| Service | Port / URL | Status | Purpose |
|---------|------------|--------|---------|
| **sh-brain** (docker compose stack) | `https://brain.sunheart.com` | **ACTIVE — production** | Sunheart Brain — AppFlowy-Cloud knowledge base. 9 containers (postgres+pgvector, redis, minio, gotrue, appflowy_cloud, appflowy_worker, appflowy_web, admin_frontend, nginx). Compose at `/opt/sh-brain/compose`, env at `/root/sh-brain-secrets/brain.env`. **Bring up with `sh-brain-up up -d` or `systemctl start sh-brain`** — never plain `docker compose up`. |
| **sh-brain-index** | `127.0.0.1:28090` | ACTIVE | FastAPI semantic-index service that wraps sh-brain's pgvector. systemd unit `sh-brain-index.service`. |
| concierge-agent-console (Next.js) | `127.0.0.1:3100` | ACTIVE (since 2026-04-24) | Concierge agent console UI. Fronted by primary nginx → secondary nginx (`Host: concierge-secondary.internal`). |
| concierge-client-dashboard (Next.js) | `127.0.0.1:3101` | ACTIVE (since 2026-04-24) | Concierge client dashboard UI. Same fronting pattern as agent-console. |

#### Stopped / orphaned on Secondary

| Service | State | Why |
|---------|-------|-----|
| `appflowy-cloud` (compose) | **REMOVED 2026-04-24** | Duplicate AppFlowy stack superseded by sh-brain. `docker compose down -v` executed; volumes deleted; source moved to `/opt/.appflowy-removed-20260424` (delete with `rm -rf` to fully reclaim disk). |
| `aria.service` / `aria-command.service` | DISABLED 2026-04-24 | aria.service was in a 1,179-restart/hr crash loop, marked `disabled` in registry, was being auto-revived by stale config. Unit files moved to `*.disabled.YYYYMMDD`. |

#### Strategic AI loop on Secondary

| Service | Path | Status | Purpose |
|---------|------|--------|---------|
| `fpai-pulse.service` | `/opt/fpai/pulse/pulse.py` | ACTIVE | **Tiered AI-to-AI loop** — heartbeat (5 min, $0) → reflect (30 min, $0) → think (2x/day + on escalation, ~$0.50/day). Writes `state.json` (health 0-100, services up/down, RAM/disk/load) and `trajectory.json` (goals, blockers, decisions_pending). View with `python3 /opt/fpai/pulse/show_pulse.py`. |

### FPAI Cockpit (cross-server status)

| Service | URL | Status | Purpose |
|---------|-----|--------|---------|
| **fpai-cockpit-status** | `https://fullpotential.ai/cockpit/status/` (basic auth) | ACTIVE (since 2026-04-24) | **Single-pane-of-glass system status.** Pulls operational state (RAM/services/errors) from primary + secondary AND strategic AI state (health/goals/blockers from `/opt/fpai/pulse/` on secondary) AND last 5 learnings. Lives on primary at `/opt/fpai/cockpit/status/`. systemd timer `fpai-cockpit-status.timer` runs every 5 min. Creds in `/root/.cockpit-pw.tmp` on primary. |
| **jsservers-bot** | Telegram: [@JSServers_bot](https://t.me/JSServers_bot) | ACTIVE (since 2026-04-28) | **Mobile/Telegram window into FPAI infra.** systemd unit `jsservers-bot` on primary at `/opt/fpai/jsservers-bot/`. Token + whitelist in `/root/.jsservers-bot.env` (mode 600). Whitelisted to James's Telegram ID only. Commands: `/status /services /health /sites /signals /pulse /learnings /whoami`. Source: `SERVICES/jsservers-bot/`. Redeploy: `BOT_TOKEN=… ./SERVICES/jsservers-bot/deploy.sh --user-ids …`. |

### Legacy Server (209.74.93.72) - $329.76/month
**Specs:** 128GB RAM, 64 CPU, 1.8TB SSD (Dual Xeon Gold 5218)
**⚠️ PRODUCTION - DO NOT DISTURB**

| Service | Port | Status | Purpose |
|---------|------|--------|---------|
| Apache/cPanel | 80/443 | ACTIVE | Web hosting for Outbounders.com |
| Outbounders.com | - | **PRODUCTION** | Live call center with 15+ active agents |
| MySQL | 3306 | ACTIVE | Databases for all hosted sites |

**Websites Hosted:**
- app.outbounders.com (call center management)
- coravida.com, coraorg.com, coradev.com (Cora sites)
- 44 total cPanel accounts

**⚠️ DO NOT:**
- Run experiments on this server
- Reboot without coordination
- Deploy FPAI services here (affects live agents/callers)

---

## ARCHIVED / LEGACY (DO NOT USE)

| Service | Location | Reason |
|---------|----------|--------|
| whaletrack-bridge | Archived | Legacy |
| whaletrack-minnow | Archived | Legacy |
| whaletrack-telegram | Archived | Legacy |

**For trading, use whaletrack-magnet on port 8600 ONLY.**

---

## STOPPED Services on Primary (DO NOT RESTART)

These services were intentionally stopped and **MASKED** on December 14, 2025 to optimize resources.
**DO NOT restart them on the primary server - they are masked to prevent auto-restart.**

| Service | Reason | Alternative Location |
|---------|--------|---------------------|
| fpai-ai-brain | Consolidated on secondary | http://162.0.208.88:8101 |
| fpai-ai-chat | Stopped - AI on secondary | - |
| fpai-aria | **MASKED** - Migrated to secondary | http://162.0.208.88:8710 |
| fpai-sparket-engine | **MASKED** - Migrated to secondary | http://162.0.208.88:8711 |
| fpai-ai-automation | **MASKED** - Migrated to secondary | http://162.0.208.88:8750 |
| fpai-ai-gateway | **MASKED** - Migrated to secondary | http://162.0.208.88 |
| fpai-strategic-intel | Duplicate of strategic-intelligence | Removed |
| fpai-consciousness-optimizer | Duplicate | Secondary server |
| fpai-consciousness_evolution | Duplicate | Secondary server |
| fpai-consciousness_verifier | Duplicate | Secondary server |
| fpai-consciousness_feeder | **STOPPED** - Memory leak bug | Disabled on secondary |
| fpai-intelligence-core | Duplicate | Secondary server |
| fpai-analytics | Non-critical | - |
| fpai-flywheel | Non-critical | - |
| fpai-backup-dashboard | Non-critical | - |
| fpai-legal-guardian | Non-critical | - |
| fpai-member-mining | Non-critical | - |
| fpai-proactive-alerter | Non-critical | - |
| fpai-ri-loop | Non-critical | - |
| fpai-resource-intelligence | Non-critical | - |

### To Unmask a Service (if needed):
```bash
systemctl unmask fpai-<service-name>
systemctl enable fpai-<service-name>
systemctl start fpai-<service-name>
```

---

## API Routing Guide

Use these endpoints in your code:

| If you need... | Use this URL | Server | Notes |
|----------------|--------------|--------|-------|
| **Aria Assistant** | http://162.0.208.88:8710 | Secondary | Chat, trading intel, tools |
| **AI inference** | http://162.0.208.88:8101 | Secondary | AI Brain (routes to best model) |
| **Ollama models** | http://162.0.208.88:11434 | Secondary | Local LLM (FREE!) |
| **Data intelligence** | http://162.0.208.88:8125 | Secondary | Data service |
| **TRADING** | http://198.54.123.234:8600 | Primary | **WhaleTrack Magnet** |
| Nerve Center | http://198.54.123.234:8120 | Primary | System hub |
| Strategic Intel | http://198.54.123.234:8500 | Primary | Strategic intelligence |
| **FP Index** | http://198.54.123.234:8550 | Primary | Constitutional economy (or via https://fullpotential.ai/api/v1/) |
| Credits Gateway | http://198.54.123.234:8765 | Primary | UC credits & payments |
| Trust Index | http://198.54.123.234:8560 | Primary | Commons Ministry |
| Consciousness | http://162.0.208.88:8130-8170 | Secondary | Various ports |

### Code Examples

```python
# AI services - SECONDARY SERVER (162.0.208.88)
ARIA_URL = "http://162.0.208.88:8710"           # Aria Assistant
AI_BRAIN_URL = "http://162.0.208.88:8101"       # AI Brain
DATA_SERVICE_URL = "http://162.0.208.88:8125"   # Data Service
OLLAMA_URL = "http://162.0.208.88:11434"        # Local Ollama (FREE)

# Core services - PRIMARY SERVER (198.54.123.234)
TRADING_URL = "http://198.54.123.234:8600"      # WhaleTrack Magnet
CREDITS_URL = "http://198.54.123.234:8765"      # Credits Gateway
NERVE_CENTER_URL = "http://198.54.123.234:8120" # System Hub

# Consciousness - SECONDARY SERVER
CONSCIOUSNESS_URL = "http://162.0.208.88:8140"
```

**Rule of thumb:**
- AI/ML services → Secondary (has Ollama + more RAM)
- Trading/Payments → Primary (has PostgreSQL)
- Legacy websites → Legacy (DO NOT TOUCH)

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

# WhaleTrack Magnet (THE trading system)
curl http://198.54.123.234:8600/health

# Strategic Intelligence
curl http://198.54.123.234:8500/health

# Aria (Demo Assistant)
curl http://198.54.123.234:8710/health

# Voice Companion (Demo)
curl http://198.54.123.234:8705/

# Commons Ministry Stack
curl http://198.54.123.234:8560/health  # Trust Index
curl http://198.54.123.234:8565/health  # Needs Allocation
curl http://198.54.123.234:8570/health  # Contribution Tracker
curl http://198.54.123.234:8560/api/trust-index  # Get current Trust Index
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

WhaleTrack Magnet (primary:8600) ⭐ THE TRADING SYSTEM
    └── Code: whaletrack-magnetic-trader/backend/api/main.py
    └── Deploy: /opt/fpai/services/whaletrack-magnet/
    └── Features: User auth, Hyperliquid live trading, paper trading, signals
    └── Dashboard: https://fullpotential.ai/dashboards/whaletrack/

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
| 2025-12-12 | Fixed trading system confusion: whaletrack-magnet (8600) is THE trading system | trading-consolidation-agent |
| 2025-12-14 | Stopped duplicate services on Primary (aria, data-service, ai-gateway) - saves 150MB RAM | Cursor Agent |
| 2025-12-14 | Added Legacy server (209.74.93.72) docs - DO NOT DISTURB (Outbounders.com production) | Cursor Agent |
| 2025-12-14 | Added server costs: $474.30/mo total ($69.88 + $74.66 + $329.76) | Cursor Agent |
| 2025-12-14 | Fixed journal memory leak on Primary - freed 1GB RAM | Cursor Agent |
| 2026-04-28 | Added jsservers-bot (Telegram) on Primary; whitelisted to James's TG ID | Cursor Agent |
| 2026-04-30 | Added Alerts (8766), Chief of Staff (8107), Proactive Monitor (8108) - Intelligent proactive alerting system integrated with Sunheart Brain | alerts-system-builder |

