# SPEC_d206_autonomy-liveness-aware-discern Result

build_kind=library

## Summary

Made the advisory opportunity axis scorer liveness-aware. The scorer now collects live-state inputs from opportunity rows, optional status JSON/JSONL paths, repo-local activation evidence, and the d206 known current state for the live assessment funnel and unbuilt resource-optimization audit. The Claude prompt now includes `live_state`, and scorer logs include the liveness inputs plus any calibration applied.

The calibration keeps the deterministic opportunity engine unchanged while correcting bad advisory axes before they are written:

- live deployed opportunities with traffic clamp `time_to_first_dollar` to `<=2`;
- lead-worker/activation evidence raises low `proof_speed` to at least `8`;
- unbuilt opportunities cannot retain a closer cash-proximity axis than the best live traffic path in the same rescore pass.

## Tests

- `python3 -B -m unittest tools.allocation.test_opportunity_axis_scorer` — 4 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/allocation/opportunity_axis_scorer.py tools/allocation/test_opportunity_axis_scorer.py`
- `python3 -B -m unittest tools.allocation.test_opportunity_axis_scorer tools.allocation.test_opportunity_engine tools.build_loop.test_spot_topple_orchestrator` — 15 OK
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d206_autonomy-liveness-aware-discern --base-ref feat/headless-build --head-ref HEAD` — OK: build_kind=library declared
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d206-registry-building.json`
- `git diff --check`

## Proof

Regression proof reproduces the d206 failure mode: Claude returns `assessment-funnel-delivery-proof.time_to_first_dollar=7` and `resource-optimization-audit.time_to_first_dollar=1`. With live-state supplied, the scorer writes the live funnel at `time_to_first_dollar=2`, raises its activation proof speed, clamps the unbuilt audit to no closer than the live path, logs liveness/calibration, and the live money path ranks at or above the unbuilt product.

## Risks

Liveness collection is intentionally advisory and defensive. It reads optional local status files and row-provided evidence; missing or malformed files are ignored. The d206 known-state hints are narrow to the two named opportunities so they can be replaced by richer live status once the server writes canonical per-opportunity liveness.

## Rollback

Revert this branch. Runtime rollback is also available by disabling the existing d202 scorer timer via `/opt/fpai-build/.opportunity_axis_scorer_disabled`; no service, deploy, outreach, money movement, or external API effect was added by d206.

## Intent solved

Discernment no longer scores opportunity descriptions while blind to deployed traffic and activation proof.

## Downstream intent unlocked

The Spot -> Topple loop can trust opportunity axes to keep the live revenue path ahead of speculative unbuilt products unless a future live-state-aware rescore proves otherwise.
