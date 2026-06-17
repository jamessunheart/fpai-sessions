# SPEC_d074_human-coach-matching-cora-credit Result

Status: done / independently AI-reviewed / awaiting merge review

Branch: `build/SPEC_d074_human-coach-matching-cora-credit`

## Files Changed

- `tools/coach/__init__.py`
- `tools/coach/identifier.py`
- `tools/coach/matcher.py`
- `tools/coach/session_tracker.py`
- `tools/coach/credit_ledger.py`
- `tools/coach/test_coach.py`
- `core/STATE/COACH_ECONOMY.md`
- `core/BUILD/specs/SPEC_d074_human-coach-matching-cora-credit.md`
- `core/BUILD/results/SPEC_d074_human-coach-matching-cora-credit.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added the d074 human coach matching and CORA credit economy scaffold. The new coach package identifies pending coaches from high-quality probe conversations, matches seekers to active coaches by blocker specialty and quality threshold, tracks completed sessions, awards CORA credits idempotently, gates fiat conversion until 20 active coaches, and returns correction-shaped learning signals for later routing improvement. The state doc captures credit tiers, DB table shape, phase gates, and no-live-effect boundaries.

## Tests

- `python3 -B -m unittest tools.coach.test_coach` (6 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/coach/__init__.py tools/coach/identifier.py tools/coach/matcher.py tools/coach/session_tracker.py tools/coach/credit_ledger.py tools/coach/test_coach.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Independent Review

Independent AI review found no P1 implementation blockers. It verified fixture-only tests/no live DB behavior, active/tag/quality coach matching, pending `active=false` coach identification at `quality_score >= 0.7`, idempotent credit awards, fiat gate behavior, and no live outreach/money/deploy/secret behavior. The initial closeout findings were registry status and uncommitted files; registry status is fixed here. Local commit may still depend on writable Git metadata in this sandbox.

## Risks

This is a repo-side scaffold. It does not apply SQL migrations, write live `brain_index` rows, send coach invitations, schedule sessions, move fiat, convert credits, deploy, push, or merge. The optional Claude tag extraction path is fallback-only and not exercised by tests; fixture heuristics keep the test path offline.

## Rollback

Remove `tools/coach/`, `core/STATE/COACH_ECONOMY.md`, this result file, the d074 spec artifact, the d074 registry row, and the d074 handoff entry. No live DB or service rollback is required because no live mutations were performed.

## Intent

Intent solved: conversations that exceed the AI's useful limit now have a repo-side scaffold for identifying human coach candidates, matching them to stuck seekers, tracking sessions, awarding credits, and producing learning signals.

Downstream intent unlocked: future approved live specs can add migrations and gated adapters so Spark/probe flows can safely route stuck seekers to human coaches and learn from successful coached interventions.

