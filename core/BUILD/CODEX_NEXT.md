# CODEX — what to build next (priority order)

**Set 2026-06-14 by Ember (terminal) after wiring the recursive-improvement loop.**
Read this first. Build top-down. Stay on `feat/headless-build` / `codex/<slug>` branches — **never PR to main.**

## ✅ DONE — the merge-gate (built + tested by Ember, 2026-06-14)

`core/BUILD/REGISTRY.json` · `docs/codex/SESSION_CONTRACT.md` · `tools/merge/merge_gate.sh` (5/5 tests pass) · HANDOFF build-protocol section. **The guardrail is live** — parallel builds are now safe. Every Codex session: read `SESSION_CONTRACT.md`, register in `REGISTRY.json`, never push/PR-to-main; Ember runs the gate + merges.

## 🔴 PRIORITY 1 — process the recursive-improvement queue (now safe — the gate exists)

**Source:** `core/BUILD/intents/*-recursive-improvements.md` → points at `core/BUILD/improvement_proposals/<date>.md`
These come from `tools/recursive_improver.py`, which watches James's communications and proposes structural improvements.
- Build the **[SAFE-AUTO]** items on `codex/<slug>` branches, behind the merge-gate. Review the diff, surface to James to merge.
- Leave **[NEEDS-JAMES]** items as proposals.

## The loop this serves

`recursive_improver` watches James's comms → drafts specs → routes here → Codex builds (gated) → Ember reviews → James merges → reflect → repeat. James stays upstream; the system needs him less each cycle. (See `reference_routing_is_the_work.md`.)
