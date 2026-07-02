# SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25-reality-fix_repair-merged-dead-build-4ed5e6f

Status: done in working tree; activation appends proof after merge.

## Summary

Added a scoped post-merge reality repair for the original decision-agent debate.py bot fix. The repair helper proves the shipped debate wrapper behavior with injected failures instead of live CLI calls:

- codex voice failure returns an empty fallback and logs `gpt_voice_error`
- GLM pragmatist failure returns an empty fallback and logs `pragmatist_voice_error`
- Claude JSON wrapper parses wrapped JSON
- Claude CLI failure raises a clear error instead of hiding the failure

When the smoke passes, the helper appends the two proof rows required by the delayed reality checker for `SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot`: `liveness:pass` and `feature_outcome` with `verdict=improved`.

## Tests

- `python3 -B -m unittest tools.build_loop.test_decision_agent_debate_reality_repair tools.build_loop.test_post_merge_reality_check tools.build_loop.test_feature_outcome tools.liveness.test_probe tools.council.test_debate` (30 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/decision_agent_debate_reality_repair.py tools/build_loop/test_decision_agent_debate_reality_repair.py`
- `bash -n core/BUILD/activate/SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25-reality-fix_repair-merged-dead-build-4ed5e6f.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/4ed-repair-registry.json`
- `/tmp` ledger smoke verified `liveness:pass` plus `feature_outcome verdict=improved`

## Rollback

Revert the files in this repair build. If the activation already ran and the proof rows need to be undone, remove the appended `liveness:pass` and `feature_outcome` rows for `SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot` from the ops ledger after confirming no downstream audit depends on them.
