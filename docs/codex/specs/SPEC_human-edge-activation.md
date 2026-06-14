# SPEC_human-edge-activation

*Make the Human-Edge Push notifier (Part B) actually reach James: build the laptop↔server queue sync + server prerequisites, then deploy + prove it with one real test gate. Owner: Codex. This is the data pipe that turns the built-but-inert notifier into a live ping on James's phone.*

## Source / why
Part B (Telegram notifier, `SERVICES/sunheart-brain/curator/human_edge.py`) is built, security-passed, and crash-safe (the per-poll scan is wrapped in try/except — it cannot take down the live `@sunheartbrain_bot` poller). But on the Brain server (`root@162.0.208.88`, service `sh-brain-tgbot`, active): `tools/queue` is MISSING, `FPAI_REPO_ROOT` is UNSET, and there is NO sync carrying `HUMAN_EDGE_QUEUE.json` from the laptop (where gates are written) to the server (where the bot would read them). Deployed as-is, the notifier finds nothing and logs a warning every cycle. This spec builds the missing pipe.

## The three declarations (per OPERATING WORKFLOW cadence doctrine)
- **Milestone (DoD):** a real gate written on the laptop produces ONE Telegram ping on `@sunheartbrain_bot`; James's tap records the answer; the answer flows back so the laptop/vault sees `state: answered`. End to end, once.
- **Dependency:** Part A is live (done). Part B code exists on `feat/human-edge-notifier`. This spec depends on both; land Part B on `feat/headless-build` first.
- **Landing target:** sync tooling → `feat/headless-build` (the loop's branch). Curator/server code → deployed to `/opt/sh-brain-src` on `162.0.208.88`. NEVER `main`.

## Sync model (decided — don't re-litigate)
**Laptop is the source of truth; bidirectional file sync; answers are monotonic (open→answered, last-answer-wins).**
- **Push (laptop → server):** after any queue write (`daily_sync`, `add_gate`, Results Engine), push `core/STATE/HUMAN_EDGE_QUEUE.json` to the server. New gates propagate up.
- **Pull-merge (server → laptop):** at the start of each laptop loop tick, pull the server copy and merge: if either side has an `answer` for a gate id, that answer wins and the gate is `answered`. This survives the Mac sleeping — a tap made while the laptop is off is applied on the next loop.
- Rationale: keeps the existing laptop tools (which use the local file) unchanged; the bot reads a fresh synced copy. (v2 note, NOT now: if tap→vault latency matters, move the queue canonically server-side. Out of scope.)

## Definition of Done
1. **Server prereqs:** `tools/queue/` (build.py) present on the server at a path the curator can import; `FPAI_REPO_ROOT` (or `FPAI_HUMAN_EDGE_QUEUE_JSON`) set in `/etc/sh-brain/curator.env` so `human_edge.py` resolves the queue. (Confirm import works: the per-poll scan no longer logs the warning.)
2. **Sync tooling** (`tools/queue/sync.py` or similar): `push` + `pull-merge` as above, idempotent, no secrets, safe if the server is briefly unreachable (log + continue). Wire `push` after queue writes and `pull-merge` into the loop's start.
3. **Deploy:** targeted rsync of the curator + queue module to `/opt/sh-brain-src` (NO blind `--delete` over the whole tree — scope it; the zen-village + existing curator jobs must remain intact), then `systemctl restart sh-brain-tgbot`. Confirm the service comes back `active` and existing jobs (dedup/triage/opportunities/`/goals` etc.) still work.
4. **Update stale labels:** `tgbot.py` docstring + `systemd/sh-brain-tgbot.service` description: `@Adamclaw_bot` → `@sunheartbrain_bot`.
5. **Live test (the milestone):** write ONE gate via `add_gate(urgent=True)` (urgent bypasses quiet hours), confirm exactly one Telegram ping arrives with tap-buttons, James taps, `answer_gate` records it server-side, and the pull-merge lands `state: answered` back on the laptop. Document the round-trip in HANDOFF.

## Safety
- 🟢 Outbound is to James only (owner-checked). 🔴 No `--delete` blast over the server tree · no money/secrets in the sync · the notifier stays crash-guarded · do NOT touch the zen-village stack or other curator jobs.
- **Rollback:** unset `FPAI_REPO_ROOT` in curator.env (notifier goes inert, bot keeps running) OR `systemctl restart` the prior curator; remove the sync wiring from the loop. The live bot is never left broken.
- Do the deploy step ONLY after James approves the diff of items 1–4; the live `systemctl restart` is the one consequential action — show it before running.

## Close-out
HANDOFF 📥 (files · summary · tests · the test-gate round-trip · risks · rollback) · PROOF LOG (Human-Edge Push fully LIVE) · BRICK (the laptop↔server queue-sync pattern).
