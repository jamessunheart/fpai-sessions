# SPEC_d070_cora-credit-for-probe-conversati Result

Status: done / awaiting independent AI review + merge review

Branch: `build/SPEC_d070_cora-credit-for-probe-conversati`

## Files Changed

- `tools/probe/award_cora.py`
- `tools/probe/test_award_cora.py`
- `core/STATE/CORA_PROBE_REWARDS.md`
- `core/BUILD/specs/SPEC_d070_cora-credit-for-probe-conversati.md`
- `core/BUILD/results/SPEC_d070_cora-credit-for-probe-conversati.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added an idempotent CORA awarder for closed probe conversations. `tools/probe/award_cora.py` applies the requested `tester_identifier` migration, creates `brain_index.cora_ledger` if needed, and writes one `probe_conversation_complete` event per `probe_id`.

Award rules:

- 10 CORA credits for a meaningful completed probe conversation.
- +5 when notes/message evidence reports a specific gap or correction.
- +10 when `corrections_triggered > 0`, treated as the James-validated correction signal requested by the spec.

Meaningful conversation source:

- `completed_spark = true`, or
- 5+ messages.

The current probe schema does not have `message_count`, so the awarder uses `message_count` when present and falls back to existing `drop_off_message`, which `refresh_session_outcomes()` already stores as the matched message count.

`core/STATE/CORA_PROBE_REWARDS.md` defines the promised points/rewards/access tiers and keeps CORA framed as closed-loop access credit, not cash, resale value, equity, governance, debt, yield, or investment.

## Tests

- `python3 -B -m unittest tools.probe.test_award_cora` — 3 tests OK.
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/probe/award_cora.py tools/probe/test_award_cora.py`
- `python3 -B -m unittest tools.probe.test_award_cora tools.probe.test_probe` — 17 tests OK.
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `git diff --check`

## Independent Review

Not completed in this sandbox. `tools/merge/ai_review.py build/SPEC_d070_cora-credit-for-probe-conversati` returned an empty-diff approval because this environment has an uncommitted working diff and the review tool compares committed branch refs only. Treat that as invalid review evidence; rerun independent review after committing from a writable Git context.

## Risks

- The live DB migration was not applied from this sandbox. The awarder will apply `ALTER TABLE brain_index.probe_sessions ADD COLUMN IF NOT EXISTS tester_identifier TEXT` when run against the live database.
- Existing probe rows without `tester_identifier` can still award only if notes contain a handle/email fallback.
- `brain_index.cora_ledger` is introduced by the awarder because no runtime CORA ledger implementation was present in the repo beyond the d035 review-only policy.
- The daily timer was not edited in this sandbox; Ember should wire `tools/probe/award_cora.py` after the probe cycle/rate governor on the live host.

## Rollback

Revert the files listed above. If the awarder has already run live, stop invoking it and remove or ignore `probe_conversation_complete` rows in `brain_index.cora_ledger`; the `tester_identifier` column is additive and can be left in place unless Ember confirms no dependent code uses it.

## Intent Solved

Probe testers now have a concrete CORA credit event tied to meaningful AI testing contribution, closing the outreach promise loop.

## Downstream Intent Unlocked

Ember can wire the awarder into the daily probe timer and show testers the reviewed CORA probe reward tiers once live DB migration and first dry-run proof are complete.
