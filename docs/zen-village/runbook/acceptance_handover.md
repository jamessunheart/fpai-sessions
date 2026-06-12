# Zen Village Brain Acceptance + Handover

Last verified: 2026-04-24 18:47 UTC

## System Status

The Brain is operational and ready for daily use.

Verified:

- AppFlowy web: `https://brain.zenvillagecr.com`
- AppFlowy workspace: `Zen Village`
- Members: `james.rick.stinson@gmail.com` = Owner, `zenvilops@gmail.com` = Member
- Databases resolved: all 7 (`master_list`, `weekly_log`, `people`, `property`, `decisions`, `events`, `metrics`)
- Hosted MCP service: `zv-mcp-http` active, 12 tools exposed
- Telegram bot service: `zv-telegram-bot` active, 7/7 databases connected
- Telegram command menu: 15 commands registered
- Atlas Claude installer: `https://brain.zenvillagecr.com/install.sh`, 4002 bytes served
- Brain-internal guide: Master List row `[Guide] Start Here: How to use the Zen Village Brain`

## Who Uses What

Sunheart:

- Uses Claude for synthesis, decisions, searches, and structured logging.
- Uses Telegram for fast capture, voice notes, daily check-ins, and quick review.
- Uses AppFlowy when visually browsing or manually executing Pending Edits.

Atlas:

- Uses Telegram for field capture and voice notes.
- Uses Claude Desktop through hosted MCP for reasoning, search, and structured writes.
- Uses AppFlowy web when he needs the visual database.

Claude Desktop:

- Reads/searches all 7 databases.
- Creates new rows in all 7 databases.
- Does not directly update existing rows because AppFlowy's REST API does not expose stable row update/delete for CRDT-backed database rows.
- Uses `zv_propose_change` for edits to existing rows.

Telegram:

- Fast capture and daily rhythm.
- Supports text, voice notes, and photos.
- Important commands: `/today`, `/note`, `/last`, `/edits`, `/standup`, `/digest`, `/status`.

AppFlowy:

- Source of truth.
- Used for visual browsing, cleanup, and executing Pending Edits.

## Daily Operating Loop

Morning:

- Run `/today`.
- Run `/edits` if you own cleanup.
- Ask Claude: "What needs attention in the Brain today?"

During the day:

- Capture quickly with Telegram voice/text/photo.
- Use `/note` for context, `/add` for actionable items.
- Use Claude when a thought needs structure or search.

End of day or week:

- Run `/last`.
- Run `/digest`.
- Check Weekly Log for missing proof, story, or operational context.

## Hygiene Rules

- New item: add it directly through Telegram, Claude, or AppFlowy.
- Existing row change: do not duplicate; create a Pending Edit.
- Pending Edit flow: `/edits` or Pending Edits view -> open target -> make exact AppFlowy edit -> mark edit request Done.
- Keep the Brain focused on proof, revenue, clarity, or operational ease.
- If something is transient chatter and does not affect operations, leave it out.

## Access

Atlas AppFlowy:

- URL: `https://brain.zenvillagecr.com`
- Email: `zenvilops@gmail.com`
- Password is stored on the Secondary host at `/root/zen-village-secrets/atlas-appflowy.env.secrets`.
- Atlas should rotate password after first login.

Atlas Claude:

```bash
ZV_TOKEN=<atlas-token> bash <(curl -sS https://brain.zenvillagecr.com/install.sh)
```

Never paste the real token in public docs or chats. It lives in `/etc/zen-village/mcp-tokens.json`.

## Verification Commands

Run from local machine:

```bash
ssh root@162.0.208.88 'systemctl is-active zv-mcp-http; systemctl is-active zv-telegram-bot'
```

MCP health:

```bash
ssh root@162.0.208.88 'curl -sS http://127.0.0.1:8701/healthz'
```

Telegram health:

```bash
ssh root@162.0.208.88 'curl -sS http://127.0.0.1:8700/healthz'
```

Public installer:

```bash
curl -sS --compressed https://brain.zenvillagecr.com/install.sh | wc -c
```

Expected: `4002`.

## Known Constraints

- AppFlowy free self-hosted build enforces a 1 Member/Owner seat cap through invite and verify endpoints.
- Additional AppFlowy members require the direct provisioning runbook: `docs/zen-village/runbook/add_appflowy_member.md`.
- AppFlowy row updates/deletes are not exposed through the REST API. Use Pending Edits until AppFlowy ships stable update APIs or we build a Yjs/CRDT write client.
- Direct database provisioning can create an empty personal workspace for the new user. Delete it if it appears, leaving only `Zen Village`.

## Next Safe Improvements

1. Morning digest push at 7am Costa Rica time.
2. Better `/edits` ergonomics. Direct "mark Done" still needs a row-update path, so this should start with "open links + assignment guidance" unless/until Yjs write support exists.
3. Telegram conversation memory for short follow-ups.
4. Backup and restore drill for AppFlowy PostgreSQL + MinIO.
