# d055 Result — Subscription dependency map

Status: done / awaiting independent review + merge review

## Files Changed

- `docs/codex/SUBSCRIPTION_DEPENDENCY_MAP.md`
- `tools/build_loop/test_subscription_dependency_map.py`
- `core/BUILD/specs/SPEC_d055_subscription-dependency-map.md`
- `core/BUILD/results/SPEC_d055_subscription-dependency-map.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Audited the repo-side build loop for Claude Max vs ChatGPT Max dependencies and wrote a durable subscription dependency map. The map separates hard failures from graceful degradations, identifies where the current build loop depends on `codex exec` vs `claude -p`, distinguishes Claude Max CLI from metered Anthropic API paths, includes post-build blueprint regeneration, and ranks local-model replacements.

Primary finding: ChatGPT Max removal breaks the headless branch-producing Codex build lane first and can leave misleading failed-build result files; Claude Max removal breaks independent AI review, context/proposal lanes, and post-build blueprint learning first. The first local replacements should be a command-compatible build executor and an independent reviewer.

## Tests

- `python3 -B -m unittest tools.build_loop.test_subscription_dependency_map` — 4 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/test_subscription_dependency_map.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`

## Independent Review

Configured Claude CLI review was attempted but failed in this sandbox with `API Error: Unable to connect to API (FailedToOpenSocket)`. Fallback independent-agent review first returned `REQUEST_CHANGES` for two map issues and one test-coverage weakness. Fixes applied: documented the `run_codex.sh` false-result-file hazard, added the `curator/blueprints/manager.py` Claude blueprint-refresh dependency, and strengthened tests to require known Claude/Codex call-site coverage.

Second fallback independent-agent review returned `APPROVE` with low risk and no findings. Residual caveat: this is a repo-evidence audit, not live subscription/account verification; adjacent non-build-loop systems can be mapped in a follow-up.

## Risks

- This is a repo evidence audit, not a live billing/account audit. It does not verify active subscriptions or external account state.
- The map reflects current files in this branch; live host scripts or vault-only Claude workflows may add dependencies outside this repo mirror.
- Independent Claude review may not be runnable in this sandbox if Claude CLI/auth is unavailable.

## Rollback

Revert the d055 files above and remove the `SPEC_d055_subscription-dependency-map` entry from `core/BUILD/REGISTRY.json`.

## Intent Solved

James/Ember can see exactly which build-loop steps rely on Claude Max vs ChatGPT Max and what breaks if either subscription disappears.

## Downstream Intent Unlocked

Route the first local-model replacement spec against the highest-risk role: a command-compatible local build executor for the Codex build lane, followed by an independent local reviewer.
