# SPEC_voice-to-intent-bridge

*Wire the TG voice/text responder to write build intents into `core/BUILD/intents/` when
James says "build: X". Voice speaks → intent file drops → Rung 4 watcher picks it up.*

## Source / why
The TG responder (`ember_check_in.sh` + `ember_responder_prompt.md`) handles voice and text
but never writes to `core/BUILD/intents/`. Rung 4 (`SPEC_builder-loop-close.md`) watches
that directory. This spec is the bridge: detect `build:` prefix in any TG message (text or
transcribed voice) → write a structured intent file → Rung 4 fires automatically.

## The three declarations
- **Milestone (DoD):** James sends "build: X" (text or voice) to @sunheartbrain_bot →
  `tools/queue/build_intent_router.py capture()` writes `core/BUILD/intents/<id>-<slug>.md`
  with `status: open` → Rung 4 watcher picks it up on the next tick → TG reply confirms
  capture: *"got it — queued `<slug>` for build. —ember"*
- **Dependency:** `tg_listen.py` (captures TG messages + transcribes voice ✅) ·
  `ember_check_in.sh` (responder ✅) · Rung 4 watcher (`SPEC_builder-loop-close.md`).
- **Landing target:** `feat/headless-build`. Never `main` without explicit review.

## Definition of Done

1. **`tools/queue/build_intent_router.py`** — `capture(message: dict) -> Path | None`:
   - Accepts a message dict from `tg_inbox/messages.jsonl` (text or transcribed voice).
   - Returns `None` if message does not start with `build:` (case-insensitive, strip whitespace).
   - Slugifies the intent description: lowercase, spaces→hyphens, max 40 chars.
   - Generates intent ID: `intent-<YYYYMMDD>-<6-char-hex>`.
   - Writes `core/BUILD/intents/<id>-<slug>.md` with frontmatter:
     ```
     ---
     id: <id>
     slug: <slug>
     status: open
     source: telegram
     source_message_id: <message_id>
     created: <UTC ISO timestamp>
     raw: "<original text or transcription>"
     ---

     # <slug>

     <raw intent description, cleaned of "build:" prefix>
     ```
   - Returns the written path.
   - Idempotent: if an intent with the same `source_message_id` already exists, skip and return existing path.

2. **`tools/queue/test_build_intent_router.py`** — tests with no live TG:
   - `"build: a daily digest"` → intent file written, status=open, slug=`a-daily-digest`.
   - `"Build: Resend email wirer"` → case-insensitive match, written correctly.
   - `"hello ember"` → returns None, no file written.
   - Duplicate message_id → returns existing path, no second file written.
   - Voice message (type=voice, text=transcription starting with "build:") → captured same as text.

3. **Wire into `ember_check_in.sh`** (or `daily_sync.py`):
   - After reading new TG messages, call `build_intent_router.capture(msg)` for each.
   - If capture returns a path (= build intent detected): send TG confirmation *"got it — queued `<slug>` for build. —ember"* and skip the normal responder for that message.
   - If capture returns None: normal responder flow continues unchanged.

4. **Update `ember_responder_prompt.md`** — remove the ad-hoc `"build me a thing"` handler.
   Replace with: *"build: intents are now captured automatically by `build_intent_router.py`.
   Confirm capture via TG and let Rung 4 handle the rest."*

## Files
- **Files ALLOWED:**
  - `tools/queue/build_intent_router.py` (new)
  - `tools/queue/test_build_intent_router.py` (new)
  - `tools/decisions/ember_check_in.sh` (add capture call + confirmation send)
  - `tools/decisions/ember_responder_prompt.md` (update build handler section only)
  - `core/BUILD/intents/.gitkeep` (ensure dir exists)
- **Files FORBIDDEN:** `tg_listen.py` · `daily_sync.py` · any live service · secrets · money.

## Safety
- 🔴 No auto-build. Capture only — Rung 4 watcher is the build trigger, not this spec.
- 🔴 Idempotent. Duplicate message_id never writes a second intent.
- 🔵 Kill-switch: `FPAI_BUILD_LOOP_DISABLE=1` skips capture call entirely.
- 🔵 Non-build messages are completely unaffected — normal responder flow unchanged.
- Rollback: `git revert <this-commit>` removes router; intent files already written are harmless.

## Tests
- `python3 -m pytest tools/queue/test_build_intent_router.py -v`
- Send "build: test intent" to @sunheartbrain_bot → confirm file appears in `core/BUILD/intents/`
- Send "hello" → confirm no file written, normal responder replies

## Rollback
- `git revert <this-commit>` removes router + responder wire.
- Existing intent files in `core/BUILD/intents/` are unaffected.

## Close-out
Update `docs/codex/HANDOFF.md`:
- Files changed · tests passing · live capture verified
- Intent solved: voice/text `build:` → intent file → Rung 4 fires
- Proof: one `build:` message captured, intent file committed, TG confirmation sent
