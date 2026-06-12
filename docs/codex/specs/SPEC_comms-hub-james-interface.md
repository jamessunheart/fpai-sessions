# SPEC: Comms Hub - James Interface

**Status:** Draft, Codex-ready  
**Created:** 2026-06-12  
**Owner:** James / Full Potential AI  
**Implementation Class:** Internal coordination service  
**Risk Level:** Restricted, because Telegram, voice, and personal routing can expose private messages

---

## 1. Purpose

Build the James-facing communication interface for the system: one reliable message path between James, the system, and builder agents.

The first release revives the stale Telegram cron path safely, creates one routed outbox that all hubs publish through, and establishes a surface ladder:

1. Terminal
2. Obsidian
3. Telegram text
4. Telegram voice, both directions, with system and builder routing

This is not a new autonomous brain. It is a controlled communications spine with durable queues, dry-run defaults, visible health, and kill switches.

---

## 2. Current Problem

The existing system has scattered coordination surfaces:

- Terminal/session messages are immediate but ephemeral.
- Obsidian-style notes are durable but not guaranteed to reach James.
- Telegram paths appear stale or absent from this worktree.
- Multiple hubs can produce messages, but there is no single routed outbox with dedupe, audit, and delivery status.
- The Telegram inbox cron is described as 16 days stale and must be revived without blindly installing or mutating host crontab.

---

## 3. Scope

### In Scope

- Create `SERVICES/comms-hub/` as the dedicated communication service.
- Create a single append-only routed outbox all hubs can publish to.
- Create a single append-only routed inbox for James-originated messages.
- Add adapters for terminal, Obsidian, Telegram text, and Telegram voice.
- Add dry-run cron revival scripts and diagnostics for stale inbox polling.
- Add FastAPI health/state/capabilities endpoints.
- Add a CLI for local send, receive, drain, and health checks.
- Add tests for routing, dedupe, kill switches, and dry-run delivery.
- Document exact activation, rollback, and manual verification steps.

### Out of Scope

- No production cron install without explicit human approval.
- No real Telegram send/receive in tests.
- No committing secrets, bot tokens, chat IDs, voice transcripts, or private messages.
- No broad rewrite of `SERVICES/hub`, `SERVICES/coordination-hub`, or existing historical orchestration scripts.
- No automatic deploy, DNS, systemd, launchd, or crontab mutation in v1.
- No LLM autonomous decision-making beyond routing and summarization fields provided by callers.

---

## 4. Allowed Files

Codex may create or edit only these paths for this implementation:

- `docs/codex/specs/SPEC_comms-hub-james-interface.md`
- `SERVICES/comms-hub/README.md`
- `SERVICES/comms-hub/SPEC.md`
- `SERVICES/comms-hub/requirements.txt`
- `SERVICES/comms-hub/app/__init__.py`
- `SERVICES/comms-hub/app/main.py`
- `SERVICES/comms-hub/app/config.py`
- `SERVICES/comms-hub/app/models.py`
- `SERVICES/comms-hub/app/store.py`
- `SERVICES/comms-hub/app/router.py`
- `SERVICES/comms-hub/app/dedupe.py`
- `SERVICES/comms-hub/app/security.py`
- `SERVICES/comms-hub/app/adapters/__init__.py`
- `SERVICES/comms-hub/app/adapters/terminal.py`
- `SERVICES/comms-hub/app/adapters/obsidian.py`
- `SERVICES/comms-hub/app/adapters/telegram.py`
- `SERVICES/comms-hub/app/adapters/voice.py`
- `SERVICES/comms-hub/scripts/comms-hub`
- `SERVICES/comms-hub/scripts/comms-hub-cron-tick.sh`
- `SERVICES/comms-hub/scripts/diagnose-telegram-cron.sh`
- `SERVICES/comms-hub/scripts/install-cron.example.sh`
- `SERVICES/comms-hub/tests/__init__.py`
- `SERVICES/comms-hub/tests/conftest.py`
- `SERVICES/comms-hub/tests/test_routes.py`
- `SERVICES/comms-hub/tests/test_store.py`
- `SERVICES/comms-hub/tests/test_kill_switches.py`
- `SERVICES/comms-hub/tests/test_telegram_adapter.py`
- `SERVICES/comms-hub/tests/test_voice_adapter.py`
- `SERVICES/comms-hub/tests/test_cli.py`
- `SERVICES/comms-hub/.env.example`
- `SERVICES/comms-hub/.gitignore`

