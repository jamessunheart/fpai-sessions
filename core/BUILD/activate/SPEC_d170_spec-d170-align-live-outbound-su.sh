#!/usr/bin/env bash
# Align live outbound surfaces to BBB v1.4 after review/merge.
set -euo pipefail

REPO="${FPAI_REPO:-/opt/fpai-build/FPAI_Cockpit}"
SITE_SRC="$REPO/sites/fullpotential-com/index.html"
SITE_ROOT="${FULLPOTENTIAL_SITE_ROOT:-/opt/fpai/core/applications/website-ai/frontend/fullpotential-com}"
GUIDE_LIVE="${FPAI_GUIDE_SERVICE_FILE:-/opt/fpai/guide/guide_service.py}"
GUIDE_SERVICE="${FPAI_GUIDE_SERVICE:-fp-guide.service}"
INTAKE_SRC="$REPO/deploy-tools/intake-agent.py"
INTAKE_LIVE="${FPAI_INTAKE_AGENT_FILE:-/opt/fpai/leads/intake-agent.py}"
INTAKE_SERVICE="${FPAI_INTAKE_SERVICE:-intake-agent.service}"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_DIR="${FPAI_D170_BACKUP_DIR:-/opt/fpai-build/deploy-backups/d170-bbb-$STAMP}"

echo "[d170] activating BBB v1.4 outbound-surface alignment"

if [[ ! -f "$SITE_SRC" ]]; then
  echo "[d170] missing reviewed homepage source: $SITE_SRC" >&2
  exit 1
fi
if [[ ! -f "$INTAKE_SRC" ]]; then
  echo "[d170] missing reviewed intake source: $INTAKE_SRC" >&2
  exit 1
fi

python3 -m py_compile "$INTAKE_SRC"
mkdir -p "$BACKUP_DIR"

if [[ -d "$SITE_ROOT" ]]; then
  if [[ -f "$SITE_ROOT/index.html" ]]; then
    cp -p "$SITE_ROOT/index.html" "$BACKUP_DIR/fullpotential-index.html"
  fi
  install -m 0644 "$SITE_SRC" "$SITE_ROOT/index.html"
  echo "[d170] installed homepage: $SITE_ROOT/index.html"
else
  echo "[d170] site root not present on this host, skipped homepage install: $SITE_ROOT"
fi

if [[ -f "$INTAKE_LIVE" ]]; then
  cp -p "$INTAKE_LIVE" "$BACKUP_DIR/intake-agent.py"
  install -m 0755 "$INTAKE_SRC" "$INTAKE_LIVE"
  python3 -m py_compile "$INTAKE_LIVE"
  echo "[d170] installed intake agent: $INTAKE_LIVE"
else
  echo "[d170] intake agent not present on this host, skipped: $INTAKE_LIVE"
fi

if [[ -f "$GUIDE_LIVE" ]]; then
  cp -p "$GUIDE_LIVE" "$BACKUP_DIR/guide_service.py"
  python3 - "$GUIDE_LIVE" <<'PY'
from __future__ import annotations

import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
prompt = '''SYSTEM = """You are the warm Full Potential guide for fullpotential.com.

Primary route: offer the Free Full Potential Assessment first. It gives the person or organization an Allocation Score and their three highest-value opportunities within 48 hours.

If they ask for the paid path, explain the ladder clearly: Assessment -> Blueprint ($2,500) -> Savings Split (25% of verified savings) -> Partnership ($2-5k/mo).

Do not lead with the Game, WPA, Character Card, manual outreach, or a generic discovery call. Those can be mentioned only when directly relevant after the Assessment route is clear.

Keep replies concise, humane, and practical. Ask one useful question when more context is needed, and route the next step to https://fullpotential.com/assessment.
"""'''

pattern = re.compile(r"(?ms)^SYSTEM\s*=\s*(?P<quote>'''|\"\"\").*?(?P=quote)")
new, count = pattern.subn(prompt, text, count=1)
if count != 1:
    raise SystemExit("could not find a top-level SYSTEM triple-quoted prompt")
path.write_text(new, encoding="utf-8")
PY
  python3 -m py_compile "$GUIDE_LIVE"
  echo "[d170] patched guide prompt: $GUIDE_LIVE"
else
  echo "[d170] guide service file not present on this host, skipped: $GUIDE_LIVE"
fi

if command -v systemctl >/dev/null 2>&1; then
  systemctl daemon-reload
  if [[ -f "$GUIDE_LIVE" ]]; then
    systemctl restart "$GUIDE_SERVICE"
    sleep 2
    systemctl is-active --quiet "$GUIDE_SERVICE"
    echo "[d170] restarted $GUIDE_SERVICE"
  fi
  if [[ -f "$INTAKE_LIVE" ]]; then
    systemctl restart "$INTAKE_SERVICE"
    sleep 2
    systemctl is-active --quiet "$INTAKE_SERVICE"
    echo "[d170] restarted $INTAKE_SERVICE"
  fi
else
  echo "[d170] systemctl unavailable; installed files only"
fi

echo "[d170] backup: $BACKUP_DIR"
echo "[d170] rollback homepage: cp -p $BACKUP_DIR/fullpotential-index.html $SITE_ROOT/index.html"
echo "[d170] rollback guide: cp -p $BACKUP_DIR/guide_service.py $GUIDE_LIVE && systemctl restart $GUIDE_SERVICE"
echo "[d170] rollback intake: cp -p $BACKUP_DIR/intake-agent.py $INTAKE_LIVE && systemctl restart $INTAKE_SERVICE"
echo "[d170] verify: curl -fsSL https://fullpotential.com/ | grep -F 'Start the Free Assessment'"
