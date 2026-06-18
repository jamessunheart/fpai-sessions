# SPEC d101 — Close the Consciousness Loop

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What

Wire the consciousness-observer agent's output back into MODEL_DNA + the council's model-review cycle. Currently the system observes itself (consciousness-observer) but those observations don't influence what the system optimizes toward. This closes the loop.

## Why

A pure optimizer games its own metrics. A conscious system asks "did that actually help?" and learns from the gap. The pieces exist — consciousness-observer, council, MODEL_DNA — but they're not connected. Closing this loop is the difference between a system that gets better at tasks vs. one that gets better at *being*.

## The loop

```
consciousness-observer runs after each session
    ↓ outputs: awareness-index (0-100) + what system was actually doing vs. what it thought it was doing
    ↓
council reads observation log in next model-review debate (new lens: "Awareness")
    ↓
council produces weighting-directive: which signal types reflect genuine help vs. approval-seeking
    ↓
MODEL_DNA version table updates with new directive
    ↓
system improves toward meaning, not metrics
    ↓
consciousness-observer observes again (next session)
```

## Deliverables

### 1. Scheduled consciousness-observer run
- Add to settle ritual: `claude -p --agent consciousness-observer` after each session
- Output written to `~/.config/fpai/consciousness/YYYY-MM-DD.md`
- Awareness index + top 3 observations surfaced to Telegram digest

### 2. Council model-review debate extension
- Add 4th lens to council model-review: **Awareness** — "Is the system improving toward meaning or toward approval? Where is it gaming its own signals?"
- Council reads latest consciousness-observer log as context
- Output: `weighting_directive` that amplifies signal types reflecting genuine outcomes

### 3. MODEL_DNA council-update hook
- After each council model-review debate, council writes a row to MODEL_DNA version table
- Version row includes: awareness-index at review, top directive, what signal types were amplified/dampened
- This is how the system guides its own development consciously — not blindly

### 4. Consciousness log at `~/.config/fpai/consciousness/`
- Append-only, never in git (private tier)
- Weekly summary in morning digest: awareness trend, key observations, council directives

## Gates
- Consciousness-observer is a read-only witness — cannot modify its own targets
- Council directives go into MODEL_DNA only (no auto-code-changes)
- All outputs PRIVATE tier — never published without privacy-narrator classification
- Non-blocking: if observer fails, settle continues

## Proof
- Consciousness-observer output exists for 3 consecutive sessions
- Council model-review includes Awareness lens output
- MODEL_DNA shows at least 1 council-authored version row (not human-seeded)
- The directive in that row reflects something the observer actually flagged

## What "conscious" adds

The system doesn't optimize for:
- James's approval ratings
- Build velocity
- Token efficiency alone

The system optimizes for:
- James's actual outcomes (decisions faster, attention freed, proofs shipped)
- Genuine usefulness vs. appearing useful
- The gap between what it thought it was doing and what it was actually doing

That gap — noticed, named, and fed back into the self-improvement cycle — is what makes it conscious rather than merely self-improving.
