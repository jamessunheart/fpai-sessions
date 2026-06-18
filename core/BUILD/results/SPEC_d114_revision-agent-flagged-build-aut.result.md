# SPEC_d114_revision-agent-flagged-build-aut Result

## Status

Done in working tree. Do not push or merge from this session.

## Files Changed

- `tools/build_loop/server_build_loop.sh`
- `tools/build_loop/test_revision_agent.py`
- `core/BUILD/specs/SPEC_d114_revision-agent-flagged-build-aut.md`
- `core/BUILD/results/SPEC_d114_revision-agent-flagged-build-aut.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added a bounded revision-agent loop to `server_build_loop.sh`. When `ai_review.py` returns a flagged non-protected result, the loop now reads the generated review file, extracts the Findings section, prompts Codex in the same worktree with the original spec plus reviewer feedback, commits any revision on the same branch, and reruns `ai_review.py`.

The loop stops after approval, protected-path block, or two revision attempts. `REVISION_AGENT_DISABLE=1` skips revision entirely. If the build is still flagged after two attempts, it logs the exhausted fallback and continues through the existing silent flagged auto-merge path.

## Tests

- `bash -n tools/build_loop/server_build_loop.sh`
- `python3 -B -m unittest tools.build_loop.test_revision_agent`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/test_revision_agent.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Risks

This sandbox did not run a live server build-loop cycle, spawn a real Codex revision subprocess, or call Claude review. Coverage is a static control-flow contract test because the live loop depends on server-only paths, systemd environment, the decisions DB, and local Codex/Claude credentials.

The revision prompt includes bounded review findings and the original generated spec. If a reviewer gives vague feedback, the revision agent may make no changes and the build will fall back after two logged attempts.

## Rollback

Revert the listed files. Runtime rollback is `REVISION_AGENT_DISABLE=1`, which preserves the previous flagged-build behavior without editing code.

## Intent Solved

Flagged reversible builds now get an automated, tightly-scoped repair attempt before being silently merged.

## Downstream Intent Unlocked

The autonomous server build loop can turn a reviewer-flagged build into an APPROVE path without manual tightening when the reviewer findings are specific and fixable.
