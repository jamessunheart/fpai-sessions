# SPEC d184 — Bot self-honesty: it must know + announce its own degradation (the precondition)

**Why (2-Sonnet capability debate 2026-07-04):** the bot spent hours broken today — dead API key → silent llama fallback, faster_whisper missing → dead voice, 0-char state feed → stale replies — and NONE of it announced itself; James found each one. Both debaters agreed: silent failure is the real enemy, not feature count. Before the bot gains ANY new capability, it must be able to tell the truth about its own state. This is the precondition for the whole capability roadmap (voice→build, approve-from-chat, briefings, alerts). Code: `/opt/sh-brain-src/curator/` (deploy live, MUST pass the d182 smoke-test gate).

## Build
1. **Live self-check, surfaced in every substantive reply's footer (terse) + on `/health`:**
   - Which model actually answered (Sonnet vs ollama-fallback) — if fallback, say so plainly ("⚠️ on fallback model").
   - Context freshness: HOT_STATE age; if >30min or empty, say "my live state is Xh old."
   - Voice STT available? (OpenAI Whisper reachable) — if not, tell James voice is down instead of silently ignoring memos.
   - Any import/degrade warnings in the last N min of its own logs.
2. **Startup self-test (loud):** on service start, run one Claude ping + one HOT_STATE read + one STT import check; if any fails, send James ONE line ("bot started degraded: <what>"). Never boot silently broken.
3. **A `/health` command** returns the full honest state: model, context age, voice, queue-write reachable, last error.
4. **Fix the underlying fragilities this exposed (so the self-check reports green):** claude-cli uses OAuth subscription only (blank/unset the dead metered ANTHROPIC_API_KEY — already patched live via drop-in; bake into config); voice STT falls back to OpenAI Whisper if faster_whisper absent; SH_HOT_STATE_MAX_CHARS defaults to ~3500 not 0 (baked, not just the live drop-in). Make the live drop-ins permanent in code/config.

## Contract
$0 · reversible · MUST pass d182 smoke-test before deploy · independent review · the self-check is READ-ONLY (reports state, changes nothing).

## Done / Proof
Force a degrade (kill claude auth) → the bot's next reply footer says "on fallback" AND a startup alert fires · `/health` returns model+context-age+voice+queue truthfully · the 3 baked fixes hold across a restart (no drop-in needed).

## Roadmap this unblocks (build in order, each gated by d182 + this self-check green)
Tier1: voice-memo→queued-build+ETA (cancel window) · proactive value-gap suggestion (notify-only).
Tier2 (confirm-gated): approve/hold builds from chat (verified-James + echo, flips a flag the reviewed loop reads) · loop-rendered daily briefing (bot delivers only) · event-only CPL/lead/spend-cap alerts (watcher computes, bot relays).
Tier3 REFUSE in bot: money movement · outreach send · deploy/ssh/run-code · agent-run dispatch → terminal-Ember/James only.
