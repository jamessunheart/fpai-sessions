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

Tests:

```bash
python3 -m unittest tools.selftest.test_check
```

## What It Checks

- Router dry-run works.
- Router escalates reserved money/public work and writes nothing.
- Closeout tool exists and is configured for the core surfaces.
- Latest proof row carries Buildstream-Law fields.
- HOME and Intent Buildstream agree on the self-standing test.
- Cost guard is visible.
- Phone/cloud Codex has repo-visible docs.
- Git state is clean enough to know what is committed vs local-only.

Warnings are useful during the test. Fails mean the loop should not be called
self-standing yet.
