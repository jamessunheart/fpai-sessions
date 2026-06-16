# Forge Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16
**Function:** #6 — Build Loop

---

## Identity

- **Function:** Forge — autonomous build engine
- **Owner:** `server_build_loop.sh` on server 162
- **Status:** Live
- **Created by:** operational from inception; formalized here

---

## What it does

Forge is the system's self-build engine. It takes decisions from the queue, builds them with Codex ($0 via ChatGPT Max subscription), reviews the result with an independent claude -p reviewer, and auto-merges clean builds — or auto-reverts broken ones. James never touches code; the loop builds continuously, laptop-free.

---

## How it works

**Input:** `brain_index.decisions` WHERE `status='answered' AND needs_build=true`, ordered by `created_at`

**Process (one cycle, every 10 min):**
1. Check kill switch (`/opt/fpai-build/.disabled`) and daily cap (`/opt/fpai-build/.daily_count`)
2. Pick next `BUILD_MAX` decisions (currently 5)
3. For each: write spec to `SPEC_dNNN_slug` worktree directory
4. Run Codex in `--sandbox read-only` mode against the spec — builds files into branch `build/SPEC_dNNN_slug`
5. `ai_review.py` reviews the diff (claude -p, `--effort high`, $0) → `APPROVE` or `REQUEST_CHANGES`
6. `REQUEST_CHANGES`: TG alert with findings, branch held for inspection
7. `APPROVE`: capture `PRE_SHA`, merge into `feat/headless-build`
8. Post-merge import check: `python -c "import curator, curator.decisions"`
9. Import fails: `git reset --hard PRE_SHA`, TG alert, branch held for inspection
10. Import passes: `mark-merged $DID`, TG success notification, ops ledger event

**Output:** merged code on `feat/headless-build` OR blocked branch + TG alert

**Side effects:**
- Ops ledger entry per build (succeed/fail/revert/blocked)
- Daily count file updated (YYYY-MM-DD + count)
- Worktrees cleaned after 24h (`reap_worktrees.sh`)

---

## Quality standard

- Review pass rate ≥ 80% (if lower: specs are too vague or reviewer is too strict)
- Zero auto-reverts due to broken imports within 48h of a good-state merge
- Build loop liveness: daily_count file dated today within 26h
- Build cycle time ≤ 30 min per decision (complex specs may use up to 2h timeout)
- James never needs to notice a bad build — auto-reversion surfaces it first

---

## Current behavior (verified 2026-06-16)

- Runs every 10 min via `fpai-build-loop.timer` on server 162
- `BUILD_MAX=5`, `DAILY_CAP=24`, `TimeoutStartSec=7200`
- Independent reviewer: `tools/merge/ai_review.py` (claude -p, `--effort high`, 300s timeout)
- Auto-reversion: PRE_SHA captured, import check post-merge, `git reset --hard` on fail
- Conflict resolution: auto-resolves conflicts in non-critical files (`REGISTRY.json`, `HANDOFF.md`, `__init__.py`)
- Cost: $0 marginal (Codex via ChatGPT Max subscription + claude -p via Claude Max subscription)
- TG notifications: verdict on every build, immediate alert on block/revert
- 9 builds auto-merged today (d022, d023, d025, d026, d029, d030, d031, d035, d038)

---

## Known gaps

- 2026-06-16: No behavioral smoke test yet (d049 queued — will verify loop liveness externally)
- 2026-06-16: Architecture doc not auto-regenerated after merge yet (d048 queued)
- 2026-06-16: Blueprint not auto-updated after merge yet (d050 queued)
- 2026-06-16: Spec quality varies — no minimum quality gate before codex receives it

---

## Integration map

- **Depends on:** `brain_index.decisions` (queue), `curator.decisions` (mark-merged), `ai_review.py` (review), Codex CLI
- **Used by:** everything — Forge is the delivery mechanism for all other modules
- **DB tables:** `brain_index.decisions` (reads + marks merged)
- **Kill switch:** `touch /opt/fpai-build/.disabled`

---

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | session | BUILD_MAX 1→5, DAILY_CAP 8→24 | Queue was clearing 1 build/day; now 5 per run, 24/day |
| 2026-06-16 | session | Auto-reversion via PRE_SHA + import check | No safety net before; bad builds could break live system |
| 2026-06-16 | session | TimeoutStartSec 1800→7200 | d031 spec took >30 min; build timed out before completing |
| 2026-06-16 | session | ai_review.py --effort high, goal-first prompt | Fable 5: effort dial + brief-not-boss = sharper reviews |
| 2026-06-16 | session | Removed one-at-a-time guard from debate.py | Guard was blocking council when any decision awaited; now decision agent auto-answers |

---

## Test coverage

- `tools/build_loop/test_queue_status.sh` — verifies queue status script
- `tools/build_loop/test_self_audit.py` — self-audit checks
- Smoke TEST 4 (d049): build loop liveness — daily_count file dated today
- Smoke TEST 5 (d049): curator import chain — all modules import cleanly
- NOT tested yet: full end-to-end build cycle with mock Codex output
