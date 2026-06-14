# SPEC · Comms Hub (Conscious Chat)

- **From intent:** Comms Hub (completeness-gate pillar · [[INTENT RADAR]])
- **Owner / route:** Codex builds → Ember/James review
- **Est cost:** 🟡
- **Gate:** ❓ needs Y/N — **🟡 SCOPE CLARIFICATION first** (see open questions)
- **Branch:** `feat/comms-hub`
- **Why now:** consolidate the messages that need James into one view, so comms stop scattering. The "respond to X" load (today: Gian · Elyahou) should land in one place with a suggested reply.

## Open questions (James — answer before Codex builds)
1. **Which channels to unify?** Telegram `@sunheartbrain_bot` · email · WhatsApp · SMS · other?
2. **Mode:** read-only inbox VIEW first (safe), or also send/reply (needs auth + guardrails — later)?
3. **"Conscious Chat" =** a triaged inbox (who needs you · drafted reply · priority), or a live chat surface?

## Definition of done (v1 — read-only triage view, pending scope)
A script `tools/decisions/comms_consolidate.py` → writes `00_MEMORY/COMMS INBOX.md`:
- Pending items needing James, per source, each with: who · gist · suggested action/draft · priority.
- Sources = whatever (1) defines. v1 likely: the bot's captured messages + any manual `COMMS INBOX` entries.
- Wired into `fpull`.

## Constraints
- 🔴 No auto-sending / no outward messages in v1 — read-only triage only. Sending is a separate gated spec.
- 🔴 No secrets/tokens in output.
- ✅ Reversible (one vault file + one fpull line).

## Steps
1. James answers the open questions (scope).
2. Codex reads `AGENTS.md` + protocol + this spec, builds the read-only view.
3. Report: files changed · summary · tests · risks · rollback.

- **Becomes a ticket?** After scope answered → Codex on its branch.
