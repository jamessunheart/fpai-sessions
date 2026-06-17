# SPEC_d081_becoming-engine-v1-per-person-jo Result

## Status
Done in working tree. Do not push or merge from this sandbox.

## Summary
Built Becoming Engine v1 SEE model for One Chat:

- Added `brain_index.becoming` schema/migration with `person_id`, identity/contact JSON, source, stage enum, stated intent, proofs JSON, current blocker, CORA balance, last touch, next nurture action, and timestamps.
- Added an advisory `curator.becoming` module that infers per-person stage and next nurture action from conversation text, preserves forward stage movement, stores proof signals, and renders bounded context.
- Wired Telegram owner and confirmed public-lane conversations to best-effort becoming capture before answer generation.
- Injected becoming state into private chat build context and confirmed public-lane answer context without granting private memory.
- Preserved v1 guardrails: no proactive messaging, no answer blocking, no sends, no deploys, reversible DB/table artifact only.

## Tests
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_becoming.py'`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_build_context.py'`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_tgbot_correction_wiring.py'`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_bot_mode_gate.py'`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_*.py'` (25 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/becoming.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_becoming.py SERVICES/sunheart-brain/curator/test_build_context.py SERVICES/sunheart-brain/curator/test_tgbot_correction_wiring.py SERVICES/sunheart-brain/curator/test_bot_mode_gate.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d081-registry.json`
- `git diff --check`

## Risks
- Stage inference is deterministic and conservative; it is useful as a v1 advisory signal, not a diagnosis or final classifier.
- The SQL migration was not applied in this sandbox. Live capture will no-op/log warnings until `brain_index.becoming` exists.
- Public-lane becoming context is same-chat/person only, but still should be reviewed under the public/private canary posture before public mode is expanded.

## Rollback
- Revert the d081 files.
- If applied live, drop `brain_index.becoming` only after exporting any wanted journey-state rows.
- Runtime rollback without code revert: set `SH_BECOMING_CONTEXT_DISABLE=1` to disable prompt injection; remove/apply no migration to disable persistence.

## Intent solved
One Chat can now SEE a person's current becoming stage, stated intent, blocker, and next nurture action during conversation.

## Downstream intent unlocked
The v2 proactive nurture loop can be specified separately against an existing advisory state table, while v1 remains non-sending and reversible.
