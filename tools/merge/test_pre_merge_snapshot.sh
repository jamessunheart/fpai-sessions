#!/usr/bin/env bash
# Temp-repo tests for numbered rollback snapshot tags.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$ROOT/tools/merge/pre_merge_snapshot.sh"
TMP="$(mktemp -d)"
PASS=0
FAIL=0

cleanup() {
  rm -rf "$TMP"
}
trap cleanup EXIT

check() {
  local desc="$1" expected="$2" actual="$3"
  if [ "$expected" = "$actual" ]; then
    echo "  ✓ $desc"
    PASS=$((PASS+1))
  else
    echo "  ✗ $desc"
    echo "      expected: $expected"
    echo "      actual:   $actual"
    FAIL=$((FAIL+1))
  fi
}

mkdir -p "$TMP/repo/tools/merge"
cp "$SCRIPT" "$TMP/repo/tools/merge/pre_merge_snapshot.sh"
chmod +x "$TMP/repo/tools/merge/pre_merge_snapshot.sh"

git -C "$TMP/repo" init -b feat/headless-build >/dev/null
git -C "$TMP/repo" config user.email test@example.invalid
git -C "$TMP/repo" config user.name "Test Bot"
printf 'base\n' > "$TMP/repo/README.md"
git -C "$TMP/repo" add README.md
git -C "$TMP/repo" commit -m base >/dev/null

echo "pre_merge_snapshot tests"

TAG1="$("$TMP/repo/tools/merge/pre_merge_snapshot.sh" feat/headless-build)"
check "first snapshot is numbered 0001" "fpai/pre-merge/0001" "$TAG1"

TAG1_REPEAT="$("$TMP/repo/tools/merge/pre_merge_snapshot.sh" feat/headless-build)"
check "same base reuses existing snapshot" "$TAG1" "$TAG1_REPEAT"

printf 'next\n' >> "$TMP/repo/README.md"
git -C "$TMP/repo" add README.md
git -C "$TMP/repo" commit -m next >/dev/null
TAG2="$("$TMP/repo/tools/merge/pre_merge_snapshot.sh" feat/headless-build)"
check "next base commit increments to 0002" "fpai/pre-merge/0002" "$TAG2"

MAIN_OUT="$("$TMP/repo/tools/merge/pre_merge_snapshot.sh" main 2>&1 || true)"
case "$MAIN_OUT" in
  *"refusing to snapshot protected base"*)
    echo "  ✓ refuses protected base"
    PASS=$((PASS+1))
    ;;
  *)
    echo "  ✗ refuses protected base"
    echo "$MAIN_OUT" | sed 's/^/      /'
    FAIL=$((FAIL+1))
    ;;
esac

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
