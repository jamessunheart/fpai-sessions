# SPEC_comms-hub-james-interface

*Rung 4 · comms hub, James-facing half. How James interfaces with the AI system:
revive the dead ambient stack, unify all hub output into one routed outbox, and climb
the surface ladder terminal → Obsidian → Telegram voice (both ways, with the SYSTEM and
the BUILDER). Companion to `SPEC_comms-hub-rung4.md`, which covers the outward half
(inbound triage · outreach drafts · gated sends) — build that scope there, not here.
Owner: Codex (build) · Ember (review).*

## Source / why

James, 2026-06-12: *"Spec the comms hub which would include how I interface with the AI
system."* His stated surface ladder (memory `project-surface-migration-terminal-to-telegram-voice`):
lives in terminal NOW → prefers Obsidian → ultimately Telegram voice both ways with TWO
counterparts — **the system** (Ember: status, decisions, digests) and **the builder**
(`build:` voice intent → spec → Codex → review → voice report back).

The infrastructure mostly EXISTS but is OFFLINE: `com.fpai.tg-listen` and
`com.fpai.ember-responder` LaunchAgents dead, TG inbox 16+ days stale, autoloop stopped.
**Revive, don't rebuild.** The one genuinely new build: a router that makes comms a *hub* —
one outbox every other hub (financial · recruiting · builder · watchfire) publishes through,
so James hears the whole system in one channel instead of N scripts pinging him.

Buildstream intent: `rung4-hubs`.

## The three declarations

- **Milestone (DoD):** `python3 tools/comms/comms_hub.py --status` shows: TG inbox lag
  <10 min · responder alive · outbox queue with per-message status · last digest UTC.
  Any tool publishes by writing one JSON file to `core/COMMS/outbox/`; the hub routes it
  by priority (red → TG now · yellow → hourly batch · blue/green → daily digest).
  End-to-end proof: James sends a TG **voice note** → Whisper transcribes → routed
  (`build:` → builder lane · question → Ember inbox) → reply comes back as **voice** in
  Ember's register.
- **Dependency:** existing TG stack (`tools/decisions/send_tg_digest.py` ✅ ·
  `tools/decisions/tts_preprocess.py` ✅ · Whisper transcription ✅ · tg_inbox poller
  ✅-but-dead) · builder lane (`build_intent_router.py` + `build_loop_watcher.py` ✅) ·
  Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main` without explicit review.

## Definition of Done

1. **Revival pass first (fix before build).** Diagnose why tg-listen + ember-responder
   LaunchAgents died; restart; root cause written to `core/COMMS/REVIVAL_NOTES.md`.
   Inbox lag <10 min sustained. If root cause is the iCloud TCC wall, repath state to
   repo-local (`core/COMMS/state/`) — do NOT block on an FDA grant.

2. **`tools/comms/comms_hub.py`** — the router:
   - `enqueue(msg: dict) -> str` — writes `core/COMMS/outbox/<utc>-<slug>.json`:
     `{to: "james", via: "tg-text|tg-voice|obsidian|file", priority: "red|yellow|blue|green",
     body, source_hub, reply_expected}`.
   - `flush()` — routes by priority class; marks `status: sent|failed`; failed retries
     max 3× then parks. Voice out = Nova TTS via `tts_preprocess.py`, register per
     `feedback-tg-voice-must-be-embers` (warm · lowercase · signed —ember).
   - `status()` — the one-command health pane.

3. **Inbound routing** — extend the revived poller handler:
   - `build: …` (text or transcribed voice) → `core/BUILD/intents/` (existing lane — wire, don't duplicate).
   - `merge <id>` / `reject <id>` → builder-loop review flow.
   - everything else → `core/COMMS/inbox_for_ember/` (next Ember session reads on start).

4. **Obsidian rung** — `tools/comms/obsidian_bridge.py`:
   - Renders `core/COMMS/SURFACE.md` (NOW · NEED · pending decisions · today's outbox
     digest), git-tracked = SSOT. Mirrors to the FPOS vault only if writable without a
     TCC prompt; else logs `vault-blocked` in status and continues — never hangs a cron.
   - Reads `<vault>/INBOX/*.md` if readable → routes through inbound routing (3).

5. **One digest, not N pings** — `send_tg_digest.py` pulls its body from the day's
   blue/green outbox items + the status line, so every hub feeds one daily digest.

6. **Tests** — `tools/comms/test_comms_hub.py`, fixture-based (no live sends, no
   launchctl): priority routing · retry+park · inbound `build:`/`merge`/question routing ·
   vault-blocked fallback · idempotent flush.

## Files

- **Files ALLOWED:** `tools/comms/comms_hub.py` · `tools/comms/obsidian_bridge.py` ·
  `tools/comms/test_comms_hub.py` (new) · `core/COMMS/` scaffold (outbox/ ·
  inbox_for_ember/ · state/ · SURFACE.md · REVIVAL_NOTES.md) ·
  `tools/decisions/send_tg_digest.py` (digest-source change only) · the existing tg_inbox
  poller handler (routing extension only) · the two LaunchAgent plists (revival fixes only).
- **Files FORBIDDEN:** `core/BUILD/intents/` writes except via existing router · bot
  tokens / `~/.config/fpai/**` secrets (read-only) · identity stack · NOW.md / AI_GOALS.md ·
  live service code · `SPEC_comms-hub-rung4.md` scope (triage/outreach) · unrelated refactors.

## Safety

- 🔴 **Outbound to James only.** Hard-fail any outbox item with `to != "james"`. Q-AI-1
  (AI outbound to other humans) stays open — answered by `SPEC_comms-hub-rung4.md`'s
  Reserved-Class gates, not here.
- 🔴 **No new bots · no token rotation · no credential writes.**
- 🟡 iCloud TCC wall: Obsidian mirror degrades gracefully; FDA grant is James's separate
  decision, never assumed.
- 🔵 Kill-switch: `FPAI_COMMS_HUB_DISABLE=1` → enqueue still writes, flush is a no-op.
- 🔵 Red-priority sends rate-limited (max 6/hour) — presence, not spam.
- Rollback: `git revert <commit>`; outbox/inbox files are inert data.

## Tests

- `python3 -m pytest tools/comms/test_comms_hub.py -v`
- `python3 tools/comms/comms_hub.py --status` renders the health pane.
- End-to-end voice proof (voice in → routed → voice out) logged in `core/BUILD/PROOF_LOG.md`.

## Rollback

- `git revert <this-commit>` · `launchctl unload` revived agents (returns to current dead
  state) · delete `core/COMMS/` (inert data).

## Close-out

Update `docs/codex/HANDOFF.md`: revival root cause · files changed · tests green · voice
proof. Downstream intent unlocked: financial + recruiting hubs publish through
`core/COMMS/outbox/` from day one; James's TG voice channel reaches both the system and
the builder.
