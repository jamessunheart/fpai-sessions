#!/usr/bin/env bash
# settle_push · one-branch era (2026-07-03). Push laptop commits to 162's live checkout.
# Handles the two normal rejections:
#   1. 162 tree dirty (build-loop artifacts) → commit them there as their own commit
#   2. 162 ahead (loop merged specs)         → pull-merge locally, push again
# Usage: bash tools/sync/settle_push.sh    (also called at SETTLE)
set -uo pipefail
R="root@162.0.208.88"; RP="/opt/fpai-build/FPAI_Cockpit"; B="feat/headless-build"
cd "$(dirname "$0")/../.."

try_push() { git push server162 "$B" 2>&1 | tail -1; }

OUT=$(try_push)
if echo "$OUT" | grep -q "unstaged changes"; then
  echo "162 tree dirty → committing loop artifacts there"
  ssh -o ConnectTimeout=12 "$R" "cd $RP && git add -A && git commit -m 'chore(162): loop artifacts (settle_push)' >/dev/null 2>&1 || true"
  OUT=$(try_push)
fi
if echo "$OUT" | grep -qE "rejected|failed"; then
  echo "162 ahead → pull-merge then push"
  git pull --no-rebase server162 "$B" --no-edit 2>&1 | tail -1
  OUT=$(try_push)
fi
if echo "$OUT" | grep -qE "rejected|failed"; then
  echo "❌ settle_push failed: $OUT"; exit 1
fi
LOCAL=$(git rev-parse HEAD); REMOTE=$(ssh -o ConnectTimeout=12 "$R" "git -C $RP rev-parse HEAD")
[ "$LOCAL" = "$REMOTE" ] && echo "✅ one branch, one head: ${LOCAL:0:10}" || echo "🟡 heads differ: local ${LOCAL:0:10} vs 162 ${REMOTE:0:10}"
