# Council Blueprint
**Version:** 0.1 (seed)
**Last updated:** 2026-06-16
**Function:** #5 — Architecture Debate

---

## Identity

- **Function:** Council — multi-lens architecture debate + build proposal
- **Owner:** `tools/council/debate.py` on server 162
- **Status:** Live
- **Created by:** d002 (Council Fire architecture), formalized here

---

## What it does

Council is the system's architectural intelligence. Every 5 minutes, it reads James's recent intents and the decision queue, debates internally with 3 lenses (Pragmatist / Visionary / Skeptic), and proposes exactly ONE build — or nothing. Its job is to surface the highest-leverage next move without wasting James's attention on low-value proposals. A second voice (Codex/GPT, $0) adds an independent outside perspective.

---

## How it works

**Input:**
- `brain_index.decisions` (current queue — what's pending)
- `brain_index.thread` (last 30 chats — James's recent intents)
- `core/STATE/COUNCIL_FOCUS.md` (standing weight directive from James)

**Process:**
1. Kill switch check (`~/.config/fpai/council/.disabled`)
2. Daily cost cap check (COUNCIL_DAILY_USD, default $3 — uses `track.py`)
3. Change-gate: SHA-256 of (queue + chats) vs last run — skip if unchanged (~$0)
4. Load intents + queue, run GPT second voice (`codex exec --sandbox read-only`, 1-2 sentences, $0)
5. Run debate via `claude -p --effort xhigh` — 3 lenses internal, produces JSON verdict
6. Dedup guard: skip if proposal's key words overlap significantly with existing queue
7. `propose=false`: log "nothing this round", done
8. `propose=true`: push to `brain_index.decisions` via `curator.decisions.recommend()`
9. Decision agent (d028) auto-answers confident proposals; uncertain ones surface to James

**Output:** One new queued decision (or nothing)

**Side effects:**
- `last_hash` file updated (prevents re-debate of same state)
- Ops ledger entry (proposed / nothing / diagnostic_error)
- Cost tracked in `track.py` (metered = $0 since claude -p is subscription)

---

## Quality standard

- Proposal rate: 1 meaningful proposal per 5-10 council cycles (not every cycle — skeptic should filter)
- Zero duplicate proposals reaching the queue (dedup guard catches them)
- Proposal-to-merge rate ≥ 60% (if lower: proposals are misaligned with system needs)
- Council detects system self-audit opportunities when queue is empty (self-diagnostic triggers)
- "Nothing this round" is a valid and frequent correct answer

---

## Current behavior (verified 2026-06-16)

- Runs every 5 min via `fpai-council.timer`
- Uses `claude -p --effort xhigh` (Claude Max, $0 marginal) with 300s timeout
- GPT second voice via `codex exec --sandbox read-only` (best-effort, drops gracefully if unavailable)
- 3 lenses in one prompt: Pragmatist / Visionary / Skeptic (honest: one model, three personas)
- Self-diagnostic: `tools/council/self_diagnostic.py` — when queue empty, interviews bot to find improvement specs
- Standing focus: `core/STATE/COUNCIL_FOCUS.md` — James sets priority; council weights toward it
- Change-gate: only runs full debate when queue + chats changed since last run
- One-at-a-time guard: removed 2026-06-16 (decision agent now auto-answers)

---

## Known gaps

- 2026-06-16: Three lenses are same model (claude -p) with persona prompts — not truly independent perspectives
- 2026-06-16: Council does not read module blueprints yet (d050 will wire this — proposals against defined standard)
- 2026-06-16: No cost tracking for the $0 marginal case (subscription runs tracked as $0, not as compute)
- 2026-06-16: GPT second voice is best-effort only — no structured integration of its perspective into verdict

---

## Integration map

- **Depends on:** `brain_index.decisions`, `brain_index.thread`, `claude` CLI, `codex` CLI, `track.py`
- **Used by:** `curator.decisions` (receives proposals), Forge (builds them)
- **DB tables:** `brain_index.decisions` (reads queue, writes proposals), `brain_index.thread` (reads intents)
- **Kill switch:** `touch ~/.config/fpai/council/.disabled`

---

## Improvement history

| Date | Build | What changed | Why it mattered |
|---|---|---|---|
| 2026-06-16 | session | --effort xhigh, goal-first prompt | Fable 5: higher reasoning effort for hardest decision = sharper proposals |
| 2026-06-16 | session | Removed one-at-a-time guard | Was blocking all proposals when any decision awaited James; now decision agent auto-answers |
| 2026-06-16 | session | Timeout 150→300s | xhigh effort needs more time; was timing out before finishing debate |
| 2026-06-14 | d031 | Self-diagnostic on empty queue | When nothing to build, council interviews bot to find gaps and generate improvement specs |
| 2026-06-14 | session | Change-gate (SHA hash) | Prevents $X/run cost when nothing has changed since last debate |

---

## Test coverage

- `tools/council/test_self_diagnostic.py` — self-diagnostic trigger logic
- NOT tested: full debate cycle (would need mock claude -p)
- NOT tested: dedup guard with queue that changes between runs
- Smoke TEST (d049): council activity check via ops_ledger events
