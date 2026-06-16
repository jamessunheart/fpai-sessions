# SPEC_d028_decision-agent-v0-1-confidence-s Result

- Status: done / independent-reviewed / awaiting merge review
- Branch: `build/SPEC_d028_decision-agent-v0-1-confidence-s`
- Completed at: 2026-06-16T12:37:03Z

## Summary

Added Decision Agent v0.1 for confidence-scored decision auto-answering. The deployed scorer lives in `SERVICES/sunheart-brain/curator/decision_agent.py`; `tools/decisions/decision_agent.py` preserves the spec-facing wrapper entry point. The scorer uses only the local `claude -p` CLI path, injects recent corrections, recent approved/reversed decisions, and a James profile stub, then returns the required `{answer, confidence, why, reversible, auto_proceed}` schema.

The curator decision loop now persists `agent_score`, `agent_answer`, and `agent_why`, auto-answers only high-confidence reversible non-reserved decisions, sends James an override affordance, and appends every auto-decision to the ops ledger. Telegram now recognizes `override dNNN: answer`; overrides update the decision answer and write a `brain_index.corrections` row with `weight=2.0`.

## Files Changed

- `tools/decisions/decision_agent.py`
- `tools/decisions/test_decision_agent.py`
- `SERVICES/sunheart-brain/curator/decision_agent.py`
- `SERVICES/sunheart-brain/curator/decisions.py`
- `SERVICES/sunheart-brain/curator/test_decisions_agent.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/index/schema.sql`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/specs/SPEC_d028_decision-agent-v0-1-confidence-s.md`
- `core/BUILD/results/SPEC_d028_decision-agent-v0-1-confidence-s.result.md`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.decisions.test_decision_agent` (5 tests OK)
- `PYTHONPATH=SERVICES/sunheart-brain python3 -B -m unittest SERVICES/sunheart-brain/curator/test_decisions_agent.py curator.test_tgbot_correction_wiring curator.test_corrections` (12 tests OK)
- `PYTHONPATH=SERVICES/sunheart-brain python3 -B -c "import curator.decisions; print('ok')"`
- `PYTHONPATH=SERVICES/sunheart-brain python3 -B -m unittest tools.decisions.test_decision_agent SERVICES/sunheart-brain/curator/test_decisions_agent.py curator.test_tgbot_correction_wiring curator.test_corrections tools.decisions.test_daily_sync tools.queue.test_migrate_decisions` (24 tests OK)
- `python3 -B -m unittest tools.decisions.test_decision_agent tools.decisions.test_daily_sync tools.queue.test_migrate_decisions`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/decisions/decision_agent.py tools/decisions/test_decision_agent.py SERVICES/sunheart-brain/curator/decision_agent.py SERVICES/sunheart-brain/curator/decisions.py SERVICES/sunheart-brain/curator/test_decisions_agent.py SERVICES/sunheart-brain/curator/tgbot.py`
- `git diff --check -- tools/decisions/decision_agent.py tools/decisions/test_decision_agent.py SERVICES/sunheart-brain/curator/decision_agent.py SERVICES/sunheart-brain/curator/decisions.py SERVICES/sunheart-brain/curator/test_decisions_agent.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/index/schema.sql core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d028_decision-agent-v0-1-confidence-s.md core/BUILD/results/SPEC_d028_decision-agent-v0-1-confidence-s.result.md docs/codex/HANDOFF.md`

Broader check attempted:

- `PYTHONPATH=SERVICES/sunheart-brain python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test*.py'` fails on existing `test_build_context.BuildContextTest.test_recent_corrections_are_injected` because the suffix did not include `Corrections:`. The new decision-agent tests pass under discovery.

## Independent Review

Independent AI review found three issues before closeout:

- Live service deployment could not import `tools.decisions.decision_agent` with service-only `PYTHONPATH`. Fixed by moving the implementation into `curator.decision_agent` and keeping the tools file as a wrapper; added a service-only import regression.
- Agent errors after `_mark_awaiting()` could strand a decision without a normal Telegram card. Fixed with a fallback around `auto_answer_if_confident()` and a regression test.
- Some SQL fallback expressions referenced absent columns. Fixed decision surfacing updates with schema-aware column selection and fixed recent-decision context lookup to avoid missing-column references.

## Risks

- This sandbox did not run against the live `brain_index` database, Telegram bot, or live `claude -p` binary.
- The live `brain_index.decisions` table must already have the columns used by the existing decision loop (`id`, `status`, `answer`, timestamps, etc.); this build adds only the requested agent score columns and weighted corrections column.
- If `claude -p` is unavailable or malformed, the agent fails closed with `auto_proceed=false`.

## Rollback

Revert the changed files. If the migration has already run live, optionally leave the additive nullable score columns and correction `weight` column in place, or remove them manually after confirming no downstream rows depend on them.

## Intent

- Intent solved: reversible low-risk decisions can move without blocking James while preserving a clear override path.
- Downstream intent unlocked: James's overrides become high-value preference data for the continuous-learning loop.
