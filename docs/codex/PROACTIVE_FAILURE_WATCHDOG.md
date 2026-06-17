# Proactive Failure Watchdog

`tools/failure_watchdog/watchdog.py` is the d060 report-only process for surfacing single points of failure before James has to ask.

## Contract

- Scans only local repo files and the ops ledger by default.
- Covers server, memory, revenue, agents, and dependencies.
- Writes `core/BUILD/signals/failure_watchdog.json` and `core/BUILD/signals/failure_watchdog.md`.
- Appends one `loop=failure_watchdog` row to the ops ledger unless `--no-ledger` is used.
- Sends a Telegram alert only when run with `--send-alert`, only for severity 4+ findings, and only outside the cooldown window.
- Does not SSH, deploy, restart services, move money, send outreach, read secrets directly, install timers, or mutate production.

## Live Cadence Artifact

Reviewed but not installed from this branch:

- `core/BUILD/cron/fpai-failure-watchdog.service`
- `core/BUILD/cron/fpai-failure-watchdog.timer`

The timer runs every 4 hours with `--send-alert`. The runtime kill switch is:

```text
/opt/fpai-build/.failure_watchdog_disabled
```

## Finding Levels

- Severity 6: P0, immediate review before more autonomous work.
- Severity 4-5: P1, surfaced to James/Ember on cadence.
- Severity 1-3: P2, tracked as fragility debt.

## Current Boundaries

This first watchdog is intentionally deterministic. It catches known concentration patterns: direct host endpoints, missing heartbeat proof, stale smoke-test proof, human-edge revenue dependency, multiple building agents, missing agent dependency maps, dependency sprawl, version conflicts, and unpinned package drift.

Live proof still belongs to Ember or an approved host-lane spec: heartbeat checks, backup restore checks, service endpoint checks, and first timer install.

