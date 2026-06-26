# SPEC_bd1e3266-aab7-4e11-bc87-1de679e783d6_standard-audit-rotation-awarenes Result

- Status: done in working tree / awaiting merge review
- Branch: `build/SPEC_bd1e3266-aab7-4e11-bc87-1de679e783d6_standard-audit-rotation-awarenes`
- Summary: Expanded the standard self-audit evidence rotation with `awareness_probe`, top-level `recent_user_messages`, and `queue_state`. The audit prompt now explicitly tells the model to inspect current awareness score/source, the last 3 user messages, and queue state before proposing specs.
- Files changed: `tools/build_loop/self_audit.py`; `tools/build_loop/test_self_audit.py`; `core/BUILD/specs/SPEC_bd1e3266-aab7-4e11-bc87-1de679e783d6_standard-audit-rotation-awarenes.md`; `core/BUILD/results/SPEC_bd1e3266-aab7-4e11-bc87-1de679e783d6_standard-audit-rotation-awarenes.result.md`; `core/BUILD/REGISTRY.json`; `docs/codex/HANDOFF.md`
- Tests: `python3 -B -m unittest tools.build_loop.test_self_audit`; `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/self_audit.py tools/build_loop/test_self_audit.py`; `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d128-registry.json`
- Risks: Live DB read for recent messages was not exercised in this sandbox; the collector fails soft with an explicit unavailable shape when DSN/psycopg/live DB is missing. Queue state is repo-local from spec/result artifacts plus registry, not live `dec pending-builds`.
- Rollback: Revert the listed files. Runtime impact is limited to read-only self-audit evidence and prompt content.
- Intent solved: Every self-audit run now includes the highest-drift operational questions the bot identified instead of relying on the model to infer them.
- Downstream intent unlocked: Future self-audit specs can prioritize awareness drift and queued-work blind spots from explicit evidence.
