# SPEC_d088_glm-5-2-sovereign-inference-runp Result

- Status: done in working tree / independent AI review blocked in sandbox / awaiting merge review
- Branch: `build/SPEC_d088_glm-5-2-sovereign-inference-runp`
- Files changed: `tools/gpu/__init__.py`; `tools/gpu/runpod_deploy.py`; `tools/gpu/glm_inference.py`; `tools/gpu/budget_guard.py`; `tools/gpu/test_runpod_deploy.py`; `tools/gpu/test_glm_inference.py`; `tools/gpu/test_budget_guard.py`; `tools/council/debate.py`; `tools/council/test_debate.py`; `core/BUILD/specs/SPEC_d088_glm-5-2-sovereign-inference-runp.md`; `core/BUILD/results/SPEC_d088_glm-5-2-sovereign-inference-runp.result.md`; `core/BUILD/REGISTRY.json`; `docs/codex/HANDOFF.md`

## Summary

Added a repo-side RunPod GLM inference scaffold for sovereign council inference. The deploy tool checks for `glm52-council`, creates a serverless endpoint when absent, writes the local endpoint registry outside git, and encodes the requested strategy order: GLM-5.2 with CPU/KTransformers-style offload first, GLM GGUF Q4 next, and GLM-4-9B fallback last. The inference wrapper posts OpenAI-style messages to RunPod `runsync`, retries once, logs GPU seconds/status to the ops ledger, enforces the budget guard, and falls back to `claude -p` when disabled, unconfigured, over budget, or unavailable. The budget guard blocks at 90% of daily cap, treats `RUNPOD_BUDGET_DAILY_USD=0` as a kill switch, and writes a local `budget_alert` row for Telegram/bot surfaces to relay.

`tools/council/debate.py` now exposes importable helpers and routes the Pragmatist lens through `glm_inference.call_glm()` before the existing Claude synthesis. The script behavior remains under `main()` for cron use instead of executing at import time.

## Tests

- `python3 -B -m unittest tools.gpu.test_budget_guard tools.gpu.test_glm_inference tools.gpu.test_runpod_deploy tools.council.test_debate` (10 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/gpu/__init__.py tools/gpu/budget_guard.py tools/gpu/glm_inference.py tools/gpu/runpod_deploy.py tools/gpu/test_budget_guard.py tools/gpu/test_glm_inference.py tools/gpu/test_runpod_deploy.py tools/council/debate.py tools/council/test_debate.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d088-registry.json`
- `git diff --check`

## Review

Independent AI review was attempted with `claude -p --effort high` against `/tmp/d088-full.patch`, including untracked files. The review produced no output after roughly 90 seconds and was terminated; no independent review verdict is available in this sandbox. Rerun from a live/writable host before merge if this branch requires the independent-review proof.

## Risks

No live RunPod API call, endpoint creation, model download, GPU job, endpoint verification request, deploy, secret read, push, or merge was performed. RunPod GraphQL schema details should be verified on the live host during activation because the repo tests use injected transports and do not call RunPod. The budget alert is an ops-ledger row, not a direct Telegram send from this build.

## Rollback

Revert the d088 files listed above. Runtime rollback is immediate with `RUNPOD_GLM_DISABLE=1` or `RUNPOD_BUDGET_DAILY_USD=0`; removing `RUNPOD_GLM_ENDPOINT_ID` also forces `claude -p` fallback. If activation later creates `/root/.config/fpai/runpod_endpoints.json`, remove the `glm52-council` entry to clear the local registry.

## Intent

- Intent solved: council Pragmatist inference now has a sovereign RunPod GLM path from owned open weights, guarded by budget and kill switches.
- Downstream intent unlocked: after live RunPod schema verification and endpoint activation, d085-style external Z-AI dependency can be removed from council debate without James manually swapping model calls.
- Next move: from the live host, rerun independent review if required, run `python3 tools/gpu/runpod_deploy.py` only after merge, verify the endpoint with a test prompt, set `RUNPOD_GLM_ENDPOINT_ID`, and keep `RUNPOD_GLM_DISABLE=1` available as the kill switch.