Runtime files must be generated under `SERVICES/comms-hub/var/` and ignored by git:

- `SERVICES/comms-hub/var/inbox.jsonl`
- `SERVICES/comms-hub/var/outbox.jsonl`
- `SERVICES/comms-hub/var/delivery_log.jsonl`
- `SERVICES/comms-hub/var/state.json`
- `SERVICES/comms-hub/var/locks/`
- `SERVICES/comms-hub/var/tmp/`

---

## 5. Forbidden Files And Actions

Codex must not edit:

- `.env`, `.envrc`, `.zshrc`, `.bashrc`, shell profile files, or real secret stores
- User crontab, system crontab, launchd plists, or systemd units
- `SERVICES/hub/**`, except documentation links if James explicitly asks
- `SERVICES/coordination-hub/**`, except documentation links if James explicitly asks
- `core/STATE/INBOX.json`, unless a later spec explicitly blesses migration
- Any file outside `SERVICES/comms-hub/**` and this spec, unless James explicitly expands scope

Codex must not run:

- `crontab`, `sudo`, `launchctl`, `systemctl`, or production deploy commands
- Real Telegram API sends unless James explicitly provides dry-run override and confirms the target chat
- Any command that prints secret values to logs

---

## 6. Architecture

### 6.1 Components

- `app/main.py`: FastAPI service, UDC-compatible status endpoints, message intake endpoints.
- `app/models.py`: Pydantic models for messages, routes, delivery attempts, health, and adapter state.
- `app/store.py`: JSONL append-only inbox, outbox, delivery log, and lock handling.
- `app/router.py`: Routing rules from source and audience to delivery surfaces.
- `app/dedupe.py`: Message fingerprinting and TTL-based duplicate suppression.
- `app/security.py`: Redaction, allowlist checks, and secret-safe logging.
- `app/adapters/terminal.py`: Writes readable terminal output and supports CLI reads.
- `app/adapters/obsidian.py`: Writes Markdown notes into configured vault path when enabled.
- `app/adapters/telegram.py`: Polls Telegram updates and sends messages when enabled.
- `app/adapters/voice.py`: Stores voice attachment metadata in v1; transcription/synthesis is adapter-gated.
- `scripts/comms-hub`: Local CLI.
- `scripts/comms-hub-cron-tick.sh`: Safe periodic tick target for cron/launchd.
- `scripts/diagnose-telegram-cron.sh`: Read-only diagnostic for stale Telegram polling.
- `scripts/install-cron.example.sh`: Prints an install command; does not install by default.

### 6.2 Message Model

```json
{
  "id": "msg_20260612_000001",
  "created_at": "2026-06-12T12:00:00-06:00",
  "source": "terminal|obsidian|telegram|system|builder",
  "audience": "james|system|builder|all",
  "priority": "low|normal|high|urgent",
  "topic": "coordination",
  "body": "message text",
  "attachments": [],
  "route": ["terminal"],
  "status": "queued|delivered|failed|blocked|dry_run",
  "dedupe_key": "sha256:...",
  "metadata": {
    "builder_id": null,
    "reply_to": null,
    "telegram_update_id": null,
    "voice_file_id": null
  }
}
```

### 6.3 Routed Outbox Contract

All hubs publish through one function or endpoint:

```http
POST /outbox/publish
```

Request:

```json
{
  "source": "system",
  "audience": "james",
  "priority": "normal",
  "topic": "daily-pulse",
  "body": "Short update",
  "route": ["terminal", "obsidian"],
  "metadata": {}
}
```

Behavior:

- Validate source, audience, priority, and route.
- Redact secrets before persistence.
- Compute `dedupe_key`.
- Append to `var/outbox.jsonl`.
- Return delivery plan without sending unless `COMMS_HUB_OUTBOX_DRAIN_ENABLED=1`.

