# Build result — SPEC_d032_model-redundancy-router-t0-subsc

_ran: 2026-06-16T16:40:21Z · branch: build/SPEC_d032_model-redundancy-router-t0-subsc_

## Status

Done / awaiting independent review + merge review.

## Files Changed

- `tools/intelligence/__init__.py`
- `tools/intelligence/model_router.py`
- `tools/intelligence/provider_health.py`
- `tools/intelligence/routing.yaml`
- `tools/intelligence/setup_ollama.sh`
- `tools/intelligence/test_model_router.py`
- `tools/merge/ai_review.py`
- `tools/council/debate.py`
- `tools/council/self_diagnostic.py`
- `tools/build_loop/self_audit.py`
- `tools/build_loop/run_codex.sh`
- `tools/build_loop/health_check.sh`
- `tools/decisions/debate.py`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d032_model-redundancy-router-t0-subsc.md`
- `core/BUILD/results/SPEC_d032_model-redundancy-router-t0-subsc.result.md`
- `docs/codex/HANDOFF.md`

## Summary

Added a tiered model router with configured task routing: T0 subscription CLIs, T1 local Ollama, and capped T2 APIs loaded from `~/.config/fpai/model_fallback.env`. The router returns provider/tier/latency/cost metadata, logs fallback/degraded/outage/restored events to the ops ledger, sends best-effort Telegram alerts, writes the all-provider outage flag, and logs metered T2 calls through `tools/cost/track.py`.

Added provider health probes and wired them into `tools/build_loop/health_check.sh`. Added an idempotent `setup_ollama.sh` for the local T1 model. Replaced direct model calls in AI review, council debate, council self-diagnostic synthesis, build-loop self-audit, and the closest existing decision debate adapter. `run_codex.sh` still prefers real `codex exec --full-auto`, then falls back through the router if Codex is missing or exits nonzero.

## Tests

- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/intelligence/model_router.py tools/intelligence/provider_health.py tools/intelligence/test_model_router.py tools/merge/ai_review.py tools/council/debate.py tools/council/self_diagnostic.py tools/build_loop/self_audit.py tools/decisions/debate.py`
- `bash -n tools/build_loop/run_codex.sh tools/build_loop/health_check.sh tools/intelligence/setup_ollama.sh`
- `python3 -B -m unittest tools.intelligence.test_model_router tools.build_loop.test_self_audit tools.council.test_self_diagnostic tools.queue.test_build tools.queue.test_build_loop_watcher` (23 tests OK)
- `git diff --check`

## Risks

- Live provider calls, real Telegram alerts, real Ollama installation/pull, and real T2 API calls were not exercised in this sandbox.
- If `codex exec` is down during `run_codex.sh`, fallback models can produce guidance in the build result, but they do not perform Codex-style repository edits.
- `tools/decisions/ember_check_in.sh` remains a direct action/sending responder because replacing it with a text-return router would break its current send semantics; it should get a separate action-aware router spec if needed.

## Rollback

Revert the changed files. Remove `/opt/fpai-build/.model_outage`, `/opt/fpai-build/.model_outage_alerted`, and `/opt/fpai-build/.model_degraded_summary_date` if created by a live run. Runtime kill switch: `MODEL_ROUTER_DISABLE=1` bypasses routing and uses direct `claude -p` behavior.

## Intent

Intent solved: subscription CLI failures no longer silently stop review/council/audit/decision model calls; they route through local or capped fallback paths and log degradation.

Downstream intent unlocked: the autonomous build loop can keep surfacing model-provider failures as explicit ops state instead of becoming invisible idle.
