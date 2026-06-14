# Session Handoff — Ember (Main Claude Code Session)
**Date:** 2026-06-12
**Session ID:** 0b0ca1df
**Branch:** feat/headless-build

---

## What this session built / changed

### Infrastructure
- **Obsidian vault migrated** from iCloud (`~/Library/Mobile Documents/iCloud~md~obsidian/FPOS/`) to local git (`~/Documents/FPOS/`) — iCloud TCC wall gone permanently
- **4 config files updated** to new vault path: `plate/prompt.md`, `eod/eod-nightly.sh`, `eod/prompt.md`, `scout/prompt.md`
- **TG voice loop revived** — `com.fpai.tg-listen` + `com.fpai.ember-responder` LaunchAgents running; Whisper transcription live; loop confirmed working (James got a reply)
- **Footer hooks disabled** — NOW/NARRATOR removed from visible output per James; NEXT+WHY only

### Specs written (Codex-ready)
- `docs/codex/specs/SPEC_voice-to-intent-bridge.md` — TG `build:` → intent file → Rung 4
- `docs/codex/specs/SPEC_build-registry-and-merge-gate.md` — system-wide build routing (THE PRIORITY)

### Treasury
- `SERVICES/unified-financial-dashboard/manual_financial_inputs.json` — seeded with live numbers: $112.9k liquid, $18.1k/mo burn, 6.2mo runway

### State fixes
- `NOW.md` refreshed — 32-day drift closed, FPOS North Star headlines (commit `b77b7e5a`)
- `INTENT_BUILDSTREAM.md` — Rungs 0-3 corrected to `done`, Rung 4 `ready`
- `HUMAN_EDGE_QUEUE.json` — inter-session sync note written

### PRs merged today
| PR | What | Tests |
|---|---|---|
| #2 | Comms hub (TG+Obsidian+voice+terminal adapters) | 30 passed |
| #3 | Recruiting hub (admin gate, launch packet, evidence map, review inbox) | 6 passed |
| #4 | Financial hub rung 4 (read-only dashboard) | 13 passed |
| #5 | Recruiting hub readiness tests | passed |
| #6 | Lantern / world scout activation | 22 passed |

---

## Open issues / what the integration session should address

### 🔴 CRITICAL — Build architecture broken
Multiple Codex sessions pushed to `feat/headless-build` without coordination. One session tried to open a PR to `main` with +619k lines. The fix is already specced:
→ **Build `SPEC_build-registry-and-merge-gate.md` FIRST before any more Codex sessions run.**

### 🟡 Dirty files — need commit or decision
```
M  SERVICES/jobs/QUICK_START.md
M  SERVICES/jobs/app/routers/recruiting_hub.py
M  SERVICES/jobs/app/services/recruiting_hub.py
D  SERVICES/jobs/tests/test_recruiting_hub.py
D  core/BUILD/specs/.gitkeep
M  docs/codex/HANDOFF.md
```
These are from Codex sessions that staged but didn't cleanly commit. Integration session should review and commit or discard.

### 🟡 PR #1 still open
`feat/financial-hub` (June 6) — self-standing surfaces: weighted index, self-model, reflections wall, closeout reconciler. Has real value. Integration session should decide: merge or close.

### 🟡 TG bot conflict resolved but fragile
`@sunheartbrain_bot` — server bot on 162 (`sh-brain-tgbot`) is now the sole responder. Local `tg-listen` + `ember-responder` are hard-disabled. If either gets re-enabled, 409 conflict returns. Memory note: `reference_sunheartbrain_bot_simplified.md`.

### 🟡 Resend API key still missing
Intake-agent on 162 is healthy but auto-email to leads won't fire until `RESEND_API_KEY` is set in `/opt/fpai/cora-loop/.env`. One key from James closes this.

### 🟡 Watchfire deploy still unrun
`tools/build_loop/deploy_reconciler.sh` is written and Reserved-Class. James must run it to protect open positions.

---

## Suggestions for integration session

1. **Build the merge gate first** (`SPEC_build-registry-and-merge-gate.md`) — stops all future collision
2. **Decide on PR #1** — merge or close
3. **Clean the dirty files** — review and commit the staged changes above
4. **Answer: TG vs Claude Code as interface** — shapes Rung 4 build (voice-to-intent-bridge)
5. **Resend key + Watchfire** — 2-min and 5-min tasks that unblock revenue and position protection

---

## What NOT to rebuild
- Obsidian vault migration — done, iCloud copy deleted
- TG voice loop — live and working (don't re-enable local pollers)
- Treasury numbers in financial hub — seeded and committed
- All 5 PRs merged today — don't touch those service directories

---

## Key file locations
- Treasury SSOT: `~/.config/fpai/treasury/CURRENT.md`
- Build specs queue: `docs/codex/specs/`
- Intent queue: `core/BUILD/intents/`
- Bot credentials: `~/.config/fpai/tg_brain/creds.cache`
- Vault: `~/Documents/FPOS/Full Potential OS/`
