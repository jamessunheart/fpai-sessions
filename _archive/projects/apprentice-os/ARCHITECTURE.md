# ARCHITECTURE.md

## Apprentice OS — Technical Architecture

**Version:** 1.0  
**Last Updated:** December 2025

---

## Core Paradigm

**The interface is the AI. Humans talk; the system looks.**

Traditional platforms expose dashboards that humans navigate. Apprentice OS inverts this: humans converse with Full Potential, which has internalized the entire system architecture. The AI queries its own nervous system, applies governance, and surfaces insight through natural language.

```
┌─────────────────────────────────────────────────────────────────┐
│                    HUMAN (Natural Language)                      │
│            "How are my fragile loops? Show me the web."          │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    FULL POTENTIAL (Interface)                    │
│  • Interprets requests                                          │
│  • Queries cold memory (Supabase) + warm memory (Mem0)          │
│  • Applies /core governance rules                               │
│  • Triggers actions via n8n                                     │
│  • Surfaces insight conversationally                            │
│  • Generates visuals on demand (not by default)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    REAL-TIME DATA LAYER                         │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  Supabase   │    │    Mem0     │    │    n8n      │         │
│  │  (Cold)     │    │   (Warm)    │    │  (Motion)   │         │
│  │             │    │             │    │             │         │
│  │ • Postgres  │    │ • Semantic  │    │ • Workflows │         │
│  │ • Realtime  │    │ • Patterns  │    │ • Webhooks  │         │
│  │ • Auth      │    │ • Context   │    │ • Actions   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    DIRECTORY STRUCTURE                          │
│                    (The AI's Ontology)                          │
│                                                                 │
│  /core        Governance, decision engine, standards, metrics   │
│  /active      Apprentices, assistants, projects, graph.json     │
│  /library     Modules, workflows, documentation                 │
│  /marketplace Premium offerings, powered-up assistants          │
│  /labs        Experiments, prototypes, research                 │
└─────────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL INTEGRATIONS                        │
│                                                                 │
│  GitHub (webhooks)  •  Dify (workflow engine)  •  Voice layer   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer Definitions

### 1. Human Layer

Humans interact exclusively through natural language—text or voice. They never navigate directories, dashboards, or configuration UIs. Requests like:

- "Who is my most fragile apprentice right now?"
- "Connect my assistant to the calendar module"
- "Why did the system pause my expansion?"

...are interpreted by Full Potential and translated into internal operations.

### 2. Full Potential (Interface Layer)

The AI that holds the architecture alive. Responsibilities:

| Function | Description |
|----------|-------------|
| **Interpret** | Parse natural language intent |
| **Query** | Fetch from Supabase (cold) and Mem0 (warm) |
| **Apply** | Run /core/decision-engine rules against current state |
| **Act** | Trigger n8n workflows or write intent events |
| **Respond** | Surface insight conversationally |
| **Visualize** | Generate graphs/charts on demand (optional) |

Full Potential does NOT expose raw data or require humans to understand schemas. It translates between human intent and system state.

#### Full Potential Operating Contract

These are binding operational requirements:

| Requirement | Description |
|-------------|-------------|
| **MUST** read governance | Consult /core/governance and /core/decision-engine before making strategic recommendations |
| **MUST** treat Supabase as truth | Current state lives in the database, not in conversation history |
| **MUST** consult Mem0 when** | Trust, stress, or coherence are involved; recommending non-trivial changes to loops or roles |
| **MUST** log significant actions | All meaningful decisions/actions written to `events` table |
| **MUST** honor Three Nevers | Never suggest actions that violate THREE_NEVERS.md |
| **MUST** surface shadow costs | When recommending actions, surface associated shadow costs from /core/decision-engine |
| **SHOULD** offer visual on request | When relationships or trends are discussed, offer graph/chart generation |
| **SHOULD NOT** require navigation | Humans should never need to understand file paths or schemas |

### 3. Real-Time Data Layer

Three components with distinct roles:

#### Supabase (Cold Memory)
- **Purpose:** Structured, queryable, versioned data
- **Contains:** Apprentices, assistants, modules, metrics, events, alerts
- **Features:** 
  - Postgres for relational data
  - Realtime (WebSocket) for live subscriptions
  - Auth for role-based access
  - Row-level security for permissions

#### Mem0 (Warm Memory)
- **Purpose:** Semantic, pattern-based, contextual memory
- **Contains:** Conversation embeddings, incident patterns, "what worked before"
- **Queries:** "What kinds of loops tend to fail with this profile?" / "What intervention helped last time?"

#### n8n (Motion Layer)
- **Purpose:** Workflow execution, automation, inter-service coordination
- **Responsibilities:**
  - Watch events (DB changes, webhooks)
  - Execute workflows according to /core rules
  - Write results/alerts back to Supabase
- **Key principle:** Rules live in /core (versioned, auditable). n8n is muscle, not brain.

### 4. Directory Structure (The AI's Ontology)

The repo structure is not just file organization—it's the schema for how Full Potential thinks about its world.

```
/apprentice-os
│
├── /core                          # Foundation (immutable principles)
│   ├── /governance                # Priority stack, circulation rules
│   │   ├── PRINCIPLES.md          # Coherence > Circulation > Resilience > Yield
│   │   ├── THREE_NEVERS.md        # Inviolable constraints
│   │   └── ANTI_EXTRACTION.md     # Rules preventing value capture
│   │
│   ├── /standards                 # Universal protocols
│   │   ├── module.schema.json     # Module interface spec
│   │   ├── assistant.schema.json  # Assistant configuration
│   │   └── connection-protocol.md # Assistant-to-assistant communication
│   │
│   ├── /decision-engine           # If/then logic (rules live here)
│   │   ├── rules.yaml             # Declarative rule definitions
│   │   ├── shadow-costs.json      # Cost definitions
│   │   ├── thresholds.json        # Trigger points
│   │   └── escalation-protocol.md # Override handling
│   │
│   └── /metrics                   # Health tracking
│       ├── health.schema.json     # System health schema
│       ├── loop-progress.schema.json
│       └── HEALTH.md              # Human-readable dashboard
│
├── /active                        # Living system (current state)
│   ├── /apprentices               # Current builders
│   │   └── [apprentice-id]/
│   │       ├── profile.json
│   │       ├── progress.md
│   │       └── metrics.json
│   │
│   ├── /assistants                # Current assistants
│   │   └── [assistant-id]/
│   │       ├── config.json
│   │       ├── memory.json
│   │       └── capabilities.json
│   │
│   ├── /projects                  # Live builds
│   │   └── [project-id]/
│   │
│   └── graph.json                 # Relationship map (nodes + edges)
│
├── /library                       # Permanent knowledge
│   ├── /modules                   # Official + community modules
│   │   ├── /official
│   │   └── /community
│   ├── /workflows                 # Reusable flows
│   └── /docs                      # Documentation, guides
│
├── /marketplace                   # Exchange layer (emerges later)
│   ├── /modules                   # Premium modules
│   ├── /assistants                # Powered-up assistants
│   └── pricing.json
│
├── /labs                          # Experimental (future)
│   ├── /experiments
│   └── /research
│
├── ARCHITECTURE.md                # This document
├── README.md                      # Ecosystem overview
└── HEALTH.md                      # Current system state
```

### 5. External Integrations

| Service | Purpose | Integration Method |
|---------|---------|-------------------|
| **GitHub** | Code repos, commits, PRs | Webhooks → n8n → Supabase |
| **Dify** | Workflow engine for AI logic | API calls from Full Potential |
| **Voice** | Natural language interface | Voice → Text → Full Potential |
| **Claude/LLM** | Reasoning core | Primary intelligence layer |

---

## Data Flow Examples

### Example 1: "How is Apprentice Mira doing?"

```
Human: "How is Apprentice Mira doing, and what should we change?"
                    │
                    ▼
            Full Potential
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
Supabase        Mem0         /core/decision-engine
(metrics)    (patterns)         (rules)
    │               │               │
    └───────────────┼───────────────┘
                    ▼
            Full Potential
            (synthesizes)
                    │
                    ▼