---

## 7. Surface Ladder

### 7.1 Terminal

Default enabled. This is the first verified surface.

- CLI: `SERVICES/comms-hub/scripts/comms-hub send --to james --body "..."`
- CLI: `SERVICES/comms-hub/scripts/comms-hub inbox --limit 20`
- CLI: `SERVICES/comms-hub/scripts/comms-hub drain --dry-run`

### 7.2 Obsidian

Second surface. Enabled only when `COMMS_HUB_OBSIDIAN_ENABLED=1` and `COMMS_HUB_OBSIDIAN_VAULT` points to an existing directory.

Default write target:

- `${COMMS_HUB_OBSIDIAN_VAULT}/FPAI/Comms Hub/YYYY-MM-DD.md`

### 7.3 Telegram Text

Third surface. Enabled only when:

- `COMMS_HUB_TG_ENABLED=1`
- `TELEGRAM_BOT_TOKEN` is present
- `COMMS_HUB_TG_ALLOWED_CHAT_IDS` includes the inbound/outbound chat ID
- `COMMS_HUB_DRY_RUN=0`

The adapter must support:

- `poll_updates` for James-to-system and James-to-builder messages
- `send_message` for system/builder-to-James messages
- update ID checkpointing in `var/state.json`
- stale inbox detection

### 7.4 Telegram Voice Both Ways

Fourth surface. Enabled only when:

- `COMMS_HUB_VOICE_ENABLED=1`
- Telegram text requirements are met
- voice transcription/synthesis provider env vars are present if transcription or reply audio is enabled

V1 requirements:

- Accept inbound Telegram voice metadata.
- Store voice file IDs and durations in inbox.
- Route to system or builder based on command prefix or default route.
- Outbound voice replies default to text unless `COMMS_HUB_VOICE_REPLY_ENABLED=1`.

---

## 8. Routing Rules

Default routes:

- `system -> james`: terminal, Obsidian; Telegram only when explicitly enabled.
- `builder -> james`: terminal, Obsidian; Telegram only for high/urgent priority or explicit route.
- `james -> system`: inbox and terminal acknowledgement.
- `james -> builder`: inbox, terminal acknowledgement, and builder channel metadata.
- `all`: blocked unless `COMMS_HUB_BROADCAST_ENABLED=1`.

Telegram command prefixes:

- `/system ...`: route James message to system.
- `/builder ...`: route James message to default builder.
- `/builder <id> ...`: route James message to named builder.
- `/status`: return comms hub health summary.
- `/pause`: set `COMMS_HUB_RUNTIME_PAUSED=1` in runtime state, not environment.
- `/resume`: clear runtime pause if sender is allowlisted.

---

## 9. Telegram Cron Revival

The stale Telegram inbox cron must be revived in phases:

### Phase A: Diagnose Only

Run:

```bash
SERVICES/comms-hub/scripts/diagnose-telegram-cron.sh
```

It must report:

- whether a comms hub tick command exists
- last inbox update timestamp
- last Telegram update ID
- whether required env vars are present, without printing values
- whether `COMMS_HUB_TG_ENABLED` is set
- whether the inbox is stale beyond `COMMS_HUB_STALE_AFTER_SECONDS`

### Phase B: Manual Tick

Run:

```bash
COMMS_HUB_DRY_RUN=1 SERVICES/comms-hub/scripts/comms-hub-cron-tick.sh
```

Expected result:

- no real Telegram send
- state file updated
- delivery log records dry-run actions

### Phase C: Cron Proposal

Run:

```bash
SERVICES/comms-hub/scripts/install-cron.example.sh
```

It must print the exact crontab line and stop. It must not install it.

### Phase D: Human Install

James installs or approves the cron outside this spec only after Phase A-C pass.

---

## 10. Kill Switches

All kill switches must be checked at runtime before polling, routing, sending, writing to Obsidian, or processing voice.

