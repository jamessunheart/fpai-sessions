# SPEC_d106_prompt-efficiency-loop-gepa-vari Result

## Status
Done in working tree. Not pushed, merged, deployed, or live-activated.

## Files Changed
- `tools/prompt_efficiency/__init__.py`
- `tools/prompt_efficiency/gepa_loop.py`
- `tools/prompt_efficiency/test_gepa_loop.py`
- `tools/benchmarks/improvement_proposer.py`
- `core/benchmarks/README.md`
- `core/benchmarks/prompt_efficiency_cases.json`
- `core/benchmarks/prompt_efficiency_adoptions.json`
- `core/STATE/PROMPT_EFFICIENCY.md`
- `core/BUILD/signals/prompt_efficiency.json`
- `core/BUILD/signals/prompt_efficiency.md`
- `core/BUILD/specs/SPEC_d106_prompt-efficiency-loop-gepa-vari.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d106_prompt-efficiency-loop-gepa-vari.result.md`
- `docs/codex/HANDOFF.md`

## Summary
Added a deterministic prompt-efficiency loop that tests GEPA-style variants for the benchmark improvement-spec prompt. The loop keeps the current prompt as `baseline`, evaluates compressed variants against fixture cases with required safety/resource/context terms, rejects under-specified compression, and writes an adoption manifest only when quality is greater than or equal to baseline and token count is lower.

The first run adopted `compressed_guarded` for `benchmark_improvement_spec`: quality stayed at `1.0` versus baseline `1.0`, average token count dropped from `108.5` to `91.5`, and the generated report shows the aggressive variants failing the quality gate. `tools/benchmarks/improvement_proposer.py` now renders through the adopted manifest with a baseline fallback if the manifest is missing or invalid.

## Tests
- `python3 -B -m unittest tools.prompt_efficiency.test_gepa_loop tools.benchmarks.test_benchmarks`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/prompt_efficiency/__init__.py tools/prompt_efficiency/gepa_loop.py tools/prompt_efficiency/test_gepa_loop.py tools/benchmarks/improvement_proposer.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool core/benchmarks/prompt_efficiency_cases.json`
- `python3 -m json.tool core/benchmarks/prompt_efficiency_adoptions.json`
- `python3 -m json.tool core/BUILD/signals/prompt_efficiency.json`
- `python3 -B -m tools.prompt_efficiency.gepa_loop --report-json /tmp/d106-prompt-efficiency.json --report-md /tmp/d106-prompt-efficiency.md --state-md /tmp/d106-prompt-efficiency-state.md --adoptions /tmp/d106-prompt-efficiency-adoptions.json`
- `git diff --check`

## Risks
- Quality scoring is deterministic contract coverage, not a live model-eval judgment. It proves safety/resource/context retention for fixture prompts; it does not prove all future prompt behavior.
- Only the benchmark improvement-spec prompt is wired in this build. More prompts can be added by adding fixture cases and variants.
- The adoption manifest is repo-local. No live benchmark queue, Claude call, deploy, push, merge, or external API call was performed.

## Rollback
Revert the d106 files listed above. Runtime rollback can also be done by removing the `benchmark_improvement_spec` entry from `core/benchmarks/prompt_efficiency_adoptions.json`; the renderer falls back to `baseline`.

## Intent Solved
Prompt compression now has a tested adoption loop instead of relying on manual prompt shrinking.

## Downstream Intent Unlocked
Future benchmark/proposal prompts can enter the same efficiency loop, letting the system reduce prompt cost and context load only when fixture quality remains at or above baseline.
