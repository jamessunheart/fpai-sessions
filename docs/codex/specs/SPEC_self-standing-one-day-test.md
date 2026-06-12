# SPEC_self-standing-one-day-test

status: blessed
blessed_by: James
blessed_scope: Measure and report the self-standing test; do not broaden autonomy beyond the existing gates.

## Intent

Prove whether the FPOS Intelligence Engine can run for one day without James acting as the glue.

This is not a new feature build. It is the proof harness for the self-standing ladder after Rungs 0-3:

- Rung 0 Safety
- Rung 1 Auto-proof
- Rung 2 Self-refreshing surfaces
- Rung 3 Auto-routing

## Downstream Intent Unlocked

If the test passes, downstream resource work can resume from a stronger engine:
Financial Hub, Comms Hub, service cleanup, revenue paths, and human delegation become products of the engine instead of distractions from finishing it.

If the test fails, the failure names the next engine repair.

## Branch

`feat/self-standing-test`

## Owner Lanes

- **James:** gives the explicit `go autonomous` / `not yet` call and handles Reserved Class decisions.
- **Ember / Claude Code:** runs or schedules the live guarded loop, mirrors vault surfaces, and stops at gates.
- **Codex:** builds repo-side specs, read-only observers, report harnesses, tests, and branchable tooling.

## Allowed Autonomous Actions

Only inside existing gates:

- run the guarded router tick;
- run closeout/surface refresh;
- write proof rows for completed safe work;
- draft downstream specs with `status: needs-bless`;
- append Codex-owned handoff run notes;
- report drift and failures.

## Stop Conditions

Stop and ask James/Ember for any:

- money/resource movement;
- public voice, outreach, or sending messages;
- people, hiring, reward, partner, relationship, or legal decisions;
- production deploys;
- secrets or credentials;
- service stops, moves, archives, or deletes;
- irreversible changes;
- metered spend beyond the configured gate;
- ambiguous action that cannot be rolled back cleanly.

## Pass Criteria

The test passes only if all five hold for the test window:

1. **Zero James glue:** James is not needed to keep the loop moving, except for genuine Reserved Class gates.
2. **Resource gate enforced:** metered spend remains within the configured cap and autonomous spenders are guarded.
3. **No stale surfaces:** HOME, Intent Buildstream, Self-Model, Handoff, Index, and Proof point to the same current truth.
4. **Every ship self-logged:** proof rows include Intent solved, Unlocks next, Proof, and Next move.
5. **Fresh session continuity:** a fresh Codex/Claude session can re-orient from repo/vault mirrors without James re-briefing.

Any fail becomes the next repair intent.

## Evidence Required

- Start time and end time.
- Commands or timers used.
- Router ticks and actions taken.
- Closeout runs and results.
- Latest proof rows.
- HOME / Buildstream / Self-Model agreement.
- Cost guard/cap evidence.
- Reserved Class escalations, if any.
- Git state: committed vs local-only changes.
- Final pass/warn/fail verdict.

## Report Harness

Codex builds:

```bash
python3 tools/selftest/report.py
```

Optional repo report:

```bash
python3 tools/selftest/report.py --output docs/codex/SELF_STANDING_TEST_REPORT.md
```

The report harness is read-only unless `--output` is explicitly passed. It does not start the autonomous loop.

## Files Allowed

- `docs/codex/specs/SPEC_self-standing-one-day-test.md`
- `docs/codex/SELF_STANDING_TEST_REPORT.md`
- `tools/selftest/**`

## Files Forbidden

- `core/STATE/identity/**`
- `SERVICES/**`
- secrets or local config
- money tools
- production deploy paths
- vault writes
- Ember-owned handoff lanes

## Definition Of Done

- Spec names pass criteria, stop conditions, owner lanes, and evidence.
- `tools/selftest/report.py` renders a human-readable Markdown report from the observer checks.
- Report tool supports `--json` and explicit `--output`.
- Tool is read-only by default.
- Unit tests cover report rendering and verdict calculation.

## Tests

- `python3 -m unittest tools.selftest.test_check tools.selftest.test_report`
- `python3 -m py_compile tools/selftest/check.py tools/selftest/report.py`
- `python3 tools/selftest/report.py`
- `git diff --check`

## Rollback

Delete `tools/selftest/report.py`, `tools/selftest/test_report.py`, `docs/codex/specs/SPEC_self-standing-one-day-test.md`, and any generated `docs/codex/SELF_STANDING_TEST_REPORT.md`.
