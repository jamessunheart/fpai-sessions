# SPEC_state-reconciler

## Intent

Build a narrow closeout helper so each work cycle can reconcile the system's current state without James manually weaving proof, index, self-model, HOME/NEXT, and handoff surfaces.

## Why This Is Next

Auto-proof, index refresh, reflection surfacing, and daily/HOME refresh now exist as separate pieces. The next adjacent unlock is to run them as one safe closeout sequence before Rung 3 auto-routing depends on them.

## Downstream Intent Unlocked

Rung 3 Auto-routing gets a trustworthy current-state report. Fresh sessions can continue from one reconciled view instead of guessing across stale surfaces.

## Branch

`feat/state-reconciler`

## Files Allowed

- `tools/state_reconciler/**`
- `docs/codex/STATE_CLOSEOUT.md`
- `docs/codex/specs/SPEC_state-reconciler.md`
- Existing helper imports only where required for read-only integration.

## Files Forbidden

- `core/STATE/identity/**`
- `SERVICES/**`
- `.claude/hooks/**`
- Direct edits to vault notes except through existing approved helper scripts.
- Direct edits to Ember-owned lanes in `docs/codex/HANDOFF.md`.
- Money movement, outreach, deploys, secrets, service stops, service moves, service deletes, or production background jobs.

## Build

Create a repo helper, suggested entrypoint:

```bash
python3 tools/state_reconciler/closeout.py --dry-run
```

The helper should:

1. Detect the repo, branch, dirty files, and whether the vault is available.
2. Report collision risk before writing. If known coordination files are dirty, continue only in dry-run/report mode unless explicitly allowed.
3. Reconcile proof state by checking the newest PROOF LOG entry and, if arguments are supplied, delegating to `tools/proof/log.py` rather than duplicating proof-writing logic.
4. Refresh the Index of Indexes by delegating to `tools/index/refresh.py` when available.
5. Resurface reflections by delegating to `tools/reflect/log.py --resurface` when available.
6. Refresh HOME/daily surfaces by delegating to `tools/decisions/daily_sync.py` when available and vault access exists.
7. Write a repo-side closeout report to `docs/codex/STATE_CLOSEOUT.md` with:
   - current branch and dirty-file summary,
   - latest proof signal,
   - index/self-model refresh result,
   - HOME/NEXT result if accessible,
   - suggested HANDOFF snippet for Codex's owned `📥` lane,
   - risks, skipped steps, and next unlocked move.

## Definition Of Done

- `closeout.py` supports `--dry-run` and does not write by default.
- The helper has clear skip behavior when the vault or optional tools are unavailable.
- The helper never edits Ember-owned `📍` or `📤` handoff lanes.
- The helper refuses or reports instead of overwriting dirty coordination files.
- The generated `docs/codex/STATE_CLOSEOUT.md` is secret-free and phone/cloud readable.
- A temp-vault or dry-run test proves the sequence can run without iCloud access.

## Tests

- `python3 -m py_compile tools/state_reconciler/closeout.py`
- `python3 tools/state_reconciler/closeout.py --dry-run`
- If a temp fixture is added, run the fixture test and include output in the run summary.
- `git diff --check`

## Rollback

Delete `tools/state_reconciler/` and `docs/codex/STATE_CLOSEOUT.md`; remove this spec from the buildstream if it is no longer the next unlock.

## Notes For Codex

This is a coordination helper, not an authority. It can gather, refresh, and report. It must not decide doctrine, route treasury, move services, or write Ember-owned lanes. If there is uncertainty, produce the closeout report and ask James/Ember.
