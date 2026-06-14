#!/usr/bin/env bash
# Print a read-only one-glance report for the local build queue.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SPECS="$REPO_ROOT/core/BUILD/specs"
RESULTS="$REPO_ROOT/core/BUILD/results"
REGISTRY="$REPO_ROOT/core/BUILD/REGISTRY.json"

echo "Pending specs"
echo "-------------"
if [ ! -d "$SPECS" ]; then
  echo "(missing: core/BUILD/specs)"
else
  shopt -s nullglob
  pending=0
  for spec in "$SPECS"/*.md; do
    id="$(basename "$spec" .md)"
    result="$RESULTS/$id.result.md"
    if [ ! -f "$result" ]; then
      echo "$id"
      pending=$((pending + 1))
    fi
  done
  shopt -u nullglob
  [ "$pending" -eq 0 ] && echo "(none)"
fi

echo
echo "Registry"
echo "--------"
if [ ! -f "$REGISTRY" ]; then
  echo "(missing: core/BUILD/REGISTRY.json)"
elif ! command -v jq >/dev/null 2>&1; then
  echo "(jq not found; cannot parse active_builds)"
else
  registry_output="$(
    jq -r '.active_builds[]? | "\(.id) · \(.branch) · \(.status)"' "$REGISTRY" 2>/dev/null
  )"
  if [ $? -ne 0 ]; then
    echo "(could not parse core/BUILD/REGISTRY.json)"
  elif [ -n "$registry_output" ]; then
    echo "$registry_output"
  else
    echo "(none)"
  fi
fi

echo
echo "Recent results"
echo "--------------"
if [ ! -d "$RESULTS" ]; then
  echo "(missing: core/BUILD/results)"
else
  recent_output="$(ls -t "$RESULTS"/*.md 2>/dev/null | head -n 5)"
  if [ -n "$recent_output" ]; then
    echo "$recent_output" | while IFS= read -r result; do
      basename "$result"
    done
  else
    echo "(none)"
  fi
fi
