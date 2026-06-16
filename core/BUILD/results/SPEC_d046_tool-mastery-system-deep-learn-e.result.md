# SPEC_d046_tool-mastery-system-deep-learn-e Result

## Status
Done / awaiting independent review and merge review.

## Files changed
- `docs/tool_mastery/`
- `curator/__init__.py`
- `curator/tool_mastery/`
- `tools/merge/ai_review.py`
- `tools/council/debate.py`
- `tools/build_loop/health_check.sh`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d046_tool-mastery-system-deep-learn-e.md`
- `core/BUILD/results/SPEC_d046_tool-mastery-system-deep-learn-e.result.md`
- `docs/codex/HANDOFF.md`

## Summary
Added the Tool Mastery substrate: reviewable mastery cards for Claude/Fable 5, Codex, Claude review, Stripe, Brevo, Hermes, Ollama, and Cal.com; a compact loader that extracts optimal-use and anti-pattern sections; `inject_mastery()` with `TOOL_MASTERY_DISABLE=1`; a `learn_tool()`/`refresh_all()` learner with `[AUTO-GENERATED]` card refresh discipline; and the `python -m curator.tool_mastery learn ...` CLI.

`tools/merge/ai_review.py` now injects `claude_review` mastery into review prompts, and `tools/council/debate.py` injects `claude_fable5` mastery into council prompts. `tools/build_loop/health_check.sh` now detects `CURATOR_ANTHROPIC_MODEL` changes and refreshes the auto-generated `claude_fable5` card from Anthropic release notes, recording the model as handled only after refresh success or an explicit human-edited-card skip.

## Tests
- `python3 -B -m unittest curator.tool_mastery.test_loader` (8 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile curator/__init__.py curator/tool_mastery/__init__.py curator/tool_mastery/loader.py curator/tool_mastery/learn.py curator/tool_mastery/__main__.py curator/tool_mastery/test_loader.py tools/merge/ai_review.py tools/council/debate.py`
- `bash -n tools/build_loop/health_check.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check -- curator docs/tool_mastery tools/merge/ai_review.py tools/council/debate.py tools/build_loop/health_check.sh core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d046_tool-mastery-system-deep-learn-e.md`

## Risks
The learner's live `claude -p --effort high` path was not exercised in this sandbox. Seed cards are human-reviewable starting cards, not authoritative vendor docs. `curator/capabilities/executor.py` was not present in this checkout, so the send_email/book_calendar injection hook could not be wired here.

## Independent review
Completed by subagent. Initial findings on model-update refresh were fixed: the health check now calls the `claude_fable5` learner against release notes instead of broad `refresh-all`, does not mark failed refreshes as handled, and `refresh_all()` now prefers the card's recorded source URL rather than stale card text.

## Rollback
Remove `docs/tool_mastery/` and `curator/tool_mastery/`; revert the prompt injection lines in `tools/merge/ai_review.py` and `tools/council/debate.py`; remove the model-refresh block from `tools/build_loop/health_check.sh`; remove the d046 registry/result/handoff entries.

## Intent solved
Integrated tools now have a repo-local mastery layer that can inject concrete use patterns and anti-patterns at call time.

## Downstream intent unlocked
Future tool integrations can create or refresh mastery cards through the CLI, then wire calls to `inject_mastery()` so tool usage improves without re-briefing James or duplicating prompt lore.
