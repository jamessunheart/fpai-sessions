#!/bin/bash
# Warn James on Telegram when any Brain Mesh bearer token expires within N days.
set -euo pipefail

export BRAIN_MESH_POLICY_FILE="${BRAIN_MESH_POLICY_FILE:-/etc/brain-mesh/policy.json}"
export BRAIN_MESH_EXPIRY_WARN_DAYS="${BRAIN_MESH_EXPIRY_WARN_DAYS:-14}"
export BRAIN_MESH_EXPIRY_STATE="${BRAIN_MESH_EXPIRY_STATE:-/opt/fpai/logs/.brain-mesh-token-expiry-alert}"
export BRAIN_MESH_EXPIRY_LOG="${BRAIN_MESH_EXPIRY_LOG:-/opt/fpai/logs/adam_daily_value.log}"

if [ ! -r "$BRAIN_MESH_POLICY_FILE" ]; then
  echo "[brain-mesh-expiry] skip: cannot read $BRAIN_MESH_POLICY_FILE" >>"$BRAIN_MESH_EXPIRY_LOG"
  exit 0
fi

python3 <<'PY'
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

policy_path = os.environ["BRAIN_MESH_POLICY_FILE"]
warn_days = int(os.environ.get("BRAIN_MESH_EXPIRY_WARN_DAYS", "14"))
state_path = os.environ["BRAIN_MESH_EXPIRY_STATE"]
log_append = os.environ["BRAIN_MESH_EXPIRY_LOG"]

with open(policy_path, encoding="utf-8") as f:
    policy = json.load(f)

now = datetime.now(timezone.utc)
soon: list[tuple[str, str, float]] = []
for _tok, meta in policy.get("tokens", {}).items():
    exp = meta.get("expires_at")
    uid = str(meta.get("user_id") or meta.get("role") or "token")
    if not exp:
        continue
    try:
        dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
    except ValueError:
        continue
    days_left = (dt - now).total_seconds() / 86400.0
    if 0 < days_left <= warn_days:
        soon.append((uid, str(exp), days_left))

if not soon:
    with open(log_append, "a", encoding="utf-8") as lg:
        lg.write(f"[brain-mesh-expiry] {now.isoformat()} no token expiring within {warn_days}d\n")
    sys.exit(0)

today = now.strftime("%Y-%m-%d")
sent: dict[str, str] = {}
if os.path.isfile(state_path):
    try:
        with open(state_path, encoding="utf-8") as sf:
            sent = json.load(sf)
    except json.JSONDecodeError:
        sent = {}

pending: list[tuple[str, str, float]] = []
for uid, exp, dleft in sorted(soon, key=lambda x: x[2]):
    key = f"{uid}|{exp}"
    if sent.get(key) == today:
        continue
    pending.append((uid, exp, dleft))

if not pending:
    with open(log_append, "a", encoding="utf-8") as lg:
        lg.write(f"[brain-mesh-expiry] {now.isoformat()} already notified today\n")
    sys.exit(0)

lines = [f"• {uid}: expires {exp} (~{int(dleft)}d left)" for uid, exp, dleft in pending]
msg = (
    "⚠️ Brain Mesh token expiry\n"
    + "\n".join(lines)
    + f"\n\nRotate in /etc/brain-mesh/policy.json (warn window: {warn_days}d)."
)


def _telegram_token() -> str:
    with open("/root/.openclaw/openclaw.json", encoding="utf-8") as f:
        data = json.load(f)

    def find(o: object) -> str | None:
        if isinstance(o, dict):
            for k, v in o.items():
                if "telegram" in k.lower() and isinstance(v, dict):
                    t = v.get("botToken") or v.get("token") or v.get("key")
                    if t:
                        return str(t)
                r = find(v)
                if r:
                    return r
        elif isinstance(o, list):
            for i in o:
                r = find(i)
                if r:
                    return r
        return None

    return find(data) or ""


def _chat_id() -> str:
    chat = "8514069423"
    try:
        with open("/opt/fpai/cora-loop/.env", encoding="utf-8") as ef:
            for line in ef:
                if line.startswith("TELEGRAM_CHAT_ID="):
                    return line.strip().split("=", 1)[1]
    except OSError:
        pass
    return chat


tg = _telegram_token()
chat = _chat_id()
if not tg:
    with open(log_append, "a", encoding="utf-8") as lg:
        lg.write("[brain-mesh-expiry] missing telegram bot token — not sending\n")
    sys.exit(0)

data = urllib.parse.urlencode({"chat_id": chat, "text": msg}).encode()
req = urllib.request.Request(
    f"https://api.telegram.org/bot{tg}/sendMessage",
    data=data,
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
try:
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode())
        if not body.get("ok"):
            raise RuntimeError(body)
except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError) as exc:
    with open(log_append, "a", encoding="utf-8") as lg:
        lg.write(f"[brain-mesh-expiry] telegram send failed: {exc}\n")
    sys.exit(1)

for uid, exp, _ in pending:
    sent[f"{uid}|{exp}"] = today

with open(state_path, "w", encoding="utf-8") as sf:
    json.dump(sent, sf, indent=0)

with open(log_append, "a", encoding="utf-8") as lg:
    lg.write(f"[brain-mesh-expiry] {now.isoformat()} notified for {len(pending)} token(s)\n")
PY
