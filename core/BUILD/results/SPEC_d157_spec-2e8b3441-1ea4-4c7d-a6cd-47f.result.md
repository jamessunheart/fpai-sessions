# SPEC_d157_spec-2e8b3441-1ea4-4c7d-a6cd-47f Result

## Status
Done in working tree / awaiting independent review + merge.

## Summary
Added a focused regression audit for the named-spec seeding path that created d157. The test recreates `SPEC_2e8b3441-1ea4-4c7d-a6cd-47f799aa2696_test-stall-audit.md`, starts the fake `brain_index.decisions` namespace at `d156`, and verifies the seeder:

- allocates `d157`;
- inserts the decision row with the original spec heading as the question;
- records the original named spec filename in the answer;
- renames the spec to `SPEC_d157_2e8b3441-1ea4-4c7d-a6cd-47f799aa2696-test-stall-audit.md`;
- emits fallback proof text containing the phrase `answered needs_build row` for `d157` and the renamed target spec.

## Tests
- `python3 -B -m unittest tools.build_loop.test_seed_orphaned_specs` (9 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/build_loop/seed_orphaned_specs.py tools/build_loop/test_seed_orphaned_specs.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d157-registry.json`

## Risks
This is a deterministic repo-local audit. It did not connect to the live `brain_index` database or rename live repo files. It proves the code path and row payload shape with the existing fake DB harness.

## Rollback
Revert this branch to remove the d157 regression test, generated d157 spec artifact, result artifact, registry entry, and handoff note.

## Intent solved
The test-stall audit now has executable proof that a named test-stall spec is converted into an answered `needs_build` d157 decision row with the expected renamed spec target.

## Downstream intent unlocked
Future named-spec seeding regressions that would stall the decision-driven build loop are caught by the focused seeder test suite before merge.
