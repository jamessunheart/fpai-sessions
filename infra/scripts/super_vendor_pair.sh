#!/usr/bin/env bash
# Pair the Super Agent's WhatsApp voice (vendor_bot) via Evolution API on 198.
# One run: creates the super-vendor instance (idempotent), fetches a fresh QR,
# saves it to ~/Desktop/super-vendor-qr.png, and opens it.
# James: scan it with WhatsApp (Linked Devices → Link a Device) on the phone
# whose number will be the Super Agent's voice. ~2 minutes total.
set -euo pipefail

HOST=root@198.54.123.234
EVO=http://localhost:8081
INSTANCE=super-vendor
OUT="$HOME/Desktop/super-vendor-qr.png"

KEY=$(ssh "$HOST" 'docker exec zv-evolution-api printenv AUTHENTICATION_API_KEY')

# Create instance if missing (409/403 on exists is fine)
ssh "$HOST" "curl -s -X POST $EVO/instance/create -H 'apikey: $KEY' -H 'Content-Type: application/json' -d '{\"instanceName\":\"$INSTANCE\",\"integration\":\"WHATSAPP-BAILEYS\"}'" >/dev/null || true

# Fetch fresh QR (base64 PNG)
B64=$(ssh "$HOST" "curl -s $EVO/instance/connect/$INSTANCE -H 'apikey: $KEY'" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("base64","").split(",")[-1])')

if [ -z "$B64" ]; then
  echo "No QR returned — instance may already be connected. State:"
  ssh "$HOST" "curl -s $EVO/instance/connectionState/$INSTANCE -H 'apikey: $KEY'"
  exit 0
fi

echo "$B64" | base64 -d > "$OUT"
echo "QR saved: $OUT — scan within ~40s (rerun this script for a fresh one)."
open "$OUT" 2>/dev/null || true
