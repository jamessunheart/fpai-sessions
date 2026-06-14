#!/bin/bash
# vastai_audit.sh — daily watchdog: alert if ANY vast.ai instance is running.
#
# Context: a Dec 2025 "GPU Collective" experiment auto-spawned 25-46 GPUs at peak.
# Cleaned up twice (this is the second). Current policy: ZERO instances expected.
# If this script finds any, something resurrected — investigate before destroying.
#
# Usage:
#   VASTAI_API_KEY=... ./vastai_audit.sh        # one-shot manual check
#   ./vastai_audit.sh                            # reads ~/.config/sunheart/secrets.env
#
# Exit codes: 0 clean · 1 instances found · 2 API error
# State file: ~/.config/sunheart/vastai_audit.log (JSONL — one line per run)

set -euo pipefail

SECRETS="${HOME}/.config/sunheart/secrets.env"
LOG="${HOME}/.config/sunheart/vastai_audit.log"
QB_BOOK="fpai"

if [ -z "${VASTAI_API_KEY:-}" ] && [ -f "$SECRETS" ]; then
  # shellcheck disable=SC1090
  source "$SECRETS"
fi

if [ -z "${VASTAI_API_KEY:-}" ]; then
  echo "❌ VASTAI_API_KEY not set (looked in env + $SECRETS)" >&2
  exit 2
fi

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RESP="$(curl -sf --max-time 30 "https://console.vast.ai/api/v0/instances/?api_key=${VASTAI_API_KEY}" 2>&1)" || {
  echo "{\"ts\":\"$TS\",\"status\":\"api_error\"}" >> "$LOG"
  echo "❌ vast.ai API call failed: $RESP" >&2
  exit 2
}

SUMMARY="$(printf '%s' "$RESP" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inst = data.get('instances', [])
total_hr = sum(i.get('dph_total', 0) for i in inst)
print(json.dumps({
    'count': len(inst),
    'hourly_usd': round(total_hr, 4),
    'monthly_usd': round(total_hr * 24 * 30, 2),
    'ids': [i.get('id') for i in inst],
    'details': [{'id': i.get('id'), 'gpu': f\"{i.get('num_gpus')}x {i.get('gpu_name')}\",
                  'dph': i.get('dph_total'), 'ssh': f\"{i.get('ssh_host')}:{i.get('ssh_port')}\",
                  'cpu_util': i.get('cpu_util'), 'gpu_util': i.get('gpu_util'),
                  'age_days': round(i.get('duration', 0) / 86400, 1)} for i in inst]
}))")"

COUNT="$(printf '%s' "$SUMMARY" | python3 -c 'import sys,json; print(json.load(sys.stdin)["count"])')"

echo "{\"ts\":\"$TS\",\"status\":\"ok\",\"summary\":$SUMMARY}" >> "$LOG"

if [ "$COUNT" -eq 0 ]; then
  echo "🟢 vast.ai clean: 0 instances at $TS"
  exit 0
fi

echo "🔴 vast.ai ALERT: $COUNT instance(s) running at $TS"
echo "$SUMMARY" | python3 -m json.tool

# Try to alert via qb if available (non-blocking — won't fail the script)
if command -v qb >/dev/null 2>&1; then
  MONTHLY="$(echo "$SUMMARY" | python3 -c 'import sys,json; print(json.load(sys.stdin)["monthly_usd"])')"
  qb open --book "$QB_BOOK" "vast.ai resurrection — ${COUNT} instance(s) running, ~\$${MONTHLY}/mo burn. Investigate origin before destroying. (auto: vastai_audit.sh)" 2>/dev/null || true
fi

exit 1
