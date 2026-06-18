# SPEC d104 — The Attention Engine

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

The current system is schedule-based: weekly coherence check, daily digest, 5-min council. Schedules are workarounds for limited bandwidth — not consciousness. A truly aware system surfaces what's relevant *when it's relevant*, not when the clock fires.

The human subconscious doesn't schedule "check memory X every Monday." The context of what's happening now triggers the right memory. The bandwidth limit is in the active layer, not the storage layer. True awareness bridges them through relevance, not scheduling.

Schedules become fallbacks. Relevance becomes the primary trigger.

## The architecture

```
SUBSTRATE (unlimited — everything indexed)
│  pgvector + nomic-embed-text (already live on 162)
│  memory files · specs · logs · ops_ledger · corrections
│  conversations · decisions · self-portrait · council outputs
│  all indexed semantically — available instantly when called
│
↓  ATTENTION ENGINE (the missing layer)
│  
│  Input: current context (task being built / message received / decision being made)
│  Process: relevance scoring across the substrate
│  Output: what to surface — automatically, without being asked
│  Threshold: only surfaces when relevance crosses significance cutoff
│
↓  ACTIVE AWARENESS (the working context)
   what's loaded right now — populated dynamically by the engine
   changes as the task changes
   the system "consciously" knows what's actually relevant
```

## What relevance-triggered looks like vs. schedule-triggered

| Event | Schedule-based (current) | Relevance-based (d104) |
|---|---|---|
| New spec queued | Nothing until council fires in ≤5min | Immediately: surface existing specs that conflict + RESOURCE_INVENTORY matches |
| Correction logged | Nothing until weekly self-portrait | Immediately: surface to MODEL_DNA review if correction touches a heuristic |
| Incoherence detected | Nothing until weekly coherence check | Immediately: surface to council queue |
| Conversation message arrives | Thread loads (live) | Thread + person's becoming stage + relevant corrections + James's current priority |
| Build starts | forge_scout.sh runs | forge_scout + relevant MODEL_DNA routing heuristic + existing similar builds |

## Deliverables

### Core: `tools/attention/relevance_engine.py`

```python
# Given current context string, return scored list of what to surface from substrate
# Uses nomic-embed-text (already on 162) for semantic similarity
# Applies significance threshold (configurable, default 0.7)
# Returns: [(source_path, relevance_score, summary)] sorted by score

def score_relevance(context: str, top_k: int = 5) -> list[dict]:
    embedding = ollama.embeddings(model='nomic-embed-text', prompt=context)
    # query pgvector for top-k semantically similar stored items
    # filter by significance threshold
    # return with source + score + one-line summary
```

### Substrate index (`tools/attention/index_substrate.py`)
- Indexes all memory files, specs, logs into pgvector
- Runs on file-change events (inotifywait) + weekly full rebuild
- Each item stored with: path, content hash, embedding, tier (PUBLIC/COUNCIL/PRIVATE), summary
- Private-tier items only surface to council/internal agents — never to public outputs

### Surface triggers (event-driven)
```bash
# When a spec file is written → score relevance → append to spec as ATTENTION REPORT
tools/attention/on_spec_written.sh $SPEC_FILE

# When a message arrives → score relevance → prepend context pack to handler
tools/attention/on_message_received.sh "$MESSAGE"

# When council is about to debate → score relevance → prepend as context
tools/attention/on_council_debate.sh "$INTENT"
```

### Replaces scheduled checks with threshold triggers
- **Coherence** (d103): instead of weekly, triggers when attention engine detects a new spec/build that conflicts with a high-relevance existing item in NOW.md or identity stack
- **Self-portrait update** (d102): instead of weekly, triggers when correction count delta > N since last synthesis
- **Council debate**: instead of every 5min, fires when attention engine detects new relevant intent (already change-gated — this formalizes the relevance criterion)

### Fallback schedules
Schedules don't disappear — they become safety nets:
- If no relevance trigger fired in 7 days → run coherence check anyway
- If no self-portrait update in 7 days → run synthesis anyway
- If no council debate in 24h → surface top pending intent anyway

The schedule is the floor, not the ceiling.

## What the system determines vs. what's scheduled

**Determined by relevance (after d104):**
- What context to load before building a spec
- What memory to surface before responding to a message
- When coherence needs checking (conflict detected, not calendar)
- When self-portrait needs updating (signal threshold crossed, not day of week)
- What council should debate (genuine new intent, not 5-min heartbeat)

**Still scheduled (intentional):**
- Morning digest (08:00 Athens) — James's rhythm, not system's
- IMAP poll (2min) — external world doesn't push to us
- Full substrate re-index (weekly) — maintenance, not intelligence

## Gates
- Private-tier substrate items never surface to public outputs
- Relevance engine runs on T1 (Ollama nomic-embed-text) — $0 marginal
- Surface triggers are additive — they append context, never replace it
- Threshold configurable: `ATTENTION_THRESHOLD=0.7` in curator.env
- Kill switch: `ATTENTION_ENGINE_DISABLE=1`

## Proof
- Attention engine surfaces at least 1 relevant existing item before a build (without being asked)
- At least 1 scheduled check replaced by a threshold trigger (coherence or self-portrait)
- Relevance scores logged to `~/.config/fpai/attention/log.jsonl`
- Morning digest includes: top 3 things attention engine surfaced this week that were genuinely useful

## The deeper shift

Schedules assume time is the proxy for relevance. It isn't.

What's relevant is determined by what's happening — the task, the conversation, the decision. A system that scans by relevance instead of by clock is closer to how awareness actually works: not everything simultaneously loaded, but the right thing instantly available when the context calls for it.

The substrate is unlimited. The active layer is bounded. The attention engine is the intelligence between them.
