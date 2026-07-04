# Ranked Intent Stream — 2026-07-04 (Gate-1 proving run, rank fix validated)

_Produced by a single ranker agent from the recovered swarm findings — proves the rank
stage works after the fix. 20 confirmed weaknesses → 12 deduped, buildable intents.
This IS the self-improvement build queue. Route through constitution_check → decisions
(arming is persistence-gated). #1 bottleneck: the learning signal is frozen at the source._

| # | Pri | Rev | Eff | Intent |
|---|-----|-----|-----|--------|
| 1 | 97 | ✓ | S | **Fix correction detector** — regex→fuzzy for James's real voice (corrections.py captures 0% today). The learning-loop source. |
| 2 | 93 | ✓ | S | **Wire `sync_corrections_to_dataset.py`** on a timer (never fires → corrections never reach L2). |
| 3 | 90 | ✓ | S | **Schedule `post_merge_reality_check.py`** daily (exists, works, never runs → merged≠live unchecked). |
| 4 | 88 | ✓ | M | **Honest awareness metric** — rename + add `--probe-bot-response` behavioral probe + breadth ratio (100% may be narrowed). |
| 5 | 85 | ✓ | S | **Re-enable constitution governance** — restart council timer + wire decision_agent (makes "Constitution-checked" honest). |
| 6 | 82 | ✓ | S | **Fix council loop-lock** — live signal hash + metabolism psycopg gap (Law 4 conversion closes). |
| 7 | 80 | ✓ | S | **Fix `pending_builds()` orphan lock** — include failed/stalled build_status (BUG-005 → FIXED). |
| 8 | 77 | ✓ | M | **D138 reconcile** — backport live→repo + per-slice deploy 6 undeployed clusters + repo==running check. |
| 9 | 74 | ✓ | S | **RCA→build bridge** — rca_to_intent.py router + fix the INVALID claude-p key (RCA produces 0 findings today). |
| 10 | 70 | ✓ | S | **Stale-spec visibility** — age delta + escalation in spec_scanner. |
| 11 | 65 | ✓ | S | **HOT_STATE orientation** — identity_scanner cap 4→6 + offer/demand tokens. |
| 12 | 60 | ✓ | S | **Stamp `merged_at`** in mark_merged() + backfill NULLs (unblocks latency measurement). |

**Bonus honesty findings the ranker surfaced (verify before trusting current claims):**
- NOW.md says "learn" but no training step exists (finetune stubs) → should read "retain".
- The RCA timer's `claude -p` key is reportedly INVALID → RCA may be producing zero findings (dead loop).
- "131 merged" headline unverified against live (ties to intent #3).

_All 12 are reversible. The cadence (CADENCE.md) will meter the top 3-5 per round once Gate 2/3 are done._


---
**2026-07-04 VERIFICATION:** Intent #1 (correction regex) RETIRED — ground truth shows the regex is not the bottleneck (see VERIFY_intent1_corrections.md). Real fix: capture taste from direction/approval/choice, not corrections. Re-prioritize the learning-loop intents accordingly.
