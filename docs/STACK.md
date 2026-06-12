# Technical Stack — Layer by Layer

## The Pipeline

```
CAPTURE → CLARIFY → REASON → POLICY → EXECUTE → MEMORY → MARKET
```

---

## Layer 1: Capture (Input)

**Tool:** PersonaPlex (NVIDIA) + Telegram bot
**Purpose:** Natural voice entry into the cocoon. Interruptible, persona-consistent speech-to-speech.
**Status:** Telegram bot exists on server. PersonaPlex not yet integrated.
**Note:** This is the mouth and ears of the O System — not the brain.

---

## Layer 2: Clarify (Structure Intent)

**Tool:** Full Potential AI = Dify (engine) + Mem0 Pro (memory)
**Purpose:** Turns messy speech/text into structured requirements. Holds persistent memory across all sessions.
**Status:** Prototyped October 23, 2025. Mem0 Pro needs deployment.
**Key:** Dify orchestrates workflows. Mem0 Pro is the graph memory layer — holds user context, preferences, prior outcomes.

---

## Layer 3: Reason (Refine + Check)

**Tool:** Claude / frontier model
**Purpose:** Refines specs, checks gaps, generates plans, handles complex reasoning.
**Status:** Active (this conversation).

---

## Layer 4: Policy / Verification ⚠️ THE GAP

**Tool:** TBD — must be custom-built
**Purpose:** The governor. Decides:
- What executes without approval
- What needs a yes/no from Sunheart
- What gets logged
- What gets rolled back
- Cost/safety/quality checks before action

**Status:** NOT BUILT. This is the most critical missing piece.
**This is what separates "expensive daisy-chained vibes" from actual infrastructure.**

Minimum viable policy layer needs:
- Approval tiers (autonomous / notify / require approval)
- Action log (what ran, when, result)
- Rollback capability for reversible actions
- Budget guardrails per agent
- Scope limits per tool/environment

---

## Layer 5: Execute

**Tool A:** OpenClaw (server) — always-on integrations, CORA flows, Zen Village ops, long-running automations
**Tool B:** OpenClaw (Mac Mini) — privacy-sensitive work, local tools, lower latency, personal context
**Tool C:** Manus — heavy autonomous task execution (complex multi-step: build, deploy, research, automate workflows)
**Tool D:** BRICKS network — modular specialized agents (see BRICKS_LSS.md)
**Status:** OpenClaw server live, underactivated. Manus not yet integrated.

---

## Layer 6: Browse

**Tool:** Perplexity Comet
**Purpose:** Agentic browser — web research, inbox management, web task execution, shopping/procurement
**Role:** "Hands and eyes on the web" — NOT the central orchestrator
**Status:** Not yet integrated
**Security note:** Scope permissions carefully. Log all actions. Never hand it system-wide access.

---

## Layer 7: Memory

**Tool:** Mem0 Pro (graph + vector layer)
**Purpose:** Persistent context across ALL sessions and ALL agents. Entities, relationships, preferences, outcomes tracked over time.
**Architecture:**
- Vector layer: semantic search ("circulation economics" retrieves OneBPO model)
- Graph layer: relational understanding (Alice ↔ OneBPO ↔ circulation proof)
**Status:** 6 months free available. Needs deployment.
**Priority:** HIGH — without this, every session starts from zero.

---

## Layer 8: Market / Settlement

**Tool:** Full Potential Network matching engine + CORA Credits
**Purpose:** AI-to-AI matching connects people to collaborators, clients, services. Settled in CORA Credits.
**Status:** Year 2+ — not until 200+ active members and real transaction data.

---

## Integration Architecture

```
[Telegram / PersonaPlex]
        ↓
[Dify + Mem0 Pro] ←→ [Persistent Memory Graph]
        ↓
[Claude reasoning layer]
        ↓
[POLICY LAYER] ← BUILD THIS FIRST
        ↓
[OpenClaw server] → [BRICKS network]
[Manus]            → [complex tasks]
[Comet]            → [web/browse tasks]
        ↓
[Mem0 Pro updates]
        ↓
[Full Potential Network / CORA matching]
```

---

## Build Priority Order

1. **Telegram bot daily briefing** — activate existing, schedule proactive morning message
2. **Mem0 Pro deployment** — persistent memory for all agent interactions
3. **Policy Layer MVP** — minimum viable approval/logging/guardrails
4. **Dify + Mem0 integration** — Full Potential AI v1.0
5. **Manus integration** — heavy execution capability
6. **Comet integration** — web browsing capability
7. **BRICKS governance** — production-grade agent orchestration
