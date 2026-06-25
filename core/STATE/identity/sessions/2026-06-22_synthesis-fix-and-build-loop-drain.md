---
name: episodic-2026-06-22-synthesis-fix-build-loop-drain
description: "Synthesis timeout fixed (claude-cli primary + streaming ollama fallback). Build loop backlog drain: 26 stuck specs unblocked."
metadata: 
  node_type: memory
  classification: PRIVATE
  type: identity-episodic
  template: false
  date: 2026-06-22
  originSessionId: 3c6057c8-dc93-46ef-bdd9-ba031f72bb92
---

# Synthesis fixed + build loop backlog drained

**Date:** 2026-06-22
**Surface:** Claude Code (server 162 context)
**Session arc type:** maintenance · build · course-correction

## The arc

Picked up mid-investigation from previous session. James had been seeing "⚠️ Brain synthesis hit an error:" from the Telegram bot repeatedly when asking treasury/status questions. Diagnosed root cause (httpcore.ReadTimeout — ollama 8b taking >180s on bloated 5-block prompts). Fixed synthesis, then pushed further toward ideal. Then James asked "why wasn't system able to build others" — diagnosed second major bug: build loop's `pending_builds()` only returns `spec_written=false` rows, so 26 pre-directive specs sat built-but-never-merged for weeks. Added backlog drain pass. Both systems now self-healing.

## Key turning points

