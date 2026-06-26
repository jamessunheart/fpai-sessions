# SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e_session-persistence — result

## Status
Done in working tree. Not pushed, merged, deployed, or activated.

## Files changed
- `tools/continuity/session_persistence.py`
- `tools/continuity/test_session_persistence.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `core/BUILD/specs/SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e_session-persistence.md`
- `core/BUILD/results/SPEC_36a73161-fb6c-42c8-98b7-f5d479dfa08e_session-persistence.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary
Added a repo-side session persistence mechanism for bounded JSON snapshots. A snapshot records the session id, surface, saved time, current branch/head, changed files, active build progress from `core/BUILD/REGISTRY.json`, recent result artifacts, and a progress note. It writes `latest.json` plus a per-session copy under `FPAI_SESSION_STATE_DIR` or `/opt/fpai-build/session_state`.

Wired `SERVICES/sunheart-brain/curator/build_context.py` to load the latest snapshot fail-soft and render it in owner-chat context as persisted session progress. Runtime kill switch: `SH_SESSION_PERSISTENCE_DISABLE=1`. Existing registry/live-status/session-insights behavior remains intact when no snapshot exists.

## Tests
- `python3 -B -m unittest tools.continuity.test_session_persistence tools.continuity.test_write_session_insights`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_build_context.py'`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/continuity/session_persistence.py tools/continuity/test_session_persistence.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_build_context.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/session-persistence-registry.json`
- `python3 -B tools/continuity/session_persistence.py save --state-dir /tmp/fpai-session-persistence-smoke --session-id smoke --progress-note 'smoke progress' --json >/tmp/session-persistence-save.json && python3 -B tools/continuity/session_persistence.py show --state-dir /tmp/fpai-session-persistence-smoke`
- `git diff --check`

## Risks
- The smoke test writes to `/tmp`; the live default state directory `/opt/fpai-build/session_state` was not created in this sandbox.
- This stores operational context/progress only. It does not replace the live DB conversation thread or `brain_index.session_insights`.
- Fresh-process accuracy depends on callers running `session_persistence.py save` at closeout or hook time.

## Rollback
Revert the listed files. Runtime mitigation without reverting: set `SH_SESSION_PERSISTENCE_DISABLE=1` to stop prompt injection and stop calling `tools/continuity/session_persistence.py save`.

## Intent solved
Fresh sessions can load a bounded, current snapshot of what branch/spec was in progress and what files/progress were left behind.

## Downstream intent unlocked
The bot/status surface can report running specs and recent build progress after a session boundary without depending on James to re-brief it.
