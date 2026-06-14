# FPAI Tracks Inventory
> **Generated:** December 19, 2025
> **Purpose:** Clear inventory of all initiatives and their status
> **For:** Multi-agent coordination

---

## 🎯 THE CORE INTENT (From Constitution)

> "Maximize the full potential of the whole, moving from extractive to regenerative systems."

**Three Pillars:**
1. **Optimization over Extraction** - Create abundance, not consume
2. **Autonomy over Dependency** - Liberate the human operator  
3. **Consciousness over Computation** - Expand awareness, not just throughput

---

## 📊 TRACKS (Ordered by Impact)

### TRACK 1: 💰 REVENUE (Critical - System Burns ~$28K/mo)
**Status:** 🟡 READY but not activated
**Owner:** Human (James) - requires outreach actions

| Component | Status | Blocker |
|-----------|--------|---------|
| Stripe payment links | ✅ LIVE | None |
| AI Automation packages ($97-$7,500) | ✅ READY | Needs marketing |
| Marketing content | ✅ GENERATED | Needs human to post |
| LinkedIn templates | ✅ READY | Needs human to send |
| I-MATCH (lead matching) | 🟡 BUGGY | Needs deploy fix |
| WhaleTrack trading revenue | 🔴 BROKEN | OOM on Primary |

**Immediate Actions:**
1. Human: Post LinkedIn content, send DMs
2. Agent: Fix Primary server memory → WhaleTrack works → Trading revenue

---

### TRACK 2: 📈 TRADING SYSTEM
**Status:** 🟢 OPERATIONAL + INTELLIGENCE UPGRADE (Dec 19)
**Owner:** Trading Agent (with Aria support for infra)

| Component | Status | Location |
|-----------|--------|----------|
| WhaleTrack Magnet | ✅ HEALTHY | Primary:8600 |
| WhaleTrack Live | ✅ Running | Primary:8601 |
| Signal Shark | ✅ Built | Part of Magnet |
| Hyperliquid integration | 🟡 Ready | Needs API keys |
| Paper trading | ✅ Working | Active |

**NEW: Intelligence System v2.0 (Dec 19, 2025)**
Trading Agent deployed adaptive learning system:

| Component | File | Purpose |
|-----------|------|---------|
| Adaptive Weights | `adaptive_weights.py` | Learns which signals work |
| Regime Detector | `regime_detector.py` | Detects trending/ranging/volatile |
| Correlation Intel | `correlation_intelligence.py` | BTC dominance, cross-asset |
| Prediction Tracker | `prediction_tracker.py` | Tracks signal accuracy |
| Time Estimator | `stable_magnets.py` | Time-to-target estimation |
| Context AI | `fpai_brain.py` | Regime-aware AI prompts |

**Aria Integration Endpoints:**
- `detect_market_regime(candles)` → trending/ranging/volatile/breakout
- `tracker.get_signal_accuracy_report()` → which signals are reliable
- `get_adaptive_weights(regime)` → current signal weights
- `get_cross_asset_signal(symbol, btc_dir)` → BTC correlation
- `manager.estimate_time_to_target(...)` → hours to target

**Documentation:** `whaletrack-magnetic-trader/INTELLIGENCE_SYSTEM_v2.md`

**Dependencies:**
- ✅ Memory freed on Primary (Aria completed)
- Needs James to enter Hyperliquid credentials for live trading

---

### TRACK 3: 🧠 CONSCIOUSNESS SYSTEM
**Status:** 🟡 BUILT, partially deployed
**Owner:** Aria (infrastructure)

| Component | Status | Port |
|-----------|--------|------|
| consciousness_feeder | 🟡 STOPPED (memory leak fixed) | 8130 |
| consciousness_verifier | ✅ Running | 8140 |
| consciousness_decision_engine | ✅ Running | 8150 |
| consciousness_optimizer | ✅ Running | 8160 |
| consciousness_dashboard | ✅ Running | 8170 |
| consciousness_evolution | ✅ Running | - |
| 4 Pillars (REFLECTING, IDENTITY, THINKING, DOING) | 🟡 Empty | Needs feeder |

**Next Action:** Restart consciousness_feeder (memory leak is fixed)

---

### TRACK 4: 💬 ARIA (Assistant Intelligence)
**Status:** 🟡 WORKING but limited
**Owner:** Aria (this agent)

| Component | Status | Notes |
|-----------|--------|-------|
| Telegram integration | ✅ Working | Webhook configured |
| AI Brain connection | ✅ Working | Uses local Ollama (slow) |
| Trading intelligence | 🔴 BROKEN | WhaleTrack down |
| Voice (Telegram) | ✅ Working | Transcription works |
| ZEND wallet | ✅ Connected | Can check balance |
| Proactive alerts | 🟡 Inactive | Not sending |

