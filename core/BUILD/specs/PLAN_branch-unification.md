# PLAN — Branch Unification (one repo, one branch, one truth)

*Drafted 2026-07-03 · the deepest remaining incoherence. Execute as a dedicated session, not a side-task.*

## The problem

Laptop works on `test/merge-base`; 162 lives on `feat/headless-build`. Diverged since **2026-06-25** (merge-base). Every cross-body sync today is hand-carried (scp) — the July mail/canon/identity staleness bugs were all symptoms of this split.

## Measured divergence (2026-07-03)

- 32 commits only on `test/merge-base` (laptop: fiart phases, governance, state/canon, sites, tools)
- 89 commits only on `feat/headless-build` (162: build-loop spec merges d129–d144, curator, vault sync)
- **17 files changed on BOTH sides** — the conflict surface. Mostly benign classes:
  - *Same-content-carried-both-ways* (CONSTITUTION, FOUNDATION, LEARNING_METRICS, specs d129–d133, identity/STORY): laptop scp'd these to 162 — content near-identical → trivial resolves.
  - *Generated/state files* (HOT_STATE, AI_GOALS, CLAUDE.md, PROTECTED_PATHS): take-newest or union.

## Target end-state

**`feat/headless-build` becomes the ONE working branch** (162's loop already governs it: auto-merge + Constitution Check + independent review). Laptop tracks the same branch via the `server162` remote. `main` stays untouched/archival. `test/merge-base` retired after merge.

## Steps (dedicated session · ~1-2h · reversible at each step)

1. **Freeze:** pause 162 build loop (`touch /opt/fpai-build/.disabled`) + laptop autoloop. Tag both branches (`pre-unify-laptop`, `pre-unify-162`).
2. **Merge on the laptop:** `git checkout -b unify server162/feat/headless-build && git merge test/merge-base`. Resolve the ~17 both-sides files (rules above: doctrine=identical, state=newest, PROTECTED_PATHS=union).
3. **Verify:** py_compile all touched tools · run fpull chain · run build-loop dry pieces (`curator.decisions pending-builds`) · heartbeat green.
4. **Land:** push `unify` → 162, fast-forward `feat/headless-build` there; laptop `git checkout feat/headless-build` tracking `server162/feat/headless-build`.
5. **Unfreeze:** remove `.disabled`, watch one full build-loop tick + one vault-sync cycle. Heartbeat board green ×2 cycles.
6. **Retire:** delete `test/merge-base` locally (tag survives as rollback). Update CLAUDE.md session-start step 7 ("checkout feat/headless-build && git pull server162" — becomes literally true).

## After-rules (prevents recurrence)

- Laptop commits → same branch, push to server162 at settle (replaces scp-carrying).
- 162 auto-merges stay on the same branch (already true).
- Weekly heartbeat-style check: `git rev-list --count` between local and server162 HEAD > 20 → surface in HEARTBEATS.md.

## Rollback

Tags `pre-unify-laptop` / `pre-unify-162`; nothing force-pushed; `.disabled` kill switch during the window.
