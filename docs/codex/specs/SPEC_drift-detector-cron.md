# SPEC_drift-detector-cron

*For Conscious Codex 1 (state domain — owns `tools/state_reconciler/`). Turn the state reconciler into a STANDING drift detector: on a schedule, diff the SSOTs and flag staleness/drift, write a report, and (when drift is real) open a human-edge gate. Make the system notice its own lies automatically. Owner: Codex. Read-only + report + gate; no auto-fix.*

## Source / why
Fable 5 audit (2026-06-10): NOW.md was 32 days stale, violating its own 7-day rule; truth scattered across 5 surfaces with no automated reconciler. `tools/state_reconciler/` exists (committed `290186be`) but runs only on demand. Automate the noticing — that's North Star Phase 0.

## The three declarations
- **Milestone (DoD):** a scheduled run (`tools/state_reconciler/cron.py` or a `--report` mode + a documented cron/launchd entry, NOT installed live) that flags: NOW.md `Last Updated` older than 7 days · rung/intent buildstream-vs-actual drift · mirror staleness. Writes `docs/codex/STATE_STATUS.md` and, when drift crosses a threshold, calls `tools.queue.build.add_gate()` once (deduped) to surface it to James.
- **Dependency:** `tools/state_reconciler/` (done). Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main`.

## Definition of Done
1. Extend the reconciler with a `report()` that computes staleness/drift across NOW.md, the buildstream rungs, and the queue; severity-ranked.
2. On real drift (e.g. SSOT >7d stale), write ONE deduped human-edge gate ("NOW.md is N days stale — refresh?") via `add_gate`. Never auto-edit the SSOT.
3. Provide the schedule as a documented, NON-installed cron/launchd snippet + a `--dry-run` that writes nothing.
4. Tests: a fresh SSOT → no gate; a >7d-stale fixture → exactly one gate + report flags it; dry-run writes nothing.

- Files ALLOWED: `tools/state_reconciler/**` · `docs/codex/STATE_STATUS.md` · read-only of SSOTs · write gates via the queue helper. FORBIDDEN: installing the cron live · auto-editing any SSOT · money/send/deploy/secrets.

## Safety
- 🔴 Reports + gates only; never auto-fixes an SSOT. Uncertain → flag, don't change. No live cron install (James installs).
- Rollback: revert the reconciler additions + remove the snippet.

## Close-out
HANDOFF 📥 · PROOF LOG (the system now notices its own SSOT drift automatically) · BRICK.
