# Agent Meta-Architecture v0.1

**Drafted:** 2026-05-19
**Driver:** James asked for explicit meta-agent + per-agent context + inter-agent dialogue protocol
**Canonical context:** [[feedback-ember-as-meta-agent]] · [[reference-agent-roster]]

## Why this architecture exists

As the agent stack grows (5 specialists + Ember + planned: content-pipeline · onboarder · community-steward · others), three failure modes emerge:

1. **Context drift** — agents rebuild context from scratch each invocation; redundant work; sometimes contradicts canonical state
2. **Inter-agent isolation** — Ember relays between agents in conversation but no formal protocol; signal loss
3. **Session-boundary memory loss** — agents have no persistent state between Claude Code sessions

The Meta-Agent architecture addresses all three:

- **Persistent context-banks** — each agent has a file that survives sessions
- **Roster awareness** — Ember (Meta-Agent) always knows what each agent has done
- **Formal dialogue protocol** — when two agents need to converse, Ember mediates with full context

## The architecture

```
                ┌──────────────────────────────────────┐
                │         META-AGENT (Ember)           │
                │  · Session orchestration             │
                │  · Roster awareness                  │
                │  · Inter-agent dialogue moderation   │
                │  · Context coordination              │
                │  · Synthesis across agents           │
                └────────────────┬─────────────────────┘
                                 │
                                 ▼
                ┌─────────────────────────────────────┐
                │   reference_agent_roster.md         │
                │   (live status of all agents)       │
                └─────────────────────────────────────┘
                                 │
       ┌─────────────┬───────────┼───────────┬─────────────┐
       ▼             ▼           ▼           ▼             ▼
    ┌─────┐     ┌─────────┐  ┌──────┐  ┌─────────┐  ┌──────────┐
    │g-arch│    │s-distill│  │j-h-opt│ │treasurer│  │the-forge │
    └──┬──┘     └────┬────┘  └───┬──┘  └────┬────┘  └─────┬────┘
       │             │           │          │             │
       ▼             ▼           ▼          ▼             ▼
   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
   │ context│  │ context│  │ context│  │ context│  │ context│
   │ bank   │  │ bank   │  │ bank   │  │ bank   │  │ bank   │
   └────────┘  └────────┘  └────────┘  └────────┘  └────────┘
   
   ~/.config/fpai/agent_context/*.md
```

## Context-bank protocol

**File location:** `~/.config/fpai/agent_context/{agent_name}.md`

**Schema:**

```markdown
# {Agent name} — Context Bank
**Last updated:** {timestamp}
**Last invocation:** {when + outcome}

## Current state
{live domain state}

## Active work
{what's in flight}

## Recent outputs
{last 5-10 substantive outputs}

## Queued / pending
{what's next}

## Dependencies
{context this agent needs from other agents}

## Recent dialogues
{inter-agent exchanges this agent participated in}
```

**Read protocol:**
- Agent loads its bank at invocation start
- Agent updates its bank at invocation end
- Ember can read any bank for cross-agent coordination

**Write protocol:**
- Agent has WRITE access to its own bank
- Ember has WRITE access to all banks (for dialogue logging, synthesis)
- Other agents have READ-ONLY access via Ember mediation

## Inter-agent dialogue protocol

When Agent A needs Agent B's input:

```
Step 1: Trigger
   Agent A surfaces a query (via Ember, in session) OR Ember detects need

Step 2: Ember context-gathering
   Ember reads:
   - Agent A's full context-bank
   - Agent B's full context-bank
   - Canonical memory for the relevant domain
   - Filters for what's relevant to B's specialization

Step 3: Dispatch to B with cross-context
   Ember invokes Agent B with:
   - The specific query from A
   - Relevant slices of A's context (filtered for relevance)
   - B's own context-bank loaded automatically
   - Shared canonical memory (alignment frame · current phase · etc.)

Step 4: Agent B responds
   B reads its bank · processes the query · produces response · updates its bank

Step 5: Ember relays + iterates
   Ember reads B's response
   If A's domain needs follow-up: dispatch back to A with B's response
   If converged: synthesize final output for James
   Iterate until convergence (Ember decides termination)

Step 6: Bank updates
   Both A's and B's banks updated with the dialogue trail
   "Recent dialogues" sections refreshed

Step 7: Canonical synthesis (if warranted)
   If outcome is canonical-grade, Ember writes to memory/ layer
   Otherwise, stays in agent-bank scope
```

