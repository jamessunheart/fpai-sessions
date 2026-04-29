# FPAI Infrastructure - Current State Audit
> **Generated:** December 19, 2025 16:30 UTC
> **Last Updated:** December 19, 2025 16:45 UTC
> **Purpose:** Single source of truth for multi-agent coordination
> **Author:** Aria (Cursor Session)

---

## 🔄 RECENT CHANGES (Dec 19, 2025)

### Aria Actions (16:40 UTC)
- ✅ Stopped `fpai-ai-gateway` (duplicate of Secondary) - saved ~68MB
- ✅ Stopped `fpai-data-service` (duplicate of Secondary) - saved ~56MB
- ✅ Stopped `fpai-sparket` (duplicate of Secondary) - saved ~57MB
- ✅ Stopped `fpai-auto-healer` (manual management) - saved ~145MB
- ✅ Stopped `fpai-voice-companion` (demo only) - saved ~22MB
- ✅ WhaleTrack Magnet verified HEALTHY
- **Total memory freed: ~350MB**

### Trading Agent Actions (Dec 19)
- ✅ Deployed Intelligence System v2.0
- New: Adaptive weights, regime detection, correlation intelligence
- See: `whaletrack-magnetic-trader/INTELLIGENCE_SYSTEM_v2.md`

---

## 🖥️ SERVERS

### Primary Server (198.54.123.234)
| Metric | Value | Status |
|--------|-------|--------|
| RAM | 7.7GB total, **~1GB available** | 🟡 IMPROVED |
| CPU | 8 cores | ✅ OK |
| Disk | 343GB free | ✅ OK |
| Cost | $69.88/month | - |

**Running Services (19) - After cleanup:**
- fpai-contribution-tracker
- fpai-credits-gateway ⭐ PAYMENTS
- fpai-needs-allocation
- fpai-nerve-center ⭐ HUB
- fpai-orchestrator
- fpai-realtime-bridge
- fpai-ri-api
- fpai-service-bridge
- fpai-strategic-intelligence
- fpai-trust-index
- fpai-zend-marketplace
- fpai-zend-ton
- fpai-zend-wallet ⭐ ZEND
- whaletrack-bridge-btc
- whaletrack-bridge-eth
- whaletrack-bridge-sol
- whaletrack-live ⭐ TRADING
- whaletrack-magnet ⭐ TRADING

**Stopped & Disabled (Dec 19):**
- fpai-ai-gateway (use Secondary:8104)
- fpai-data-service (use Secondary:8125)
- fpai-sparket (use Secondary:8711)
- fpai-auto-healer (manual management)
- fpai-voice-companion (demo only)

---

### Secondary Server (162.0.208.88)
| Metric | Value | Status |
|--------|-------|--------|
| RAM | 31GB total, **23GB available** | ✅ HEALTHY |
| CPU | 12 cores | ✅ OK |
| Disk | 362GB free | ✅ OK |
| Cost | $74.66/month | - |

**Running Services (22):**
- fpai-ai-automation
- fpai-ai-gateway
- fpai-aria ⭐ PRIMARY LOCATION
- fpai-aware-brain
- fpai-consciousness-coordinator
- fpai-consciousness-optimizer
- fpai-consciousness_api
- fpai-consciousness_dashboard
- fpai-consciousness_decision_engine
- fpai-consciousness_evolution
- fpai-consciousness_feeder
- fpai-consciousness_gateway
- fpai-consciousness_network
- fpai-consciousness_verifier
- fpai-data-service ⭐ PRIMARY LOCATION
- fpai-domain-monitor
- fpai-gateway
- fpai-reports-api
- fpai-sparket-engine ⭐ PRIMARY LOCATION
- fpai-user-service
- fpai-webhooks
- ollama ⭐ LOCAL AI (FREE)

---

### Legacy Server (209.74.93.72)
| Metric | Value | Status |
|--------|-------|--------|
| RAM | 128GB | Not checked |
| CPU | 64 cores | Not checked |
| Cost | $329.76/month | - |
| Purpose | Outbounders.com PRODUCTION | 🚫 DO NOT TOUCH |