- `COMMS_HUB_ENABLED=0`: disable the service except `/health`.
- `COMMS_HUB_DRY_RUN=1`: persist and plan deliveries, but do not send external messages.
- `COMMS_HUB_RUNTIME_PAUSED=1`: pause drains and polling from runtime state.
- `COMMS_HUB_OUTBOX_DRAIN_ENABLED=0`: disable outbox delivery.
- `COMMS_HUB_TG_ENABLED=0`: disable Telegram adapter.
- `COMMS_HUB_TG_POLL_ENABLED=0`: disable Telegram polling only.
- `COMMS_HUB_TG_LIVE_POLL_CONFIRM=0`: prevent live Telegram `getUpdates` calls even when polling is otherwise configured.
- `COMMS_HUB_TG_SEND_ENABLED=0`: disable Telegram sends only.
- `COMMS_HUB_OBSIDIAN_ENABLED=0`: disable Obsidian writes.
- `COMMS_HUB_VOICE_ENABLED=0`: disable all voice handling.
- `COMMS_HUB_VOICE_REPLY_ENABLED=0`: disable outbound voice replies.
- `COMMS_HUB_BUILDER_BRIDGE_ENABLED=0`: prevent James messages from being routed to builder agents.
- `COMMS_HUB_BROADCAST_ENABLED=0`: block fanout to `all`.

Default `.env.example` values must be safe:

```bash
COMMS_HUB_ENABLED=1
COMMS_HUB_DRY_RUN=1
COMMS_HUB_OUTBOX_DRAIN_ENABLED=0
COMMS_HUB_TG_ENABLED=0
COMMS_HUB_TG_LIVE_POLL_CONFIRM=0
COMMS_HUB_OBSIDIAN_ENABLED=0
COMMS_HUB_VOICE_ENABLED=0
COMMS_HUB_BUILDER_BRIDGE_ENABLED=0
COMMS_HUB_BROADCAST_ENABLED=0
```

---

## 11. API

### Health

```http
GET /health
```

Response:

```json
{
  "status": "healthy",
  "service": "comms-hub",
  "version": "0.1.0",
  "dry_run": true,
  "runtime_paused": false
}
```

### Capabilities

```http
GET /capabilities
```

Must include enabled/disabled adapter status.

### State

```http
GET /state
```

Must include queue lengths, last inbox timestamp, last outbox drain timestamp, last Telegram update ID, and stale status.

### Publish Outbox

```http
POST /outbox/publish
```

Queues a message through the routed outbox.

### Drain Outbox

```http
POST /outbox/drain
```

Drains pending deliveries only when kill switches allow it.

### Poll Inbox

```http
POST /inbox/poll
```

Polls enabled inbound adapters only when kill switches allow it.

### Receive Inbox

```http
POST /inbox/receive
```

Appends a local James-originated message into the inbox. This is the terminal-first path for testing James-to-system and James-to-builder flows without Telegram.

### Dispatch Inbox

```http
POST /inbox/dispatch
```

Dispatches undispatched James-originated inbox messages to the addressed system or builder target. V0.1 records dispatch attempts in `var/delivery_log.jsonl` and marks dispatched inbox IDs in `var/state.json`; it does not rewrite inbox records or call external builder APIs.

### Heartbeat Tick

```http
POST /tick
```

Runs exactly one heartbeat: poll enabled inbound adapters, dispatch undispatched inbox records, then drain the routed outbox. This is the command cron/launchd should call after dry-run verification.

---

## 12. Tests

Run from `SERVICES/comms-hub/`:

```bash
python -m pytest
```

Required tests:

- `tests/test_store.py`
  - appends valid JSONL records
  - rejects malformed messages
  - preserves append-only behavior
  - lock prevents concurrent drain corruption
- `tests/test_routes.py`
  - system-to-James route defaults to terminal and Obsidian plan
  - builder-to-James urgent route can include Telegram when enabled
  - James-to-builder is blocked when `COMMS_HUB_BUILDER_BRIDGE_ENABLED=0`
  - broadcast is blocked when `COMMS_HUB_BROADCAST_ENABLED=0`
- `tests/test_kill_switches.py`
  - global disabled blocks poll and drain
  - dry-run prevents external sends
  - Telegram send and poll switches are independent
  - runtime pause blocks drain without changing environment
