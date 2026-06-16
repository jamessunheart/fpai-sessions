# SPEC_d045_life-data-intake-v0-1 Result

- Status: done
- Branch: `build/SPEC_d045_life-data-intake-v0-1`
- Generated: `2026-06-16T19:20:00Z`

## Summary

Added Life Data Intake v0.1 as a fixture/local-export-first ingestion scaffold for James's financial accounts, calendar, and communications. The pipeline normalizes records into a shared signal shape, hashes source IDs, redacts emails/phone-like identifiers, tags useful signals, and refuses live provider mode until a future scoped adapter spec exists.

Full normalized JSONL is sensitive and writes outside the git repo by default at `/tmp/fpai-life-data/intake.jsonl`. Repo-path full-record writes are refused unless `FPAI_LIFE_DATA_ALLOW_REPO_OUTPUT=1` is explicitly set for a reviewed local-only run. The committed Markdown report is aggregate/signal-index only.

## Files Changed

- `tools/life_data/`
- `docs/codex/LIFE_DATA_INTAKE.md`
- `core/BUILD/specs/SPEC_d045_life-data-intake-v0-1.md`
- `core/BUILD/reviews/build-SPEC_d045_life-data-intake-v0-1.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.life_data.test_intake` - 6 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/life_data/intake.py tools/life_data/test_intake.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -m json.tool tools/life_data/fixtures/financial.json`
- `python3 -m json.tool tools/life_data/fixtures/calendar.json`
- `python3 -m json.tool tools/life_data/fixtures/communications.json`
- JSONL parse check for `/tmp/fpai-life-data/intake.jsonl`
- `git diff --check`

## Independent Review

Completed by subagent. Initial review found a high blocker: full normalized life records were being written into repo state/docs, which would leak sensitive real data if used with live exports. That was fixed by moving full JSONL outside the repo by default, refusing repo-local full-record writes, deleting the repo JSONL artifact, and reducing the Markdown report to aggregate/signal metadata. Re-review found no remaining code/safety blockers.

## Risks

- V0.1 does not connect to real providers. It requires local/export JSON or a future scoped live adapter spec with James-owned credentials.
- Full JSONL remains sensitive even outside the repo; it must be handled as private local state.
- Signal tagging is deterministic and conservative, not a complete personal optimization model.

## Rollback

Delete `tools/life_data/`, `docs/codex/LIFE_DATA_INTAKE.md`, this result file, and `core/BUILD/reviews/build-SPEC_d045_life-data-intake-v0-1.md`; remove the d045 row from `core/BUILD/REGISTRY.json`; remove the d045 HANDOFF entry. Remove `/tmp/fpai-life-data/intake.jsonl` if the local generated artifact is no longer wanted.

## Intent

- Intent solved: FPOS now has a safe, test-covered personal signal intake lane for finance, calendar, and communications exports without exposing secrets or performing live actions.
- Downstream intent unlocked: James/Ember can approve scoped provider adapters or local export jobs that feed this single normalized lane, then route real personal signals into optimization surfaces without inventing separate ingestion shapes per domain.
