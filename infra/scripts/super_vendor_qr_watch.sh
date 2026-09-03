#!/usr/bin/env bash
# Keeps a FRESH pairing QR for the super-vendor WhatsApp instance on the Desktop.
# Refreshes every 25s until the instance connects. No 40-second race:
# open ~/Desktop/super-vendor-qr.html whenever ready — it auto-reloads.
set -uo pipefail

HOST=root@198.54.123.234
EVO=http://localhost:8081
INSTANCE=super-vendor
PNG="$HOME/Desktop/super-vendor-qr.png"
HTML="$HOME/Desktop/super-vendor-qr.html"

cat > "$HTML" <<'EOF'
<meta http-equiv="refresh" content="10">
<body style="background:#111;display:flex;flex-direction:column;align-items:center;justify-content:center;height:95vh;font-family:sans-serif;color:#eee">
<h2>Scan with WhatsApp &rarr; Linked Devices</h2>
<img src="super-vendor-qr.png" style="width:min(80vw,80vh)">
<p>Auto-refreshes &mdash; always fresh. Close after it says connected.</p>
</body>
EOF

KEY=$(ssh "$HOST" 'docker exec zv-evolution-api printenv AUTHENTICATION_API_KEY') || exit 1

for i in $(seq 1 120); do  # up to ~50 min
  STATE=$(ssh "$HOST" "curl -s $EVO/instance/connectionState/$INSTANCE -H 'apikey: $KEY'")
  if echo "$STATE" | grep -q '"open"'; then
    printf '<body style="background:#0a2;color:#fff;font-size:3em;text-align:center;padding-top:40vh">CONNECTED ✓</body>' > "$HTML"
    echo "CONNECTED"
    exit 0
  fi
  B64=$(ssh "$HOST" "curl -s $EVO/instance/connect/$INSTANCE -H 'apikey: $KEY'" \
    | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("base64","").split(",")[-1])
except Exception: pass')
  [ -n "$B64" ] && echo "$B64" | base64 -d > "$PNG" 2>/dev/null
  sleep 25
done
echo "TIMEOUT after 50 min — rerun when ready"
exit 1
