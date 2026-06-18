# SPEC_d095_adopt-gepa-dittofeed-vllm-router Result

## Status

Done in working tree / awaiting merge review.

## Files Changed

- `tools/adoption/__init__.py`
- `tools/adoption/frontier_adoption.py`
- `tools/adoption/test_frontier_adoption.py`
- `core/STATE/FRONTIER_ADOPTIONS.md`
- `core/BUILD/signals/frontier_adoptions.json`
- `core/BUILD/specs/SPEC_d095_adopt-gepa-dittofeed-vllm-router.md`
- `core/BUILD/results/SPEC_d095_adopt-gepa-dittofeed-vllm-router.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Converted the d095 Forge frontier scan into safe, additive shadow-mode adoption artifacts. GEPA is recorded as already covered by d106/d107 rather than duplicated. Dittofeed now has a reviewed journey shape plus anonymized probe-session event export rules that hash user ids and exclude names, emails, phones, raw notes, raw conversations, corrections, and credentials. LiteLLM plus vLLM Semantic Router now has a config artifact and 10 deterministic routing fixtures covering local, public, private, blocked, and James-gated cases before any replacement of existing router paths.

No deploy, send, package install, service start, secret access, external API call with effect, push, merge, or money movement occurred.

## Tests

- `python3 -B -m unittest tools.adoption.test_frontier_adoption`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/adoption/__init__.py tools/adoption/frontier_adoption.py tools/adoption/test_frontier_adoption.py`
- `python3 -m json.tool core/BUILD/signals/frontier_adoptions.json`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks

This branch proves config/evaluation readiness only. It does not prove a live Dittofeed send or a live LiteLLM proxy call, because those require reviewed service wiring, credentials, and activation outside this sandbox. The LiteLLM `claude_review` entry is intentionally an artifact requiring an approved API path or bridge, not an active secret-bearing config.

## Rollback

Revert the listed d095 files. Since nothing was deployed or activated, rollback is repo-only. Existing probe follow-up, GEPA d106/d107, and router paths remain untouched.

## Intent Solved

The Forge frontier scan findings are no longer loose recommendations: each has a shadow-mode adoption state, privacy gate, proof gate, and rollback path.

## Downstream Intent Unlocked

Ember can review one Dittofeed shadow journey and one LiteLLM/vLLM-router 10-decision eval before choosing any live activation or replacement of existing journey/router code.
