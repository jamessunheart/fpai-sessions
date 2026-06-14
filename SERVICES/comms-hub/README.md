# Comms Hub - James Interface

Restricted internal communications spine for James, system agents, and builder agents.

Default behavior is safe:

- local queues only
- dry-run enabled
- Telegram disabled
- voice disabled
- builder bridge disabled
- broadcast disabled

## Quick Start

```bash
cd SERVICES/comms-hub
python3 -m pytest
COMMS_HUB_DRY_RUN=1 scripts/comms-hub send --to james --body "Comms hub smoke test"
COMMS_HUB_DRY_RUN=1 scripts/comms-hub drain --dry-run
scripts/comms-hub health
```

Inbound James messages can be dispatched locally without mutating the inbox:

```bash
COMMS_HUB_DRY_RUN=1 scripts/comms-hub receive --to system --body "/system status"
COMMS_HUB_DRY_RUN=1 scripts/comms-hub dispatch
```

Use one heartbeat for automation:

```bash
COMMS_HUB_DRY_RUN=1 scripts/comms-hub tick
```

Check Telegram safety before enabling live polling:

```bash
scripts/comms-hub tg-status
```

Real `getUpdates` calls require `COMMS_HUB_TG_LIVE_POLL_CONFIRM=1` in addition to the token and poll flags.

## Runtime Files

Runtime state lives in `var/` and is ignored by git:

- `var/inbox.jsonl`
- `var/outbox.jsonl`
- `var/delivery_log.jsonl`
- `var/state.json`

## Cron Revival

Diagnostics are read-only:

```bash
scripts/diagnose-telegram-cron.sh
```

The cron installer is intentionally non-mutating:

```bash
scripts/install-cron.example.sh
```
