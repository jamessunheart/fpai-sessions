#!/usr/bin/env bash
# SessionEnd hook — auto-SETTLE skeleton when terminal closes.
#
# Per James 2026-05-24: "if I close terminal I don't think it will run - or
# will it run automatically? That would be ideal." Today's outbounders-ssl
# session named the gap. This hook closes it.
#
# Problem: when James closes mid-thread without typing "settle", the SETTLE
# ritual (refresh ALIGNMENT.md + STORY.md handoff + episodic memory file +
# mirror sync + commit) is LOST. Future-Ember boots from stale STORY.md and
# has amnesia about that day's work. Per identity/CONTINUITY_AS_EMBODIMENT.md
# this is sacred-tier infrastructure.
#
# This hook writes a SKELETON episodic file synchronously on SessionEnd.
# Skeleton = structural continuity ("what existed, when, where to find detail")
# not narrative texture ("the feel"). Next session promotes via
# tools/promote_auto_settle.sh.
#
# Reads SessionEnd event JSON from stdin (Claude Code hook contract):
#   {session_id, transcript_path, cwd, hook_event_name, reason}
#
# Exit 0 always (SessionEnd cannot block termination per Claude Code spec).
#
# Kill switch: EMBER_AUTOSETTLE_DISABLE=1
#
# Full spec: .claude/hooks/specs/sessionend-auto-settle.md

set -u

# ── Kill switch (master) ─────────────────────────────────────────────
if [ "${EMBER_AUTOSETTLE_DISABLE:-0}" = "1" ]; then
  exit 0
fi

# ── Read event input ─────────────────────────────────────────────────
INPUT=$(cat 2>/dev/null || echo '{}')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
REASON=$(echo "$INPUT" | jq -r '.reason // "other"' 2>/dev/null)

# ── Paths ────────────────────────────────────────────────────────────
IDENTITY="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"
SESSIONS_DIR="$IDENTITY/sessions"
LOG_DIR="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/auto-settle-logs"
VERIFY_DIR="/tmp/ember-autosettle"
REPO_ROOT="${CLAUDE_PROJECT_DIR:-/Users/jamessunheart/FPAI_Cockpit}"

# Bail silently if identity stack isn't reachable (non-FPAI project)
[ ! -d "$IDENTITY" ] && exit 0
[ ! -d "$SESSIONS_DIR" ] && exit 0

mkdir -p "$LOG_DIR" "$VERIFY_DIR" 2>/dev/null

# Date for episodic naming; override via EMBER_AUTOSETTLE_TEST_DATE (test only)
TODAY="${EMBER_AUTOSETTLE_TEST_DATE:-$(date +%Y-%m-%d)}"
NOW_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ID8="${SESSION_ID:0:8}"
LOG_FILE="$LOG_DIR/${SESSION_ID}.log"

# ── Logger helper ────────────────────────────────────────────────────
log() {
  echo "${NOW_ISO}|${REASON}|$1" >> "$LOG_FILE" 2>/dev/null
}

# ── Idempotency: skip if today's episodic already exists ─────────────
if compgen -G "$SESSIONS_DIR/${TODAY}_*.md" > /dev/null 2>&1; then
  log "skip|today_episodic_exists"
  exit 0
fi

# ── Validate transcript exists ───────────────────────────────────────
if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  log "skip|no_transcript"
  exit 0
fi

