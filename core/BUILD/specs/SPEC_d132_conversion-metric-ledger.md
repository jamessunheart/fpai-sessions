# SPEC_d132 — Conversion-metric ledger + weakest-link surfacing

Authored by Ember from the Learning Intelligence Flywheel (diagram #3, 2026-06-30). Implements the
measurement spine defined in `core/STATE/LEARNING_METRICS.md`: the 7 conversion-efficiency metrics,
the weakest-conversion rule, and the Rate-of-Improvement north metric. Pairs with d129 (outcome
signal + Academy), which provides one of the raw inputs.

## Build

A measurement tool, not a new agent. Honesty-gated — populate only what reality can truthfully feed.

1. **Metric computer** `tools/metrics/conversion_ledger.py`:
   - Computes the 7 metrics from existing sources: IPT (cost + benchmark per token from build/probe logs), HTS (James-hours freed — from session + automation logs), LR (improvement-over-time on a fixed benchmark suite), DR (horizon_scan new-discovery count). 
   - For VPI / VCR / RR: emit `verdict=unknown` with reason `no_external_users` / `no_revenue` — DO NOT estimate. The emptiness is the signal.
   - Writes a bounded `core/STATE/CONVERSION_LEDGER.md` + machine-readable `~/.config/fpai/metrics/conversion_latest.json`.
2. **Weakest-link surfacer**: compute which conversion is lowest (treating `unknown` as a flagged gap, not zero) and surface it as ONE line into HOT_STATE + the alignment footer. This is what the metabolism (d131) targets next.
3. **North-metric swap**: make LR (Rate of Improvement) the headline number in the awareness/dashboard surface; demote raw awareness % to a sub-probe feeding LR. Update the dashboard "🎯 The Goal" panel source to read LR.

## Context — why this and not more learning infra

Diagram #3's own rule: improve the weakest conversion first. Instrumenting all 7 reveals (truthfully)
that our weakest conversions are the VALUE ones (VPI/VCR) — starved because we have ~zero external
users, not because learning is weak. The ledger makes that visible and undeniable, which is the point:
it should push the system (and James) toward Reality (real users) instead of more engine-polishing.

## Honest constraints (load-bearing)
- 🔴 Never fabricate starved metrics. `unknown` is an honest, useful value. (`feedback_honesty_first_virtue.md`)
- 🟡 The ledger measures; it does NOT auto-act. Weakest-link → surfaced for the gated metabolism/human, not auto-deployed.

## Follow-on
- d131 metabolism reads `conversion_latest.json` and targets the weakest measurable conversion each night.
- When `OUTREACH_LIVE=1` flips and real users arrive, VPI/VCR populate and the spine becomes fully live.

## Contract
Follow `docs/codex/SESSION_CONTRACT.md`. Branch off `feat/headless-build` (never main).
Register in `core/BUILD/REGISTRY.json` (status building->done). Tests required (fixture-test each
metric computer; assert VPI/VCR return `unknown` not a fabricated number when inputs are empty).
Do NOT push or open PRs — Ember merges after the independent AI review.

## Done / Proof
independent-AI-reviewed branch with: `conversion_ledger.py` producing `CONVERSION_LEDGER.md` with all 7
metrics (measurable ones populated, starved ones honestly `unknown`), weakest-link surfaced into
HOT_STATE, and LR shown as the headline metric. Ready for merge.
