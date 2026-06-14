#!/usr/bin/env bash

# Lantern detector: read-only anomaly report.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ANOMALIES=0
NOW_EPOCH="$(date +%s 2>/dev/null || printf '0')"
ONE_DAY_SECONDS=86400
SYSTEM_MAP="${HOME}/.claude/projects/-Users-jamessunheart-FPAI-Cockpit/memory/SYSTEM_MAP.md"

increment() {
  ANOMALIES=$((ANOMALIES + 1))
}

section() {
  printf '\n== %s ==\n' "$1"
}

clear_line() {
  printf '✓ clear\n'
}

file_age_seconds() {
  local path="$1"
  local mtime=""

  mtime="$(stat -f %m "$path" 2>/dev/null || stat -c %Y "$path" 2>/dev/null || true)"
  if [ -n "$mtime" ] && [ "$NOW_EPOCH" -gt 0 ] 2>/dev/null; then
    printf '%s\n' $((NOW_EPOCH - mtime))
  else
    printf '0\n'
  fi
}

iso_to_epoch() {
  local stamp="$1"

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$stamp" <<'PY' 2>/dev/null || true
from datetime import datetime, timezone
import sys

raw = sys.argv[1].strip()
if not raw:
    raise SystemExit(1)
if raw.endswith("Z"):
    raw = raw[:-1] + "+00:00"
dt = datetime.fromisoformat(raw)
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
print(int(dt.timestamp()))
PY
  fi
}

scan_stale_ssots() {
  section "Stale SSOTs"

  if [ ! -f "$SYSTEM_MAP" ]; then
    clear_line
    return
  fi

  local findings
  findings="$(
    awk '
      /^## .*STALE SSOTs/ { in_section=1; next }
      in_section && /^## / { in_section=0 }
      in_section && /^- 🔴/ { print }
    ' "$SYSTEM_MAP" 2>/dev/null || true
  )"

  if [ -z "$findings" ]; then
    clear_line
    return
  fi

  while IFS= read -r line; do
    [ -z "$line" ] && continue
    local clean
    clean="$(printf '%s\n' "$line" | sed 's/^- 🔴[[:space:]]*//')"
    printf '🔴 %s\n' "$clean"
    increment
  done <<EOF
$findings
EOF
}

scan_stuck_builds() {
  section "Stuck builds"

  local registry="$ROOT/core/BUILD/REGISTRY.json"
  if [ ! -f "$registry" ]; then
    clear_line
    return
  fi

  if ! command -v jq >/dev/null 2>&1; then
    printf '🟡 skipped: jq not found for %s\n' "$registry"
    return
  fi

  local rows
  rows="$(
    jq -r '
      .updated_at as $registry_updated |
      (.active_builds // [])[]? |
      select((.status // "") != "merged" and (.status // "") != "cancelled") |
      [
        (.id // .slug // "(unknown-build)"),
        (.status // "(missing-status)"),
        (.updated_at // $registry_updated // ""),
        (.branch // ""),
        (.spec // "")
      ] | @tsv
    ' "$registry" 2>/dev/null || true
  )"

  if [ -z "$rows" ]; then
    clear_line
    return
  fi

  local found=0
  while IFS=$'\t' read -r id status updated_at branch spec; do
    [ -z "${id:-}" ] && continue

    local epoch age label
    epoch="$(iso_to_epoch "${updated_at:-}")"
    age=0
    label="unknown age"
    if [ -n "$epoch" ] && [ "$NOW_EPOCH" -gt 0 ] 2>/dev/null; then
      age=$((NOW_EPOCH - epoch))
      label="$((age / 3600))h old"
    fi

    if [ "$age" -gt "$ONE_DAY_SECONDS" ] || [ -z "$epoch" ]; then
      printf '🟡 %s status=%s updated_at=%s (%s)' "$id" "$status" "${updated_at:-unknown}" "$label"
      [ -n "${branch:-}" ] && printf ' branch=%s' "$branch"
      [ -n "${spec:-}" ] && printf ' spec=%s' "$spec"
      printf '\n'
      increment
      found=1
    fi
  done <<EOF
$rows
EOF

  if [ "$found" -eq 0 ]; then
    clear_line
  fi
}

scan_stuck_specs() {
  section "Stuck specs"

  local specs_dir="$ROOT/core/BUILD/specs"
  local results_dir="$ROOT/core/BUILD/results"
  if [ ! -d "$specs_dir" ]; then
    clear_line
    return
  fi

  local found=0
  while IFS= read -r spec_path; do
    [ -z "$spec_path" ] && continue

    local base id result_path age label
    base="$(basename "$spec_path")"
    id="${base%.md}"
    result_path="$results_dir/${id}.result.md"

    if [ -f "$result_path" ]; then
      continue
    fi

    age="$(file_age_seconds "$spec_path")"
    if [ "$age" -gt "$ONE_DAY_SECONDS" ] 2>/dev/null; then
      label="stuck spec (>1d)"
    else
      label="pending spec"
    fi

    printf '🟡 %s: %s' "$label" "$spec_path"
    if [ "$age" -gt 0 ] 2>/dev/null; then
      printf ' (%sh old)' "$((age / 3600))"
    fi
    printf '\n'
    increment
    found=1
  done < <(find "$specs_dir" -maxdepth 1 -type f -name '*.md' -print 2>/dev/null | sort)

  if [ "$found" -eq 0 ]; then
    clear_line
  fi
}

scan_failed_results() {
  section "Failed results"

  local results_dir="$ROOT/core/BUILD/results"
  if [ ! -d "$results_dir" ]; then
    clear_line
    return
  fi

  local matches
  matches="$(grep -RIlE 'FAIL|codex exited non-zero' "$results_dir"/*.md 2>/dev/null || true)"

  if [ -z "$matches" ]; then
    clear_line
    return
  fi

  while IFS= read -r result_path; do
    [ -z "$result_path" ] && continue
    printf '🔴 failed result evidence: %s\n' "$result_path"
    increment
  done <<EOF
$matches
EOF
}

main() {
  printf 'Lantern anomaly scan\n'
  printf 'Root: %s\n' "$ROOT"

  scan_stale_ssots
  scan_stuck_builds
  scan_stuck_specs
  scan_failed_results

  printf '\n%s anomalies\n' "$ANOMALIES"
  exit 0
}

main "$@"
