#!/usr/bin/env bash

# Read-only anomaly scan for the build loop. This script is intentionally
# report-only: every path is optional and the final exit status is always 0.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ANOMALIES=0
NOW_EPOCH="$(date +%s 2>/dev/null || printf '0')"
DAY_SECONDS=86400

red() {
  printf '🔴 %s\n' "$1"
  ANOMALIES=$((ANOMALIES + 1))
}

yellow() {
  printf '🟡 %s\n' "$1"
  ANOMALIES=$((ANOMALIES + 1))
}

clear_section() {
  printf '✓ clear\n'
}

header() {
  printf '\n## %s\n' "$1"
}

file_age_seconds() {
  local path="$1"
  local mtime

  mtime="$(stat -c %Y "$path" 2>/dev/null || stat -f %m "$path" 2>/dev/null || printf '')"
  if [ -n "$mtime" ] && [ "$NOW_EPOCH" -gt 0 ]; then
    printf '%s' $((NOW_EPOCH - mtime))
  else
    printf ''
  fi
}

iso_to_epoch() {
  local value="$1"

  [ -n "$value" ] || return 1
  date -d "$value" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%SZ" "$value" +%s 2>/dev/null
}

is_older_than_day() {
  local epoch="$1"

  [ -n "$epoch" ] || return 1
  [ "$NOW_EPOCH" -gt 0 ] || return 1
  [ $((NOW_EPOCH - epoch)) -gt "$DAY_SECONDS" ]
}

scan_stale_ssots() {
  local map="$HOME/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/SYSTEM_MAP.md"
  local findings

  header "Stale SSOTs"
  if [ ! -f "$map" ]; then
    clear_section
    return
  fi

  findings="$(
    awk '
      /^## ⚠ STALE SSOTs/ { in_section=1; next }
      in_section && /^## / { exit }
      in_section && /^- 🔴/ { print }
    ' "$map" 2>/dev/null
  )"

  if [ -n "$findings" ]; then
    printf '%s\n' "$findings"
    ANOMALIES=$((ANOMALIES + $(printf '%s\n' "$findings" | sed '/^[[:space:]]*$/d' | wc -l | tr -d ' ')))
  else
    clear_section
  fi
}

scan_stuck_builds() {
  local registry="$ROOT/core/BUILD/REGISTRY.json"
  local found=0
  local status updated epoch age label line

  header "Stuck builds"
  if [ ! -f "$registry" ]; then
    clear_section
    return
  fi

  if ! command -v jq >/dev/null 2>&1; then
    printf '✓ clear (jq unavailable; skipped structured registry age scan)\n'
    return
  fi

  while IFS=$'\t' read -r label status updated; do
    [ -n "$label" ] || continue
    case "$status" in
      merged|cancelled) continue ;;
    esac

    if [ -n "$updated" ] && [ "$updated" != "null" ]; then
      epoch="$(iso_to_epoch "$updated" || true)"
      if is_older_than_day "$epoch"; then
        red "$label status=$status updated_at=$updated"
        found=1
      fi
      continue
    fi

    line="$(jq -r --arg label "$label" '
      (.active_builds // [])[]
      | select((.id // .slug // .branch // "") == $label)
      | .spec // empty
    ' "$registry" 2>/dev/null | head -n 1)"

    if [ -n "$line" ] && [ -f "$ROOT/$line" ]; then
      age="$(file_age_seconds "$ROOT/$line")"
      if [ -n "$age" ] && [ "$age" -gt "$DAY_SECONDS" ]; then
        red "$label status=$status spec_age_seconds=$age"
        found=1
      fi
    fi
  done < <(
    jq -r '
      (.active_builds // [])[]
      | [(.id // .slug // .branch // "unknown"), (.status // "unknown"), (.updated_at // "")]
      | @tsv
    ' "$registry" 2>/dev/null
  )

  if [ "$found" -eq 0 ]; then
    clear_section
  fi
}

scan_stuck_specs() {
  local specs_dir="$ROOT/core/BUILD/specs"
  local results_dir="$ROOT/core/BUILD/results"
  local found=0
  local spec base id result age

  header "Stuck specs"
  if [ ! -d "$specs_dir" ]; then
    clear_section
    return
  fi

  while IFS= read -r spec; do
    [ -n "$spec" ] || continue
    base="$(basename "$spec" .md)"
    id="$base"
    result="$results_dir/$id.result.md"

    [ -f "$result" ] && continue

    age="$(file_age_seconds "$spec")"
    if [ -n "$age" ] && [ "$age" -gt "$DAY_SECONDS" ]; then
      red "$base has no result and spec_age_seconds=$age"
    else
      yellow "$base has no result yet"
    fi
    found=1
  done < <(find "$specs_dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort)

  if [ "$found" -eq 0 ]; then
    clear_section
  fi
}

scan_failed_results() {
  local results_dir="$ROOT/core/BUILD/results"
  local found=0
  local result matches

  header "Failed results"
  if [ ! -d "$results_dir" ]; then
    clear_section
    return
  fi

  while IFS= read -r result; do
    [ -n "$result" ] || continue
    matches="$(grep -En 'FAIL|codex exited non-zero' "$result" 2>/dev/null || true)"
    if [ -n "$matches" ]; then
      red "$(basename "$result")"
      printf '%s\n' "$matches" | sed 's/^/  /'
      found=1
    fi
  done < <(find "$results_dir" -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort)

  if [ "$found" -eq 0 ]; then
    clear_section
  fi
}

main() {
  printf '# Lantern anomaly scan\n'
  scan_stale_ssots
  scan_stuck_builds
  scan_stuck_specs
  scan_failed_results
  printf '\n%s anomalies\n' "$ANOMALIES"
}

main "$@" || true
exit 0
