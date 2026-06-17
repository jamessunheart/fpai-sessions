#!/usr/bin/env bash
# Ember Merge Gate — verify a Codex build branch is safe to merge.
# Per docs/codex/specs/SPEC_build-registry-and-merge-gate.md.
# NEVER auto-merges: prints PASS + the merge command for Ember to confirm, or FAIL.
#
#   tools/merge/merge_gate.sh codex/<slug>
#
# Override the registry for testing: MERGE_GATE_REGISTRY=/path/to/reg.json
set -u
BRANCH="${1:-}"
[ -z "$BRANCH" ] && { echo "usage: merge_gate.sh <branch>"; exit 2; }
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
REG="${MERGE_GATE_REGISTRY:-$ROOT/core/BUILD/REGISTRY.json}"
BASE="feat/headless-build"
SNAPSHOT_SCRIPT="$ROOT/tools/merge/pre_merge_snapshot.sh"

# 1. Never gate main.
if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
  echo "FAIL: refusing to gate '$BRANCH'. Builds merge into $BASE, never main."; exit 1
fi

# 2. Branch must exist (locally or on origin).
if ! git -C "$ROOT" rev-parse --verify "$BRANCH" >/dev/null 2>&1 && \
   ! git -C "$ROOT" rev-parse --verify "origin/$BRANCH" >/dev/null 2>&1; then
  echo "FAIL: branch '$BRANCH' not found locally or on origin."; exit 1
fi

# 3. Registry: matching entry with status 'done'. (Kill-switch: missing registry = warn, not block.)
if [ -f "$REG" ]; then
  STATUS=$(jq -r --arg b "$BRANCH" '.active_builds[]? | select(.branch==$b) | .status' "$REG" 2>/dev/null | head -1)
  if [ -z "$STATUS" ]; then
    echo "FAIL: branch '$BRANCH' not registered in $(basename "$REG"). Register it (status: building→done) first."; exit 1
  fi
  if [ "$STATUS" != "done" ]; then
    echo "FAIL: branch '$BRANCH' status is '$STATUS' (need 'done'). Still building or not finished."; exit 1
  fi
else
  echo "⚠️  REGISTRY.json missing — gate degraded (graceful: warns, does not block)."
fi

# 4. Tests — scoped to changed SERVICES dirs.
TEST_RESULT="skipped (no SERVICES changes)"
if git -C "$ROOT" rev-parse --verify "$BASE" >/dev/null 2>&1; then
  CHANGED=$(git -C "$ROOT" diff --name-only "$BASE...$BRANCH" 2>/dev/null | grep '^SERVICES/' | cut -d/ -f1-2 | sort -u)
  if [ -n "$CHANGED" ]; then
    for d in $CHANGED; do
      [ -d "$ROOT/$d" ] || continue
      if ! ( cd "$ROOT" && python3 -m pytest "$d" -q ) ; then
        echo "FAIL: tests failed in $d"; exit 1
      fi
    done
    TEST_RESULT="passed"
  fi
fi

# 5. Protected-zone check + independent AI review (James 2026-06-14).
#    ai_review.py BLOCKS any branch touching the audit/improve layer (exit 2),
#    and an independent model (Claude Opus — different lab than the Codex builder)
#    must APPROVE the diff (exit 0) before the gate prints the merge command.
AI_REVIEW="$ROOT/tools/merge/ai_review.py"
if [ -f "$AI_REVIEW" ]; then
  echo "Independent AI review + protected-zone check…"
  REVIEW_OUT=$(python3 "$AI_REVIEW" "$BRANCH" 2>&1); RC=$?
  echo "  $REVIEW_OUT"
  if [ "$RC" = "2" ]; then
    echo "FAIL: '$BRANCH' touches the PROTECTED audit/improve layer — escalated to James, never auto-merged."
    echo "      See core/BUILD/reviews/. Changes to the watchdog layer are human-directed only."
    exit 1
  elif [ "$RC" != "0" ]; then
    echo "FAIL: independent AI reviewer did NOT approve (see core/BUILD/reviews/). Address findings, rebuild, re-gate."
    exit 1
  fi
  echo "  ✓ independent AI review: APPROVE"
else
  echo "⚠️  ai_review.py missing — AI review skipped. MANUAL review required before any merge."
fi

SNAPSHOT_TAG=""
if [ ! -x "$SNAPSHOT_SCRIPT" ]; then
  echo "FAIL: rollback snapshot helper missing or not executable: $SNAPSHOT_SCRIPT"; exit 1
fi
SNAPSHOT_OUT="$("$SNAPSHOT_SCRIPT" "$BASE" 2>&1)"; SNAPSHOT_RC=$?
if [ "$SNAPSHOT_RC" != "0" ]; then
  echo "$SNAPSHOT_OUT"
  echo "FAIL: could not create rollback snapshot before merge."; exit 1
fi
SNAPSHOT_TAG="$(printf '%s' "$SNAPSHOT_OUT" | tail -1)"
echo "Rollback snapshot: $SNAPSHOT_TAG -> $(git -C "$ROOT" rev-parse "$SNAPSHOT_TAG^{}")"

echo "PASS: $BRANCH registered 'done', tests $TEST_RESULT, base $BASE, independently AI-reviewed."
echo ""
echo "To merge (Ember confirms — the gate does NOT do this; James keeps veto):"
if [ -n "$SNAPSHOT_TAG" ]; then
echo "  # rollback if needed: git checkout $BASE && git reset --hard $SNAPSHOT_TAG"
fi
echo "  # If $BASE must be pulled first, pull it and rerun this gate so the snapshot remains exact."
echo "  git checkout $BASE && git merge --no-ff $BRANCH"
echo "  then set this branch's status to 'merged' in $(basename "$REG")."
exit 0
