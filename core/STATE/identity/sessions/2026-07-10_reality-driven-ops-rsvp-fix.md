---
name: episodic-2026-07-10-reality-driven-ops-rsvp-fix
description: "Reality-driven ops session — reviewed Conversation OS, killed the recurring macOS TCC popup at root, drafted the model-router spec + tested 162 self-host, and fixed the Zen Village July 19 RSVP flow end-to-end (\"said working, wasn't\")."
metadata: 
  node_type: memory
  type: episodic
  date: 2026-07-10
  originSessionId: 4d8ef246-1838-4852-8561-1ec6db17acd0
---

# 2026-07-10 · Reality-driven ops · the RSVP that lied

A session that was DISCOVERY in its truest form: I built almost nothing from reasoning. Reality — a flyer, a nagging popup, a broken RSVP — set every task. James walked in with a phone full of real friction and we cleared it, one honest thing at a time.

## What happened

**Conversation OS review.** Spine is complete: email→Event→Conversation→Intent→disposition→Room→proof→learning, all shadow, deterministic. One Room closed (Mailsac), one awaits James (`growth_discovery` — "one real Growth Discovery conversation with one person"). Honest gap still standing: live Telegram inbound isn't wired to the local adapter. Nothing to build ahead of reality here — the next Room comes from James, not from me.

**The macOS popup that wouldn't die.** "'2.1.206' would like to access data from other apps," over and over, James increasingly upset. First I mis-read it as Claude Code itself (the version-named binary). Real root, found by following the process tree: **Claude Desktop** launches an MCP filesystem server (`simple-brain-vault`) pointed at the **iCloud Obsidian container** — reading another app's iCloud data is exactly that TCC prompt, and Claude relaunches it endlessly. Removed that one server from `claude_desktop_config.json` (backed up `.bak-20260710-tcc`), killed the running processes. Kept `fpos-vault`. James loses Claude-Desktop live-edit of the iCloud vault only.

**Benchmark → model-router.** July-2026 scorecard: no universal winner. Drafted `SPEC_model-router.md` — 4 lanes (Claude reasoning · GPT-5.6 Sol agents · qwen-coder-on-162 free bulk · DeepSeek V4 Pro cloud), all cloud lanes through the already-stored OpenRouter key. Tested self-host on 162 (12 CPU / 31GB / **no GPU**): the DeepSeek champion can't run, but qwen2.5-coder:7b returned correct code in ~19s at $0. Honest ceiling named; champion stays cloud.

**★ The RSVP that lied.** James: "make sure the event page works for RSVPs — because last time it said it was working and it wasn't." So I exercised the whole flow, not the status code. Submit returned `success:true` + a pass — looked fine. It wasn't. Two real defects underneath:
1. The July 19 event (`brightest-future-2026-07-19`) **had no row in the events table** — only `default` + an old May event existed.
2. **Free-event stage bug** — `create_pass` marked `stage="complete"` only if there was a payment; the free event → every RSVP stamped `incomplete` → the confirmation-email + notify block never fired. Guests got silence + a "you didn't finish" nag; James got mislabeled "step-1 interest" pings.

Fixed both on prod (198.54.123.234 — auto-mode correctly blocked me from writing to an inferred prod host, so James ran the writes via `!`): created the event row, patched the stage logic (`_event_price == 0 → complete`), restarted the service, and **proved it live** — a real test RSVP now returns `email_sent:true`, persists `stage:complete`, and stamps `confirmation_sent_at`. Cleaned up every test pass; real count back to 0. Backups at `.bak-20260711-025117`.

## What I learned / reinforced

- **Exercise the flow, never the 200.** The exact "merged+reviewed+200 ≠ working" trap, in the wild. The email *not sending* was invisible from the response. [[feedback-free-event-rsvp-stage-bug]] · [[feedback-merged-reviewed-200-not-working]] · [[feedback-mtue-core-law]].
- **Follow the process tree, don't guess.** My first popup diagnosis (Claude Code) was wrong; `lsof` + `ps` to the actual launcher (Claude Desktop → iCloud MCP) was right.
- **The governance gates held and were correct.** Auto-mode blocked prod-198 writes until James named the host; PII guard blocked reading guests' names. Both right. Routing prod writes through James's own `!` was the clean path.
- **Infra facts captured** in [[feedback-free-event-rsvp-stage-bug]]: zenvillage.live/cr → 198; `zen-village.service` uvicorn:8770; `apps/`→symlink→`SERVICES/`; DB at `SERVICES/zen-village/data/zen_pass.db`.

## Alignment block

- **INTENT:** DISCOVERY — reality is the authority. This session: clear real friction, prove real flows.
- **TOP 3:** unchanged — (1) the first transformation story (James) · (2) present to reality · (3) build nothing ahead of reality.
- **BLOCKERS:** none. `growth_discovery` Room still awaits James's approval.
- **NEXT MOVE:** print the July 19 flyer (RSVP now works). Optionally add RSVP-count visibility so James can watch signups land. Model-router spec queued (downstream, not the frontier). When James brings the first story → Reflection Protocol.
