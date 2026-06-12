# 🧠 FPAI System Mind Map (As I See It)

**Goal:** One “at-a-glance” mental model of the whole FPAI system: services, servers, and the core flows.  
**Source of truth for service locations:** `docs/coordination/SERVICE_REGISTRY.md`

---

## Mind Map (High-Level System)

```mermaid
mindmap
  root((FPAI OS))
    Mission
      Revenue First
      Reliability + Self‑reliance
      Closed‑loop learning (outcomes drive improvement)
    Architecture
      Two‑Server Allocation
        Primary (198.54.123.234)
          "Trading + Revenue + Data"
        Secondary (162.0.208.88)
          "AI + Consciousness + Heavy inference"
      Routing
        "AI Brain -> Secondary:8101"
        "Data Service -> Primary:8125"
        "Nerve Center -> Primary:8120"
        "Trading -> Primary:8601"
    Primary Server (198.54.123.234)
      Web + Routing
        Nginx (80/443)
      Data + Intelligence
        Data Service (8125)
          "Collect -> Clean -> Patterns/Insights"
          "Mem0 learning endpoint"
        Nerve Center (8120)
          "Pipeline health"
          "Action Digest"
          "Digest -> Intents"
          "Outcome ledger"
        Strategic Intelligence (8500)
          "Signals ingestion"
          "Prioritize + dispatch"
      Trading
        WhaleTrack Live (8601)
          "Real execution"
      Revenue Engines
        Credits Gateway (8765)
          "UC purchases + pricing"
        AI Automation (8750)
          "Leadgen + automations"
        Sparket Engine (8711)
          "Marketing intelligence"
      Commons Stack
        Trust Index (8560)
        Needs Allocation (8565)
        Contribution Tracker (8570)
      Monitoring
        God Mode (8300)
          "Operator UI"
          "Data tab"
        Auto‑Healer
        Resource Monitor (timer)
    Secondary Server (162.0.208.88)
      AI Inference
        AI Brain (8101)
          "Generate endpoint"
          "Model routing/failover"
        Ollama (11434)
      Consciousness
        Feeder (8130)
        Verifier (8140)
        Decision Engine (8150)
        Optimizer (8160)
        Dashboard (8170)
      Intelligence processing
        "daemon/hub/evolution (as allocated)"
    Core Flywheels (Flows)
      "Data -> Actions -> Outcomes -> Learning"
        Collect
          "HN / arXiv / RSS / CoinGlass"
        Store
          "Data Service"
        Synthesize
          "AI Brain (optional)"
        Decide
          "Nerve Center digest"
          "Strategic Intelligence priorities"
        Execute
          "Humans + Agents + Services"
        Observe Outcomes
          "Nerve Center outcome ledger"
        Learn
          "Mem0 learnings (via Data Service)"
      "Coordination -> Safe multi-agent work"
        SSOT.json
        SERVICE_REGISTRY.md
        claims/*.claim
        intents/*.json
        heartbeats/*.json
        messages/*
    Operator Interfaces
      God Mode
        Overview
        Mission/Team
        Intel
        Data System
      Docs
        DATA_SYSTEM_MAP.md
        SERVICE_REGISTRY.md
        SSOT.json
```

---

## Fallback (Always-readable Text Mind Map)

```text
FPAI OS
├─ Mission: Revenue first + reliability + closed-loop learning
├─ Two servers
│  ├─ Primary (198.54.123.234): Trading, Revenue, Data, UI
│  └─ Secondary (162.0.208.88): AI Brain, Consciousness, heavy inference
├─ Primary services (high signal)
│  ├─ WhaleTrack Live (8601) – trading execution
│  ├─ Credits Gateway (8765) – revenue
│  ├─ AI Automation (8750) – revenue / leadgen
│  ├─ Data Service (8125) – collect/clean/patterns/insights + Mem0 learn
│  ├─ Nerve Center (8120) – digest → intents + outcome ledger
│  ├─ Strategic Intelligence (8500) – prioritize + dispatch
│  └─ God Mode (8300) – operator UI (includes Data tab)
├─ Secondary services (high signal)
│  ├─ AI Brain (8101) – generation + routing
│  ├─ Ollama (11434) – local models
│  └─ Consciousness (8130–8170) – feeder/verifier/decider/optimizer/dashboard
└─ Main flow (flywheel)
   Collect → Store → (Analyze) → Digest → Intents → Execute → Outcomes → Learn → Better digest
```




