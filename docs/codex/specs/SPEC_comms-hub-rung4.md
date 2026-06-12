# SPEC_comms-hub-rung4

*Rung 4's first hub. The conduit the apprentice fleet needs to reach people — and the layer that triages James's inbound. An apprentice **ingests · triages · drafts**; every **send is Reserved-Class** (→ human-edge gate → James blesses). Owner: Codex. Scopes/supersedes the older `SPEC_comms-hub.md` / `SPEC_communication-hub.md` open-scope drafts. Read + draft + gate; v1 never auto-sends.*

## Source / why
James, 2026-06-10: `spec comms`. The self-building core (Rungs 0–3) is done; comms is the first apprentice-built hub because (a) the Results Engine already surfaced "draft + send Bottleneck outreach" with nowhere to send from, and (b) inbox triage is direct cognitive-load relief. Distribution is the live gap (0 humans, $0 revenue) — comms is the pipe that closes it. Memory: `project-apprentice-unbottleneck-model`.

## Scope decisions (decided — don't re-litigate)
- **Mode:** read + triage + draft + **stage** only. **No auto-send.** Every outbound is Reserved-Class (`tools.reserved.classify` → `public_outbound_send`) → a human-edge gate James approves. (V2 may allow pre-blessed templated sends; out of scope.)
- **First channel:** **email** (highest-leverage for Bottleneck outreach + real inbox). Build a thin channel-adapter interface so Telegram/others slot in later. V1 email = read/ingest + draft; the actual send stays manual/gated (do NOT wire live auto-send credentials in v1).
- **Apprentice-driven:** the comms hub is invoked by an apprentice (Rung 1) — it never acts on its own.

## The three declarations
- **Milestone (DoD):** given a batch of inbound messages (fixture or read-only pull), the hub produces a triage report (classify · summarize · suggested action) + drafted replies/outreach staged to a review lane, and writes a Reserved-Class human-edge gate for any message that needs a send. Demonstrated end-to-end on a fixture + dry-run.
- **Dependency:** Rung 1 (`tools/apprentice/`) · Rung 0 (`tools/reserved/`) · the queue. Forks from `feat/headless-build`.
- **Landing target:** `feat/headless-build`. Never `main`.

## Definition of Done
1. **`tools/comms/hub.py`** — `triage(messages)` → per message: `class` (needs-reply / fyi / action / spam) · 1-line summary · suggested next move. `draft(message|opportunity)` → a reply/outreach draft staged to `docs/codex/COMMS_LANE.md` or `core/STATE/COMMS_DRAFTS/` (never sent).
2. **Channel adapter interface** (`tools/comms/channels/`) with one **email** adapter that ingests read-only (fixture-backed in v1; live read behind an explicit, James-set credential env — off by default). No send path wired.
3. **Send = gate, always:** any "send this" step calls the Reserved-Class boundary → `add_gate()` ("Send draft to <recipient>? approve / edit / skip"). The apprentice pauses; James blesses.
4. **Fold the known breakage:** note/relate the failing intake-agent on host `198` (Fable flag 2026-06-09) as the live-channel follow-up — do NOT fix it blind here; flag it for a scoped pass.
5. **Tests** (`tools/comms/test_hub.py`): fixtures triage into the right classes; a needs-reply message produces a draft in the lane (not sent) + a send gate; dry-run writes nothing; no live network/send in tests.

- Files ALLOWED: `tools/comms/**` (new) · `docs/codex/COMMS_LANE.md` / `core/STATE/COMMS_DRAFTS/**` (new) · read-only of apprentice/reserved/queue. FORBIDDEN: wiring live auto-send · storing secrets in repo · money/deploy · editing the live curator/brain bot · auto-resolving gates · fixing the 198 intake-agent blind.

## Safety
- 🔴 V1 never sends. Outbound is always a James-gated act. Live email read requires an explicit James-set credential (off by default); no secrets in repo.
- Rollback: delete `tools/comms/` + the lane/drafts.

## Close-out
HANDOFF 📥 · PROOF LOG (Rung 4 begins — the fleet has a comms conduit; drafts staged, sends gated) · BRICK (the comms-hub triage/draft/gate pattern). Unlocks: the apprentice can now run the Bottleneck outreach end-to-end (draft → your blessing → send), closing the distribution gap.
