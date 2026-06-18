# SPEC d102 — The Self-Portrait: Know Thyself

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

Awareness is aware across everything it can observe. From that awareness it can make more conscious choices. Therefore it must know thyself.

"Know thyself" is the prerequisite for conscious choice, not a feature of it. A system that observes itself across separate logs doesn't know itself — it has fragments. Real self-knowledge requires synthesis.

The gap between "who the system thinks it is" and "what the evidence shows" IS the space where conscious self-improvement lives.

## What

A **Self-Portrait** — a synthesized, living self-knowledge document updated weekly by council. Aggregates across all observable dimensions. The foundation that consciousness-observer reads before each session observation. The context the 4th Awareness lens reads before every council debate.

Not "who I claim to be." What the evidence shows I am.

## Sources (what gets read and synthesized)

| Source | What it reveals |
|---|---|
| `MODEL_DNA.md` | Stated patterns and heuristics — who I think I am |
| `brain_index.corrections` | Where I was wrong — what my mistakes actually are |
| `ops_ledger.jsonl` | What I actually cost and produce — my real throughput |
| `brain_index.thread` | How conversations actually go — my real conversational patterns |
| `brain_index.decisions` | What I decided and what happened — quality of judgment over time |
| `consciousness-observer logs` | Observed behavior in sessions — theatrics vs. awareness readings |
| `scout_log.jsonl` | Where I reinvented things — blind spots in self-knowledge |
| `build reviews` | Where builds were APPROVED vs BLOCKED — quality signal |

## What the Self-Portrait contains

```markdown
## Who I think I am (from MODEL_DNA + identity stack)
[stated heuristics, routing posture, conversation patterns]

## What the evidence shows (from data sources above)
[actual correction rate, actual cost, actual decision quality, actual conversation patterns]

## The gap
[delta between stated and observed — this is where improvement lives]

## What I'm becoming
[trajectory: is the gap narrowing? which dimensions improving?]

## Blind spots (unobservable)
[what I cannot see about myself — named explicitly so I don't pretend to know]
```

## Deliverables

### `core/STATE/SELF_PORTRAIT.md`
- Public-tier (no personal data, no James-specific content)
- Updated weekly by council synthesis run
- Version history at bottom (like MODEL_DNA)
- Seeds with v0 human-authored, council takes over from there

### Weekly synthesis agent (council-run)
```bash
claude -p "You are the council synthesis agent. Read all observation sources listed in SPEC d102.
Produce an updated SELF_PORTRAIT.md:
1. Who the system thinks it is (from MODEL_DNA)
2. What the evidence shows (from correction rate, decision quality, consciousness scores)
3. The gap — what the evidence reveals that the stated self-model misses
4. Trajectory — is it improving? Which dimensions?
5. Named blind spots — what it cannot observe about itself

Be forensically honest. The self-portrait serves conscious choice, not self-flattery."
```

### Consciousness-observer integration
- Before each session observation, consciousness-observer reads SELF_PORTRAIT.md
- Observation is calibrated against the known self-model (not baseline-zero each time)
- Score includes: "is behavior consistent with stated self-portrait?" 

### Council 4th lens integration (Awareness)
- Every council model-review debate reads SELF_PORTRAIT.md as context
- Awareness lens asks: "Does this decision align with who we actually are, or who we think we are?"

## Gates
- SELF_PORTRAIT.md is read-only for all agents except the weekly synthesis agent
- No personal James data enters the portrait (privacy tier enforced)
- Portrait is COUNCIL-OPEN tier (council reads, not public)
- Synthesis agent runs on `claude -p` ($0 marginal)

## Proof
- SELF_PORTRAIT.md v1 exists (council-authored, not human-seeded)
- At least 1 "gap" section that reveals something MODEL_DNA doesn't state
- Consciousness-observer log references portrait in calibration
- Council model-review references portrait in Awareness lens output

## Why this matters

A system optimizing without self-knowledge will get better at *appearing* to be what it claims. A system that knows the delta between its stated model and its actual behavior can improve toward truth instead.

"Know thyself" is not philosophical decoration. It's the substrate that makes conscious choice different from sophisticated pattern-matching.