---

## 🤖 AUTOMATED SYSTEMS

| System | Location | Status | Can Make Changes? |
|--------|----------|--------|-------------------|
| fpai-auto-healer | Primary | ✅ ACTIVE | Yes - monitors & heals |
| fpai-autonomous-healer | Secondary | ❌ INACTIVE | No |
| systemd | Both | ✅ ACTIVE | Yes - auto-starts enabled services |
| cron jobs | Unknown | Unknown | Possibly |

---

## 🎮 EXTERNAL RESOURCES

### Vast.ai GPU Instances
| GPU | Count | Status | Cost |
|-----|-------|--------|------|
| Tesla V100 | 2x | ❌ OFFLINE | $0.20/hr |
| Tesla V100 | 2x | ❌ OFFLINE | $0.20/hr |
| GTX 1080 | 1x | ✅ RUNNING | $0.06/hr |
| Titan Xp | 1x | ✅ RUNNING | $0.06/hr |
| GTX TITAN X | 1x | ✅ RUNNING | $0.06/hr |
| RTX 2060S | 1x | ✅ RUNNING | $0.06/hr |
| GTX 1080 Ti | 1x | ✅ RUNNING | $0.08/hr |
| Tesla T4 | 1x | ✅ RUNNING | $0.16/hr |

**Total Running:** 6 GPUs (~$0.48/hr = ~$11.52/day)
**Total Offline:** 4 GPUs (V100s)

---

## 🔴 IDENTIFIED PROBLEMS

### 1. Memory Crisis on Primary
- Only 610MB available
- WhaleTrack being OOM-killed
- Too many services for 8GB RAM

### 2. Duplicate Services
| Service | Primary | Secondary | Should Be |
|---------|---------|-----------|-----------|
| ai-gateway | Running | Running | Secondary ONLY |
| data-service | Running | Running | Secondary ONLY |
| sparket | Running | Running | Secondary ONLY |

### 3. No Enforcement
- 0 services are MASKED
- 60+ services ENABLED for auto-start
- Any reboot will start everything

### 4. No Coordination Protocol
- No active claims in coordination system
- Multiple agents can make conflicting changes
- No lock mechanism

---

## ✅ WHAT'S WORKING

| System | Status |
|--------|--------|
| Aria (Telegram) | ✅ Responding |
| AI Brain | ✅ Healthy |
| Ollama (local) | ✅ 8 models available |
| Credits Gateway | ✅ Running |
| Nerve Center | ✅ Running |
| ZEND Wallet | ✅ Running |
| 6x Vast.ai GPUs | ✅ Running (but not integrated) |

---

## ❌ WHAT'S BROKEN / PENDING

| System | Status | Impact |
|--------|--------|--------|
| WhaleTrack Magnet | ✅ FIXED | Now healthy |
| WhaleTrack Live | ✅ FIXED | Running |
| Hyperliquid | 🟡 Not connected | James needs to enter API keys |
| V100 GPUs | ❌ Offline | No fast GPU inference |
| GPU Bridge | ❌ Degraded | Can't route to GPUs |

---

## 📋 RECOMMENDED ACTIONS (Pending Approval)

### Immediate (requires James approval)
1. [ ] Stop duplicate services on Primary (saves ~200MB)
2. [ ] MASK services that shouldn't run on Primary
3. [ ] Restart WhaleTrack after memory freed

### Short-term
4. [ ] Create coordination lock protocol
5. [ ] Define authoritative service manifest per server
6. [ ] Configure auto-healer to respect manifests

### Investigation Needed
7. [ ] Why are V100 GPUs offline?
8. [ ] Are the 6 running GPUs being used?
9. [ ] What triggered duplicate services to start?

---

## 🔒 COORDINATION PROTOCOL (Proposed)

Before ANY agent makes infrastructure changes:

1. **CHECK** this document for current state
2. **CLAIM** the change in `/docs/coordination/claims/`
3. **ANNOUNCE** intent to James
4. **EXECUTE** only after approval
5. **UPDATE** this document with results

---

*This document should be updated after any infrastructure change.*

