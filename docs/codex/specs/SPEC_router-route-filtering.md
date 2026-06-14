# SPEC_router-route-filtering

*Hardening for Rung 3 auto-routing (`tools/router/route.py`). Makes the autonomous loop clean + fully-live-safe. Owner: Codex (owns route.py + its tests). One spec = one branch.*

## Intent
Today the router picks the highest-weighted **ready** intent regardless of its `route`, and would draft a spec even for `route:ember` / `route:james` intents (e.g. it proposes `SPEC_self-standing-one-day-test` for the `ember`-routed test). The autonomous loop should **only auto-act on `route:auto` intents**, and **escalate** everything else to the right builder instead of drafting speculative specs.

## Definition of Done
In `tools/router/route.py`:
1. After choosing the highest-weighted ready intent, branch on its `route`:
   - **`auto`** → proceed with the existing one-step action (draft-spec / build / proof) under all current guards.
   - **`ember` / `codex` / `api`** → **escalate**: append a one-line note to `docs/codex/HANDOFF.md` 📤 ("intent `<id>` is ready, routed to `<route>` — needs that builder") and take NO write action on a spec. Report it.
   - **`james`** (or any gated word) → escalate to the 📥 "Questions for James" lane; never act.
2. `--dry-run` and report-only behavior unchanged (writes nothing).
3. Idempotent: don't append the same escalation note twice in a run.
4. Update `tools/router/test_route.py` with cases: `route:auto` acts · `route:ember` escalates-not-drafts · `route:james` escalates to James lane.

## Files allowed
- `tools/router/route.py` · `tools/router/test_route.py` · `tools/router/README.md`

## Files forbidden
- everything else (vault, money, secrets, services, deploy).

## Tests
- `python3 -m unittest tools.router.test_route` (all pass, incl. new route cases)
- `python3 tools/router/route.py --dry-run` → for the current `test` (route:ember) intent, **escalates** rather than proposing a spec draft.

## Rollback
- revert route.py + test_route.py; escalation notes are appends, hand-removable.

## Why now
Unlocks the autonomous loop running **fully live** (router writing `route:auto` specs) instead of report-only — the last step before the one-day test runs with real self-advancement.
