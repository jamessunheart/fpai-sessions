# SPEC d194 — The Spot & Topple Orchestrator (make the system proactively spot & topple)

**Why (James 2026-07-05):** the system should proactively Spot & Topple, not wait to be prompted. Today the TOPPLE half exists (build loop auto-builds queued specs) but SPOT only happens when James/Ember prompts. Close the loop so the organism runs it on its own cadence: Spot → Topple → Proof → Learning → better Spot.

## The loop (scheduled orchestrator, e.g. every N hours + on idle-queue)
1. **SPOT** — run the Spot questions against live state (HOT_STATE + treasury + funnel metrics + last cycle's proofs): where is value trapped? what blocks cash flow? which one action unlocks ten? the smallest domino with the biggest downstream effect. Rank by cash-proximity + Allocation Score. This IS the d186 Opportunity/Gap engine — activate it as the proactive scanner, seeded with real live signals not guesses (P21).
2. **TOPPLE (auto)** — the top domino that is REVERSIBLE + within-cap + aligned → auto-write a spec + queue to the build loop. No James in the loop for these (Constitution L5/L6/L7). 
3. **VERIFY BY REAL EXECUTION** — the missing muscle. After a build merges, actually RUN/TEST the thing end-to-end (like the 2026-07-05 funnel topple: submit a live test lead, trace it, judge reality) — not "merged = done." Wire to d182 smoke-gate + d188 activation-audit. A domino isn't toppled until reality confirms it moved.
4. **LEARN** — write the outcome to the d185 Capability-Created Ledger (what worked/failed/surprised) → feeds back to sharpen step 1's ranking.
5. **GATE to James** — only RESERVED dominoes (spend money · deploy to prod public · James's personal voice · strategic direction) surface to James as a single clear decision. Everything else the substrate topples silently and reports proof.

## Guardrails (critical — proactivity without recklessness)
- Auto-topple ONLY reversible + within $20/day cap + north-star-aligned (constitution_check.py gates every auto-queue).
- NEVER auto: money moves · prod-public deploys · security config · James's voice. Those → James-gated.
- Kill switch: `touch /opt/fpai-build/.spot_topple_disabled`.
- Every cycle logs: domino spotted · why · toppled? · proof · learning — to an auditable ledger + a ONE-line James digest (P17: only surface what earns interruption).

## Contract
Builds on d186 (spot) + build loop (topple) + d182 (verify gate) + d185 (learn). $0 (local). Reversible. Independent review. The orchestrator itself must be dogfooded: its first proactive cycle should re-spot the funnel-deliver domino (d193) and verify it after build.

## Done / Proof
The system, unprompted, spots a real domino overnight → queues + topples the reversible ones → verifies each by real execution → logs proof + learning → surfaces James ONE decision (if any) with a clean digest. James wakes to "here's what I spotted, toppled, and proved" — not silence, not noise.