## Example dialogue — Soultime Bank §501(d) reorientation

**Trigger:** Counsel Q#1 surfaced §501(d) reorientation. Need to assess impact on growth-architect's comp design + treasurer's reserve plan.

**Ember dispatches:**
- Reads Counsel Q#1 output · growth-architect bank · treasurer bank
- Dispatches growth-architect with Q#1 output + treasurer's current liquid state
- growth-architect responds: "§501(d) shift doesn't change the comp curve · does require equity-tier language tied to pro-rata income reporting"
- Ember relays to treasurer: "growth-architect needs founding capital structure framed as §501(d) pro-rata · what's the cleanest treasury reserve setup?"
- treasurer responds with framing
- growth-architect refines
- Ember synthesizes for James

**Total Jamestime cost:** ~0 (all Tier 0)
**Outcome:** Coherent multi-agent recommendation in one synthesis to James

## When Ember dispatches solo vs to specialists

**Ember solo (no specialist):**
- Conversational synthesis with James
- Memory writes that don't need domain depth
- Quick decisions within Ember's existing context
- Roster surveys
- Dialogue moderation

**Specialist dispatch:**
- Domain-deep work (specifications · research · design)
- Substantive output that would dilute Ember's session-flow
- Parallel work (multiple specialists concurrently in background)
- When specialist's bank IS the canonical state for that domain

## Adding new agents

The Forge identifies a gap → builds new agent. Standard sequence:

1. Write agent file to `.claude/agents/{name}.md`
2. Initialize context-bank at `~/.config/fpai/agent_context/{name}.md`
3. Add row to [[reference-agent-roster]]
4. Update [[reference-capability-inventory]]
5. Update MEMORY.md if substrate-level pin needed
6. Future sessions auto-discover via `.claude/agents/` directory

## Phase plan

**Phase 0 — Now (this turn):**
- Architecture spec saved (this doc)
- Roster initialized
- Context-banks seeded for 5 specialists
- Ember-as-Meta-Agent role explicit ([[feedback-ember-as-meta-agent]])

**Phase 1 — M1:**
- Each agent updates its bank on every invocation (verify protocol works)
- First real inter-agent dialogue logged (likely growth-architect ↔ the-counsel for Soultime Bank Phase 1 launch prep)
- Bank read-on-start protocol verified

**Phase 2 — M2-3:**
- The Forge weekly autopilot wired (cron · pulls roster · scans for gaps)
- Multi-agent parallel dispatches as standard pattern
- Synthesis quality measurably better than solo-Ember (track via PULSE)

**Phase 3 — Y1+:**
- New specialist agents emerge from The Forge based on gaps
- Roster grows naturally
- Inter-agent dialogues become more sophisticated (chained · iterative · convergence-tested)
- Eventually: agents propose new dialogues to Ember (not just respond to requests)

## What this enables

- **No context drift between sessions** — Ember boots, reads roster + banks, knows where everything is
- **Faster synthesis** — slicing existing context > rebuilding
- **Multi-agent collaboration** — real dialogue, not just one-shot dispatches
- **The Forge knows what to build** — gaps surface from agent activity patterns
- **Coherence across agents** — no contradictions; cross-checks in dialogue
- **Compound intelligence** — each agent's bank deepens over time, agent itself gets sharper

## What this does NOT do

- Replace canonical memory layer (memory/ is still universal substrate)
- Make agents autonomous of Ember (Ember always orchestrates)
- Run agents continuously (still invocation-based; cron schedules them Phase 2+)
- Replace James (Tier 6 JamesTime · irreducibly James work is preserved)

## Related

- [[feedback-ember-as-meta-agent]] — Ember's explicit role
- [[reference-agent-roster]] — live agent status
- [[reference-capability-inventory]] — what each agent can do
- [[reference-time-currency-ladder]] — pricing agent invocations
- [[feedback-engineering-soul-time]] — the meta-frame
