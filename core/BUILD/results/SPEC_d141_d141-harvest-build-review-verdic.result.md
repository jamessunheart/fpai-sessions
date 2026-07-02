# SPEC_d141_d141-harvest-build-review-verdic Result

## Status

Done in working tree. Not pushed, merged, deployed, or live-run against brain_index.

## Files Changed

- `tools/learn/sync_corrections_to_dataset.py`
- `tools/learn/test_sync_corrections_to_dataset.py`
- `tools/learning/schema.sql`
- `core/BUILD/specs/SPEC_d141_d141-harvest-build-review-verdic.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d141_d141-harvest-build-review-verdic.result.md`
- `docs/codex/HANDOFF.md`

## Summary

Extended the correction sync bridge so build-review verdicts become learning data:

- parses repo-local `core/BUILD/reviews/*.md` without modifying them;
- extracts `spec_id`, normalized `verdict`, bounded `reasons`, and stable `code_ref`;
- creates `brain_index.review_signals` if a live DSN and psycopg driver are available;
- inserts review signals append-only with `ON CONFLICT (code_ref) DO NOTHING`;
- converts approved/pass/council-ready reviews into positive preference pairs;
- converts request-changes/blocked/reversal reviews into hold-or-repair preference pairs;
- keeps existing correction sync behavior intact.

The current review corpus yields 112 labeled review signals, satisfying the 100+ row proof target in this repo snapshot.

## Tests

- `python3 -B -m unittest tools.learn.test_sync_corrections_to_dataset tools.learn.test_capture_corrections tools.learn.test_learn` (11 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/learn/sync_corrections_to_dataset.py tools/learn/test_sync_corrections_to_dataset.py`
- `python3 -B tools/learn/sync_corrections_to_dataset.py --dry-run --skip-corrections` (`review_signals_read=112`, `review_pairs_added=112`)
- `python3 -B tools/learn/sync_corrections_to_dataset.py --skip-corrections --dataset /tmp/d141-review-pairs-smoke.jsonl` (`review_pairs_added=112`; no DB insert because psycopg unavailable)
- `wc -l /tmp/d141-review-pairs-smoke.jsonl` (`112`)
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d141-registry.json`
- `git diff --check`

## Risks

- Live `brain_index.review_signals` insertion was not exercised in this sandbox because psycopg is unavailable.
- Parser is deterministic markdown parsing; unusual future review formats may be skipped until patterns are expanded.
- Review-derived pairs are coarse preference signals. They should guide L2 preference learning as evidence labels, not become autonomous merge authority.

## Rollback

Revert the changed files listed above. Runtime mitigation without code rollback is to run `tools/learn/sync_corrections_to_dataset.py --skip-reviews` so only the pre-existing correction sync path runs.

## Intent Solved

Build-review verdicts, council verdicts, blocked protected-layer reviews, and reversal-shaped review evidence now become structured learning signals instead of staying inert markdown.

## Downstream Intent Unlocked

The L2 preference ladder can train/evaluate from 100+ review-labeled examples rather than starving on the small live correction count alone.
