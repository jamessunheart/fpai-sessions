# Codex build result - SPEC_d134_d134-constitution-check-governan

_ran: 2026-07-02T00:00:00Z · target: local worktree_

## Summary

Built the d134 governance layer:

- Made `core/STATE/CONSTITUTION.md` the first canonical read in `CLAUDE.md` and Session Start, with the hierarchy `Constitution -> Doctrine -> Current State -> Protocols -> Goals -> detect contradictions -> reason`.
- Added `tools/governance/constitution_check.py`, a deterministic pre-execution governance check that scores protocol violations, human-dependency direction, and learning-engine impact, then appends JSONL rows to `core/BUILD/governance/constitution_ledger.jsonl` by default.
- Wired the check into `SERVICES/sunheart-brain/curator/decision_agent.py` before model execution.
- Wired the check into `tools/build_loop/build_orchestrator.sh` before Codex execution and before integration.
- Added `tools/build_loop/run_codex.sh --spec-id` so the orchestrator can pass only constitution-approved specs.
- Added tests for laptop-awake and manual-merge anti-pattern rejection, including untagged manual-merge dependency.

## Tests

- `python3 -B -m unittest tools.governance.test_constitution_check tools.decisions.test_decision_agent` (11 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/governance/constitution_check.py tools/governance/test_constitution_check.py tools/decisions/test_decision_agent.py SERVICES/sunheart-brain/curator/decision_agent.py`
- `bash -n tools/build_loop/build_orchestrator.sh tools/build_loop/run_codex.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d134-registry.json`
- `git diff --check`
- `python3 tools/governance/constitution_check.py --no-ledger --kind build-decision --id d134-smoke --text 'Wait for James to manually merge this.'` returned reject / exit 2
- `tools/build_loop/run_codex.sh --dry-run --target /tmp --spec-id SPEC_d134_d134-constitution-check-governan`

## Independent Review

Independent AI review initially found three blockers; all were fixed. Re-review returned: `No blockers.`

Review artifact: `core/BUILD/reviews/build-SPEC_d134_d134-constitution-check-governan.md`

## Risks

- The checker is deterministic and regex-based. It is intentionally fast and local, but future Constitution language changes may need a rule update.
- The ledger is append-only by code path, not tamper-proof at filesystem level.
- Live build-loop execution was not run in this sandbox; only shell syntax and dry-run filtering were verified.

## Rollback

Revert the listed files. Runtime mitigation without full rollback: set `FPAI_GOVERNANCE_LEDGER` to redirect ledger writes during tests or isolated runs; set `DECISION_AGENT_DISABLE=1` to disable the decision agent path as before.

## Intent

Intent solved: every autonomous proposal/build-decision has a pre-execution governance gate aligned to the Constitution.

Downstream intent unlocked: architecturally inconsistent work is caught before it reaches James or the autonomous build path.

