#!/usr/bin/env bash
set -euo pipefail

mode="${1:---sync}"
if [[ "$mode" != "--sync" ]]; then
  echo "NOTICE: unsupported mode '$mode'; only --sync is available"
  exit 0
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"

registry="${PROOF_REGISTRY:-${REGISTRY:-$repo_root/core/BUILD/REGISTRY.json}}"
proof_log="${PROOF_LOG:-$repo_root/core/BUILD/PROOF_LOG.md}"

if ! command -v jq >/dev/null 2>&1; then
  echo "NOTICE: jq not found; proof sync skipped"
  exit 0
fi

if [[ ! -f "$registry" ]]; then
  echo "NOTICE: registry missing at $registry; proof sync skipped"
  exit 0
fi

mkdir -p "$(dirname "$proof_log")"
if [[ ! -f "$proof_log" ]]; then
  printf '# Proof Log\n\n' >"$proof_log"
fi

logged=0
today="$(date +%F)"

while IFS=$'\t' read -r id branch spec; do
  if [[ -z "$id" ]]; then
    continue
  fi

  if grep -Fq -- "$id" "$proof_log"; then
    continue
  fi

  printf -- '- %s · %s · %s · merged · spec:%s\n' "$today" "$id" "$branch" "$spec" >>"$proof_log"
  logged=$((logged + 1))
done < <(
  jq -r '
    .active_builds[]?
    | select(.status == "merged")
    | [.id // "", .branch // "", .spec // ""]
    | @tsv
  ' "$registry"
)

echo "Logged $logged new proof entr$(if [[ "$logged" -eq 1 ]]; then printf 'y'; else printf 'ies'; fi)"
