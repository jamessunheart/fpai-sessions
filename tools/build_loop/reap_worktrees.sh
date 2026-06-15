#!/usr/bin/env bash

set -u

APPLY=0
BASE_BRANCH="${REAP_BASE:-feat/headless-build}"
WT_ROOT="${REAP_WT_DIR:-$HOME/.fpai-build-worktrees}"

usage() {
  cat <<'EOF'
Usage: bash tools/build_loop/reap_worktrees.sh [--apply]

Dry-run by default. With --apply, removes only clean, merged build/* worktrees
under REAP_WT_DIR (default: ~/.fpai-build-worktrees), then deletes their merged
branches. REAP_BASE overrides the merge base branch (default: feat/headless-build).
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --apply)
      APPLY=1
      ;;
    --dry-run)
      APPLY=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1"
      usage
      exit 0
      ;;
  esac
  shift
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "NOTICE: not inside a git worktree; nothing to reap."
  echo "reaped 0, skipped 0 (dirty/unmerged)"
  exit 0
fi

if [ -d "$WT_ROOT" ]; then
  WT_ROOT_CANON="$(cd "$WT_ROOT" 2>/dev/null && pwd -P)"
else
  WT_ROOT_CANON="$WT_ROOT"
fi

reaped=0
skipped=0

finish() {
  git worktree prune >/dev/null 2>&1 || true
  echo "reaped $reaped, skipped $skipped (dirty/unmerged)"
  exit 0
}

if ! git rev-parse --verify --quiet "$BASE_BRANCH^{commit}" >/dev/null 2>&1; then
  echo "NOTICE: base branch '$BASE_BRANCH' is absent; skipping all worktrees."
  finish
fi

MERGED_FILE="$(mktemp "${TMPDIR:-/tmp}/fpai-reap-merged.XXXXXX")"
git branch --merged "$BASE_BRANCH" >"$MERGED_FILE" 2>/dev/null || {
  echo "NOTICE: could not read branches merged into '$BASE_BRANCH'; skipping all worktrees."
  rm -f "$MERGED_FILE"
  finish
}

is_under_worktree_root() {
  wt_path="$1"
  if [ -d "$wt_path" ]; then
    wt_canon="$(cd "$wt_path" 2>/dev/null && pwd -P)"
  else
    wt_canon="$wt_path"
  fi

  case "$wt_canon/" in
    "$WT_ROOT_CANON"/*) return 0 ;;
    *) return 1 ;;
  esac
}

is_merged_branch() {
  branch_name="$1"
  sed 's/^[*+ ]*//' "$MERGED_FILE" | grep -Fx -- "$branch_name" >/dev/null 2>&1
}

process_worktree() {
  wt_path="$1"
  branch_ref="$2"

  [ -n "$wt_path" ] || return 0
  [ -n "$branch_ref" ] || return 0

  case "$branch_ref" in
    refs/heads/build/*) ;;
    *) return 0 ;;
  esac

  if ! is_under_worktree_root "$wt_path"; then
    return 0
  fi

  if [ ! -d "$wt_path" ]; then
    echo "SKIP $wt_path (missing; prune will clean metadata)"
    return 0
  fi

  branch_name="${branch_ref#refs/heads/}"

  status_output="$(git -C "$wt_path" status --porcelain 2>/dev/null)"
  if [ -n "$status_output" ]; then
    echo "SKIP $wt_path (dirty)"
    skipped=$((skipped + 1))
    return 0
  fi

  if ! is_merged_branch "$branch_name"; then
    echo "SKIP $wt_path (branch unmerged)"
    skipped=$((skipped + 1))
    return 0
  fi

  if [ "$APPLY" -eq 0 ]; then
    echo "WOULD REMOVE $wt_path (branch merged)"
    reaped=$((reaped + 1))
    return 0
  fi

  if git worktree remove "$wt_path" >/dev/null 2>&1; then
    if git branch -d "$branch_name" >/dev/null 2>&1; then
      echo "REMOVED $wt_path (branch merged)"
      reaped=$((reaped + 1))
    else
      echo "REMOVED $wt_path; SKIP branch delete $branch_name (delete failed)"
    fi
  else
    echo "SKIP $wt_path (remove failed)"
  fi
}

current_path=""
current_branch=""

while IFS= read -r line || [ -n "$line" ]; do
  if [ -z "$line" ]; then
    process_worktree "$current_path" "$current_branch"
    current_path=""
    current_branch=""
    continue
  fi

  case "$line" in
    worktree\ *)
      current_path="${line#worktree }"
      ;;
    branch\ *)
      current_branch="${line#branch }"
      ;;
  esac
done <<EOF
$(git worktree list --porcelain 2>/dev/null)
EOF

process_worktree "$current_path" "$current_branch"

rm -f "$MERGED_FILE"
finish
