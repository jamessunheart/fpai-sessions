# SPEC d203 — Conversation-Assessment MVP (run the assessment as a chat, not a form)

**Why (James 2026-07-05, doctrine):** forms are the leak (41 landing views/wk → ~0 submits). The front door should be a **conversation**: cheapest sensor for what someone has+needs, cheapest actuator to match+settle. New canonical metrics — **cost/conversation** + **conversation→value** — replace cost-per-form-lead. Full doctrine: `memory/project_conversation_funnel.md`, extends d199 (Ember comms limb).

**Proven already (2026-07-05):** `tools/growth/score_assessment.py` turns a 4-sentence natural message ("i run a small pilates studio... front desk copies everything into a google sheet... pay for some AI thing nobody touches...") into a full personalized Allocation Score — archetype, surprise, 3 opportunities with $ ranges, Monday move. The value engine already eats conversation. This spec builds the conversational front-end around that proven core.

## Design (LIBRARY + CLI — no live bot, no deploy)

Create `tools/growth/conversation_assessment.py`:
1. Accepts a running chat transcript (stdin or `--transcript <file>`) instead of form fields.
2. If key signal is missing (business type OR main bottleneck), returns at most 2–3 warm follow-up questions in Ember's voice, rather than scoring blind. Enough-signal heuristic documented + tested.
3. Once enough signal exists, calls the EXISTING `score_assessment.score_one(transcript)` — do NOT duplicate scoring logic.
4. Instruments the two canonical metrics to a local JSONL ledger: `cost_per_conversation` ($0 subscription marker + run cost) and `conversation_to_value` (1 if a scored deliverable was produced, else 0).
5. Preserves the reserved CTA wall unchanged — deliverable stays DRAFT unless `ASSESSMENT_CTA_URL` is set.

## Guardrails

- Reuse `score_assessment.py`; no scoring duplication. No live-bot wiring, no deploy, no email/outreach, no push/merge/secrets/money. Reversible, scoped.
- The chat SURFACE (Telegram @emberfp_bot / @sunheartbrain_bot / email) is a SEPARATE later spec — this MVP is the transcript→value engine + metrics, callable by any surface.

## Contract

Adds `tools/growth/conversation_assessment.py` + tests. Register in `core/BUILD/REGISTRY.json`. Independent review. Do NOT push or merge.

## Done / Proof

`python3 tools/growth/conversation_assessment.py --transcript <3-sentence natural chat>` prints a full Allocation Score deliverable (archetype + 3 opportunities + Monday move + reserved DRAFT next-step) and appends one metrics row with `cost_per_conversation` + `conversation_to_value=1`. Tests: (a) minimal transcript scores end-to-end, (b) transcript missing business-type/bottleneck returns follow-up questions instead of a score, (c) CTA stays reserved when `ASSESSMENT_CTA_URL` unset.

## Context

- Doctrine: `memory/project_conversation_funnel.md` (cost/conversation · conversation→value · value→$/match · frictionless yes/no).
- Value-layer proof: 2026-07-05, 4-sentence message → full Score via `score_assessment.py`.
- Enqueue note for orchestrator: the autonomous build queue (`brain_index.decisions`) is seeded by the d194 Spot-Topple Orchestrator; external `dec seed` drops `build_spec` (add + set-build required) and needs the loop's DB creds — so this build must be seeded by the orchestrator or the loop, not hand-injected.
