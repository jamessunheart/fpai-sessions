#!/usr/bin/env bash
# Start the Super Agent's WhatsApp voice on 198 as a systemd service (survives ssh + reboot).
# NOTE (James decided 2026-09-03): the paired number is JAMES'S OWN WhatsApp — so every
# bot message is James speaking. Bot stays silent until a consented `start`; each `start`
# is James's explicit per-conversation approval on his own line.
set -uo pipefail
ssh root@198.54.123.234 '
  KEY=$(docker exec zv-evolution-api printenv AUTHENTICATION_API_KEY)
  curl -s -X POST http://localhost:8081/webhook/set/super-vendor -H "apikey: $KEY" -H "Content-Type: application/json" \
    -d "{\"webhook\":{\"enabled\":true,\"url\":\"http://host.docker.internal:8790/webhook\",\"events\":[\"MESSAGES_UPSERT\"]}}" >/dev/null && echo "webhook: set"
  iptables -C INPUT -s 172.17.0.0/16 -p tcp --dport 8790 -j ACCEPT 2>/dev/null || iptables -I INPUT 3 -s 172.17.0.0/16 -p tcp --dport 8790 -j ACCEPT
  echo "iptables: 8790 open (runtime-only)"
  cat > /etc/systemd/system/super-vendor-bot.service <<EOF
[Unit]
Description=SUPER vendor bot (WhatsApp voice via Evolution)
After=network.target docker.service
[Service]
WorkingDirectory=/opt/fpai
Environment=EVO_URL=http://localhost:8081
Environment=EVO_APIKEY=$KEY
Environment=EVO_INSTANCE=super-vendor
Environment=WA_TRANSPORT=evolution
Environment=PORT=8790
ExecStart=/usr/bin/python3 /opt/fpai/super_vendor_bot.py serve
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload && systemctl enable --now super-vendor-bot >/dev/null 2>&1
  sleep 3
  systemctl is-active super-vendor-bot
  curl -s -o /dev/null -w "bot health: %{http_code}\n" "http://localhost:8790/webhook?hub.verify_token=super&hub.challenge=ok"
'
echo "Success = 'active' + 'bot health: 200'. Bot sends NOTHING until a consented start."
