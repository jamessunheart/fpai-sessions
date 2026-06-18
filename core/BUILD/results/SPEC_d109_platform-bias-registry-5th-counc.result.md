# SPEC d109 Result — Platform Bias Registry + Platform Critic Lens

Status: done in working tree / awaiting merge review
Branch: `build/SPEC_d109_platform-bias-registry-5th-counc`
Date: 2026-06-18

## Summary

Added a living platform-bias registry and wired it into the council, self-portrait, Forge proposal prompts, and scout reports. The council prompt now asks for an advisory `platform_critic` JSON field unless `PLATFORM_CRITIC_DISABLE=1` is set. The registry seeds known Anthropic/OpenAI/cloud-era distortions, a Sovereign/Hybrid/Dependent rubric, update rules, and high-risk zones.

Forge-style improvement proposals and Tool Scout outputs now require a sovereignty check: every tool recommendation should rate Sovereign/Hybrid/Dependent, name a local/open/self-hosted alternative, and state the real loss before adopting a dependent platform. Self-portrait synthesis now preserves the known platform-bias section on regeneration.

## Files Changed

- `core/STATE/PLATFORM_BIAS_REGISTRY.md`
- `core/STATE/SELF_PORTRAIT.md`
- `core/STATE/PROMPT_EFFICIENCY.md`
- `core/BUILD/signals/prompt_efficiency.json`
- `core/BUILD/signals/prompt_efficiency.md`
- `core/BUILD/signals/tool_scout_report.md`
- `core/BUILD/signals/tool_scout_proposals.jsonl`
- `core/benchmarks/prompt_efficiency_cases.json`
- `core/benchmarks/prompt_efficiency_adoptions.json`
- `tools/platform_bias/`
- `tools/council/debate.py`
- `tools/council/test_debate.py`
- `tools/self_portrait/synthesize.py`
- `tools/self_portrait/test_synthesize.py`
- `tools/benchmarks/improvement_proposer.py`
- `tools/benchmarks/test_benchmarks.py`
- `tools/prompt_efficiency/gepa_loop.py`
- `tools/prompt_efficiency/gepa_library.py`
- `tools/prompt_efficiency/test_gepa_loop.py`
- `tools/scout/tool_scout.py`
- `tools/scout/test_tool_scout.py`
- `tools/scout/scout.py`
- `tools/scout/SCOUT_REPORT.md`
- `core/BUILD/specs/SPEC_d109_platform-bias-registry-5th-counc.md`
- `core/BUILD/results/SPEC_d109_platform-bias-registry-5th-counc.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -m py_compile tools/council/debate.py tools/platform_bias/registry.py tools/self_portrait/synthesize.py tools/benchmarks/improvement_proposer.py tools/prompt_efficiency/gepa_loop.py tools/prompt_efficiency/gepa_library.py tools/scout/tool_scout.py tools/scout/scout.py`
- `python3 -B -m unittest tools.platform_bias.test_registry tools.council.test_debate tools.self_portrait.test_synthesize tools.prompt_efficiency.test_gepa_loop tools.benchmarks.test_benchmarks tools.scout.test_tool_scout`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool core/benchmarks/prompt_efficiency_cases.json`
- `python3 -B -m tools.self_portrait.synthesize`
- `python3 -B -m tools.prompt_efficiency.gepa_loop`
- `python3 -B -m tools.scout.tool_scout --focus 'sovereign local-first model and tool replacements' --no-ledger --json`
- `python3 -B tools/scout/scout.py 'sovereign local-first model and tool replacements' --json`
- `git diff --check`

## Risks

- This build wires the Platform Critic prompt and output schema but does not run three live council cycles; the proof that output appears in three consecutive live council logs is a post-merge observation for Ember.
- Platform Critic is advisory only and cannot veto council decisions.
- The sandbox has an installed `gepa` package with an incompatible `optimize()` signature; the adapter now records that as an unavailable fallback instead of crashing.
- No live council run, external scan, deploy, push, merge, secret access, outreach, or money movement occurred.

## Rollback

Revert the listed d109 files and remove the d109 registry/result/handoff entries. Runtime bypass for council is `PLATFORM_CRITIC_DISABLE=1`; reverting the registry removes the self-portrait and Forge/scout calibration source.

## Intent Solved

The system now has an explicit, living way to notice platform-shaped recommendations before choosing Anthropic/OpenAI/API/SaaS defaults.

## Downstream Intent Unlocked

Future council and Forge recommendations can compare commercial-tool defaults against sovereign/local/open alternatives with a consistent rating instead of relying on unstated model intuition.

