# SPEC_human-edge-push

*The system taps James when it's blocked at a human-only decision — instead of parking the gate silently in a note for him to scan and discover. Inverts the loop from pull to push. Owner: Codex. Two parts, sequenced (B depends on A). One spec = one branch per part.*

## Intent
The self-standing loop (Rungs 0–3) runs itself until it hits a decision only James can make, then parks that gate silently. The only sensor for *where it's waiting* is James walking in to prompt — a pull system pretending to be proactive. Invert it: the loop reaches OUT, James answers in one verb, the loop continues. He stops being the scanner; he becomes the responder.

**Decisions locked (James, 2026-06-09):** Channel = Telegram `@sunheartbrain_bot` · Cadence = real-time on every new gate, **deduped** (one ping per gate) + **quiet-hours-respecting** (post-10:30pm queues to morning unless `urgent: 🔴`).

## Routing
- Owner: **Codex** builds both parts (Ember already did the design = this spec).
- Autonomy: 🟢 outbound is **to James only** (not the world) → low trust-stakes, no per-message confirm. 🔴 a gate NEVER auto-resolves — James's verb is the only thing that closes it.
- Sequencing: **Part A first** (`feat/human-edge-queue`), merge, then **Part B** (`feat/human-edge-notifier`) — B reads the queue, so it depends on A. Not parallel with each other; disjoint files.

## Part A — Gate schema + canonical queue  (`feat/human-edge-queue`)
**Definition of Done:** a single SSOT — `core/STATE/HUMAN_EDGE_QUEUE.md` (+ `.json` mirror) — where every open human-edge gate lives in one shape:
`id · surfaced(ts) · stream(Play|Game|Zen|Ventures|Treasury|Legal|Cheyenne) · question(one framed line) · verbs(1-tap replies) · blocking(bool) · urgent(🔴 bool) · state(open|answered|expired) · answer`.
- The loop + Ember WRITE gates here instead of burying them in prose.
- DECISIONS / HOME "to decide" / the daily block become **renders of this queue** (repoint the existing render hooks to read it) — kills the drift where gates live in 4 hand-kept places.
- Provide `tools/queue/build.py` (render the human-readable surfaces from the queue) + a tiny `add_gate()` / `answer_gate()` helper the loop calls.
- Files ALLOWED: `core/STATE/HUMAN_EDGE_QUEUE.*` (new) · `tools/queue/**` (new) · the render hooks that emit DECISIONS / HOME / daily "to decide" (repoint only).
- Files FORBIDDEN: Brain server code (that's Part B) · secrets · any money/deploy/outbound-to-world path · auto-resolving a gate.
- Tests: add a gate → it appears in the queue + renders into DECISIONS/HOME; answer it → state flips to `answered`; dedup holds (same id added twice = one entry).

## Part B — Notifier + reply handler  (`feat/human-edge-notifier`, Brain server)
**Definition of Done:** when a new `state: open` gate appears, the bot sends James a Telegram message — the framed question + tap-reply verbs as buttons. His tap writes the answer back (`state: answered, answer: <verb>`), which the loop consumes next tick to continue.
- Real-time, deduped (one ping per `id`), kind: a gate surfacing after 10:30pm queues to morning **unless** `urgent: 🔴`. Never re-nag an already-sent gate.
- Files ALLOWED: Brain bot notifier + reply-parse module + its config. Files FORBIDDEN: anything that sends to anyone but James · resolving a gate without his verb · money/deploy/outbound-to-world.
- Tests: open gate → exactly one Telegram message with correct verbs; tap → queue updates; second identical gate id → no second send; 11pm non-urgent gate → deferred to morning.

## Safety
- Queue entries are DATA; the bot renders, never executes them. Rollback: delete the queue file + revert the render-hook repoint (Part A) / remove the notifier hook (Part B) → loop reverts to silent-park.
- 🔴 Hard line: never sends to anyone but James · never resolves a gate without his verb · never moves money/deploys/outbound-to-world.

## Close-out
Per protocol: update HANDOFF 📥 (files · summary · tests · risks · rollback) · PROOF LOG · AGENT RUN LEDGER · BRICK (the human-edge-queue pattern — the inversion that makes "self-standing" honest). Do NOT merge/move money/deploy — show James the diff first.
