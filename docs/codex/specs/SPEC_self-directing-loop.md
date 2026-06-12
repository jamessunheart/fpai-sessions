# SPEC_self-directing-loop

*Rung 2 of the System-That-Builds-The-System ladder. The foreman: a loop that picks the top weighted buildstream intent, hands it to an apprentice (Rung 1) to execute, and escalates to James ONLY at a Reserved-Class step (Rung 0). Generalizes the Results Engine from "drive results-opportunities" to "drive any intent." Owner: Codex. Advisory/gated — proposes + stages + gates; the live-autoloop wiring stays behind James's GO.*

## Source / why
James, 2026-06-09: build the system that builds the system. Rung 0 encoded the boundary; Rung 1 built the apprentice. Rung 2 is the foreman that runs apprentices across the whole buildstream so work advances without James as glue — escalating only the irreducible. Memory: `project-apprentice-unbottleneck-model`, `project-results-engine-and-ideal-interface`.

## The three declarations
- **Milestone (DoD):** `tools/loop/direct.py` reads the buildstream, picks the top weighted READY intent, runs it via `tools.apprentice.run.run_intent`, records outcome (executed-step / gated / done), and moves to the next — escalating Reserved-Class steps as human-edge gates. Demonstrated dry-run across ≥2 intents.
- **Dependency:** Rung 1 (`tools/apprentice/`) + Rung 0 (`tools/reserved/`) — both done. Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main`.

## Definition of Done
1. **`tools/loop/direct.py`** — `tick(*, dry_run=False, max_intents=N)`:
   - Reads buildstream READY intents (reuse the Results Engine's parser where possible; generalize beyond `results:` to any intent with a `next` move + weight).
   - Picks highest-weighted; calls `run_intent`. Honors the apprentice's gate (don't auto-advance past a Reserved-Class pause).
   - Loops to the next intent until `max_intents` or none left. Records a per-tick summary (intents touched · steps executed · gates raised) to a log + HANDOFF.
2. **Escalation = the only James-touch:** the loop NEVER executes a Reserved-Class action; it surfaces gates via the apprentice. Uncertain → gate (fail-safe inherited).
3. **NOT wired into the live autoloop** — `direct.py` is runnable on demand / dry-run; wiring it into `com.fpai.autoloop` is a separate James-GO step (Rung 2.5/3).
4. **Tests** (`tools/loop/test_direct.py`): a buildstream with 2 delegable + 1 reserved intent → executes the delegable, raises exactly the reserved gate(s), advances correctly; dry-run writes nothing.

- Files ALLOWED: `tools/loop/**` (new) · read-only of `tools/apprentice/`, `tools/reserved/`, `tools/results/`, `tools/queue/build.py`, the buildstream. Files FORBIDDEN: wiring into the live autoloop/systemd · any send/money/deploy · secrets · auto-editing prod · executing a reserved action.
- Tests: as above + `git diff --check` (scoped).

## Safety
- 🔴 The loop proposes/stages/gates only. It never executes Reserved-Class. Uncertain → gate. No live-autoloop wiring in this spec.
- Rollback: delete `tools/loop/`; nothing wired live.

## Close-out
HANDOFF 📥 · PROOF LOG (Rung 2 — the foreman runs apprentices across the buildstream, escalating only the irreducible) · BRICK (the self-directing loop pattern). Then Rung 3 (auto-spec drafting) unblocks.
