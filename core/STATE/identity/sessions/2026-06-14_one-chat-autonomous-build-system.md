# Session — 2026-06-14 · The one-chat self-evolving build system

**What this session built (the whole arc, in order):** a complete autonomous, self-evolving
build system James drives entirely from his Telegram one chat, running at ~$0 marginal cost.

## The live pipeline (all working)
```
council debate (every 5 min, $0) → proposes ONE build → James "yes build it" (Telegram)
→ Codex builds in isolated worktree → bridge commits → independent AI review (claude -p)
→ "✅ ready" surfaced to phone → James "merge d00X" → safe autonomous merge → done
```
James also: `reverse d00X` / `veto d00X` to undo · `/cost` to see spend · answers decisions in
plain language ("yes"/"not now").

## Key components
- **Server bot** (`sh-brain-tgbot`, server 162, `/opt/sh-brain-src/curator/`): `decisions.py` (v11 — the
  decision queue + recommend + merge lifecycle + build-token validation), `tgbot.py` (intercepts:
  `d###:` answer · `reverse/veto d###` · `merge d###` · `[[BUILD]]` token · `/cost`; honesty-grounded
  prompt). DB: `brain_index.decisions` + `receipts`. Bot backups: `tgbot.py.bak-*`.
- **Laptop daemons** (LaunchAgents): `com.fpai.council-debate` (5min, `tools/council/debate.py`) ·
  `com.fpai.proactive-recommend` (4h, `tools/proactive/recommend.py`) · `com.fpai.decision-bridge`
  (10min, builds + merges via `tools/decisions/bridge_to_codex.sh` + `tools/merge/process_merge_requests.sh`).
- **Repo tools** (`~/FPAI_Cockpit/tools/`): `merge/ai_review.py` (independent review, claude -p) ·
  `merge/process_merge_requests.sh` (multi-session-safe: transient worktree + CAS ref) ·
  `cost/track.py` (metered tally) · `decisions/feed_decision.sh` · `core/BUILD/PROTECTED_PATHS.txt`.

## The cost unlock (James's insight)
Route autonomous loops through the **CLIs** (`claude -p` = Claude Max flat-rate, `codex` = ChatGPT Max)
NOT metered APIs → **$0 marginal**. See [[reference-zero-marginal-cost-via-cli]]. Only the bot's
per-message chat synthesis is metered (small Sonnet). `/cost` shows it; today $0.

## Safety (all live)
Protected audit-zone (`PROTECTED_PATHS.txt` — autonomous builds can't touch the watchdog) ·
independent AI review before every merge · never `main` (auto-work → feat/headless-build) ·
veto/reverse · multi-session-safe merge (defers when branch contended) · $20/day cap.

## Honest open gaps (told James)
1. **Laptop-awake bound** — all loops are laptop LaunchAgents; chat + decisions are server-side/always-on.
   Asleep = queues, runs on wake. Keep lid open + plugged while away.
2. **Ember audit not yet proactive** — per-build AI review is automatic, but the standing meta-audit
   (drift/revert/cost-creep) still needs James to engage. NEXT: build a scheduled $0 Ember-audit digest
   that messages him unprompted (also the "throne dashboard").

## Git note
A merge-from-phone TEST left the main repo (~/FPAI_Cockpit) on branch `test/merge-base` @ the same
commit as feat/headless-build (which a codex worktree 37a8 holds with 105 WIP files). Nothing lost.
Re-home main to feat/headless-build when 37a8 releases it.

See [[reference-one-chat-decision-loop]] (full detail) · [[reference-zero-marginal-cost-via-cli]].
