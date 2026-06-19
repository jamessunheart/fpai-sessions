# SPEC_d124_spec-d124-chat-context-routing-s Result

Status: done in working tree / awaiting merge review
Branch: `build/SPEC_d124_spec-d124-chat-context-routing-s`
Date: 2026-06-19

## Summary

Added a lightweight, deterministic chat context router for Telegram synthesis. `CURATOR_CONTEXT_ROUTING=1` now classifies incoming owner questions into `ops`, `treasury`, `memory`, or `general` and routes context blocks before synthesis:

- `ops`: system-state + buildstream, no corrections, no becoming, no brain search
- `treasury`: system-state + corrections, no buildstream, no becoming, no brain search
- `memory` / `general`: all context blocks + brain search, matching current behavior

The env gate is off by default, so production behavior remains unchanged until explicitly enabled.

## Files Changed

- `tools/synthesis/__init__.py`
- `tools/synthesis/context_router.py`
- `tools/synthesis/test_context_router.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `core/BUILD/specs/SPEC_d124_spec-d124-chat-context-routing-s.md`
- `core/BUILD/results/SPEC_d124_spec-d124-chat-context-routing-s.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Proof

Three test messages in `tools/synthesis/test_context_router.py` measure routed context blocks against the legacy 5-block baseline:

- `What is the current build status?` -> `ops` -> 2 blocks
- `What is treasury runway and wallet balance?` -> `treasury` -> 2 blocks
- `What did I say about Josh last week?` -> `memory` -> 5 blocks

## Tests

- `env HOT_MEMORY_STATE_PATH=/tmp/d124-no-hot-state.md SELF_DIAGNOSTIC_CONTEXT_FILE=/tmp/d124-no-diagnostic.json python3 -B -m unittest tools.synthesis.test_context_router SERVICES.sunheart-brain.curator.test_build_context SERVICES.sunheart-brain.curator.test_tgbot_correction_wiring` (22 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/synthesis/context_router.py tools/synthesis/test_context_router.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_build_context.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks

- No live Telegram chat, production bot restart, deploy, push, merge, outreach, secrets, external API call with effect, or money movement was run in this sandbox.
- Independent AI review was attempted with local `claude -p`, but the command timed out after 60 seconds with no output. This branch still needs a successful pre-merge reviewer pass before claiming independent-AI-reviewed.
- Ops and treasury routed answers skip brain search by design when `CURATOR_CONTEXT_ROUTING=1`; if a question is ambiguous, the classifier falls back to `general` to preserve the full legacy path.

## Rollback

Revert the listed files. Runtime mitigation without reverting is to leave `CURATOR_CONTEXT_ROUTING` unset or set it to `0`.

## Intent

Intent solved: owner chat synthesis no longer has to inject every heavy context block for ops/status and treasury questions.

Downstream intent unlocked: Ember can enable `CURATOR_CONTEXT_ROUTING=1` on the live bot for a reversible proof cycle and compare shorter prompt context against answer quality before making routing default.
