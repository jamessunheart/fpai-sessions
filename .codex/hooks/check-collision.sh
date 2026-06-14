#!/usr/bin/env bash
# PreToolUse hook for Edit/Write/MultiEdit on hot SSOT files.
#
# Blocks the edit if the target file has uncommitted git changes that this
# session didn't author. Prevents the bug from commit 8b8a64de where one
# session's edit accidentally bundled another session's dirty work.
#
# Reads JSON from stdin (Claude Code hook contract):
#   {session_id, cwd, tool_input: {file_path, ...}, ...}
#
# Exit 0 = allow. Exit 2 = block, stderr surfaces to user.

set -u

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)
SESSION_CWD=$(echo "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)

# Nothing to check if we couldn't parse a file path.
[ -z "$FILE_PATH" ] && exit 0

# Find repo root from the file path (works even if hook script CWD differs).
REPO_ROOT=$(cd "$(dirname "$FILE_PATH")" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -z "$REPO_ROOT" ] && exit 0

# Make path repo-relative for hot-list comparison.
case "$FILE_PATH" in
  "$REPO_ROOT"/*)  REL_PATH="${FILE_PATH#$REPO_ROOT/}" ;;
  *)               exit 0 ;;  # Outside repo, not our concern.
esac

HOT_LIST="$REPO_ROOT/.claude/hot-files.txt"
[ -f "$HOT_LIST" ] || exit 0

# Is this path on the hot list?
IS_HOT=0
while IFS= read -r pattern; do
  # Strip leading/trailing whitespace; skip blanks and comments.
  pattern="${pattern#"${pattern%%[![:space:]]*}"}"
  pattern="${pattern%"${pattern##*[![:space:]]}"}"
  [ -z "$pattern" ] && continue
  case "$pattern" in '#'*) continue ;; esac
  if [ "$REL_PATH" = "$pattern" ]; then
    IS_HOT=1
    break
  fi
done < "$HOT_LIST"

[ "$IS_HOT" -eq 0 ] && exit 0

# File is hot. Check if it has uncommitted changes.
DIRTY=$(cd "$REPO_ROOT" && git status --porcelain -- "$REL_PATH" 2>/dev/null)
[ -z "$DIRTY" ] && exit 0  # Clean, no collision possible.

# File is dirty. Did THIS session edit it?
SESSION_LOG="$REPO_ROOT/.claude/sessions/$SESSION_ID/edited.txt"
if [ -f "$SESSION_LOG" ] && grep -Fxq "$REL_PATH" "$SESSION_LOG" 2>/dev/null; then
  exit 0  # Own work, OK.
fi

# Collision risk. Block with an actionable message.
cat <<EOF >&2
🛑 Collision risk on hot SSOT file: $REL_PATH

This file has uncommitted git changes that your session ($SESSION_ID)
didn't author. A sibling Claude session is likely mid-edit. Editing now
risks bundling their unfinished work into your commit (this happened in
commit 8b8a64de — see .claude/hooks/README.md for context).

Inspect what's pending:
  git -C "$REPO_ROOT" diff -- "$REL_PATH"

Then choose:
  • Wait — let the sibling commit, then re-attempt
  • Stash it — git stash push -- "$REL_PATH"
  • Commit as-is (attribute clearly) — git commit -- "$REL_PATH"
  • Override (you accept bundling) — touch this session's edit log:
      mkdir -p .claude/sessions/$SESSION_ID
      echo "$REL_PATH" >> .claude/sessions/$SESSION_ID/edited.txt
EOF
exit 2
