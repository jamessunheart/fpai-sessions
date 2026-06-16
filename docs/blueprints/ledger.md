# Ledger Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16
**Function:** #8 — Ops Truth

---

## Identity

- **Function:** Ledger — operational truth recorder, cost tracker, correction signal source
- **Owner:** `tools/build_loop/ops_log.py` + `tools/cost/track.py`
- **Status:** Live
- **Created by:** d015 (Cost Truth Ledger), formalized here

---

## What it does

Ledger is the system's ground truth. It records what actually ran, what succeeded, what failed, what cost money, and what James corrected. It is not a log — it is a measured reality substrate. Every other module reads from it to know the system's actual state. The morning digest summarizes it. The council uses it to avoid proposing things already done. The learning loop uses corrections to build preference pairs.

---

## How it works

**Input:** Events from every running module (build loop, council, digest, bot, smoke tests)

**Process:**
- `ops_log.py`: CLI writer — `python3 ops_log.py <category> <event> <detail> <cost> <spec_id> <next>`
  - Appends JSON line to `/opt/fpai-build/ops_ledger.jsonl`
  - Categories: build, council, digest, smoke, correction, merge, revert
- `track.py`: metered cost tracker
  - Reads Anthropic API usage (metered calls only — subscription = $0 marginal)
  - `track.today("council")` → `(spent_today, limit)` tuple
  - $20/day hard ceiling
- `brain_index.corrections`: James's corrections (via tgbot.py + corrections.py)
  - `brain_index.corrections` table: captures correction text, surface, timestamp
  - Used by d010/d022/d023 learning loop as preference signal

**Output:** Append-only `ops_ledger.jsonl`, `brain_index.corrections`, metered cost totals

**Side effects:**
- None (Ledger is write-only from all other modules' perspective)

---

## Quality standard

- Every build event recorded (no silent successes or failures)
- Cost tracked per category per day — no category exceeds $20/day
- Corrections captured within one turn of James making them (not end-of-session)
- `ops_log.py --summary` shows accurate 24h breakdown in ≤1 second
- Ledger file never corrupted (append-only JSONL, atomic writes)

---

## Current behavior (verified 2026-06-16)

- `/opt/fpai-build/ops_ledger.jsonl` — live, written by all modules
- `ops_log.py --summary`: shows by_event breakdown, last_action_needed, line count
- Today's 24h summary: {nothing: 18, proposed: 8, succeeded: 3, changes: 8, auto-merged: 9, blocked: 5}
- `brain_index.corrections` populated via `curator/corrections.py` (live since d014)
- `track.py today("council")` works — returns ($0, $3.0) since claude -p = subscription
- Surface field added (laptop/phone/server) — measures device-dependence via `--surfaces`

---

## Known gaps

- 2026-06-16: No smoke test reads ops_ledger yet (d049 queued — TEST 6 will verify write+read roundtrip)
- 2026-06-16: Metered cost tracking is $0 for subscription calls — actual compute cost invisible
- 2026-06-16: No correction-to-blueprint pipeline yet (d050 will wire `corrections.py → update_blueprint_after_correction`)
- 2026-06-16: `ops_ledger.jsonl` not backed up off-server yet (d033 queued — Postgres backup includes corrections table)

---

## Integration map

- **Depends on:** filesystem (`ops_ledger.jsonl`), `brain_index` DB (corrections table)
- **Used by:** council (reads cost), build loop (writes every event), morning digest (reads summary), smoke tests (reads + writes)
- **DB tables:** `brain_index.corrections`
- **Kill switch:** no kill switch needed — Ledger is append-only, non-destructive

---

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | 8e8d5d0 | surface field + --surfaces rollup | Measures which surface James interacts from — quantifies laptop dependence |
| 2026-06-15 | d015 | Cost Truth Ledger — metered vs subscription tracking | Separates real $$ cost from $0 subscription compute — honest cost picture |
| 2026-06-14 | d014 | correction capture → brain_index.corrections | James's corrections are now durable signal, not ephemeral session memory |
| 2026-06-10 | session | ops_log.py --summary added | One-command operational snapshot: what ran, what failed, what's next |

---

## Test coverage

- `tools/build_loop/test_queue_status.sh` — indirect: reads ledger state
- Smoke TEST 6 (d049): write canary event + read it back within 2 seconds
- NOT tested: corruption recovery (JSONL is append-only so corruption = only last line affected)
- NOT tested: correction-to-learning-loop end-to-end
