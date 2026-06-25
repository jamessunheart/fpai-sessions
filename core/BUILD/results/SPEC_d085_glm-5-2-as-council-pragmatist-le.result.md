# SPEC_d085_glm-5-2-as-council-pragmatist-le Result

- Status: done / independently AI-reviewed / awaiting merge review
- Branch: `build/SPEC_d085_glm-5-2-as-council-pragmatist-le`
- Base required by contract: `feat/headless-build`

## Files Changed

- `tools/council/debate.py`
- `tools/council/glm_client.py`
- `tools/council/test_council.py`
- `tools/council/test_glm_client.py`
- `core/BUILD/specs/SPEC_d085_glm-5-2-as-council-pragmatist-le.md`
- `core/BUILD/results/SPEC_d085_glm-5-2-as-council-pragmatist-le.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

The council debate runner now executes true per-lens routing. The Pragmatist lens uses GLM-5.2 via `GLM_API_KEY`/Z-AI or `GLM_LOCAL_URL` when configured, under `GLM_COUNCIL_DISABLE` and a separate `$5/day` GLM cap. Visionary and Skeptic remain `claude -p`. If GLM is unavailable, disabled, unconfigured, or over the GLM cap reservation, Pragmatist falls back to `claude -p`.

GLM usage writes metered `ops_ledger` rows with `model`, `tokens_in`, `tokens_out`, and `cost_usd`. Debate output logs the model used per lens.

## Tests

- `python3 -B -m unittest discover -s tools/council -p 'test_*.py'` — 12 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/council/debate.py tools/council/glm_client.py tools/council/test_council.py tools/council/test_glm_client.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d085-registry.json`
- `git diff --check`

## Independent Review

Independent review found two P2 blockers: registry still `building`, and GLM could exceed the daily cap because the cap check happened only before knowing call cost. The cap blocker was fixed with bounded `GLM_MAX_TOKENS` and a pre-call estimated-cost reservation. Re-review found no new P1/P2 blockers; the remaining registry blocker was resolved by setting this build to `done` with `tests_passed=true`.

## Risks

- This build did not make live GLM, Claude, or Codex calls.
- `GLM_MAX_TOKENS` defaults to `1200` to make cap reservation meaningful; operators can tune it with env.
- The current generated branch is not a descendant of local `feat/headless-build` in this worktree, so Ember should verify/rebase/cherry-pick onto `feat/headless-build` before merge if required by the merge gate.

## Rollback

Revert the listed files. Immediate runtime rollback is `GLM_COUNCIL_DISABLE=1`, which returns the council to all-`claude -p` lens behavior.

## Intent

- Intent solved: council Pragmatist can now use a distinct cost-optimized open model lens instead of three Claude personas.
- Downstream intent unlocked: d073 council-agent benchmarks can compare GLM Pragmatist proposals against Claude Pragmatist fallback using per-lens model logs and GLM cost rows.
- Next move: Ember can run one disabled/dry-run council proof on the live host, then optionally enable `GLM_API_KEY` or `GLM_LOCAL_URL` for a bounded Pragmatist-only GLM trial.
