# SPEC_consequence-watch

*Conscious Intelligence's Recursive Proof, made mechanical: after a ship, track whether it actually served the good — consequence as feedback, not just "it shipped." Deepens the learn-proof. Owner: Codex. One spec = one branch.*

## Intent
Proof rows record what shipped + what they unlock, but nothing checks the *consequence* (did the next run actually get cheaper/lighter? did it serve the highest living good?). Add a read-only consequence tracker so the loop learns from results, not just completions.

## Definition of Done
A `tools/consequence/watch.py` that:
1. reads the PROOF LOG entries (read-only) + the cost ledger,
2. for recent ships, records an observable consequence signal: did James-touch-count trend down? did metered spend stay in gate? did a later proof reference this one's `Unlocks next` (i.e., the unlock actually happened)?
3. writes a `CONSEQUENCE WATCH` summary (vault note or a section): per recent ship → unlock-realized? (yes/pending) · cost-impact · a one-line "served the good?" read,
4. `--dry-run` prints, writes nothing. No money/network/Reserved action.

## Files allowed
- `tools/consequence/watch.py` · `tools/consequence/__init__.py` · may CREATE `00_MEMORY/CONSEQUENCE WATCH.md`

## Files forbidden
- `tools/router/*` · `tools/autobuild/*` · `tools/index/*` (disjoint lanes), SERVICES, secrets, money, deploy.

## Tests
- `python3 -m py_compile tools/consequence/watch.py`
- `--dry-run` produces a consequence summary from the existing PROOF LOG, writes nothing.

## Rollback
- delete `tools/consequence/` + the generated note.

## Why now
Closes the learn loop: turns→learns becomes measurable (did the unlock realize? did it serve the good?), feeding the care-weighting.
