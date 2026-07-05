# SPEC_d207_autonomy-quality-value-gate-for Result

Status: done in working tree / awaiting review + merge.

## Summary

Added a quality + value curation layer for autonomous product-building while keeping `/opt/fpai-build/.spot_topple_autobuild_enabled` semantics intact. The system may still proactively queue/build reversible product candidates; d207 now assesses the resulting portfolio for working quality, proof strength, useful/value alignment, buyer clarity, and keep/kill/develop recommendation.

`spot_topple_orchestrator.py` now writes a `PORTFOLIO REVIEW` digest with QUALITY and VALUE scores for the top candidates and sends it to James via the existing Telegram notifier on live queued runs. `build_orchestrator.sh` now runs the same assessor before auto-merge and puts low-quality builds into `QUALITY HOLD` instead of silently merging them.

## Files Changed

- `tools/build_loop/product_portfolio_review.py`
- `tools/build_loop/test_product_portfolio_review.py`
- `tools/build_loop/spot_topple_orchestrator.py`
- `tools/build_loop/test_spot_topple_orchestrator.py`
- `tools/build_loop/build_orchestrator.sh`
- `core/BUILD/specs/SPEC_d207_autonomy-quality-value-gate-for.md`
- `core/BUILD/results/SPEC_d207_autonomy-quality-value-gate-for.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.build_loop.test_product_portfolio_review tools.build_loop.test_spot_topple_orchestrator tools.allocation.test_opportunity_axis_scorer tools.allocation.test_opportunity_engine` (19 OK)
- CLI smoke: `python3 -B tools/build_loop/spot_topple_orchestrator.py ... --dry-run --json` with temp ledgers and `--portfolio-review-path`, then verified generated review contains `PORTFOLIO REVIEW`, `QUALITY`, `VALUE`, and `Rec:`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d207_autonomy-quality-value-gate-for --base-ref feat/headless-build --head-ref HEAD` (OK: `build_kind=library` declared)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/product_portfolio_review.py tools/build_loop/test_product_portfolio_review.py tools/build_loop/spot_topple_orchestrator.py tools/build_loop/test_spot_topple_orchestrator.py`
- `bash -n tools/build_loop/build_orchestrator.sh core/BUILD/cron/fpai-spot-topple-run.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d207-registry-check.json`

## Proof

The orchestrator dry-run generated a portfolio review digest with three candidates, each carrying QUALITY score, VALUE score, buyer/value take, and a keep/develop/kill recommendation. The top candidate with no result artifact was flagged as weak quality rather than treated as merge-ready, while high-value candidates stayed in `DEVELOP` rather than being blocked from building.

## Risks

Quality scoring is deterministic and based on result artifacts, tests/smoke/lint evidence, and visible functionality language. It is intentionally conservative: a valuable candidate with weak proof becomes `DEVELOP`/quality-held, not discarded automatically. Telegram sending was not performed in sandbox; it remains fail-soft through the existing notifier.

## Rollback

Revert this branch. Runtime hold without code rollback: remove `/opt/fpai-build/.spot_topple_autobuild_enabled` to return Spot/Topple to surface-only queue posture, or pass `--no-portfolio-review` to the orchestrator if the review digest itself needs to be disabled.

## Intent Solved

Autonomous product-building stays on, but its output is curated by quality and value before James is asked to pick winners.

## Downstream Intent Unlocked

James can review a portfolio digest of built/candidate products, see weak builds flagged, and reserve only launch/funding/public voice decisions for himself while the system keeps building reversible candidates and improving the live funnel.
