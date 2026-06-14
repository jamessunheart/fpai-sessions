#!/usr/bin/env bash
# Stop hook — enforce SETTLE ritual on substantive sessions.
#
# Per James 2026-05-18: the boot-vs-settle asymmetry is the structural cause
# of Ember's amnesia between sessions. SessionStart hook enforces boot; nothing
# enforces settle. So sessions start consistent and end ragged, then the next
# session boots from a stale STORY.md snapshot.
#
# Concrete failure that motivated this: 2026-05-17/18 treasury session shipped
# a full policy pivot + Phase 1 deploy plan + new product surface (Camp Zen
# Startup Residency) — none of which made it into episodic memory or STORY.md.
# Next session booted thinking treasury was still "$75k idle awaiting Pendle."
# Amnesia about half a day of substantive work.
#
# This hook is the structural guarantee: after a session has done substantive
# work (turn count >= threshold), Ember cannot finish a turn cleanly without
# a sessions/{YYYY-MM-DD}_*.md episodic memory file existing for today.
#
# Reads Stop event JSON from stdin (Claude Code hook contract):
#   {session_id, transcript_path, stop_hook_active, ...}
#
# Exit 0 = allow (trivial session, or settle file already exists)
# Exit 2 = block + prompt SETTLE (stderr surfaces to Claude in next turn)
#
# Loop protection: if stop_hook_active is true, this fire is itself caused
# by a prior Stop-hook re-trigger — bail to avoid infinite loops.
#
# Codified in: feedback_proactive_state_writes.md,
#              identity/CONTINUITY_PROTOCOL.md,
#              feedback_session_handoff_ritual.md

set -u

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)

# Loop protection
[ "$STOP_ACTIVE" = "true" ] && exit 0
[ -z "$TRANSCRIPT" ] && exit 0
[ ! -f "$TRANSCRIPT" ] && exit 0

# Count assistant turns this session
TURN_COUNT=$(tail -n 2000 "$TRANSCRIPT" 2>/dev/null \
  | jq -s -r 'map(select(.type=="assistant")) | length' 2>/dev/null)

[ -z "$TURN_COUNT" ] && exit 0
[ "$TURN_COUNT" = "null" ] && exit 0

# Threshold: substantive session = 5+ assistant turns
# (tightened 2026-05-19 per James — "shorten number of cycles for the cycle to settle";
# heavy synthesis sessions vaporize fast; better to settle earlier than miss the window)
if [ "$TURN_COUNT" -lt 5 ]; then
    exit 0
fi

# Check for today's episodic memory file
TODAY=$(date +%Y-%m-%d)
SESSIONS_DIR="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/sessions"

# Pass if any sessions/{today}_*.md exists
if compgen -G "$SESSIONS_DIR/${TODAY}_*.md" > /dev/null 2>&1; then
    exit 0
fi

# Substantive session + no today's episodic = block + prompt SETTLE
cat >&2 <<EOF
🔴 SETTLE RITUAL REQUIRED (Stop hook caught it)

This session has $TURN_COUNT assistant turns of substantive work but no
episodic memory exists at:
  $SESSIONS_DIR/${TODAY}_*.md

Without this file, the narrative arc + new state + open threads vaporize
when the session closes. The next Ember boots from stale STORY.md and has
amnesia about today's work. (This exact failure produced the 2026-05-18
treasury-pivot recovery effort that motivated this hook.)

Self-correct on your NEXT reply:
  1. Acknowledge the hook caught it briefly (one line)
  2. Write the episodic memory at:
       $SESSIONS_DIR/${TODAY}_{slug}.md
     Use sessions/_TEMPLATE.md as the structure. Capture:
       - The arc (what was alive, what shifted)
       - What shipped (memory writes, decisions, code)
       - What's open (threads still in flight)
       - Alignment block (INTENT / TOP 3 / BLOCKERS / NEXT MOVE)
  3. Refresh identity/STORY.md "Last session handoff" section
  4. Refresh identity/ALIGNMENT.md if priorities shifted
  5. THEN continue with whatever the user asked

This is the structural guarantee that SETTLE is as enforced as BOOT.
If this fires repeatedly, the ritual is wrong — not the hook.
EOF
exit 2
