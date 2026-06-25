# SPEC_d050_module-blueprint-system-living-c Result

- **Status:** done / awaiting James review + merge review
- **Branch:** `build/SPEC_d050_module-blueprint-system-living-c`
- **Completed:** 2026-06-16T21:46:57Z

## Files changed

- `curator/__init__.py`
- `curator/blueprints/__init__.py`
- `curator/blueprints/__main__.py`
- `curator/blueprints/manager.py`
- `curator/blueprints/test_manager.py`
- `docs/blueprints/_TEMPLATE.md`
- `docs/blueprints/beacon.md`
- `docs/blueprints/cora.md`
- `docs/blueprints/health.md`
- `docs/blueprints/hermes.md`
- `docs/blueprints/learning_loop.md`
- `docs/blueprints/steward.md`
- `tools/build_loop/run_codex.sh`
- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/build_orchestrator.sh`
- `tools/council/debate.py`
- `SERVICES/sunheart-brain/curator/corrections.py`
- `SERVICES/sunheart-brain/curator/test_corrections.py`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d050_module-blueprint-system-living-c.md`
- `docs/codex/HANDOFF.md`

## Summary

Added the living Module Blueprint system. Existing seed blueprints for Forge, Council, Ember, Spark, and Ledger were preserved; missing required blueprints for Hermes, CORA, Steward, Beacon, Learning Loop, and Health were seeded along with `_TEMPLATE.md`.

Added `curator.blueprints` with `get`, `list`, `seed`, `update`, `update-after-build`, `correction`, `sharpen`, and `detect` CLI paths. The manager supports best-effort Claude regeneration after builds, correction appends to Known gaps, quality-standard proposals, module detection from paths/text, and `BLUEPRINTS_DISABLE=1`.

Wired blueprint context into `run_codex.sh` before headless Codex receives a spec, into `tools/council/debate.py` before Claude debate prompts, into `server_build_loop.sh` after successful backlog and normal auto-merges, and into correction capture using both James's correction and the previous bot turn for module detection.

## Tests

- `python3 -B -m unittest curator.blueprints.test_manager SERVICES/sunheart-brain/curator/test_corrections.py tools.council.test_self_diagnostic` (21 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile curator/blueprints/manager.py curator/blueprints/__main__.py curator/blueprints/test_manager.py tools/council/debate.py SERVICES/sunheart-brain/curator/corrections.py SERVICES/sunheart-brain/curator/test_corrections.py`
- `BLUEPRINTS_DISABLE=1 python3 -m curator.blueprints update forge --no-commit`
- `python3 -m curator.blueprints list`
- `python3 -m curator.blueprints get beacon`
- `python3 curator/blueprints/manager.py detect 'tools/beacon variant generator campaign'`
- `bash -n tools/build_loop/run_codex.sh tools/build_loop/build_orchestrator.sh tools/build_loop/server_build_loop.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check -- curator docs/blueprints tools/build_loop tools/council/debate.py SERVICES/sunheart-brain/curator/corrections.py SERVICES/sunheart-brain/curator/test_corrections.py core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d050_module-blueprint-system-living-c.md`

## Independent review

Completed by subagent. Findings:

1. The documented `python -m curator.blueprints update {module}` CLI was missing. Fixed by adding the `update` alias and regression test.
2. Correction blueprint routing only inspected correction text and ignored previous bot context. Fixed by detecting the module from previous bot text plus correction text, with regression test.

No remaining blocker was reported after fixes. Residual risk: live post-merge blueprint regeneration was not exercised against real `claude -p`, git commit behavior, or server-162 build-loop state in this sandbox.

Follow-up 2026-06-25: added the missing `server_build_loop.sh` post-merge hook and registry row. A local `claude -p --effort high` review attempt for this follow-up delta timed out after 90 seconds with no output, so this small delta still needs a successful independent reviewer pass before claiming the full review gate.

## Risks

- Module detection is keyword/path based and may need tuning after live builds produce real evidence.
- `update_blueprint_after_build` best-effort commits are intentionally ignored by the build loop if they fail; live commit behavior needs server proof.
- Seed blueprints are conservative where live d034/d037/d039-d043/d049 evidence is not present in this checkout.

## Rollback

Revert the changed files listed above. Runtime automation can be disabled without reverting by setting `BLUEPRINTS_DISABLE=1`.

## Intent solved

Modules now have living contracts that future builds, council prompts, Codex specs, corrections, and review loops can read and sharpen.

## Downstream intent unlocked

Future Buildstream work can improve existing module standards instead of rebuilding from stale one-time specs.
