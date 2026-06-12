#!/usr/bin/env bash
# Pull live revenue counts from ZV booking ops summary and merge into ledger.json.
# Runs from the dev box; ZV booking is bound to localhost on 198.54.123.234,
# so we SSH-tunnel via the ops summary endpoint.
set -euo pipefail

ZV_HOST="${ZV_OPS_HOST:-198.54.123.234}"
HERE="$(cd "$(dirname "$0")" && pwd)"
COCKPIT_ROOT="$(cd "${HERE}/../../.." && pwd)"
LEDGER="${COCKPIT_ROOT}/core/STATE/ledger.json"

OPS=$(ssh -o ConnectTimeout=5 "root@${ZV_HOST}" 'curl -s -m 5 http://127.0.0.1:8770/api/ops/summary' 2>/dev/null || echo '')
if [[ -z "${OPS}" ]] || ! echo "${OPS}" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
    echo "[refresh_revenue] WARN: could not fetch ops summary from ${ZV_HOST}; ledger unchanged" >&2
    exit 0
fi

python3 - "${LEDGER}" <<PY
import json, sys, os
from datetime import datetime, timezone

ledger_path = sys.argv[1]
ops = json.loads('''${OPS}''')

with open(ledger_path) as f:
    ledger = json.load(f)

totals = ops.get("nocodb", {}).get("totals", {}) or {}
recent = ops.get("nocodb", {}).get("recent", {}) or {}

zv = ledger.setdefault("revenue_monthly", {}).setdefault("zen_village", {})
zv["inquiries"] = totals.get("inquiries", 0)
zv["bookings_confirmed"] = totals.get("bookings", 0)
zv["recent_inquiries"] = recent.get("inquiries", 0)
zv["recent_bookings"] = recent.get("bookings", 0)
zv["applications"] = totals.get("applications", 0)
zv["as_of"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
zv.setdefault("source_endpoint", "http://198.54.123.234:8770/api/ops/summary")
zv["_note"] = "Counts pulled live from ZV ops summary. revenue_usd not yet wired (per-booking price lookup pending)."

ledger["last_updated"] = datetime.now(timezone.utc).date().isoformat()

with open(ledger_path, "w") as f:
    json.dump(ledger, f, indent=2)

print(f"[refresh_revenue] OK — bookings={zv['bookings_confirmed']}, inquiries={zv['inquiries']}, recent_bookings={zv['recent_bookings']}")
PY