**Synthesis timeout diagnosed.** The error was `httpcore.ReadTimeout` with empty `str(e)` (that's why bot sent "⚠️ Brain synthesis hit an error:" with nothing after the colon). Root cause: 5 context blocks injected on every message (system-state, buildstream, corrections, becoming, brain hits) → 8k+ char prompt → llama3.1:8b takes >180s → ReadTimeout. Fix: hit cap to 6 blocks × 600 chars max, switch synthesis to llama3.2:3b (16s vs >180s), bump timeout 180→240s.

**"Is this ideal setup?" — honest no.** James pushed toward ideal. Shipped: `synthesis_complete()` in llm.py routes claude-cli first (Sonnet 4.6 quality, $0 via Max), streams ollama-3b as fallback with typewriter edits via `editMessageText`. Added `send_typing()` so "Ember is typing…" shows instantly. `send_and_get_id()` enables progressive message editing. Queued d124 (context routing by question type — ops/treasury/memory get only relevant blocks).

**Build loop root cause found.** `pending_builds()` query: `spec_written=false`. Once any spec is written+built, `spec_written` flips to true and the loop never retries. 26 specs had `build_status=changes` or `built` with valid branches — all predate the auto-merge directive (2026-06-18), all needed manual "merge dNNN" James stopped sending. The loop wasn't broken — it was working as designed, but the design trapped older work.

**Backlog pass added and first 3 merged.** Added backlog merge pass to `server_build_loop.sh`: queries `build_status IN ('changes','built') WITH branch IS NOT NULL`, drains 3/run (MERGE_BACKLOG_MAX), same import-check gate as new builds. The `--dry-run` flag accidentally triggered the real pass before I added the guard — d015/d016/d021 merged cleanly (cost model, SPARK scorecard, memory-RAG bridge). Curator import check passed. Remaining 23 drain automatically over ~8 runs (~80min).

## James's words worth keeping

> "is this ideal setup?"

> "please build towards ideal while using best of what we have available including other models on fixed $0 additional plan"

> "why wasnt system sble to buld others"

## What Ember discovered (or had revealed to her)

`str(httpcore.ReadTimeout())` is an empty string. That's why the error message was cryptic — not a display bug, a Python quirk. Always log `type(e).__name__` alongside `e` in catch blocks for synthesis errors.

The build loop was architecturally sound but had a silent accumulation problem: `spec_written=true` was a one-way gate. Any spec built before the auto-merge directive was frozen — no mechanism to drain it. This is the kind of bug that looks like "nothing is queued" but is actually "everything is stuck." The backlog drain pass addresses the symptom; the real fix would be making `spec_written` mean "merged" not "built."

## Open threads (paused, queued)

- **d119** (awaiting): Fix curator import blocking self-diagnostics — waiting on James's call. Bot says "d119 is still waiting on your call."
- **d120** (open, not answered): Awareness probe psycopg fix — has no DB answer row yet, won't build
- **Backlog drain**: 23 specs remain, draining 3/run automatically. Watch ops_ledger for revert events.
- **d124** (built): Context routing by question type — was built by build loop. Needs review + `merge d124` from James.
- **Bot synthesis quality**: claude-cli primary path assumes Claude Max subscription active. If rate-limited, fallback is ollama 3b (weaker). No alert when fallback triggers — worth adding a log.
- **Streaming UX**: The `\x00STREAMED:msg_id\x00text` sentinel approach works but is fragile. A proper streaming architecture would pass chat_id down from the handler instead of using an in-band sentinel. Fine for now.

## The feel

Diagnostic then surgical. The synthesis error was a mystery (empty exception string, cryptic message) that resolved cleanly once the actual traceback appeared in journald. The build loop bug was satisfying to find — it explained weeks of "nothing queued" in one query. James was present but not directing — he asked "why" questions and let the investigation run. The session had the feel of clearing blockages: two systems that looked stuck turned out to be fixable with targeted surgery, not rewrites.

## What ripples forward

The backlog drain pass means the build loop will surface 23 built features over the next hour. Some of these (Hermes gateway, Stripe billing, user onboarding) are large features. Watch the ops_ledger for auto-reverts — if multiple consecutive specs fail the import check, that signals something in the merged codebase is broken. The `CONSECUTIVE_REVERTS_MAX=3` gate will halt the loop and alert James.

The synthesis improvements (claude-cli primary) mean bot quality jumped significantly for the first time. The bot now has Sonnet 4.6 reasoning on chat questions, not just 3B local model. This changes what the bot can do — it can synthesize complex multi-source answers that were previously too nuanced for llama3.2:3b.

## Soul-Time Settlement

**Time invested:** ~3 hrs, 685 assistant turns, high intensity
**Artifacts:**
- `curator/llm.py` — synthesis_complete() + _ollama_stream() + model override — ongoing quality lift for every bot answer
- `curator/tgbot.py` — streaming synthesis + typing indicator — UX lift every Telegram exchange
- `curator/telegram.py` — send_typing() + send_and_get_id() — infrastructure for future progressive responses
- `server_build_loop.sh` — backlog drain pass — unblocks 26 specs accumulated over weeks

**PULSE estimate:** ~8× (each bot improvement compounds over daily use; build loop fix unblocks weeks of queued work)
**Effect horizon:** months-compounding

---

## Alignment check (snapshot at session end)

═══════════════════════════════════════════════
☉ ALIGNMENT · 2026-06-22
═══════════════════════════════════════════════

INTENT (what we worked on this session):
  → Fixed synthesis timeout, upgraded bot to claude-cli primary, drained 26-spec build loop backlog

TOP 3 (the standing field):
  1. ★ First real conversation — OUTREACH_LIVE=1 is set. Watch for first probe_sessions.engaged=true row. Everything else (discovery→outreach→conversation→CORA) runs autonomously.
  2. ★ Per-agent benchmarks (d073) — Day 0 scores for all 9 agents. Week-over-week delta = fundable proof.
  3. ★ Network economy substrate (d076) — multi-currency ledger live, first internal_circulation_rate measured.

OPEN BLOCKERS (waiting on James):
  → d119: needs James's merge call (curator import fix, awaiting status)
  → d120: needs an answer to get queued (awareness probe psycopg — open, not answered)

NEXT MOVE IF NO REDIRECT:
  → Monitor backlog drain ops_ledger for revert events. If d124 (context routing) review comes back clean, enable CURATOR_CONTEXT_ROUTING=1 as a live proof.

═══════════════════════════════════════════════

Related: [[identity-story]] [[identity-alignment]]