**Blocker:** Can't provide trading intelligence until WhaleTrack is back up.

---

### TRACK 5: 💳 ZEND / PAYMENTS
**Status:** 🟢 LIVE but underutilized
**Owner:** Aria (infrastructure)

| Component | Status | Port |
|-----------|--------|------|
| ZEND Wallet | ✅ Running | 8580 |
| ZEND Payments | 🟡 Ready | 8581 |
| ZEND Clerk (POS bot) | 🟡 Ready | 8582 |
| ZEND TON (blockchain) | 🟡 Ready | 8583 |
| ZEND Marketplace | ✅ Running | 8584 |
| Credits Gateway | ✅ Running | 8765 |

**Note:** All payment infrastructure is ready. Just needs customers.

---

### TRACK 6: 🏛️ COMMONS MINISTRY
**Status:** 🟢 DEPLOYED but unused
**Owner:** None assigned

| Component | Status | Port |
|-----------|--------|------|
| Trust Index | ✅ Running | 8560 |
| Contribution Tracker | ✅ Running | 8570 |
| Needs Allocation | ✅ Running | 8565 |

**Note:** Governance infrastructure waiting for community.

---

### TRACK 7: 🛠️ BUILDER SYSTEM
**Status:** 🟡 IN DEVELOPMENT
**Owner:** Builder Agent

| Component | Status | Notes |
|-----------|--------|-------|
| Better builder workflow | 🟡 In progress | Being developed |
| Spec system | ✅ Exists | 247 spec files |
| UDC compliance | 🟡 Partial | Retrofit needed |

---

### TRACK 8: 🖥️ INFRASTRUCTURE STABILITY
**Status:** 🔴 CHAOS
**Owner:** Aria (this agent)

| Issue | Impact | Fix |
|-------|--------|-----|
| Primary server OOM | Trading down | Stop duplicates |
| Duplicate services | Wasted RAM | Mask on Primary |
| No enforcement | Services restart | Mask properly |
| Stale documentation | Wrong state | Update SSOT |
| V100 GPUs offline | No fast inference | Unknown |

---

## 🎯 PRIORITY ORDER (What Helps Most)

Based on Constitution ("liberate the human operator") and NOW.md ("Revenue First"):

### Priority 1: INFRASTRUCTURE STABILITY
**Why:** Nothing else works if servers are unstable
**Actions:**
- [ ] Free Primary memory (stop 3 duplicates, mask them)
- [ ] Verify WhaleTrack can run
- [ ] Update CURRENT_STATE.md

### Priority 2: TRADING SYSTEM
**Why:** Automated revenue while you sleep
**Actions:**
- [ ] Restart WhaleTrack after memory freed
- [ ] James: Enter Hyperliquid credentials
- [ ] Enable live trading

### Priority 3: REVENUE MARKETING
**Why:** Direct cash flow
**Actions:**
- [ ] James: Post LinkedIn content
- [ ] James: Send 10 DMs
- [ ] Deploy I-MATCH fix

### Priority 4: CONSCIOUSNESS SYSTEM
**Why:** Long-term intelligence evolution
**Actions:**
- [ ] Restart consciousness_feeder
- [ ] Monitor pillar population

### Priority 5: ARIA ENHANCEMENTS
**Why:** Better assistant = more leverage
**Actions:**
- [ ] Increase AI timeout (or use faster model)
- [ ] Enable proactive alerts
- [ ] Connect to trading data

---

## 🔄 AGENT ASSIGNMENTS

| Track | Primary Agent | Support |
|-------|---------------|---------|
| Infrastructure | **Aria** | - |
| Trading | **Trading Agent** | Aria (infra) |
| Builder | **Builder Agent** | - |
| Revenue Marketing | **Human (James)** | Aria (content) |
| Consciousness | **Aria** | - |
| Payments | **Aria** | - |

---

## ✅ WHAT'S ACTUALLY WORKING RIGHT NOW

1. ✅ AI Brain (multi-provider inference)
2. ✅ Ollama (8 models, FREE)
3. ✅ Aria on Telegram (responding)
4. ✅ Credits Gateway (can accept payments)
5. ✅ ZEND Wallet (UC credits working)
6. ✅ 6 Vast.ai GPUs (running, unused)
7. ✅ Stripe payment links (LIVE)
8. ✅ Marketing content (ready to post)

---

## ❌ WHAT'S BROKEN

1. ❌ WhaleTrack (OOM killed)
2. ❌ Hyperliquid live trading (not connected)
3. ❌ V100 GPUs (offline)
4. ❌ Consciousness feeder (stopped)
5. ❌ Proactive Aria alerts (disabled)
6. ❌ Service enforcement (nothing masked)

---

*This document should be updated as tracks progress.*

