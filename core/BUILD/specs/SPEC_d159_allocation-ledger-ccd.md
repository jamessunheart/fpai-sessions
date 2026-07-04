# SPEC — Allocation Ledger + CCD Scorer (the keystone instrumented)

James asked 2026-07-03: "do we need tools/agents to streamline allocation?" Answer: not agents — ONE missing instrument.

## Build
Per core/STATE/ALLOCATION_INTELLIGENCE.md (the keystone): the system reasons about allocation but has no single table of scarce resources → allocations → outcomes. Build `tools/allocation/ledger.py`:

1. **Resource table** (generated): pull money (latest ~/.config/fpai/treasury CURRENT_RESOURCES + cost ledger $/day), compute ($0-marginal CLI budget), attention (open decisions count), builders (0 for now) → one JSON + MD table `core/STATE/ALLOCATION_LEDGER.md`.
2. **CCD scorer**: function `score(proposal) -> {today_revenue, tomorrow_capability, recursion, ccd}` per mindmap-94's 3-question framework — callable by council debate + nightly metabolism (wire as input alongside constitution_check, same pattern as d134).
3. **Outcome loop**: each scored allocation gets an id; `record_outcome(id, verified_result)` appends — Law 3 (learn before repeat). Metabolism reads misses.

## Contract
Branch off feat/headless-build. Tests required (score() ranks a revenue+capability+recursion proposal above a cost-only one). Reversible; no money moves — this MEASURES allocation, never executes it. Independent AI review before merge.

## Done / Proof
ALLOCATION_LEDGER.md generated with real treasury numbers · council debate cites a CCD score in its next proposal.
