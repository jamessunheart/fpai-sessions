# SPEC_apprentice-execution-tier

*Rung 1 of the System-That-Builds-The-System ladder. Define an AI apprentice: an agent that takes one buildstream item and drives it end-to-end (plan → do the AI-doable work → test → prove), escalating to James ONLY at its own bottleneck — a Reserved-Class action, per Rung 0's classifier. The unit of the workforce. Owner: Codex. Advisory/gated — an apprentice never executes a Reserved-Class action; it gates.*

## Source / why
James, 2026-06-09: he becomes the un-bottlenecker of an AI fleet, not the doer. Rung 0 encoded WHERE he's required (`tools/reserved/classify.is_reserved`). Rung 1 builds the worker that runs everything below that line and escalates only the irreducible. See memory `project-apprentice-unbottleneck-model`.

## The three declarations
- **Milestone (DoD):** `tools/apprentice/run.py` takes one buildstream intent and produces, per step: either an executed AI-doable action (logged, reversible) OR — when the next step is Reserved-Class — a human-edge gate written via `tools.queue.build.add_gate()`, then pauses that item. Demonstrated on one real intent end-to-end (dry-run + one live gated run).
- **Dependency:** Rung 0 (`tools/reserved/`) — done. Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main`.

## Definition of Done
1. **`tools/apprentice/run.py`** — `run_intent(intent, *, dry_run=False)`:
   - Reads the intent's `next` move (from the buildstream / a passed intent dict).
   - Decomposes into concrete steps (for v1, a simple plan: the named next move + any obvious sub-steps).
   - For each step: call `reserved.classify.is_reserved(step)`. If **delegable** → perform the AI-doable action (or, for code, emit a Codex kickoff / draft to a review lane — do NOT auto-edit prod). If **reserved** → `gate_or_proceed()` writes a human-edge gate (framed question + verbs) and the apprentice **pauses that item** (does not proceed past the gate).
   - Records what it did / what it gated to a per-run log + HANDOFF.
2. **Bottleneck-only escalation:** the apprentice surfaces a gate ONLY for the reserved step it actually hit — not the whole task. (Re-route example: instead of gating "name 5 leads" to James, the apprentice drafts candidate leads + outreach [delegable], then gates only "approve/send these 5" [reserved].)
3. **Fail-safe inheritance:** uncertain steps are Reserved (Rung 0 already defaults that way) → apprentice escalates rather than guessing.
4. **Tests** (`tools/apprentice/test_run.py`): a delegable-only intent runs to completion writing no gate; an intent with a reserved step writes exactly one well-formed gate and pauses; dry-run writes nothing.

- Files ALLOWED: `tools/apprentice/**` (new) · read-only of `tools/reserved/`, `tools/queue/build.py`, the buildstream. Files FORBIDDEN: auto-editing prod code · any send/money/deploy · secrets · wiring into the live autoloop (that's Rung 2) · executing a reserved action.
- Tests: as above + `git diff --check` (scoped).

## Safety
- 🔴 An apprentice NEVER executes a Reserved-Class action — it gates. Uncertain → gate. It drafts/proposes/stages only; humans (or Rung 2's loop, later) act on approval.
- Rollback: delete `tools/apprentice/`; nothing wired live.

## Close-out
HANDOFF 📥 · PROOF LOG (Rung 1 — the apprentice unit exists, gates only its bottleneck) · BRICK (the apprentice run-loop pattern). Then Rung 2 (self-directing loop) unblocks.
