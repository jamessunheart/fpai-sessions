#!/usr/bin/env bash
# Start the Super Agent's WhatsApp voice on 198 (post-pairing).
# Points the Evolution webhook at vendor_bot and runs the bot. Idempotent.
set -uo pipefail
ssh root@198.54.123.234 '
  KEY=$(docker exec zv-evolution-api printenv AUTHENTICATION_API_KEY)
  curl -s -X POST http://localhost:8081/webhook/set/super-vendor -H "apikey: $KEY" -H "Content-Type: application/json" \
    -d "{\"webhook\":{\"enabled\":true,\"url\":\"http://host.docker.internal:8790/webhook\",\"events\":[\"MESSAGES_UPSERT\"]}}" >/dev/null && echo "webhook: set"
  iptables -C INPUT -s 172.17.0.0/16 -p tcp --dport 8790 -j ACCEPT 2>/dev/null || iptables -I INPUT 3 -s 172.17.0.0/16 -p tcp --dport 8790 -j ACCEPT
  echo "iptables: 8790 open to docker subnet (runtime-only)"
  pkill -f super_vendor_bot.py 2>/dev/null
  pip3 list 2>/dev/null | grep -qi flask || pip3 install -q flask requests
  cd /opt/fpai && EVO_URL=http://localhost:8081 EVO_APIKEY=$KEY EVO_INSTANCE=super-vendor WA_TRANSPORT=evolution PORT=8790 \
    nohup python3 super_vendor_bot.py serve >/opt/fpai/super_vendor_bot.log 2>&1 &
  sleep 3
  curl -s -o /dev/null -w "bot health: %{http_code}\n" "http://localhost:8790/webhook?hub.verify_token=super&hub.challenge=ok"
  tail -2 /opt/fpai/super_vendor_bot.log
'
echo "Voice is live if 'bot health: 200' above. Bot sends NOTHING until a consented start command."
