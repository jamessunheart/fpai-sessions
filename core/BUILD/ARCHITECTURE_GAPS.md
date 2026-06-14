# Architecture gaps — Command Constellation: what's built vs what's not

**Gap-analysis 2026-06-14 (checked against SYSTEM_MAP + repo + memory).** The honest finding: **most of the 14 functions are PARTIAL, not missing.** Building all of them at once violates concentrate-harder + incremental-agent-evolution. So this is a *prioritized queue* the recursive loop works through (3/run, gated, surfaced to James's one chat) — not a flood.

## The 14 Command Functions

| # | Function | Status | What exists / the gap |
|---|---|---|---|
| 1 | Compass (direction) | 🟡 PARTIAL | NOW.md, INTENT RADAR exist; not auto-prioritizing |
| 2 | Lantern (see clearly) | 🔴 GAP | mostly conceptual — a real "detect patterns/anomalies" function isn't built |
| 3 | Maproom (hold context) | 🟢 BUILT | Cartographer / SYSTEM_MAP (today) + auto-refresh |
| 4 | Gate (rules/reversibility) | 🟢 BUILT | merge-gate (today) + collision hooks |
| 5 | Bridge (signal→action) | 🟡 PARTIAL | build_intent_router, verb_router, SPEC_comms-hub (designed, not built) |
| 6 | Forge (build) | 🟢 BUILT | run_codex + orchestrator (today) |
| 7 | Mirror (review outcomes) | 🟡 PARTIAL | narrator + recursive_improver (today); not a standing review surface |
| 8 | Root (memory = continuity) | 🟢 BUILT | Cartographer + conversation memory (today) |
| 9 | Watchfire (guard the system) | 🟢 BUILT | recursive_improver (today) + check-* hooks + security-watch |
| 10 | Healer (self-repair) | 🟡 PARTIAL | state_reconciler + freshness --heal; no standing self-repair loop |
| 11 | Council Fire (multi-model debate) | 🟡 PARTIAL | the-cross-substrate-auditor + decisions/debate exist; not a standing service |
| 12 | Instrument Rack (model routing) | 🟡 PARTIAL | routing.yaml + multi-model pipeline exist; not fully wired |
| 13 | Proof River (proof) | 🟡 PARTIAL | PROOF_LOG exists; SPEC_auto-proof drafted, not built |
| 14 | Loop (ever becoming) | 🟢 BUILT | recursive build pipeline (today) |

**INPUTS / one-chat surface** | 🟢 BUILT TODAY | `notify_telegram.sh` — the system now reaches James proactively in his one chat.

## Build queue (loop works through these, surfacing each to one-chat)

**SAFE-AUTO (Codex builds, gated, James merges):**
1. ⬜ Proof River v1 — build `SPEC_auto-proof.md` (auto-log shipped builds to PROOF_LOG). Spec exists.
2. ⬜ Lantern v1 — a pattern/anomaly detector over logs + state (the genuine GAP).
3. ⬜ Mirror surface — a standing "what shipped / what failed / what's next" digest to one-chat.

**NEEDS-JAMES (design decision first — not auto-built):**
- Council Fire as a standing multi-model debate service (which models, when it fires, cost).
- Instrument Rack — finalize model-routing policy.
- Healer — autonomous self-repair scope (what it's allowed to fix without asking).
- Bridge / Comms Hub — the full conscious-chat interface (SPEC_comms-hub).

## How this gets built
The orchestrator builds the SAFE-AUTO queue (cap 3/run), gates each, and surfaces "ready to merge" to James's one chat. NEEDS-JAMES items wait for his decision. Incremental — smallest functional pieces first, each proven before the next.
