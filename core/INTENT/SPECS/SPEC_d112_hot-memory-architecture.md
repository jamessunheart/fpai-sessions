# SPEC d112 — Hot Memory Architecture

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Principle

The bot reads a patchwork of 6+ sources at query time. Some are stale. Some contradict each other. The bot hallucinated a fake email and a fake model name because it had no reliable source for those facts.

The fix: parallel domain scanners compress their sources into deltas, a synthesis agent compresses those into one cited, pruned, always-current HOT_STATE document. The bot reads one document. The reliability probe (d111) compares bot answers against HOT_STATE as ground truth.

**The bot is as reliable as HOT_STATE is current.**

## Architecture

```
RAW SOURCES (unlimited substrate — everything on disk + brain_index)
        ↓ (runs every 30 min + on any significant change)
DOMAIN SCANNERS (parallel, T1/Ollama, each owns one chunk)
  → Spec Scanner:     core/INTENT/SPECS/ + build_loop logs
  → Identity Scanner: STORY · ALIGNMENT · DAILY_AWAKENING · NOW.md
  → Ops Scanner:      ops_ledger.jsonl · systemctl status · cost rate
  → Decision Scanner: brain_index.decisions + session_insights
  → Signal Scanner:   brain_index.corrections + thread + feedback_*.md
        ↓ (each scanner writes a delta: what changed + current state)
SYNTHESIS AGENT (T1/Ollama — lightweight summarization)
  → reads all 5 scanner deltas
  → compresses to HOT_STATE.md (~2-3KB)
  → cites every fact (source + date last verified)
  → actively prunes stale content (removes superseded facts)
        ↓
HOT_STATE.md — the single source of truth the bot reads
        ↓
d111 PROBE — compares bot answers against HOT_STATE as ground truth
```

## HOT_STATE.md format

```markdown
# HOT_STATE — {timestamp} · synthesized from 5 scanners

## Active directives (James's stated priorities — highest weight)
- {directive} [{James · date · source}]

## Spec queue
- Queued: {dNNN list} [source: SPEC dir · {date}]
- Last built: {spec} [source: build_loop · {date}]
- Last merged: {spec} [source: git · {date}]

## System identity facts
- System email: {address} [source: curator.env · {date}]
- Bot: {name} on {server} [source: RESOURCE_INVENTORY · {date}]
- Build loop: {status} [source: systemctl · {date}]

## Recent architecture decisions
- {decision} [source: session_insights · {date}]

## Active measurements
- Bot awareness score: {N}% [source: d111 probe · {date}]
- Bandwidth recovered: {N} [source: ops_ledger · {date}]

## Pruned (removed as stale — kept for audit)
- {old fact} → superseded by {new fact} on {date}
```

## Deliverables

### 5 domain scanner scripts (`tools/hot_memory/scanners/`)

Each scanner:
- Reads its domain
- Computes delta vs. previous scan (what changed since last run)
- Writes: `~/.config/fpai/hot_memory/scanner_{domain}.json`
  - `{changed: bool, facts: [{text, source, date, weight}], pruned: [...]}`
- Runs on T1 Ollama (summarization, $0)
- Non-blocking: failure logs to ops_ledger, hot_state falls back to last good scan

```python
# tools/hot_memory/scanners/spec_scanner.py
# Scans SPEC dir + build loop logs → extracts queued/built/merged facts
# Runs: every 30 min via systemd timer

# tools/hot_memory/scanners/identity_scanner.py
# Scans STORY.md + ALIGNMENT.md + NOW.md → extracts current intent + directives
# Runs: every 30 min, also triggered on any write to identity files

# tools/hot_memory/scanners/ops_scanner.py
# Scans ops_ledger.jsonl + systemctl + cost_track.py → health + cost facts
# Runs: every 30 min

# tools/hot_memory/scanners/decision_scanner.py
# Scans brain_index.decisions + brain_index.session_insights → decision facts
# Runs: every 30 min + triggered by any brain_index.session_insights write

# tools/hot_memory/scanners/signal_scanner.py
# Scans brain_index.corrections + thread + memory/feedback_*.md → feedback facts
# Runs: every 30 min
```

### Synthesis agent (`tools/hot_memory/synthesize.py`)

```python
# Reads all 5 scanner JSON outputs
# Sends to Ollama: "Synthesize these domain reports into a single HOT_STATE.
#   - Cite every fact (source + date)
#   - Prune facts superseded by newer ones
#   - Prioritize: James directives > architecture decisions > ops facts > spec queue
#   - Output < 2500 characters"
# Writes: ~/.config/fpai/hot_memory/HOT_STATE.md
# Also writes: brain_index.hot_state_log (each synthesis as a versioned row)
```

### Bot reads HOT_STATE (replaces patchwork)

Modify `_build_context()` in tgbot.py:
```python
# Attempt to read ~/.config/fpai/hot_memory/HOT_STATE.md
# If exists and < 30 min old: return it as the build context (replace all patchwork)
# If stale or missing: fall back to current patchwork (existing behavior)
# This makes HOT_STATE the primary source, patchwork the fallback
```

### Systemd timers

```
hot-memory-scan.timer:    OnUnitActiveSec=30min  # scanner cadence
hot-memory-synthesize.timer: OnActiveSec=35min   # synthesis runs after scanners
```

Triggered immediately on:
- Any brain_index.session_insights write (d110)
- Any identity file write (SETTLE ritual)
- Any spec committed to repo

### d111 integration (HOT_STATE as ground truth)

d111 probe now:
1. Reads HOT_STATE.md
2. For each cited fact, generates a probe question
3. Asks the bot
4. Scores against HOT_STATE (not against raw sources)

If HOT_STATE is current → probe is authoritative → reliability score is meaningful.

## What this replaces

| Current (patchwork) | After d112 (unified) |
|---|---|
| 6+ sources assembled at query time | 1 HOT_STATE.md read at query time |
| Some facts hours/days stale | Every fact dated, max 30 min old |
| No citations | Every fact has source + date |
| No pruning | Stale content actively removed |
| Bot hallucinated when no source exists | Bot says "not in hot state" honestly |

## Gates
- HOT_STATE.md is read-only for the bot (synthesis agent writes, bot reads)
- Private-tier content never enters HOT_STATE (James personal data, credentials, corrections with personal context)
- HOT_STATE bounded at 3000 chars (fits in context without crowding)
- All scanners + synthesis run on T1 Ollama ($0)
- Kill switch: `HOT_MEMORY_DISABLE=1` → bot falls back to patchwork
- Synthesis agent is non-authoritative: it compresses, doesn't decide

## Proof
- HOT_STATE.md exists and updates every 30 min (verified via timestamp)
- HOT_STATE correctly contains: system email, top 3 active specs, James's 100% directive
- Bot probe score improves from 5% to ≥80% within 1 week of HOT_STATE going live
- d111 probe runs against HOT_STATE as ground truth (not raw sources)
- Pruning works: old facts replaced by new ones, not accumulated indefinitely

## The path to 100%

```
d110 live: Claude Code sessions write to brain_index.session_insights
d112 live: decision_scanner reads session_insights → HOT_STATE updated within 35 min
d111 live: probe runs every 2h against HOT_STATE as ground truth
Bot reads HOT_STATE: answers from current, cited, pruned state
Score: 5% → 80%+ within days of all three building
Score: 80% → 100% by fixing remaining scanner gaps
```
