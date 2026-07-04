#!/usr/bin/env bash
# Smoke tests for build worktree reaping.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SCRIPT="$REPO_ROOT/tools/build_loop/reap_worktrees.sh"
TMPDIR_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/fpai-reap-test.XXXXXX")"
REPO="$TMPDIR_ROOT/repo"
WT_ROOT="$TMPDIR_ROOT/worktrees"
PASSED=0
FAILED=0

cleanup() {
  rm -rf "$TMPDIR_ROOT"
}
trap cleanup EXIT

pass() {
  PASSED=$((PASSED + 1))
}

fail() {
  FAILED=$((FAILED + 1))
  echo "FAIL: $1"
}

assert_contains() {
  output="$1"
  needle="$2"
  label="$3"
  if echo "$output" | grep -Fq "$needle"; then
    pass
  else
    fail "$label"
    echo "$output"
  fi
}

assert_not_contains() {
  output="$1"
  needle="$2"
  label="$3"
  if echo "$output" | grep -Fq "$needle"; then
    fail "$label"
    echo "$output"
  else
    pass
  fi
}

mkdir -p "$WT_ROOT"
git init "$REPO" >/dev/null 2>&1
git -C "$REPO" config user.email "codex@example.test"
git -C "$REPO" config user.name "Codex Test"
git -C "$REPO" checkout -b feat/headless-build >/dev/null 2>&1
printf 'base\n' >"$REPO/README.md"
git -C "$REPO" add README.md
git -C "$REPO" commit -m "base" >/dev/null 2>&1

git -C "$REPO" worktree add -b build/stale-unmerged "$WT_ROOT/stale-unmerged" feat/headless-build >/dev/null 2>&1
printf 'stale\n' >"$WT_ROOT/stale-unmerged/stale.txt"
git -C "$WT_ROOT/stale-unmerged" add stale.txt
git -C "$WT_ROOT/stale-unmerged" commit -m "stale unmerged" >/dev/null 2>&1
touch -d '5 days ago' "$WT_ROOT/stale-unmerged"

DRY_OUTPUT="$(cd "$REPO" && REAP_WT_DIR="$WT_ROOT" REAP_AGE_LIMIT=3 bash "$SCRIPT" 2>&1)"
assert_contains "$DRY_OUTPUT" "WOULD FORCE-REAP $WT_ROOT/stale-unmerged (stale/unmerged, age > 3d)" "dry-run should report stale unmerged force reap"
assert_contains "$DRY_OUTPUT" "reaped 0, force-reaped 1, skipped 0" "dry-run should surface force_reaped count"
if [ -d "$WT_ROOT/stale-unmerged" ]; then
  pass
else
  fail "dry-run should not remove stale worktree"
fi
if git -C "$REPO" rev-parse --verify --quiet build/stale-unmerged >/dev/null 2>&1; then
  pass
else
  fail "dry-run should not delete stale branch"
fi

APPLY_OUTPUT="$(cd "$REPO" && REAP_WT_DIR="$WT_ROOT" REAP_AGE_LIMIT=3 bash "$SCRIPT" --apply 2>&1)"
assert_contains "$APPLY_OUTPUT" "FORCE-REAPED $WT_ROOT/stale-unmerged (stale/unmerged, age > 3d)" "apply should force-reap stale unmerged worktree"
assert_contains "$APPLY_OUTPUT" "reaped 0, force-reaped 1, skipped 0" "apply should surface force_reaped count"
if [ ! -d "$WT_ROOT/stale-unmerged" ]; then
  pass
else
  fail "apply should remove stale worktree"
fi
if git -C "$REPO" rev-parse --verify --quiet build/stale-unmerged >/dev/null 2>&1; then
  fail "apply should delete stale branch"
else
  pass
fi

git -C "$REPO" worktree add -b build/fresh-unmerged "$WT_ROOT/fresh-unmerged" feat/headless-build >/dev/null 2>&1
printf 'fresh\n' >"$WT_ROOT/fresh-unmerged/fresh.txt"
git -C "$WT_ROOT/fresh-unmerged" add fresh.txt
git -C "$WT_ROOT/fresh-unmerged" commit -m "fresh unmerged" >/dev/null 2>&1

FRESH_OUTPUT="$(cd "$REPO" && REAP_WT_DIR="$WT_ROOT" REAP_AGE_LIMIT=3 bash "$SCRIPT" 2>&1)"
assert_contains "$FRESH_OUTPUT" "SKIP $WT_ROOT/fresh-unmerged (branch unmerged)" "fresh unmerged worktree should still skip"
assert_contains "$FRESH_OUTPUT" "reaped 0, force-reaped 0, skipped 1" "fresh unmerged skip should not increment force_reaped"
assert_not_contains "$FRESH_OUTPUT" "FORCE-REAPED" "fresh unmerged dry-run should not force-reap"

echo "RESULT: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
