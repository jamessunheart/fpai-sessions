# BUG LOG — the brain's fault record

The orderly record of every bug found, its **root cause** (not just symptom), how
it was fixed, the **brain version** it was fixed in, and the git ref to **revert**
to. Append-only. Newest first.

**The flow:** error (ops_ledger) → root cause (`tools/rca/autonomous_rca.py`) →
fix (git commit) → **BUG_LOG entry** → version bump + git tag → if the root is
structural/recurring, it graduates to a Principle in [AI_PRINCIPLES.md](AI_PRINCIPLES.md).

**Revert:** `git checkout brain-v<X.Y.Z>` returns the brain to any tagged version.
Versioning: MAJOR = architecture change · MINOR = new capability · PATCH = bug fix.

**Status vocab:** FIXED (root fixed + verified) · MITIGATED (symptom handled, root
open) · ROOT-CAUSED (root known, class-fix queued) · OPEN.

---

## Brain v1.0.0 — 2026-07-03 · structured versioning begins
_Anchor. Prior state = ~6 months, 125 merged specs, no version tags. This is the first tagged brain version and the first structured bug batch._

| ID | Symptom | Root cause | Root (P#) | Fix | Status | Commit |
|----|---------|-----------|-----------|-----|--------|--------|
| BUG-001 | Awareness probe scored 0% for 79 consecutive probes | Probe imported the **repo** copy of build_context, not the live bot (`/opt/sh-brain-src`); the repo copy's DB import fails silently | [P2](AI_PRINCIPLES.md) | Probe targets the live path, repo as fallback | FIXED (100% now) | `fix(measurement)` |
| BUG-002 | 207 of 212 corrections were garbage (empty original) | Capture fired on bare words (no/actually/fix) with no verified prior bot turn — signal recorded without its referent | [P1](AI_PRINCIPLES.md) | Require correction phrases + a real bot turn; purged 207 (backed up) | FIXED | `fix(measurement)` |
| BUG-003 | Reality-check marked all 113 merged specs "dead" + spam-queued 113 repairs | Demanded proof from a channel specs never emit; overwrote `build_status` (build axis) with a liveness verdict | [P2](AI_PRINCIPLES.md) [P6](AI_PRINCIPLES.md) | Write `reality_status` only + circuit breaker (skip if >50% flagged); data restored | FIXED | `fix(reality-check)` |
| BUG-004 | Nightly metabolism ran but shipped nothing | Wrote a work-order prompt then stopped — `optimizer: "no command configured"`; merged-but-dead | [P1](AI_PRINCIPLES.md) | Bridge work-order → brain_index decision → build loop | FIXED (d143 built) | `feat(metabolism)` |
| BUG-005 | d143/d144 sat unbuilt ~12h looking like a "strategic wait" | `spec_written=true` set before the codex build; a failed build orphans the decision (queue skips spec_written=true) | [P1](AI_PRINCIPLES.md) | Data unblock (reset flag); durable query/ordering fix queued | MITIGATED | `data` |
| BUG-006 | `diagnostic_error` fired **96×** (swallowed each time) | `curator` name collision — repo-root stub + live package both importable as top-level `curator`; import resolves to the wrong one | [P2](AI_PRINCIPLES.md) [P3](AI_PRINCIPLES.md) | RCA identified; class-fix (rename stub + fail-loud guard) queued | ROOT-CAUSED | — |
| BUG-007 | 26 build worktrees stuck >24h (failed `failed` alert 26×) | Work-items created assuming they reach a terminal state; no reaper for builds that fail review | [P1](AI_PRINCIPLES.md) | RCA identified; class-fix (terminal-state lifecycle + reaper) queued | ROOT-CAUSED | — |
| BUG-008 | `debate_error: response did not contain a JSON object` (13×) | LLM text treated as guaranteed-parseable; no shared tolerant extractor at any LLM→JSON boundary | [P2](AI_PRINCIPLES.md) | RCA identified; class-fix (shared `robust_json()` helper) queued | ROOT-CAUSED | — |

**Class-fixes this batch surfaced (become the next builds):** eliminate the `curator`
name collision · terminal-state reaper for every pipeline work-item · one shared
`robust_json()` at every LLM→JSON boundary. Each kills a whole class, not one instance.
