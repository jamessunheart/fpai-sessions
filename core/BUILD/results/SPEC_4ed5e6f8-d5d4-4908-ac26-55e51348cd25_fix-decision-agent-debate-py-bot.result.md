# SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot Result

## Status
done in working tree / awaiting merge review

## Summary
Hardened `tools/council/debate.py` voice execution so council runs fail transparently and isolate optional voice failures. The Claude JSON caller now resolves the CLI from `PATH` or `CLAUDE_BIN`, checks non-zero exits, reports stderr/stdout in the raised error, and parses the first JSON object from wrapped output. The GPT/Codex second-lab voice now resolves `codex` from `PATH` or `CODEX_BIN`, checks non-zero exits, logs `gpt_voice_error`, and remains best-effort. The GLM/Pragmatist auxiliary lens now logs `pragmatist_voice_error` instead of silently disappearing.

## Files Changed
- `tools/council/debate.py`
- `tools/council/test_debate.py`
- `core/BUILD/specs/SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot.md`
- `core/BUILD/results/SPEC_4ed5e6f8-d5d4-4908-ac26-55e51348cd25_fix-decision-agent-debate-py-bot.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests
- `python3 -B -m unittest tools.council.test_debate`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/council/debate.py tools/council/test_debate.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks
- No live council run was executed because it depends on live Claude/Codex auth, server env, and the decisions database.
- If the live Claude CLI is authenticated but returns malformed JSON, the council still stops the debate round, but now logs `debate_error` with the concrete parse failure instead of hiding the cause.

## Rollback
Revert the listed files. Runtime bypass remains the existing council kill switch at `~/.config/fpai/council/.disabled`.

## Intent solved
Decision-agent council runs no longer lose both voices silently or fail without actionable CLI/error detail.

## Downstream intent unlocked
The autonomous decision loop can distinguish unavailable auxiliary voices from a main debate failure and route the next repair from ops-ledger evidence instead of repeatedly retrying an opaque broken council run.