- `tests/test_telegram_adapter.py`
  - no token means disabled state, not crash
  - allowlist rejects unknown chat ID
  - update checkpoint prevents duplicate inbox messages
  - adapter never logs token value
- `tests/test_voice_adapter.py`
  - inbound voice metadata persists without downloading in dry-run
  - outbound voice reply is text fallback unless explicitly enabled
- `tests/test_cli.py`
  - `send`, `inbox`, `drain --dry-run`, and `health` commands work

Tests must not require network access.

---

## 13. Manual Verification

### Step 1: Local Queue

```bash
cd SERVICES/comms-hub
python -m pytest
COMMS_HUB_DRY_RUN=1 scripts/comms-hub send --to james --body "Comms hub smoke test"
COMMS_HUB_DRY_RUN=1 scripts/comms-hub drain --dry-run
scripts/comms-hub health
```

Pass criteria:

- pytest passes
- outbox entry created
- delivery log shows dry-run terminal delivery
- no external send attempted

### Step 2: Obsidian Dry Run

```bash
COMMS_HUB_OBSIDIAN_ENABLED=1 COMMS_HUB_DRY_RUN=1 scripts/comms-hub drain --dry-run
```

Pass criteria:

- delivery plan names target Markdown file
- no write occurs unless `COMMS_HUB_DRY_RUN=0`

### Step 3: Telegram Diagnostics

```bash
scripts/diagnose-telegram-cron.sh
```

Pass criteria:

- secrets are reported as present/missing only
- stale status is clear
- suggested tick command is printed

### Step 4: Telegram Dry Poll

```bash
COMMS_HUB_TG_ENABLED=1 COMMS_HUB_TG_POLL_ENABLED=1 COMMS_HUB_TG_LIVE_POLL_CONFIRM=1 COMMS_HUB_DRY_RUN=1 scripts/comms-hub poll
```

Pass criteria:

- no outbound messages
- update checkpoint behavior is visible
- unknown chat IDs are blocked

---

## 14. Rollback

Rollback must be file-local and reversible:

1. Stop any local dev server running `SERVICES/comms-hub/app/main.py`.
2. Set these runtime/env values:
   - `COMMS_HUB_ENABLED=0`
   - `COMMS_HUB_OUTBOX_DRAIN_ENABLED=0`
   - `COMMS_HUB_TG_ENABLED=0`
   - `COMMS_HUB_VOICE_ENABLED=0`
3. If a human installed cron, remove only the line containing `SERVICES/comms-hub/scripts/comms-hub-cron-tick.sh`.
4. Preserve `SERVICES/comms-hub/var/*.jsonl` for audit unless James explicitly asks to purge runtime data.
5. Revert code by deleting `SERVICES/comms-hub/` and this spec if the implementation must be fully abandoned.

No rollback step may delete unrelated hub state, existing coordination hub databases, or `core/STATE/INBOX.json`.

---

## 15. Acceptance Criteria

- Spec exists at `docs/codex/specs/SPEC_comms-hub-james-interface.md`.
- Implementation stays inside the allowed file list.
- `python -m pytest` passes under `SERVICES/comms-hub/`.
- Default mode is dry-run and cannot send Telegram messages.
- A single outbox receives messages from system and builder sources.
- Terminal route works first.
- Obsidian route is planned and gated by env.
- Telegram route is planned, allowlisted, and gated by env.
- Voice route accepts metadata and defaults to text fallback.
- Diagnostics can identify a stale Telegram inbox without mutating crontab.
- Kill switches are tested and documented.
- Rollback is documented and does not touch unrelated services.

---

## 16. First Build Order

1. Implement models, config, store, and tests.
2. Implement terminal adapter and CLI.
3. Implement router and kill-switch enforcement.
4. Implement Obsidian adapter in dry-run-safe mode.
5. Implement Telegram adapter with mocked tests and no network-required CI.
6. Implement voice metadata handling.
7. Add diagnostics and cron example scripts.
8. Run tests and manual dry-run smoke checks.
