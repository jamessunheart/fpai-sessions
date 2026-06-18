# SPEC_d107_gepa-library-wire-install-real-m Result

## Status

Done in working tree / awaiting merge review.

## Files Changed

- `tools/prompt_efficiency/gepa_library.py`
- `tools/prompt_efficiency/gepa_loop.py`
- `tools/prompt_efficiency/test_gepa_loop.py`
- `tools/council/debate.py`
- `tools/council/test_debate.py`
- `core/benchmarks/README.md`
- `core/benchmarks/prompt_efficiency_cases.json`
- `core/benchmarks/prompt_efficiency_adoptions.json`
- `core/BUILD/signals/prompt_efficiency.json`
- `core/BUILD/signals/prompt_efficiency.md`
- `core/STATE/PROMPT_EFFICIENCY.md`
- `core/BUILD/activate/SPEC_d107_gepa-library-wire-install-real-m.sh`
- `core/BUILD/specs/SPEC_d107_gepa-library-wire-install-real-m.md`
- `core/BUILD/results/SPEC_d107_gepa-library-wire-install-real-m.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Wired d106 prompt efficiency to prefer the real MIT `gepa` package for template-shaped prompt optimization. Added a `PromptTemplateAdapter` around `gepa.optimize(...)`, with a `claude -p` custom reflection proposer, local/Ollama eval configuration metadata, package status reporting, a fail-closed `GEPA_OPTIMIZE_DISABLE=1` kill switch, and deterministic fallback when the package is unavailable.

The council Pragmatist lens now renders through the prompt-efficiency adoption layer. Because council prompts are high-impact, optimized council prompt candidates are reported as `pending_adoptions` and are not activated until human approval. The activation script installs/import-checks `gepa` after merge; no live install was performed in this sandbox.

## Tests

- `python3 -B -m unittest tools.prompt_efficiency.test_gepa_loop tools.council.test_debate`
- `python3 -B -m tools.prompt_efficiency.gepa_loop`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/prompt_efficiency/gepa_library.py tools/prompt_efficiency/gepa_loop.py tools/prompt_efficiency/test_gepa_loop.py tools/council/debate.py tools/council/test_debate.py`
- `bash -n core/BUILD/activate/SPEC_d107_gepa-library-wire-install-real-m.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool core/benchmarks/prompt_efficiency_cases.json`
- `python3 -m json.tool core/benchmarks/prompt_efficiency_adoptions.json`
- `python3 -m json.tool core/BUILD/signals/prompt_efficiency.json`
- `git diff --check`

## Risks

`gepa` and `dspy` are not installed in this sandbox, so the live package import path is covered by fake-module tests and by the post-merge activation artifact, not by an actual installed-package run here. The generated report honestly records `gepa package is not installed` for this sandbox run. Council prompt changes remain pending approval and are not active.

No live pip install, Ollama rollout, Claude reflection call, DB write, prompt activation, deploy, push, merge, outreach, secret access, or money movement occurred.

## Rollback

Revert the listed d107 files. Runtime rollback is `GEPA_OPTIMIZE_DISABLE=1`; active prompt rollback is to remove the relevant entry from `core/benchmarks/prompt_efficiency_adoptions.json`. If the activation script has been run and package rollback is required, uninstall `gepa` from the Python environment used by the build loop.

## Intent Solved

d106 now has a real GEPA package integration path instead of only hand-built variant selection.

## Downstream Intent Unlocked

After merge activation installs `gepa`, prompt-efficiency runs can evolve template-shaped prompts with GEPA and keep high-impact council/build-review prompt changes staged for approval instead of silently adopting them.