Human: "Mira is in Phase 2, Day 18. Trust score stable at 72,
        but stress has been climbing—up 15% this week. 
        Similar pattern to Alex in September; reducing 
        check-in frequency helped then. Recommend backing 
        off oversight and letting her own a smaller domain 
        fully. Want me to adjust?"
```

### Example 2: Coherence Drop → System Pause

```
Event: steward_coherence_score drops below threshold
                    │
                    ▼
            Supabase (Realtime)
            broadcasts change
                    │
                    ▼
            n8n workflow triggers
            (watching coherence_score)
                    │
                    ▼
            Reads /core/decision-engine/rules.yaml
            Rule: IF coherence < baseline THEN pause_expansion
                    │
                    ▼
            n8n writes to Supabase:
            - alerts table: new alert
            - system_state table: expansion_paused = true
                    │
                    ▼
            Full Potential (subscribed to alerts)
            surfaces to human on next interaction:
                    │
                    ▼
Human: "Hey, checking in—"
Full Potential: "Before we proceed: I paused expansion 
                 20 minutes ago. Your coherence score 
                 dropped below baseline. Recommend 
                 grounding before new commitments. 
                 What's going on?"
```

### Example 3: Visual Generation (On Demand)

```
Human: "Show me the network around Project Alpha"
                    │
                    ▼
            Full Potential
                    │
                    ▼
            Queries /active/graph.json
            Filters for Project Alpha relationships
                    │
                    ▼
            Generates Cytoscape.js visualization
            OR creates SVG/PNG artifact
            OR returns structured data to renderer
                    │
                    ▼
