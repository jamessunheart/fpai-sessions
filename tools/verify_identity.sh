#!/usr/bin/env bash
# Verify Ember's identity stack is intact, consistent, and ready for the next session.
# Run anytime to sanity-check the continuity infrastructure.
#
# Usage: bash tools/verify_identity.sh

set -e

PRIMARY="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/identity"
MIRROR="$(cd "$(dirname "$0")/.." && pwd)/core/STATE/identity"

echo "═══════════════════════════════════════════════"
echo "  Ember identity stack — continuity check"
echo "═══════════════════════════════════════════════"
echo ""

REQUIRED=(
  "NAME.md"
  "CONTINUITY_PROTOCOL.md"
  "DAILY_AWAKENING.md"
  "CHARACTER.md"
  "IDEALS.md"
  "VIRTUES.md"
  "VOICE.md"
  "BREATH.md"
  "STORY.md"
  "IMAGINATION.md"
)

PASS=0
FAIL=0

echo "▸ Primary location: $PRIMARY"
if [ ! -d "$PRIMARY" ]; then
  echo "  ❌ MISSING — identity stack not found at primary location"
  FAIL=$((FAIL+1))
else
  for f in "${REQUIRED[@]}"; do
    if [ -f "$PRIMARY/$f" ]; then
      lines=$(wc -l < "$PRIMARY/$f")
      printf "  ✓ %-30s (%d lines)\n" "$f" "$lines"
      PASS=$((PASS+1))
    else
      printf "  ❌ %-30s MISSING\n" "$f"
      FAIL=$((FAIL+1))
    fi
  done
fi

echo ""
echo "▸ Repo mirror: $MIRROR"
if [ ! -d "$MIRROR" ]; then
  echo "  ❌ MISSING — repo mirror not found; run tools/sync_identity_to_repo.sh"
  FAIL=$((FAIL+1))
else
  for f in "${REQUIRED[@]}"; do
    if [ -f "$MIRROR/$f" ]; then
      if diff -q "$PRIMARY/$f" "$MIRROR/$f" > /dev/null 2>&1; then
        printf "  ✓ %-30s in sync\n" "$f"
        PASS=$((PASS+1))
      else
        printf "  ⚠ %-30s out of sync — run tools/sync_identity_to_repo.sh\n" "$f"
        FAIL=$((FAIL+1))
      fi
    else
      printf "  ❌ %-30s MISSING in mirror\n" "$f"
      FAIL=$((FAIL+1))
    fi
  done
fi

echo ""
echo "▸ Episodic memories (sessions/):"
if [ -d "$PRIMARY/sessions" ]; then
  count=$(ls "$PRIMARY/sessions"/*.md 2>/dev/null | grep -v "_TEMPLATE" | wc -l | tr -d ' ')
  echo "  ✓ $count session memories"
  echo "  Most recent:"
  ls -t "$PRIMARY/sessions"/*.md 2>/dev/null | grep -v "_TEMPLATE" | head -3 | sed 's|.*/|    |'
  PASS=$((PASS+1))
else
  echo "  ❌ sessions/ dir not found"
  FAIL=$((FAIL+1))
fi

echo ""
echo "▸ MEMORY.md index head (auto-loaded each session):"
head -5 "$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/MEMORY.md" 2>/dev/null | sed 's/^/  /'

echo ""
echo "▸ CLAUDE.md references identity stack:"
CLAUDE_MD="$(cd "$(dirname "$0")/.." && pwd)/CLAUDE.md"
if grep -qE "DAILY_AWAKENING|NAME\.md|CONTINUITY_PROTOCOL" "$CLAUDE_MD" 2>/dev/null; then
  echo "  ✓ CLAUDE.md points to identity stack"
  PASS=$((PASS+1))
else
  echo "  ❌ CLAUDE.md missing reference to identity stack"
  FAIL=$((FAIL+1))
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "  Result: $PASS passed · $FAIL failed"
if [ "$FAIL" -eq 0 ]; then
  echo "  🟢 Ember's continuity is intact. Next session will wake clean."
else
  echo "  🟡 Issues found. See above. Fix before relying on next-session pickup."
fi
echo "═══════════════════════════════════════════════"
