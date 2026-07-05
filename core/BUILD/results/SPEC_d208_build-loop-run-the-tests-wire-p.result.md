# SPEC_d208_build-loop-run-the-tests-wire-p Result

## Status

Done in working tree. Not pushed. Not merged.

## Summary

Added a real scoped pytest gate to `tools/build_loop/server_build_loop.sh` before independent review or auto-merge. After Codex builds and activation policy passes, the loop now runs `tools/build_loop/test_gate.py` with `/opt/sh-brain-src/.venv/bin/python -m pytest -q -x --tb=short -ra` semantics, scoped to:

- touched `test_*.py` files,
- adjacent tests for changed Python modules,
- a fast build-loop smoke subset.

The gate writes `core/BUILD/reports/<SPECID>.test_gate.json` into the build branch. A failure or timeout marks the decision `changes`, sends/surfaces the pytest tail, writes an ops-ledger `pytest-gate-failed` event, and returns before review or merge. Passing reports are committed and logged before review.

`product_portfolio_review.py` now reads the pytest-gate JSON report. Failed/timed-out tests lower the d207 quality score and add explicit quality flags, so auto-built products with failing tests are scored low/flagged even if their result artifact claims tests passed.

## Files Changed

- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/test_gate.py`
- `tools/build_loop/test_test_gate.py`
- `tools/build_loop/test_pytest_gate_contract.py`
- `tools/build_loop/product_portfolio_review.py`
- `tools/build_loop/test_product_portfolio_review.py`
- `core/BUILD/specs/SPEC_d208_build-loop-run-the-tests-wire-p.md`
- `core/BUILD/results/SPEC_d208_build-loop-run-the-tests-wire-p.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.build_loop.test_test_gate tools.build_loop.test_pytest_gate_contract tools.build_loop.test_product_portfolio_review tools.build_loop.test_activation_policy_contract tools.build_loop.test_auto_merge_governance tools.build_loop.test_changes_rework_loop` (20 OK)
- `python3 -m py_compile tools/build_loop/test_gate.py tools/build_loop/test_test_gate.py tools/build_loop/test_pytest_gate_contract.py tools/build_loop/product_portfolio_review.py tools/build_loop/test_product_portfolio_review.py`
- `bash -n tools/build_loop/server_build_loop.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d208-registry-final.json`
- `git diff --check`

Attempted the requested runner directly:

- `/opt/sh-brain-src/.venv/bin/python -m pytest ...` could not run in this sandbox because the venv lacks `pytest` (`No module named pytest`).

## Proof

Unit proof covers the selector including touched tests, adjacent module tests, and smoke tests; a failing pytest run returning a failed report/nonzero status; and timeout reporting. Static shell proof verifies the pytest gate runs before independent review, failure sets `build_status=changes`, surfaces `PYTEST GATE FAILED`, logs `pytest-gate-failed`, and returns before the merge path. Product portfolio proof verifies a failed test-gate report forces a low-quality flag.

## Risks

The live server venv must have `pytest` installed for green builds to proceed. In this sandbox, the venv exists but lacks pytest, so direct pytest verification was unavailable. If server 162 has the same venv state, the first gated build will correctly hold and surface the missing runner instead of auto-merging untested code.

## Rollback

Revert this branch. Runtime hold without rollback: set `PYTEST_GATE_TIMEOUT` higher/lower as needed; to fully disable the new gate requires reverting the `server_build_loop.sh` hook.

## Intent Solved

Autonomous builds no longer move from Codex output to review/auto-merge without running their own scoped tests.

## Downstream Intent Unlocked

The build loop can start treating written tests as protection, and d207 quality curation can distinguish tested green builds from failing or unproven ones.
