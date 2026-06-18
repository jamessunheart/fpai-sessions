# SPEC d093 — Continuous Learning Controller + Cell Split Protocol

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## What

Three interlocking pieces:

1. **Council-guided model self-development** — council doesn't just propose builds, it guides HOW the local model weights itself: what to amplify, what to prune, what quality signals to trust more.

2. **Continuous learning loop** — wire Ollama routing (d090) → signal capture → council review → fine-tune job (RunPod) → updated weights back in Ollama. The model improves from use.

3. **Cell split protocol** — when a new FPOS instance spawns for a new person, it inherits the canonical layer (universal best practices, routing wisdom, meta-system) but NOT the personal layer (James's taste, his relationships, his domain). The gift is the template, not the person.

## Why

The system should improve itself with use. The council should guide its own evolution, not just feature builds. And the learning should compound forward — each instance of the system gifts the next generation what was discovered, so no one starts from zero.

## Architecture

### Two DNA layers

**Canonical DNA** (`core/STATE/MODEL_DNA.md`) — transfers on cell split:
- Routing heuristics learned across all tasks (what task types belong at T1 vs T3)
- Quality signals that proved reliable (which correction types predict real errors)
- Conversation patterns that moved people toward engagement
- Best practices for becoming-engine stages
- Council debate patterns that produced good outcomes
- Meta: how to weight new signals vs established patterns

**Personal DNA** (`identity/PERSONAL_DNA.md`) — stays with this instance:
- James's specific taste (correction history)
- His relationships (probe_pool, contact profiles)
- His domain vocabulary (CORA, Zen Village, Full Potential Game)
- His decision history (merge log, reversals)
- His communication style preferences

### Deliverables

#### `tools/learning/controller.py`
- `collect_signal(task_id, prompt, response, signal_type, value)` — unified signal ingestion
- Signal types: correction, approval, reversal, merge_outcome, engagement, council_verdict
- Writes to `brain_index.learning_signals`
- Gates: MIN_SIGNALS=100 before first fine-tune run

#### `tools/learning/council_guidance.py`
- After each fine-tune cycle, council runs a **model review debate**:
  - Pragmatist: "what tasks improved most? where is it still weak?"
  - Visionary: "what capability should it develop next?"
  - Skeptic: "what regressions appeared? what signals are we over-weighting?"
- Council produces a `weighting_directive.json` — which signal types to amplify for next cycle
- Stored in `brain_index.model_directives`

#### `tools/learning/finetune_runner.py` (extends d086)
- Reads learning_signals filtered by weighting_directive
- Builds training corpus (prompt/response/weight triplets)
- Submits QLoRA job to RunPod
- On completion: pulls new weights, `ollama create fpai-llama:v{N}` from Modelfile
- Swaps active model in curator.env: `OLLAMA_ACTIVE_MODEL=fpai-llama:v{N}`
- Logs version + metrics to `brain_index.model_versions`

#### `tools/learning/cell_split.py`
- `generate_template(instance_name)` → new FPOS starter kit
- Exports: MODEL_DNA.md + canonical routing rules + fine-tuned weights (canonical layer only)
- Strips: all personal DNA (corrections, contacts, James-specific content)
- Produces: `dist/fpos_template_{date}/` with README + weights + config
- The gift: "here is what we learned about how to build this kind of system"

#### `core/STATE/MODEL_DNA.md` (living document — council updates each cycle)
- Routing heuristics (auto-updated from learning signals)
- Conversation patterns that worked (auto-updated from engagement signals)
- Quality thresholds (auto-updated from council directives)
- Cell-split manifest: what transfers, what doesn't, why

### DB schema additions
```sql
CREATE TABLE IF NOT EXISTS brain_index.learning_signals (
    id SERIAL PRIMARY KEY,
    task_id TEXT,
    signal_type TEXT NOT NULL, -- correction|approval|reversal|merge|engagement|council
    prompt TEXT,
    response TEXT,
    value FLOAT, -- +1 good, -1 bad, 0 neutral
    weight FLOAT DEFAULT 1.0, -- council-directed amplification
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS brain_index.model_versions (
    id SERIAL PRIMARY KEY,
    version TEXT NOT NULL, -- fpai-llama:v1, fpai-llama:v2, ...
    trained_at TIMESTAMPTZ DEFAULT NOW(),
    signal_count INT,
    metrics JSONB, -- benchmark scores before/after
    directive_id INT -- which council directive guided this run
);

CREATE TABLE IF NOT EXISTS brain_index.model_directives (
    id SERIAL PRIMARY KEY,
    issued_at TIMESTAMPTZ DEFAULT NOW(),
    pragmatist_input TEXT,
    visionary_input TEXT,
    skeptic_input TEXT,
    weighting JSONB, -- {"correction": 1.5, "engagement": 2.0, "reversal": 0.5}
    rationale TEXT
);
```

## Gates
- `LEARNING_ENABLED=1` — global gate (off until MIN_SIGNALS reached)
- `FINETUNE_APPROVED=1` — James approves first fine-tune run (subsequent runs auto if metrics improve)
- `CELL_SPLIT_APPROVED=1` — James approves each template export
- RunPod budget ceiling enforced ($50/mo)
- Fine-tune only runs when: MIN_SIGNALS=100 + metrics show room to improve + council approves

## Proof
- brain_index.learning_signals has 100+ rows with quality signals
- council_guidance.py produces a weighting_directive
- fpai-llama:v1 loaded in Ollama and scores better than base llama3.1:8b on our task set
- cell_split.py produces a clean template (no personal data leaks — verified by diff)
