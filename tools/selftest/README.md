# Selftest Observer

`tools/selftest/check.py` is a read-only instrument panel for the self-standing
one-day test.

It does not start timers, mutate vault pages, send messages, deploy, move money,
or touch services. It only reports pass/warn/fail evidence.

## Run

```bash
python3 tools/selftest/check.py
```

JSON:

```bash
python3 tools/selftest/check.py --json
```

Render the Markdown proof report:

```bash
python3 tools/selftest/report.py
```

Write the repo-local report explicitly:

```bash
python3 tools/selftest/report.py --output docs/codex/SELF_STANDING_TEST_REPORT.md
```

Tests:

```bash
python3 -m unittest tools.selftest.test_check tools.selftest.test_report
```

## What It Checks

- Router dry-run works.
- Router escalates reserved money/public work and writes nothing.
- Closeout tool exists and is configured for the core surfaces.
- Latest proof row carries Buildstream-Law fields.
- HOME and Intent Buildstream agree on the self-standing test.
- Cost guard is visible.
- Safety Seal holds: unattended loops expose a cost guard, pause/disable switches,
  run log, closeout step, and report-only router posture.
- Phone/cloud Codex has repo-visible docs.
- Git state is clean enough to know what is committed vs local-only.

Warnings are useful during the test. Fails mean the loop should not be called
self-standing yet.
