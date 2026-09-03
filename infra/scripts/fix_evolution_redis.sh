#!/usr/bin/env bash
# Fix Evolution pairing failure: Redis unreachable from the container (bound 127.0.0.1 only).
# Rebinds a Redis container to the docker gateway, opens the port, restarts Evolution,
# then reopens a fresh QR locally. Same class of fix as this morning's Postgres/iptables wall.
set -uo pipefail
ssh root@198.54.123.234 '
  docker rm -f zv-redis >/dev/null 2>&1
  docker run -d --name zv-redis --restart unless-stopped -p 172.17.0.1:6379:6379 redis:7-alpine >/dev/null && echo "redis: up on docker gateway"
  iptables -I INPUT -s 172.17.0.0/16 -p tcp --dport 6379 -j ACCEPT && echo "iptables: 6379 open to docker subnet (runtime-only — re-add after reboot)"
  sleep 2
  docker restart zv-evolution-api >/dev/null && echo "evolution: restarted"
  sleep 8
  docker logs zv-evolution-api --since 10s 2>&1 | grep -ci "redis disconnected" | xargs -I{} echo "redis-disconnected errors in last 10s: {}"
'
bash /Users/jamessunheart/FullPotentialOS/infra/scripts/super_vendor_qr_watch.sh >/tmp/qr_watch.log 2>&1 &
sleep 3; open "$HOME/Desktop/super-vendor-qr.html"
echo "Fresh QR on screen — scan from WhatsApp → Linked Devices."
