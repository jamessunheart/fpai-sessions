#!/usr/bin/env bash
# process_merge_requests — execute merges James approved from his phone ("merge d00X").
# For each merge_requested build: re-run the INDEPENDENT AI review (final check +
# protected-zone block), and if APPROVED, merge the branch into feat/headless-build.
# NEVER main. Marks merged + notifies. main stays terminal + Ember-audit only.
#   Kill: touch ~/.config/fpai/decisions/.bridge_disabled
set -uo pipefail
REPO="$HOME/FPAI_Cockpit"; cd "$REPO"
HOST="${BRAIN_HOST:-root@162.0.208.88}"
BASE="${MERGE_BASE:-feat/headless-build}"
NOTIFY="${NOTIFY_SCRIPT:-tools/build_loop/notify_telegram.sh}"
SNAPSHOT_SCRIPT="tools/merge/pre_merge_snapshot.sh"
[ -f "$HOME/.config/fpai/decisions/.bridge_disabled" ] && { echo "disabled"; exit 0; }

REMOTE_ENV='ENVFILE=$(systemctl show sh-brain-tgbot -p EnvironmentFiles 2>/dev/null | sed -E "s/EnvironmentFiles=//; s/ .*//"); cd /opt/sh-brain-src && set -a; . "$ENVFILE" 2>/dev/null; set +a;'
PENDING=$(ssh -o BatchMode=yes -o ConnectTimeout=20 "$HOST" "$REMOTE_ENV ./.venv/bin/python -m curator.decisions pending-merges" 2>/dev/null | grep -E '^\{')
[ -z "$PENDING" ] && { echo "no merges requested"; exit 0; }

mark() {  # did  ok|fail
  ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" "$REMOTE_ENV ./.venv/bin/python -m curator.decisions mark-merged $1 $2" >/dev/null 2>&1 || true
}

regenerate_architecture_doc() {
  python3 "$REPO/tools/docs/generate_architecture.py" >/dev/null 2>&1 || true
  git -C "$REPO" add docs/ARCHITECTURE.md >/dev/null 2>&1 || true
  git -C "$REPO" commit -q -m 'docs(architecture): auto-regenerate after merge' >/dev/null 2>&1 || true
}

while IFS= read -r line; do
  [ -z "$line" ] && continue
  DID=$(printf '%s' "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
  BR=$(printf '%s' "$line" | python3 -c 'import sys,json;print(json.load(sys.stdin)["build_branch"])')
  [ -z "$BR" ] && { mark "$DID" fail; continue; }
  echo "merge request: $DID -> $BR"
  # Final independent AI review (also enforces the protected-zone block) before merge.
  REVIEW=$(python3 tools/merge/ai_review.py "$BR" 2>&1); RC=$?
  if [ "$RC" != "0" ]; then
    mark "$DID" fail
    [ -x "$NOTIFY" ] && "$NOTIFY" "⚠️ Final review did NOT approve [$DID] — not merged.
$REVIEW" >/dev/null 2>&1 || true
    continue
  fi
  # Merge into feat/headless-build only. NEVER main.
  git checkout "$BASE" >/dev/null 2>&1 || { mark "$DID" fail; continue; }
  if ! git pull --ff-only >/dev/null 2>&1; then
    mark "$DID" fail
    [ -x "$NOTIFY" ] && "$NOTIFY" "⚠️ Merge [$DID] held — could not fast-forward $BASE before snapshot/merge." >/dev/null 2>&1 || true
    continue
  fi
  SNAPSHOT=$("$SNAPSHOT_SCRIPT" "$BASE" 2>&1); SNAPSHOT_RC=$?
  if [ "$SNAPSHOT_RC" != "0" ]; then
    mark "$DID" fail
    [ -x "$NOTIFY" ] && "$NOTIFY" "⚠️ Merge [$DID] held — rollback snapshot failed before merge.
$SNAPSHOT" >/dev/null 2>&1 || true
    continue
  fi
  if git merge --no-ff -m "merge($DID): $BR — James-approved from phone, AI-reviewed" "$BR" >/dev/null 2>&1; then
    mark "$DID" ok
    regenerate_architecture_doc
    [ -x "$NOTIFY" ] && "$NOTIFY" "🔀 Merged [$DID] → $BASE ✅
$BR is in. Rollback snapshot: $SNAPSHOT. (main still needs the terminal + Ember's audit.)" >/dev/null 2>&1 || true
  else
    git merge --abort >/dev/null 2>&1 || true
    mark "$DID" fail
    [ -x "$NOTIFY" ] && "$NOTIFY" "⚠️ Merge [$DID] hit a conflict — held for Ember on the terminal. Not merged." >/dev/null 2>&1 || true
  fi
done <<< "$PENDING"