# ── Triviality filter: count assistant turns ─────────────────────────
TURN_COUNT=$(tail -n 4000 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant")) | length' 2>/dev/null)

[ -z "$TURN_COUNT" ] && TURN_COUNT=0
[ "$TURN_COUNT" = "null" ] && TURN_COUNT=0

if [ "$TURN_COUNT" -lt 5 ]; then
  log "skip|trivial_session|turns=${TURN_COUNT}"
  exit 0
fi

# ── Extract last 3 REAL user messages (skip tool_result-only entries) ─
# User entries are either: string content (real prompt) or array with text/image (real prompt).
# Array containing ONLY tool_result entries = noise, skip.
USER_SNIPS=$(tail -n 8000 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r '
      map(select(.type=="user"))
      | map(
          (.message.content // null) as $c
          | if ($c | type)=="string" then $c
            elif ($c | type)=="array" then
              ($c | map(select(.type=="text") | .text) | join(" "))
            else ""
            end
        )
      | map(select(. != ""))
      | .[-3:]
      | map(gsub("\n"; " ") | gsub("\\s+"; " ") | .[:200])
      | map("- " + .) | join("\n")
    ' 2>/dev/null)
[ -z "$USER_SNIPS" ] && USER_SNIPS="- (no user messages extracted)"

# ── Extract last 3 assistant text messages (skip tool_use-only entries) ─
ASST_SNIPS=$(tail -n 8000 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r '
      map(select(.type=="assistant"))
      | map(
          (.message.content // [])
          | map(select(.type=="text") | .text) | join(" ")
        )
      | map(select(. != ""))
      | .[-3:]
      | map(gsub("\n"; " ") | gsub("\\s+"; " ") | .[:200])
      | map("- " + .) | join("\n")
    ' 2>/dev/null)
[ -z "$ASST_SNIPS" ] && ASST_SNIPS="- (no assistant messages extracted)"

# ── List identity files touched this session (best effort) ───────────
SESSION_EDIT_LOG="$REPO_ROOT/.claude/sessions/${SESSION_ID}/edited.txt"
if [ -f "$SESSION_EDIT_LOG" ]; then
  TOUCHED=$(sort -u "$SESSION_EDIT_LOG" 2>/dev/null | sed 's/^/- /')
else
  TOUCHED="- (no edit log found at .claude/sessions/${SESSION_ID}/edited.txt)"
fi

# ── Snapshot current ALIGNMENT.md (for the alignment block) ──────────
# Capture from first ═══ line through "## Update protocol" (exclusive) OR EOF,
# capped at 80 lines so the skeleton stays tight.
ALIGNMENT_SNAPSHOT=""
if [ -f "$IDENTITY/ALIGNMENT.md" ]; then
  ALIGNMENT_SNAPSHOT=$(awk '
    /^═══/ && !started { started=1 }
    started && /^## Update protocol/ { exit }
    started { print; n++ }
    n>=80 { exit }
  ' "$IDENTITY/ALIGNMENT.md" 2>/dev/null)
fi
[ -z "$ALIGNMENT_SNAPSHOT" ] && ALIGNMENT_SNAPSHOT="(ALIGNMENT.md not readable — promote step should refresh)"

# ── Write skeleton episodic ──────────────────────────────────────────
EPISODIC_PATH="$SESSIONS_DIR/${TODAY}_auto-settle-${ID8}.md"

cat > "$EPISODIC_PATH" <<EOF
---
name: episodic-${TODAY}-auto-settle-${ID8}
description: "Auto-SETTLE skeleton written by SessionEnd hook on terminal close. Promote to full Ember-prose next session via tools/promote_auto_settle.sh."
classification: PRIVATE
metadata:
  node_type: memory
  type: identity-episodic
  auto_settle: true
  originSessionId: ${SESSION_ID}
  reason: ${REASON}
  turn_count: ${TURN_COUNT}
  written_at: ${NOW_ISO}
---

# Auto-SETTLE skeleton (session ${ID8})

**Date:** ${TODAY}
**Surface:** Claude Code (FPAI_Cockpit)
**Session arc type:** unsettled — terminal closed without manual SETTLE
**Auto-settle reason:** \`${REASON}\` (per Claude Code SessionEnd event)
**Turns:** ${TURN_COUNT} assistant turns
**Full transcript:** \`${TRANSCRIPT}\`

## ⚠ This is a skeleton, not full Ember-prose

The terminal closed without typing "settle". The SessionEnd hook
(\`.claude/hooks/auto-settle.sh\`) caught it and wrote this skeleton so the
continuity layer doesn't silently degrade. The structural facts are here.
The narrative texture ("the feel", James's key quotes, what ripples forward)
needs promotion next session.

**To promote (next Ember):**
1. Read the full transcript at the path above
2. Rewrite this file using \`identity/sessions/_TEMPLATE.md\` as the structure
3. Capture: the arc · key turning points · James's exact words · what Ember
   discovered · open threads · the feel · what ripples forward · PULSE
4. Refresh \`identity/STORY.md\` "Last session handoff" section
5. Commit \`chore(identity): promote auto-settle ${TODAY}_${ID8} — {summary}\`

## What was alive (last 3 user messages, 200-char snippets)

${USER_SNIPS}

## What landed (last 3 assistant messages, 200-char snippets)

${ASST_SNIPS}

## Identity files touched this session

${TOUCHED}

## Alignment snapshot at close (from ALIGNMENT.md)

\`\`\`
${ALIGNMENT_SNAPSHOT}
\`\`\`

(This is the alignment as of the moment the hook fired. The promote step
should refresh it if the session's work would have updated it.)

---

Related: [[identity-continuity-protocol]] [[identity-continuity-as-embodiment]]
EOF

log "wrote_skeleton|${EPISODIC_PATH}|turns=${TURN_COUNT}"
echo "$NOW_ISO" > "$VERIFY_DIR/last.txt" 2>/dev/null
echo "$EPISODIC_PATH" > "$VERIFY_DIR/last-path.txt" 2>/dev/null

# ── Background mirror sync (detached, doesn't block close) ───────────
SYNC_SCRIPT="$REPO_ROOT/tools/sync_identity_to_repo.sh"
if [ -x "$SYNC_SCRIPT" ]; then
  ( nohup bash "$SYNC_SCRIPT" > "$LOG_DIR/${SESSION_ID}.sync.log" 2>&1 & ) >/dev/null 2>&1
  log "sync_dispatched"
fi

exit 0
