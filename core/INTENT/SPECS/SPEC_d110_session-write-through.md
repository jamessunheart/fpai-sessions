# SPEC d110 — Session Write-Through: Every Surface Writes to brain_index

**Status:** queued | **Stream:** Game | **Blast radius:** additive only

## Problem

Bot awareness reliability is ~65%. The primary cause: Claude Code sessions make significant decisions and design insights that never reach brain_index. The bot only knows what passed through Telegram. Everything else is invisible.

Current write coverage:
- Telegram decisions → brain_index.decisions ✅
- Telegram thread → brain_index.thread ✅
- Corrections → brain_index.corrections ✅
- Claude Code sessions → brain_index ❌ (gap)
- Architecture decisions → brain_index ❌ (gap)
- Frontier scan findings → brain_index ❌ (gap)

## What

A write-through mechanism: at SETTLE, every Claude Code session writes its significant decisions, insights, and architectural changes to brain_index. The bot then reads ONE unified layer — not a patchwork.

## Deliverables

### 1. New table: `brain_index.session_insights`

```sql
CREATE TABLE brain_index.session_insights (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW(),
    session_id TEXT,
    surface TEXT DEFAULT 'claude_code',  -- claude_code | telegram | phone
    insight_type TEXT,  -- decision | architecture | spec_queue | feedback | frontier
    title TEXT NOT NULL,
    body TEXT,
    specs_affected TEXT[],  -- e.g. ['d101', 'd102']
    weight INTEGER DEFAULT 5,  -- 1-10, influences bot surfacing priority
    expires_at TIMESTAMPTZ  -- null = permanent
);
CREATE INDEX ON brain_index.session_insights (ts DESC);
CREATE INDEX ON brain_index.session_insights (insight_type, weight DESC);
```

### 2. `tools/continuity/write_session_insights.py`

Called at SETTLE (added to settle ritual in CLAUDE.md hooks):

```python
# Writes structured session summary to brain_index.session_insights
# Input: list of insight dicts from the session
# Each insight: {type, title, body, specs_affected, weight}
# Called with: python3 tools/continuity/write_session_insights.py --session-id $SESSION_ID

# What gets written each settle:
# - Any new specs queued (d-numbers + titles)
# - Key architectural decisions made
# - New feedback rules that emerged
# - Frontier scan findings
# - Platform bias additions
# Weight 8-10: James-stated directives ("make this 100%")
# Weight 5-7: design decisions made autonomously
# Weight 1-4: housekeeping (file updates, minor fixes)
```

### 3. `tools/continuity/append_session_hook.sh`

Thin wrapper called by the UserPromptSubmit + Stop hooks at session end:
```bash
#!/usr/bin/env bash
# Appends current session's key decisions to brain_index.session_insights
# Non-blocking: logs failure, never halts the session
python3 /opt/fpai-build/FPAI_Cockpit/tools/continuity/write_session_insights.py \
  --session-id "${CLAUDE_SESSION_ID:-unknown}" \
  --source claude_code \
  || echo "[session-write-through] write failed (non-blocking)"
```

### 4. Bot reads session_insights

Add to `build_context.py` (`_with_recent_insights` function):
```python
# Query brain_index.session_insights where ts > now() - interval '7 days'
# Order by weight DESC, ts DESC, limit 8
# Append to BuildContext as new field: recent_insights
# Render in build context: "Recent decisions (all surfaces):"
```

### 5. System prompt auto-refresh trigger

When a session_insight with weight >= 8 is written → invalidate bot's cached system prompt → next message uses fresh context. Ensures architecture-level decisions propagate to bot awareness within one message cycle.

## What the bot gains

After d110:
- Every spec queued in Claude Code → bot knows within one session cycle
- Every design decision (consciousness architecture, platform bias, etc.) → bot knows
- Every James directive → bot knows with high weight
- One unified read: `brain_index.session_insights` ordered by weight + recency

## Gates
- Non-blocking: write failures log to ops_ledger, never halt session
- No personal data in session_insights (private-tier content stays in memory files)
- Max 20 insights per session (bounded — prevents runaway writes)
- Weight >= 8 requires explicit James directive or major architectural change (not self-assigned)

## Proof
- brain_index.session_insights table exists with data from 3+ sessions
- Bot correctly reports d101–d109 in detail (not just filenames) when asked
- Bot correctly surfaces James's "make awareness 100%" directive when asked "what are our active mandates"
- Awareness reliability score (d111) shows measurable improvement
