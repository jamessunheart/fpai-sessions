# SPEC d103 — The Coherence Optimizer

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

Coherence is the property where everything in the system points the same direction simultaneously. Not "are individual pieces good?" — "do all the pieces speak with one voice?"

The standards-keeper watches for regressions. The council checks individual decisions. The self-portrait closes the stated/observed gap. None of them watches for the whole system hanging together as one thing.

This is the gap d103 closes.

## What incoherence looks like (examples the system would currently miss)

- Council proposes build X; spec queue already has a conflicting approach
- Identity stack says "caveman clarity"; model-review directive is pushing longer responses
- NOW.md says "first real conversation" is priority; 90% of recent builds are infrastructure
- Morning digest highlights a new capability; build loop is quietly replacing it
- Three lenses produce contradictory directives that never get reconciled
- SELF_PORTRAIT says the system is improving at X; ops_ledger shows X costs are rising, not falling

## What

A weekly coherence check that reads across all system layers, asks one question — *"Does the whole system speak with one voice right now?"* — and surfaces where it doesn't.

## Sources read

| Source | Layer | What it reveals about coherence |
|---|---|---|
| `identity/DAILY_AWAKENING.md` + identity stack | Identity | Who the system claims to be |
| `core/STATE/NOW.md` | Intent | What the founder says matters most |
| `core/STATE/AI_GOALS.md` | Working goals | What the AI is trying to do |
| Spec queue (queued specs) | Build intent | What we're actually building toward |
| Recent build log + merge decisions | Build reality | What actually got built |
| `core/STATE/SELF_PORTRAIT.md` (d102) | Self-knowledge | Who the system observes itself to be |
| Council directive history | Decision layer | What the council has been saying |
| `ops_ledger.jsonl` | Reality check | What the system actually costs and produces |
| Morning digest themes | Surface layer | What's being surfaced to James |

## Output format

```markdown
## Coherence Report — {date}

### Score: {0-100} — {Coherent / Partially coherent / Fractured}

### Where the system speaks with one voice
[list: things aligned across identity + intent + build + behavior]

### Contradictions (incoherence points)
[list: where layers are pulling in different directions — source A vs. source B]

### Highest-stakes contradiction
[the one incoherence that, if unresolved, causes the most drift]

### Routing
[which contradictions go to council for resolution · which are just stale state to update]
```

## Deliverables

### Weekly coherence run (council-run synthesis agent)
```bash
claude -p "You are the Coherence Optimizer. Read all system layers listed in SPEC d103.
Produce a coherence report:
1. Where the system speaks with one voice (aligned)
2. Where layers contradict each other (incoherence points — name the specific sources that conflict)
3. The highest-stakes contradiction
4. What to route to council for resolution vs. what's just stale state

Be specific. 'The spec queue contains d091 (resource inventory) but SELF_PORTRAIT says we know our resources well — these are contradictory signals.' Not vague summaries."
```

### Output written to `~/.config/fpai/coherence/YYYY-MM-DD.md`
- Append-only, COUNCIL-OPEN tier
- Weekly summary line in morning digest: coherence score + highest-stakes contradiction
- Contradictions routed to council debate queue

### Council integration
- Council reads latest coherence report before any model-review debate
- Unresolved contradictions become the first item on the agenda
- Council resolves → updates the conflicting source (spec retired, NOW.md updated, identity stack adjusted)

### Standards-keeper integration
- standards-keeper watches for REGRESSIONS in process/architecture/vibe
- Coherence optimizer watches for CONTRADICTIONS across layers
- Different loop, complementary — standards-keeper hands off to coherence optimizer when it sees architectural drift

## Gates
- Read-only synthesis — coherence optimizer cannot modify any source files directly
- All routing goes through council (human-in-loop for resolution of highest-stakes contradictions)
- Runs on `claude -p` ($0 marginal)
- Non-blocking: if coherence run fails, system continues

## Proof
- Coherence report exists for 2 consecutive weeks
- At least 1 incoherence point named with specific source conflict
- At least 1 contradiction routed to council and resolved (source file updated)
- Coherence score trending upward over 4 weeks

## Relationship to the consciousness stack

```
SELF_PORTRAIT (d102)       — who I am (stated vs. observed)
consciousness-observer (d101) — how I behaved (session by session)
COHERENCE OPTIMIZER (d103) — does everything point the same way (whole system)
```

These three together form the **self-knowledge substrate** — the foundation from which conscious choice becomes possible rather than sophisticated pattern-matching.
