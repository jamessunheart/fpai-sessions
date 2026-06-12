#!/bin/bash
# security-watch.sh — Tier 2: inotify-based instant permission repair
# Watches secret-bearing trees; on write/create/attrib runs sentinel --quick.
set -uo pipefail

SENTINEL=/opt/fpai/openclaw/workspace/tools/security-sentinel.sh
LOG=/opt/fpai/logs/security-watch.log
LOCK=/run/security-watch.lock

mkdir -p /opt/fpai/logs
touch "$LOG" "$LOCK" || true
chmod 600 "$LOG" 2>/dev/null || true

# Prune noisy / huge subtrees under /opt/fpai (regex on full path)
EXCLUDE='(/node_modules/|/\.git/|/venv/|/\.venv/|/__pycache__/|/dist/|/build/|/\.next/|/Trash/)'

{
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") security-watch starting (inotify)"
  inotifywait -m -r \
    --exclude "$EXCLUDE" \
    -e close_write,create,moved_to,attrib \
    --format '%w%f' \
    /opt/fpai /root/.metaclaw /root/.openclaw /etc/zen-village \
  | while IFS= read -r path; do
      [ -n "${path:-}" ] || continue
      [ -f "$path" ] || continue
      case "$path" in
        *.env|*.json|*.yaml|*.yml|*.log) ;;
        *) continue ;;
      esac
      flock -n "$LOCK" timeout 12 "$SENTINEL" --quick "$path" || true
    done
} >>"$LOG" 2>&1
