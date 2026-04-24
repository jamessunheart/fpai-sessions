#!/usr/bin/env bash
#
# Create the Sunheart Brain workspace owner via GoTrue's admin API, then log in
# once to trigger AppFlowy's user + workspace auto-provisioning. Writes the
# resulting workspace_id back into brain.env.
#
# This is the exact pattern from docs/zen-village/deploy_log.yaml phase-3b,
# kept here so sh-brain is self-contained.

set -euo pipefail

SECRETS=/root/sh-brain-secrets/brain.env
[ -f "$SECRETS" ] || { echo "missing $SECRETS — run bootstrap.sh first"; exit 1; }
# shellcheck disable=SC1090
set -a; source "$SECRETS"; set +a

BASE="$APPFLOWY_BASE_URL"

# Look up an existing admin JWT from the gotrue container. We use the admin
# password from the env as the shared-secret flow.
GOTRUE_ADMIN_TOKEN=$(curl -fsS \
  -X POST "$BASE/gotrue/token?grant_type=password" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$GOTRUE_ADMIN_EMAIL\",\"password\":\"$GOTRUE_ADMIN_PASSWORD\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

echo "→ creating owner $SH_OWNER_EMAIL via /gotrue/admin/users"
curl -fsS \
  -X POST "$BASE/gotrue/admin/users" \
  -H "Authorization: Bearer $GOTRUE_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$SH_OWNER_EMAIL\",\"password\":\"$SH_OWNER_PASSWORD\",\"email_confirm\":true}" \
  >/dev/null || echo "(user may already exist — continuing)"

echo "→ logging in to trigger af_user/af_workspace auto-provision"
OWNER_TOKEN=$(curl -fsS \
  -X POST "$BASE/gotrue/token?grant_type=password" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$SH_OWNER_EMAIL\",\"password\":\"$SH_OWNER_PASSWORD\"}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["access_token"])')

curl -fsS "$BASE/api/user/verify" -H "Authorization: Bearer $OWNER_TOKEN" >/dev/null

echo "→ fetching workspace_id"
WS_JSON=$(curl -fsS "$BASE/api/workspace" -H "Authorization: Bearer $OWNER_TOKEN")
WS_ID=$(echo "$WS_JSON" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["data"][0]["workspace_id"])')

echo "→ renaming workspace to 'Sunheart Brain'"
curl -fsS -X PATCH "$BASE/api/workspace/$WS_ID" \
  -H "Authorization: Bearer $OWNER_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"workspace_name":"Sunheart Brain"}' >/dev/null || true

# Persist workspace_id into brain.env (idempotent).
if grep -q '^SH_WORKSPACE_ID=' "$SECRETS"; then
  sed -i "s|^SH_WORKSPACE_ID=.*$|SH_WORKSPACE_ID=$WS_ID|" "$SECRETS"
else
  echo "SH_WORKSPACE_ID=$WS_ID" >> "$SECRETS"
fi

echo "✓ done"
echo "   SH_WORKSPACE_ID=$WS_ID written to $SECRETS"
