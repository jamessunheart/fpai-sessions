#!/usr/bin/env bash
# feed_decision — the canonical "system needs James's call" entry point.
# Routes ONE decision into James's one chat (server 162 = SSOT) as a Decision Card,
# then surfaces it (skips the send if another decision is already awaiting — one at a time).
# Anything (recursive_improver, build_orchestrator, Ember) calls THIS to reach James.
#
# Usage:
#   feed_decision.sh "<question>" "<opt1|opt2|...>" [why] [recommendation] [risk] [attention]
# Env: BRAIN_HOST (default root@162.0.208.88), FEED_NO_SURFACE=1 to add-without-surfacing.
set -euo pipefail
Q="${1:?question required}"; OPTS="${2:-}"
WHY="${3:-}"; REC="${4:-}"; RISK="${5:-}"; ATTN="${6:-}"
HOST="${BRAIN_HOST:-root@162.0.208.88}"

# Build one JSON line (card fields only included when non-empty) — python avoids all quoting hazards.
JSON=$(python3 - "$Q" "$OPTS" "$WHY" "$REC" "$RISK" "$ATTN" <<'PY'
import json, sys
q, o, why, rec, risk, attn = sys.argv[1:7]
card = {}
if why:  card["why_surfaced"] = why
if rec:  card["recommendation"] = rec
if risk: card["risk_class"] = risk
if attn: card["attention_cost"] = attn
row = {"question": q, "options": o}
if card: row["card"] = card
print(json.dumps(row))
PY
)

REMOTE='ENVFILE=$(systemctl show sh-brain-tgbot -p EnvironmentFiles 2>/dev/null | sed -E "s/EnvironmentFiles=//; s/ .*//"); cd /opt/sh-brain-src && set -a; . "$ENVFILE" 2>/dev/null; set +a; PY=./.venv/bin/python; '
if [ "${FEED_NO_SURFACE:-0}" = "1" ]; then
  printf '%s\n' "$JSON" | ssh -o BatchMode=yes -o ConnectTimeout=20 "$HOST" "$REMOTE \$PY -m curator.decisions seed"
else
  printf '%s\n' "$JSON" | ssh -o BatchMode=yes -o ConnectTimeout=20 "$HOST" "$REMOTE \$PY -m curator.decisions seed && \$PY -m curator.decisions surface"
fi
