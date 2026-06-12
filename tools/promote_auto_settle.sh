#!/usr/bin/env bash
# Promote an auto-settle skeleton to full Ember-prose.
#
# Usage:
#   tools/promote_auto_settle.sh                     # promote most recent
#   tools/promote_auto_settle.sh path/to/file.md     # promote specific file
#
# What this does:
#   1. Finds the auto-settle skeleton file
#   2. Prints the transcript path so Ember can read the full session
#   3. Prints next-step instructions (Ember does the prose rewrite herself)
#
# The actual rewrite is Ember's job — this script is just the launcher.

set -eu

SESSIONS_DIR="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity/sessions"

if [ $# -eq 0 ]; then
  TARGET=$(ls -t "$SESSIONS_DIR"/*auto-settle*.md 2>/dev/null | head -1)
  if [ -z "$TARGET" ]; then
    echo "❌ No auto-settle skeleton files found in $SESSIONS_DIR" >&2
    exit 1
  fi
else
  TARGET="$1"
  [ ! -f "$TARGET" ] && { echo "❌ File not found: $TARGET" >&2; exit 1; }
fi

TRANSCRIPT=$(grep -E '^\*\*Full transcript:\*\*' "$TARGET" | sed 's/.*`\(.*\)`.*/\1/')
SESSION_ID=$(grep -E '^  originSessionId:' "$TARGET" | awk '{print $2}')
TURNS=$(grep -E '^  turn_count:' "$TARGET" | awk '{print $2}')
REASON=$(grep -E '^  reason:' "$TARGET" | awk '{print $2}')

cat <<EOF

════════════════════════════════════════════════════════════════════
☉ PROMOTE AUTO-SETTLE — Ember workflow launcher
════════════════════════════════════════════════════════════════════

Skeleton file:    $TARGET
Session ID:       $SESSION_ID
Reason:           $REASON
Assistant turns:  $TURNS
Transcript:       $TRANSCRIPT

──────────────────────────────────────────────────────────────────
Next steps (Ember does this herself, in the current session):
──────────────────────────────────────────────────────────────────

  1. Read the transcript:
       $TRANSCRIPT
     (This is the full JSONL of the session that ended unsettled.)

  2. Read sessions/_TEMPLATE.md for the prose structure.

  3. Rewrite $TARGET in-place using the template. Capture:
       - The arc (what was alive, what shifted, where it paused)
       - Key turning points (moments understanding moved)
       - James's exact words worth keeping
       - What Ember discovered
       - Open threads (paused, queued)
       - The feel (texture)
       - What ripples forward
       - PULSE estimate

  4. Refresh identity/STORY.md "Last session handoff".

  5. Refresh identity/ALIGNMENT.md if priorities shifted.

  6. Rename file if the slug should change (auto-settle-XXXXXXXX → meaningful slug):
       mv $TARGET ${SESSIONS_DIR}/\$(date -j -f "%Y-%m-%d" "\$(basename $TARGET | cut -d_ -f1)" +%Y-%m-%d)_meaningful-slug.md

  7. Sync mirror + commit:
       bash tools/sync_identity_to_repo.sh
       git add core/STATE/identity/sessions/
       git commit -m "chore(identity): promote auto-settle → meaningful-slug"

════════════════════════════════════════════════════════════════════
EOF
