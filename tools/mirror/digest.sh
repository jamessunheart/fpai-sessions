#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTRY="$ROOT/core/BUILD/REGISTRY.json"
SPECS_DIR="$ROOT/core/BUILD/specs"
RESULTS_DIR="$ROOT/core/BUILD/results"
PROPOSALS_DIR="$ROOT/core/BUILD/improvement_proposals"
NOTIFY="$ROOT/tools/build_loop/notify_telegram.sh"

print_registry_section() {
  local title="$1"
  local selector="$2"
  local empty="$3"

  echo "## $title"
  if [ ! -f "$REGISTRY" ]; then
    echo "- Registry unavailable: core/BUILD/REGISTRY.json"
    echo
    return 0
  fi

  local rows=""
  if command -v jq >/dev/null 2>&1; then
    rows="$(
      jq -r --arg selector "$selector" '
        def entry_label:
          (.slug // .id // "unknown")
          + (if .branch then " - " + .branch else "" end)
          + (if .tests_passed == true then " (tests passed)" else "" end);
        (.active_builds // [])
        | map(select(
            if $selector == "merged" then .status == "merged"
            else (.status == "building" or .status == "done")
            end
          ))
        | .[:5]
        | .[]
        | "- " + entry_label
      ' "$REGISTRY" 2>/dev/null || true
    )"
  elif command -v python3 >/dev/null 2>&1; then
    rows="$(
      python3 - "$REGISTRY" "$selector" <<'PY' 2>/dev/null || true
import json
import sys

path, selector = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as handle:
    data = json.load(handle)

entries = data.get("active_builds") or []
if selector == "merged":
    entries = [entry for entry in entries if entry.get("status") == "merged"]
else:
    entries = [entry for entry in entries if entry.get("status") in {"building", "done"}]

for entry in entries[:5]:
    label = entry.get("slug") or entry.get("id") or "unknown"
    if entry.get("branch"):
        label += " - " + entry["branch"]
    if entry.get("tests_passed") is True:
        label += " (tests passed)"
    print("- " + label)
PY
    )"
  else
    rows="- Registry parser unavailable: install jq for detailed entries"
  fi

  if [ -n "$rows" ]; then
    printf '%s\n' "$rows"
  else
    echo "- $empty"
  fi
  echo
}

pending_specs_count() {
  local count=0
  local spec base result

  [ -d "$SPECS_DIR" ] || {
    echo 0
    return 0
  }

  for spec in "$SPECS_DIR"/*.md; do
    [ -e "$spec" ] || continue
    base="$(basename "$spec" .md)"
    result="$RESULTS_DIR/$base.result.md"
    [ -f "$result" ] || count=$((count + 1))
  done

  echo "$count"
}

latest_proposal() {
  [ -d "$PROPOSALS_DIR" ] || return 0
  find "$PROPOSALS_DIR" -maxdepth 1 -type f ! -name '.gitkeep' -print 2>/dev/null \
    | sort \
    | tail -n 1 \
    | xargs -n 1 basename 2>/dev/null || true
}

build_digest() {
  print_registry_section "Shipped" "merged" "No merged builds recorded"
  print_registry_section "In flight" "in-flight" "No building or done builds recorded"

  echo "## Next"
  echo "- Pending specs without results: $(pending_specs_count)"

  local proposal
  proposal="$(latest_proposal)"
  if [ -n "$proposal" ]; then
    echo "- Latest improvement proposal: $proposal"
  else
    echo "- Latest improvement proposal: none"
  fi
}

main() {
  local notify=0
  if [ "${1:-}" = "--notify" ]; then
    notify=1
  elif [ $# -gt 0 ]; then
    echo "usage: $0 [--notify]" >&2
    return 2
  fi

  local digest
  digest="$(build_digest)"
  printf '%s\n' "$digest"

  if [ "$notify" -eq 1 ] && [ -x "$NOTIFY" ]; then
    printf '%s\n' "$digest" | "$NOTIFY" "$digest" >/dev/null 2>&1 || true
  fi
}

main "$@"
