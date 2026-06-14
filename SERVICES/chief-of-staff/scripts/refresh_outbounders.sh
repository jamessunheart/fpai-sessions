#!/usr/bin/env bash
# Pull live Outbounders revenue from MariaDB on the legacy droplet.
# Updates ledger.json revenue_monthly.outbounders with txn counts + recent revenue.
set -euo pipefail

OB_HOST="${OB_HOST:-209.74.93.72}"
HERE="$(cd "$(dirname "$0")" && pwd)"
COCKPIT_ROOT="$(cd "${HERE}/../../.." && pwd)"
LEDGER="${COCKPIT_ROOT}/core/STATE/ledger.json"

# Use SSH heredoc → remote bash → mysql with stdin SQL.
# The single-quoted SSH heredoc prevents local var expansion of $.
OUT=$(ssh -o ConnectTimeout=5 "root@${OB_HOST}" 'bash -s' 2>/dev/null <<'REMOTE' || echo ""
mysql -u obapp_user -p'G9$1I_a4-KNu!rE.' obapp_outbounders -BN 2>/dev/null <<'SQL'
SELECT
  (SELECT COUNT(*) FROM main_transaction WHERE deleted='N') AS lifetime_txns,
  (SELECT ROUND(SUM(credits),2) FROM main_transaction WHERE deleted='N') AS lifetime_revenue_usd,
  (SELECT COUNT(*) FROM main_transaction WHERE deleted='N' AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS last30d_txns,
  (SELECT ROUND(SUM(credits),2) FROM main_transaction WHERE deleted='N' AND transaction_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)) AS last30d_revenue_usd,
  (SELECT ROUND(AVG(monthly_total),2) FROM (
     SELECT SUM(credits) AS monthly_total
     FROM main_transaction
     WHERE deleted='N' AND transaction_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
     GROUP BY DATE_FORMAT(transaction_date, '%Y-%m')
   ) m) AS avg_monthly_revenue_6mo;
SQL
REMOTE
)

if [[ -z "${OUT}" ]]; then
    echo "[refresh_outbounders] WARN: could not query MariaDB on ${OB_HOST}; ledger unchanged" >&2
    exit 0
fi

read -r LIFE_TXNS LIFE_REV LAST30_TXNS LAST30_REV AVG_6MO <<< "${OUT}"

python3 - "${LEDGER}" "${LIFE_TXNS}" "${LIFE_REV}" "${LAST30_TXNS}" "${LAST30_REV}" "${AVG_6MO}" <<'PY'
import json, sys
from datetime import datetime, timezone

ledger_path, life_txns, life_rev, last30_txns, last30_rev, avg_6mo = sys.argv[1:]

with open(ledger_path) as f:
    ledger = json.load(f)

ob = ledger.setdefault("revenue_monthly", {}).setdefault("outbounders", {})
ob["revenue_usd"] = float(avg_6mo)
ob["last30d_revenue_usd"] = float(last30_rev)
ob["last30d_txns"] = int(last30_txns)
ob["lifetime_txns"] = int(life_txns)
ob["lifetime_revenue_usd"] = float(life_rev)
ob["activity_summary"] = f"{int(last30_txns)} txns last 30d · {int(life_txns):,} lifetime · ${float(life_rev):,.0f} cumulative"
ob["as_of"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
ob["source"] = "obapp_outbounders.main_transaction (credits, deleted='N')"
ob["_note"] = f"6-month avg: ${float(avg_6mo):,.0f}/mo. Last 30d: ${float(last30_rev):,.0f}."

ledger["last_updated"] = datetime.now(timezone.utc).date().isoformat()

with open(ledger_path, "w") as f:
    json.dump(ledger, f, indent=2)

print(f"[refresh_outbounders] OK — 30d=${float(last30_rev):,.0f} ({int(last30_txns)} txns) · 6mo avg=${float(avg_6mo):,.0f}/mo · lifetime ${float(life_rev):,.0f}")
PY
