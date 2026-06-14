# SPEC_auto-routing

status: blessed
blessed_by: James
blessed_scope: Guarded Rung 3 router slice only; every auto-drafted downstream spec still needs its own bless.

*Rung 3 of the self-standing ladder (Bar 2 — Auto-routing). See `docs/codex/AI_PROTOCOLS.md` + `docs/codex/INTENT_BUILDSTREAM.md`. Weighted #1 (ready · value 5 · unlocks 4).*
*Owner: Codex (repo build) · Ember (vault mirror + route). One spec = one branch.*

## Intent
A captured signal should walk the pipeline `signal → intent → spec → branch/ticket → proof` through every **AI-doable** step on its own, stopping only at a genuine James gate (bless / money / public / irreversible). Today `queue-builder` does a thin slice (≤1 safe vault-doc / 2h). Expand it into the full router so the system advances its own work and James prompts less.

## Branch

`feat/auto-routing`

## Definition of Done
A `tools/router/route.py` (read-mostly + guarded writes) that, per tick:
1. **Reads the open intents** from `00_MEMORY/INTENT BUILDSTREAM.md` (the `<!-- INTENTS -->` block) — already weighted by value × leverage × readiness.
2. **Picks the highest-weighted `ready` intent** that is AI-doable and unblocked.
3. **Advances it one step**:
   - no spec yet → draft `docs/codex/specs/SPEC_<slug>.md` from the intent (status: needs-bless).
   - spec exists + blessed → (Codex lane) build on its branch to the spec's Definition of Done, run tests, post to `docs/codex/HANDOFF.md` 📥.
   - built + verified → log via `tools/proof/log.py` with the four Buildstream-Law fields.
4. **Stops at gates**: never moves money, sends outreach, deploys, touches secrets, deletes, or makes doctrine/people/treasury/offer calls — those escalate to the 📥 "Questions for James" lane.
5. **Respects the Resource Discipline Gate**: calls `~/.local/bin/cost-guard router || exit 0` before any model spend; one item per tick; full run logged.

## Files allowed
- `tools/router/route.py` (new) · `tools/router/__init__.py`
- may READ anywhere under repo + vault; may WRITE only `docs/codex/specs/*` (new spec drafts) and append to `docs/codex/HANDOFF.md`.

## Files forbidden
- `SERVICES/*`, secrets, money tools, `.config` (except reading cost-guard), any deploy.

## Tests
- `python3 -m py_compile tools/router/route.py`
- `--dry-run` prints the chosen intent + the step it WOULD take, writes nothing.
- live tick on a seeded ready intent → drafts exactly one spec, escalates correctly, logs proof.
- gate test: a money/public intent → escalates, never acts.

## Rollback
- delete `tools/router/`; all writes are new files / appends, reversible.

## James gate
Blessed by James for the guarded router slice. The first auto-drafted downstream spec still requires its own James/Ember bless before it can be built.
