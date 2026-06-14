#!/bin/bash
# Read-only inventory for primary / legacy host. Safe to run anytime.
# Usage: on server: bash primary-legacy-readonly-audit.sh
#        from laptop: ssh root@198.54.123.234 'bash -s' < primary-legacy-readonly-audit.sh
set +e

echo "# Primary legacy server — read-only audit"
echo ""
echo "**Host:** \`$(hostname -f 2>/dev/null || hostname)\` · **When (UTC):** $(date -u +"%Y-%m-%d %H:%M UTC")"
echo ""
echo "## 1. Identity & resources"
echo "\`\`\`"
echo "Kernel: $(uname -r)"
echo "Uptime: $(uptime -p 2>/dev/null || uptime)"
grep -m1 -i "model name" /proc/cpuinfo 2>/dev/null
grep -m1 "^cpu(s)" /proc/cpuinfo 2>/dev/null || grep -m1 "^processor" /proc/cpuinfo 2>/dev/null
grep MemTotal /proc/meminfo
echo "\`\`\`"
echo ""
echo "## 2. Disk (top pressure)"
echo "\`\`\`"
df -hT | sed -n '1,16p'
echo "\`\`\`"
echo ""
echo "### Largest under /opt/fpai (depth aggregate, top 15)"
echo "\`\`\`"
du -x --max-depth=2 /opt/fpai 2>/dev/null | sort -rn | head -15
echo "\`\`\`"
echo ""
echo "## 3. Listening TCP"
echo "\`\`\`"
ss -tlnp 2>/dev/null | head -70
echo "\`\`\`"
echo ""
echo "## 4. systemd — failed"
echo "\`\`\`"
systemctl --failed --no-legend 2>/dev/null | head -50
fc=$(systemctl list-units --state=failed --no-legend 2>/dev/null | wc -l | tr -d ' ')
echo "failed-unit-count: ${fc:-0}"
echo "\`\`\`"
echo ""
echo "## 5. Running services (filtered)"
echo "\`\`\`"
systemctl list-units --type=service --state=running --no-legend 2>/dev/null | grep -iE 'fpai|nginx|docker|postgres|redis|mysql|mongo|traefik|caddy|certbot' | head -50
echo "\`\`\`"
echo ""
echo "## 6. Docker"
echo "\`\`\`"
if command -v docker >/dev/null 2>&1; then
  docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | head -35
else
  echo "docker not installed or not on PATH"
fi
echo "\`\`\`"
echo ""
echo "## 7. Cron"
echo "\`\`\`"
echo "### root crontab"
crontab -l 2>/dev/null | head -60 || echo "(none)"
echo ""
echo "### /etc/cron.d (filenames)"
ls -la /etc/cron.d 2>/dev/null | head -30
echo "\`\`\`"
echo ""
echo "## 8. Journal errors (tail, last 7d)"
echo "\`\`\`"
journalctl -p err -S -7d --no-pager 2>/dev/null | tail -35
echo "\`\`\`"
echo ""
echo "## 9. Security spot checks (read-only)"
echo "\`\`\`"
echo "### .env under /opt/fpai, perm != 600"
find /opt/fpai -maxdepth 7 \( -path '*/node_modules/*' -o -path '*/.git/*' -o -path '*/venv/*' \) -prune -o -name '.env' -type f ! -perm 600 -print 2>/dev/null | head -40
echo ""
echo "### world-writable files under /opt/fpai (sample)"
find /opt/fpai -type f -perm -0002 2>/dev/null | head -25
echo "\`\`\`"
echo ""
echo "## 10. OOM / pressure (journal grep, 14d)"
echo "\`\`\`"
journalctl -S -14d --no-pager 2>/dev/null | grep -iE 'out of memory|oom-killer|killed process' | tail -20 || true
echo "\`\`\`"
echo ""
echo "## Adam — prioritize"
echo "1. Fix **failed systemd** units (reliability)."
echo "2. Reconcile **unexpected LISTEN** ports with SERVICE_REGISTRY intent."
echo "3. **Disk hogs** under /opt/fpai — log rotation / archives before incidents."
echo "4. **chmod 600** any secret .env files flagged above."
echo "5. **Cron** inventory: remove dead pollers / duplicate jobs (cost + noise)."
echo ""
echo "---"
echo "*Read-only audit; no changes were made on this host.*"
