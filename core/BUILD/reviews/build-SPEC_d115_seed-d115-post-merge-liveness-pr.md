# AI Review — build/SPEC_d115_seed-d115-post-merge-liveness-pr

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds optional per-decision post-merge liveness_check shell probe on server 162 with kill switch, timeout, ops-ledger logging and HOT_STATE surfacing — matches spec, default no-op, well-guarded; safe to merge with eyes on the trust boundary.

## Findings
- New capability: run_liveness_probe executes an operator-provided command via `timeout bash -lc "$check"` on prod server 162 post-merge. This is arbitrary code execution by design. It is gated (empty/absent check = no-op early return, LIVENESS_PROBE_DISABLE=1 kill switch, timeout-bounded, cwd=repo), and no current code path WRITES decisions.liveness_check — only manual operator/curator can. Before any row carries a check, verify the write path (esp. the Telegram d###: intercept and any external decision seeding) cannot set liveness_check, or RCE on 162 becomes reachable via DB write.
- Silent live-schema mutation: ensure_liveness_column() runs `ALTER TABLE IF EXISTS brain_index.decisions ADD COLUMN IF NOT EXISTS liveness_check TEXT` against the live 162 brain_index on every pending-builds call (~every 10min). Idempotent, nullable, additive, and falls back to `NULL::text` if DDL is rejected — low risk, but it is a prod DB migration that happens implicitly rather than via a reviewed migration step.
- Probe runs AFTER merge and always returns 0 — a failing liveness check does not block or roll back the merge (correct per 'merged≠live' detection intent), so a bad merge still lands and is only surfaced retroactively via liveness:fail + queued repair spec. Confirm this is the intended posture (detect, not prevent).
- Followup-spec loop is bounded only because repair specs are seeded without a liveness_check; if a future repair spec is ever given one and keeps failing, queue_liveness_followup could generate repeated repair decisions each loop. Low likelihood, worth a guard later.
- schema.sql uses unqualified `decisions` while decisions.py uses `brain_index.decisions` — relies on search_path; cosmetic but worth aligning.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
