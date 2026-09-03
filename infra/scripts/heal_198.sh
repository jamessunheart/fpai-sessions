#!/usr/bin/env bash
# Heal 198 after a wedge/reboot: re-add runtime-only iptables rules, restart the SUPER stack, verify.
# Safe to run repeatedly. Run automatically by watch_198.sh when ssh recovers.
set -uo pipefail
H=root@198.54.123.234
ssh -o ConnectTimeout=15 "$H" '
  echo "== uptime/load =="; uptime
  # runtime-only firewall rules (vanish on reboot — the known trap)
  iptables -C INPUT -s 172.17.0.0/16 -p tcp --dport 5432 -j ACCEPT 2>/dev/null || iptables -I INPUT 3 -s 172.17.0.0/16 -p tcp --dport 5432 -j ACCEPT
  iptables -C INPUT -s 172.17.0.0/16 -p tcp --dport 6379 -j ACCEPT 2>/dev/null || iptables -I INPUT 3 -s 172.17.0.0/16 -p tcp --dport 6379 -j ACCEPT
  iptables -C INPUT -s 172.17.0.0/16 -p tcp --dport 8790 -j ACCEPT 2>/dev/null || iptables -I INPUT 3 -s 172.17.0.0/16 -p tcp --dport 8790 -j ACCEPT
  echo "firewall: runtime rules present"
  docker start zv-redis 2>/dev/null; docker start zv-evolution-api 2>/dev/null
  systemctl restart super-vendor-bot fpai-fp-index 2>/dev/null
  sleep 6
  echo "== health =="
  systemctl is-active super-vendor-bot fpai-fp-index
  KEY=$(docker exec zv-evolution-api printenv AUTHENTICATION_API_KEY 2>/dev/null)
  curl -s http://localhost:8081/instance/connectionState/super-vendor -H "apikey: $KEY" 2>/dev/null
  echo; tail -2 /opt/VENDOR_LOG.md 2>/dev/null
  echo "== biggest cpu/mem =="; ps aux --sort=-%cpu | head -4
'