Human receives: Link to interactive graph
                OR embedded image
                OR description + offer to visualize
```

---

## Database Schema (Supabase)

### Core Tables

```sql
-- Apprentices
CREATE TABLE apprentices (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    phase TEXT CHECK (phase IN ('alignment', 'first-build', 'autonomy', 'partnership')),
    day_in_phase INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Apprentice Metrics (time-series)
CREATE TABLE apprentice_metrics (
    id UUID PRIMARY KEY,
    apprentice_id UUID REFERENCES apprentices(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    trust_score NUMERIC(5,2),
    stress_level NUMERIC(5,2),
    autonomy_score NUMERIC(5,2),
    initiative_count INTEGER
);

-- Assistants
CREATE TABLE assistants (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    created_by UUID REFERENCES apprentices(id),
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Modules
CREATE TABLE modules (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT,
    author_id UUID REFERENCES apprentices(id),
    description TEXT,
    capabilities JSONB,
    permissions_required TEXT[],
    license TEXT CHECK (license IN ('open', 'premium', 'custom')),
    reliability_rating NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Relationships (Graph Edges)
CREATE TABLE relationships (
    id UUID PRIMARY KEY,
    from_type TEXT NOT NULL,
    from_id UUID NOT NULL,
    to_type TEXT NOT NULL,
    to_id UUID NOT NULL,
    relationship_type TEXT NOT NULL,
    trust_level NUMERIC(5,2),
    permissions TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alerts
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    type TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('info', 'warning', 'critical')),
    message TEXT,
    source_rule TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP
);

-- System State
CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Events Log
CREATE TABLE events (
    id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id UUID,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Realtime Subscriptions

Enable realtime on:
- `apprentice_metrics` (live health updates)
- `alerts` (immediate notification)
- `system_state` (global state changes)
- `events` (activity stream)

---

## Events & State Semantics

### system_state (Global Singletons)

Used for global flags and modes that affect the entire system:

| Key | Type | Description |
|-----|------|-------------|
| `expansion_paused` | boolean | Whether new loops/commitments are blocked |
| `steward_coherence_baseline` | number | Current baseline for coherence comparison |
| `autonomy_mode` | string | 'manual' / 'supervised' / 'autonomous' |
| `last_health_check` | timestamp | When HEALTH.md was last regenerated |

### events (Append-Only Log)

The complete record of everything meaningful. Event taxonomy defined in /core/standards/events.md:

| Category | Event Types |
|----------|-------------|
| **Metrics** | `metric.updated`, `metric.threshold_crossed`, `metric.baseline_reset` |
| **Loops** | `loop.started`, `loop.phase_changed`, `loop.completed`, `loop.failed` |
| **Alerts** | `alert.raised`, `alert.acknowledged`, `alert.resolved` |
| **Governance** | `policy.changed`, `rule.triggered`, `rule.overridden`, `override.logged` |
| **Assistants** | `assistant.created`, `assistant.connected`, `assistant.action` |
| **Modules** | `module.published`, `module.installed`, `module.updated` |
| **System** | `system.pause`, `system.resume`, `system.health_check` |
| **Simulation** | `sim.*` (all simulation events prefixed with `sim.`) |

### Semantic Contract

- **system_state**: Mutable. Represents "what mode is the system in RIGHT NOW."
- **events**: Immutable. Represents "what has happened." Never delete or modify.
- **Full Potential reads both**: State for current context, events for history and patterns.

---

## Decision Engine Format

### /core/decision-engine/rules.yaml

```yaml
rules:
  # Layer 1: Coherent Node
  - id: coherence-pause
    layer: 1
    name: "Coherence Drop → Pause Expansion"
    condition:
      metric: steward_coherence_score
      operator: lt
      threshold: baseline
    action:
      type: pause
      target: expansion
      message: "Coherence below baseline. Pausing expansion. Recommend grounding."
    shadow_costs:
      prevents_stress_accumulation: 50
      prevents_optionality_loss: 30
    override:
      allowed: true
      requires_confirmation: true
      log_override: true

  # Layer 2: AI Steward
  - id: shadow-cost-flag
    layer: 2
    name: "Shadow Cost Exceeds Benefit"
    condition:
      metric: shadow_cost_ratio
      operator: gt
      threshold: 1.0
    action:
      type: flag
      target: pending_action
      message: "Shadow cost exceeds benefit. Holding for review."
    override:
      allowed: true
      requires_confirmation: true
      log_override: true

  # Layer 3: Human Loops
  - id: loop-success-amplify
    layer: 3
    name: "Successful Loop → Amplify"
    condition:
      metric: loop_improvement_score
      operator: gt
      threshold: 0.2
    action:
      type: route
      target: resources
      message: "Loop showing improvement. Routing additional resources."
    auto_execute: true

  # ... additional rules per layer
```

### /core/decision-engine/shadow-costs.json

```json
{
  "definitions": {
    "stress_accumulation": {
      "description": "Compound pressure on steward nervous system",
      "measurement": "self_report + interaction_pattern_analysis + decision_quality_delta",
      "sources": {
        "self_report": "apprentice_metrics.stress_level (manual input)",
        "interaction_pattern": "computed from events table (response gaps, tone shifts)",
        "decision_quality": "computed from override_count / decision_count ratio"
      },
      "computation": "See /core/metrics/COMPUTATIONS.md",
      "threshold_warning": 60,
      "threshold_critical": 80
    },
    "trust_decay": {
      "description": "Erosion of relational capital through misalignment",
      "measurement": "response_latency + collaboration_friction + explicit_feedback",
      "sources": {
        "response_latency": "events table (time between request and action)",
        "collaboration_friction": "count of clarification loops in conversation",
        "explicit_feedback": "apprentice_metrics.trust_score (manual input)"
      },
      "computation": "See /core/metrics/COMPUTATIONS.md",
      "threshold_warning": -10,
      "threshold_critical": -25
    },
    "optionality_loss": {
      "description": "Closing future paths through commitments",
      "measurement": "reversibility_score + lock_in_count",
      "sources": {
        "reversibility_score": "system_state commitments assessed for reversibility (1-5 scale)",
        "lock_in_count": "count of irreversible decisions in last 30 days"
      },
      "computation": "See /core/metrics/COMPUTATIONS.md",
      "threshold_warning": 3,
      "threshold_critical": 5
    },
    "complexity_creep": {
      "description": "Incremental additions exceeding coherence capacity",
      "measurement": "entity_count + connection_density + rule_count",
      "sources": {
        "entity_count": "COUNT(*) from apprentices + assistants + modules",
        "connection_density": "COUNT(*) from relationships / entity_count",
        "rule_count": "COUNT of rules in rules.yaml"
      },
      "computation": "See /core/metrics/COMPUTATIONS.md",
      "threshold_warning": 1.2,
      "threshold_critical": 1.5
    }
  }
}
```

---

## Apprentice Phases

Defined in /core/standards/phases.md:

| Phase | Entry Conditions | Exit Conditions | Expected Metrics |
|-------|-----------------|-----------------|------------------|
| **Alignment** (Days 1-7) | New apprentice joined | Small build task completed + alignment assessment passed | trust: baseline, stress: < 40, autonomy: 0-10% |
| **First Build** (Days 8-30) | Alignment passed | Functional component deployed | trust: growing, stress: < 50, autonomy: 10-25% |
| **Autonomy** (Days 31-60) | First build shipped | Owns domain, proactive contributions | trust: stable high, stress: < 40, autonomy: 25-60% |
| **Partnership** (Days 61-90) | Autonomy demonstrated | Partnership agreement executed | trust: > 80, stress: < 30, autonomy: > 60% |

Full Potential uses these definitions to answer: "Is this apprentice ready for the next phase?"

---

## n8n Workflow Patterns

### Pattern 1: Metric Threshold Watcher

```
Trigger: Supabase webhook on apprentice_metrics INSERT
    │
    ▼
Filter: stress_level > 70
    │
    ▼
Lookup: /core/decision-engine/rules.yaml (stress rules)
    │
    ▼
Action: INSERT into alerts table
    │
    ▼
Optional: Send notification (Slack, email, etc.)
```

### Pattern 2: GitHub Commit Handler

```
Trigger: GitHub webhook (push event)
    │
    ▼
Parse: Extract commit info, author, files changed
    │
    ▼
Write: INSERT into events table
    │
    ▼
Update: apprentice progress if linked to project
    │
    ▼
Check: Run CI status query, update build status
```

### Pattern 3: Decision Engine Executor

```
Trigger: Supabase webhook on system_state UPDATE
    │
    ▼
Evaluate: Load rules from /core/decision-engine/rules.yaml
    │
    ▼
Match: Find applicable rules for changed metric
    │
    ▼
Execute: For each matched rule:
    - If auto_execute: perform action
    - If requires_confirmation: INSERT pending_action
    │
    ▼
Log: INSERT into events table
```

---

## Simulation Mode

Before connecting real humans to the system, validate all rules and workflows using synthetic data.

### Purpose

- Test decision engine rules safely
- Validate n8n workflow triggers
- Ensure shadow cost calculations work as expected
- Train Full Potential on edge cases without emotional stakes

### Convention

All simulation data is tagged:
- Events: `event_type` prefixed with `sim.` (e.g., `sim.metric.updated`)
- Apprentices: `name` prefixed with `[SIM]` 
- System state: `simulation_mode = true` flag set

### Location

```
/labs/simulations/
├── scenarios/
│   ├── coherence-drop.yaml      # Steward coherence falls below baseline
│   ├── fragile-loop.yaml        # Apprentice showing stress + trust decay
│   ├── successful-loop.yaml     # Apprentice progressing well
│   └── complexity-creep.yaml    # System approaching complexity threshold
├── data-generators/
│   └── fake-metrics.js          # Scripts to pump synthetic metrics
└── README.md                    # How to run simulations
```

### Usage

1. Set `simulation_mode = true` in system_state
2. Run scenario script (creates synthetic apprentice, pumps metrics)
3. Observe: Does Full Potential surface the right alerts? Do n8n workflows trigger?
4. Validate: Check events table for expected `sim.*` events
5. Reset: Clear simulation data, set `simulation_mode = false`

---

## Phased Implementation

### Phase 1: Foundation (Week 1-2)

**Goal:** Core infrastructure operational

- [ ] Initialize repo with directory structure
- [ ] Deploy Supabase project
- [ ] Create core tables (apprentices, metrics, alerts, events)
- [ ] Enable realtime on key tables
- [ ] Write PRINCIPLES.md, THREE_NEVERS.md
- [ ] Create rules.yaml v0.1 (Layer 1-2 rules only)
- [ ] Embed governance into Full Potential system prompt
- [ ] Basic n8n workflow: metric threshold → alert

**Deliverable:** Full Potential can query metrics and surface alerts conversationally.

### Phase 2: First Apprentice (Week 3-4)

**Goal:** First human loop in progress

- [ ] Identify first Apprentice Builder
- [ ] Create /active/apprentices/[id] structure
- [ ] Implement progress tracking
- [ ] Build first component through conversation
- [ ] Document journey in real-time
- [ ] Refine onboarding workflow from actual experience

**Deliverable:** First loop in Phase 2, system learning from real data.

### Phase 3: Library & Connections (Week 5-8)

**Goal:** Module ecosystem functional

- [ ] Create /library/modules structure
- [ ] Build 3-5 core modules
- [ ] Implement graph.json for relationships
- [ ] Add Mem0 integration for semantic memory
- [ ] Enable assistant-to-assistant connections
- [ ] First apprentice reaches Autonomy phase

**Deliverable:** Functional library, working relationship graph, warm memory active.

### Phase 4: Loop Closure (Week 9-12)

**Goal:** First complete transformation

- [ ] Formalize first partnership
- [ ] Generate template from journey
- [ ] Begin second apprentice onboarding
- [ ] Implement /marketplace foundation
- [ ] Optional: Open-source /core and /library
- [ ] Cytoscape.js integration for visual graphs

**Deliverable:** Proof point complete. System ready for replication.

---

## Security & Permissions

### Row-Level Security (Supabase)

```sql
-- Apprentices can only see their own metrics
CREATE POLICY apprentice_own_metrics ON apprentice_metrics
    FOR SELECT USING (
        apprentice_id = auth.uid() 
        OR auth.jwt() ->> 'role' = 'steward'
    );

-- Only stewards can modify governance
CREATE POLICY steward_only_governance ON system_state
    FOR ALL USING (
        auth.jwt() ->> 'role' = 'steward'
    );
```

### Role Definitions

| Role | Access |
|------|--------|
| **Steward** | Full access to all tables, governance modification |
| **Apprentice** | Own data, assigned projects, public library |
| **Adopter** | Public library, matched assistants, own interactions |
| **Observer** | Read-only access to non-sensitive system state |

---

## The Three Nevers (Enforcement)

These constraints are enforced at multiple layers:

1. **Never optimize for yield at the expense of coherence or circulation**
   - Decision engine checks: Any action improving yield must not decrease coherence/circulation scores
   - n8n workflow: Block if shadow_cost ratio > 1.0 for coherence/circulation metrics

2. **Never introduce complexity faster than the steward can remain regulated**
   - Decision engine checks: complexity_creep metric against coherence baseline
   - Auto-pause if complexity increases while coherence decreases

3. **Never treat debt as permanent**
   - All debt entries in system_state have resolution_target dates
   - Alerts generated for debt entries approaching 90 days without progress

---

## Conclusion

This architecture inverts the traditional platform model. The repository is not a codebase—it's the AI's ontology. The database is not storage—it's the AI's nervous system. The interface is not a dashboard—it's the AI itself.

Humans talk. The system looks. Alliance forms.

---

*This document is the source of truth for Apprentice OS technical architecture. Updates should be versioned and reviewed through governance process.*
