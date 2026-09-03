#!/usr/bin/env bash
# Stop the four crash-looping zombie services on 198 that caused the load-160 wedge (2026-09-03).
# All four are in endless activating/auto-restart loops (not functioning). Reversible: systemctl enable --now <unit>.
ssh root@198.54.123.234 '
  for u in ad-portal fpai-aria fpai-level10-trader fpai-memory-dashboard; do
    systemctl stop "$u" 2>/dev/null; systemctl disable "$u" 2>/dev/null && echo "disabled: $u"
  done
  sleep 5; echo "--"; uptime
  systemctl is-active super-vendor-bot fpai-fp-index zv-evolution-api 2>/dev/null | head -3
'
