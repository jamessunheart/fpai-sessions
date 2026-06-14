#!/usr/bin/env bash
# outbounders_revenue_pull.sh — live revenue snapshot from obapp_outbounders DB
# Usage: ./tools/outbounders_revenue_pull.sh
# Writes both stdout summary + machine-readable JSON snapshot to
#   ~/.config/fpai/outbounders/snapshot_<ts>.json (per treasury SSOT pattern)
#
# Reads obapp_outbounders on 209.74.93.72 as root (creds in /root/.my.cnf there).
# Read-only: NO writes against the live app DB.

set -euo pipefail

SERVER="root@209.74.93.72"
SNAPSHOT_DIR="$HOME/.config/fpai/outbounders"
mkdir -p "$SNAPSHOT_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
SNAPSHOT="$SNAPSHOT_DIR/snapshot_$TS.json"
LATEST="$SNAPSHOT_DIR/latest.json"

# Single SSH session pulling all metrics via TSV
read_metrics() {
  ssh -o BatchMode=yes -o ConnectTimeout=10 "$SERVER" 'mysql obapp_outbounders -B -N -e "
SELECT
  (SELECT ROUND(SUM(credits),2) FROM main_transaction WHERE deleted=\"N\" AND transaction_date >= NOW() - INTERVAL 30 DAY) AS deposits_30d,
  (SELECT ROUND(SUM(debits),2)  FROM main_transaction WHERE deleted=\"N\" AND transaction_date >= NOW() - INTERVAL 30 DAY) AS debits_30d,
  (SELECT COUNT(DISTINCT client_id) FROM main_transaction WHERE deleted=\"N\" AND transaction_date >= NOW() - INTERVAL 30 DAY) AS active_clients_30d,
  (SELECT ROUND(SUM(amount),2)  FROM agent_payment WHERE date_created >= NOW() - INTERVAL 30 DAY) AS agent_payouts_30d,
  (SELECT COUNT(*)              FROM agent_payment WHERE date_created >= NOW() - INTERVAL 30 DAY) AS agent_payments_n_30d,
  (SELECT COUNT(*)              FROM membership_payroll_fee WHERE status=\"A\") AS active_payroll_fees,
  (SELECT ROUND(SUM(amount),2)  FROM membership_payroll_fee WHERE status=\"A\") AS active_payroll_fees_total,
  (SELECT COUNT(*)              FROM membership WHERE status=\"A\" AND subscription_end >= CURDATE()) AS active_memberships,
  (SELECT COUNT(*)              FROM main_users) AS total_users_lifetime,
  (SELECT COUNT(*)              FROM main_users WHERE date_created >= NOW() - INTERVAL 30 DAY) AS new_users_30d
;"' 2>&1 | grep -vE "WARNING|post-quantum|store now|may need|openssh.com|insecure"
}

VALUES="$(read_metrics)"
IFS=$'\t' read -r DEPOSITS DEBITS ACTIVE_CLIENTS AGENT_PAYOUTS AGENT_N PAYROLL_FEES_N PAYROLL_FEES_TOTAL ACTIVE_MEMS TOTAL_USERS NEW_USERS_30D <<< "$VALUES"

cat > "$SNAPSHOT" <<EOF
{
  "snapshot_at": "$TS",
  "source": "obapp_outbounders @ 209.74.93.72",
  "windows": {
    "deposits_30d": ${DEPOSITS:-0},
    "debits_30d": ${DEBITS:-0},
    "active_paying_clients_30d": ${ACTIVE_CLIENTS:-0},
    "agent_payouts_30d_total": ${AGENT_PAYOUTS:-0},
    "agent_payments_count_30d": ${AGENT_N:-0},
    "new_signups_30d": ${NEW_USERS_30D:-0}
  },
  "subscriptions": {
    "active_memberships": ${ACTIVE_MEMS:-0},
    "active_payroll_fees_count": ${PAYROLL_FEES_N:-0},
    "active_payroll_fees_total": ${PAYROLL_FEES_TOTAL:-0}
  },
  "users": {
    "total_lifetime": ${TOTAL_USERS:-0}
  },
  "notes": [
    "Real active client float is approximately \$0 (settles to zero each cycle).",
    "Old ledger ghosts from 2013-2018 sum to ~\$2.24M but are not real money.",
    "main_invoice table is dead since 2014 - do not use as revenue source."
  ]
}
EOF

cp "$SNAPSHOT" "$LATEST"

echo "=== Outbounders snapshot $TS ==="
cat "$SNAPSHOT" | python3 -m json.tool 2>/dev/null || cat "$SNAPSHOT"
echo
echo "Latest: $LATEST"
echo "Archive: $SNAPSHOT"
