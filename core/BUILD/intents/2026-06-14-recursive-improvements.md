# Intent — recursive improvements (2026-06-14)
**status:** open · **source:** recursive_improver (watched James's comms)

Codex: process the proposals in `core/BUILD/improvement_proposals/2026-06-14.md`.

- Build the **[SAFE-AUTO]** items (3) on `codex/<slug>` branches off `feat/headless-build`, behind the merge-gate. Review diff, then surface to James to merge.
- Leave **[NEEDS-JAMES]** items (0) as proposals — James decides.
- 🔴 GUARDRAIL: do NOT merge to main. If `core/BUILD/REGISTRY.json` doesn't exist yet, build `docs/codex/specs/SPEC_build-registry-and-merge-gate.md` FIRST — it is the gate that makes everything after it safe.
