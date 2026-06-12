# Team Intake: Feeding the Zen Village Brain

The Brain has three intake lanes:

1. **Telegram** for daily field capture.
2. **Claude MCP** for reasoning, cleanup, and structured extraction.
3. **AppFlowy** for visual/manual review and source-of-truth cleanup.

## Team Telegram Setup

Each team member needs to message `@zenvillagebot`.

If they are not authorized yet, the bot replies with:

```text
Sorry, you're not authorized yet. Your user_id is <number> — ask Sunheart to add you.
```

Send that numeric ID to the operator. Add it to:

```bash
ssh root@162.0.208.88
nano /etc/zen-village/telegram.env
# append the ID to ZV_TG_ALLOWED_IDS=...
systemctl restart zv-telegram-bot
```

Verify:

```bash
curl -sS http://127.0.0.1:8700/healthz
```

Current allowed users:

- Sunheart
- Atlas

## What Team Members Send

Use Telegram for fast input:

- Text: "Add: call the electrician about pool lights"
- Voice: "Log that campsite 2 is cleared, campsite 3 needs leveling"
- Photo: photo of handwritten notes, schedule, receipt, or whiteboard
- Document: `.md`, `.txt`, `.csv`, `.json`, `.docx`, or Notion Markdown/CSV `.zip`

Bot behavior:

- Text/voice/photos are routed by AI into the Brain.
- Documents are saved as Weekly Log source material with extracted text.
- After a document upload, ask Claude to process it into structured records.

## Meeting Notes Flow

Best path:

1. During/after meeting, send notes to Telegram as text, voice, `.md`, `.txt`, `.docx`, or Notion ZIP.
2. Bot saves the material.
3. Ask Claude:

```text
Process the latest meeting notes/document intake. Extract:
- decisions into Decision Log
- tasks into Master List
- events into Events
- people updates into People or Pending Edits
- property issues into Property
- metrics into Metrics
Use Pending Edits for any changes to existing rows.
```

Why this two-step path:

- Telegram is best at capture.
- Claude is best at structured extraction and cross-checking.
- AppFlowy remains clean because existing row changes go through Pending Edits.

## Atlas Notion Export Flow

Recommended Notion export:

- Export as **Markdown & CSV**
- Include subpages
- Zip the export

Then Atlas can either:

1. Send the ZIP to `@zenvillagebot`.
2. Ask Claude: "Process the latest Notion document intake and extract people, events, decisions, tasks, property issues, and metrics."

For large exports, split by area:

- People / contacts
- Events
- Property
- Operations / tasks
- Meeting notes
- Finance / metrics

This keeps each intake reviewable and avoids one giant noisy import.

## Claude Prompts for Cleanup

After any substantial intake:

```text
Find the latest document intake in Weekly Log. Summarize it first, then propose a clean import plan before writing anything.
```

Then:

```text
Proceed with the import plan. Create new rows where needed. Use Pending Edits for changes to existing rows. Do not duplicate people or events.
```

For meeting notes:

```text
Turn these notes into Zen Village Brain records. Log decisions, create tasks, add events, and propose edits to existing people/property rows.
```

For voice notes:

```text
Review my last captures and tell me what should become tasks, decisions, or weekly log context.
```

## Intake Hygiene

- Do not dump everything into Master List.
- Meeting context and long docs go into Weekly Log first.
- Tasks go into Master List.
- Decisions go into Decision Log.
- People updates go into People only if the person is new; otherwise Pending Edit.
- Existing event/property/person changes go through Pending Edits.
- If the intake is uncertain, save it as Weekly Log source material and let Claude extract later.

## Current Bot Capabilities

Commands:

- `/today`
- `/week`
- `/standup`
- `/digest`
- `/add`
- `/decide`
- `/event`
- `/metric`
- `/note`
- `/find`
- `/edits`
- `/last`
- `/status`
- `/cancel`
- `/help`

Media:

- Voice/audio -> transcription -> routed by AI
- Photo -> OCR -> routed by AI
- Document -> extracted text -> Weekly Log source note

Supported document formats:

- `.md`
- `.txt`
- `.csv`
- `.json`
- `.html`
- `.docx`
- Notion Markdown/CSV `.zip`
- `.pdf` only if `pypdf` is installed; prefer Markdown/TXT export instead

## Next Upgrade

If document intake becomes frequent, build a dedicated `Document Inbox` database or add a `Source Type` field to Weekly Log. For now, Weekly Log is the simplest durable source-material lane.
