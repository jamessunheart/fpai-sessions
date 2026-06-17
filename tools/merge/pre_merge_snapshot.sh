#!/usr/bin/env bash
# Create a numbered rollback tag for the current base before any merge.
#
# Usage:
#   tools/merge/pre_merge_snapshot.sh [base-branch]
#
# The tag points at the base branch commit that is about to receive a merge.
# It is intentionally local: pushes/remote publication stay Ember-owned.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${1:-${MERGE_BASE:-feat/headless-build}}"
PREFIX="${MERGE_SNAPSHOT_PREFIX:-fpai/pre-merge/}"

case "$BASE" in
  main|master)
    echo "FAIL: refusing to snapshot protected base '$BASE'. Builds merge into feat/headless-build, never main."
    exit 1
    ;;
esac

if ! git -C "$ROOT" rev-parse --verify "$BASE" >/dev/null 2>&1; then
  echo "FAIL: base branch '$BASE' not found; cannot create rollback snapshot."
  exit 1
fi

BASE_SHA="$(git -C "$ROOT" rev-parse "$BASE")"

# Idempotency: a repeated gate run before the merge should reuse the existing
# snapshot for the same base SHA instead of minting misleading extra versions.
EXISTING="$(git -C "$ROOT" tag --points-at "$BASE_SHA" --list "${PREFIX}[0-9][0-9][0-9][0-9]" | sort -V | tail -1 || true)"
if [ -n "$EXISTING" ]; then
  echo "$EXISTING"
  exit 0
fi

LATEST="$(git -C "$ROOT" tag --list "${PREFIX}[0-9][0-9][0-9][0-9]" | sort -V | tail -1 || true)"
if [ -n "$LATEST" ]; then
  NUM="${LATEST#$PREFIX}"
  # Force base-10 so 0008/0009 do not parse as invalid octal.
  NEXT=$((10#$NUM + 1))
else
  NEXT=1
fi

TAG="$(printf '%s%04d' "$PREFIX" "$NEXT")"
if git -C "$ROOT" rev-parse --verify "refs/tags/$TAG" >/dev/null 2>&1; then
  echo "FAIL: computed snapshot tag '$TAG' already exists."
  exit 1
fi

git -C "$ROOT" tag "$TAG" "$BASE_SHA"

VERIFY_SHA="$(git -C "$ROOT" rev-parse "$TAG^{}")"
if [ "$VERIFY_SHA" != "$BASE_SHA" ]; then
  echo "FAIL: snapshot tag '$TAG' points at $VERIFY_SHA, expected $BASE_SHA."
  exit 1
fi

echo "$TAG"
