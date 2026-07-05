# D138 — tgbot repo ↔ live reconciliation (map ≠ territory)

**Date:** 2026-07-03 · **Status:** DIVERGENCE MAPPED · merge = scoped follow-up (not auto-done)

## The incoherence

The running Telegram bot and its repo source have **forked in both directions**. Anyone
reading the repo assumes that's what runs — it isn't. This is the concrete `repo ≠ running`
hole (sibling of `merged ≠ live` and the metric-drift caught by `metric_coherence.py`).

- **Live (running):** `/opt/sh-brain-src/curator/tgbot.py` — 5301 lines, service `sh-brain-tgbot` active, syntax OK.
- **Repo (stale/forked):** `SERVICES/sunheart-brain/curator/tgbot.py` — 5028 lines.
- 100 shared functions · **16 repo-only** · **12 live-only** · 1408-line diff.

Captured this pass (insurance against the zen-village "vanished on restart" class):
- `tgbot.live-snapshot-20260703.py` — the running truth, now in git (recoverable).
- `tgbot.repo-vs-live-20260703.diff` — the full divergence.

## Built in repo but NOT running live (merged ≠ live — decide: deploy or drop)

Substantial features that were built (likely by the build loop) and **never deployed**:

| Cluster | Functions |
|---|---|
| AI pairing | `_verify_ai_pairing` · `_record_pairing_event` · `_load_pairing_guard` · `_pairing_denied_text` |
| Public mode | `_public_mode_enabled` · `_load_public_context_pack` · `_synthesize_public_answer` · `_is_private_james_chat` |
| Context routing | `_context_routing_enabled` · `_classify_context_route` · `_context_blocks_for_route` · `_load_context_router` |
| Constitution surface | `_load_constitution_surface` |
| Becoming engine | `_capture_becoming_from_message` |
| Voice | `_download_telegram_voice` |
| Util | `_env_truthy` |

## Running live but NOT in git (hand-edits — must back-port to repo)

| Cluster | Functions |
|---|---|
| Identity | Ember system prompt (replaced "Sunheart Brain second-brain") |
| Brain retrieval | canonical-tier boost in `_search_brain` (academy/council +0.28–0.35) |
| Commands | `_cmd_status` · `_cmd_cost` · `_cmd_correct` |
| Cost tracking | `_log_cost` · `_cost_rate` |
| Question routing | `_is_meta_question` · `_is_status_question` · history-aware search |
| State/memory | `_system_state` · `_recent_turns` · `_refresh_treasury_memory` · `_build_context` |
| Voice | `_tts_pronounce` · token tuning (max_tokens 220→380 etc.) |

## Recommended reconciliation (scoped, NOT blind-merged — production blast radius)

1. **Back-port live → repo first** (truth into source): make repo's `tgbot.py` = live, so
   HEAD reflects reality. The 16 repo-only functions are preserved in git history + listed
   above, so nothing is lost.
2. **Then decide, per feature, which of the 16 repo-only clusters to (re)deploy** — via the
   gated additive `tools/deploy/deploy_curator_slice.sh` (d019), one slice at a time, tested.
   Pairing / public-mode / context-routing are meaningful capabilities that may simply have
   never shipped.
3. **Guard against recurrence:** treat the live curator as deploy-from-repo going forward, or
   add a `repo == running` coherence check (the code analog of `metric_coherence.py`).

**Why not auto-merged here:** merging two divergent forks of the live bot is high-risk
(could break production or resurrect dead code). Per guardrails/small-blast-radius, the
visible+captured+documented state is the safe increment; the per-slice deploy is the careful
follow-up.

## 2026-07-04 — concrete cost of the fork (awareness self-heal escalation)
The self-healer proved the fork's live cost: awareness slid 100→89% (latest session_insight
truncated from the bot's ~1800-char context as insights grew to 444). The build loop queued
+ merged a render-fix (d180, 82 lines to `SERVICES/sunheart-brain/curator/build_context.py`)
— but the awareness probe reads the LIVE `/opt/sh-brain-src/curator/build_context.py`, which
is a DIFFERENT forked file. So the fix merged, passed review, "done" — and awareness stayed
89%. **d138 repo≠running is not cosmetic: it silently voids every build-loop fix to the
curator.** The awareness fix (and any future curator fix) needs the per-slice deploy to live,
not just a merge. This is the highest-value item the autonomous run surfaced.

## 2026-07-05 — first 2 slices DEPLOYED to live (James explicit greenlight)
The `repo==running` guard (`tools/governance/repo_running_coherence.py`, wired into self_audit)
classified all 6 forked curator files. Two were pure repo-supersets (live-only=0 → additive,
no clobber): **corrections.py** (+30, blueprint-correction hook, try/except-gated) and
**live_system_status.py** (+53, liveness + git-based last-merge). Both deployed repo→live with
backup (`*.bak-d138-20260705-001004`) + syntax + runtime-import check; `sh-brain-tgbot` restarted
clean (PID 3155911). Guard re-run: both now IDENTICAL, drift 6→4.

**Remaining (NOT deployed — per-file merge, gated):** build_context.py (live+6/repo+78),
conversation_memory.py (live+23/repo+46), telegram.py (live+16/repo+34) = TWO-SIDED merges;
**decisions.py (live+489/repo+285) = LANDMINE — two different engines, never blind-deploy.**
