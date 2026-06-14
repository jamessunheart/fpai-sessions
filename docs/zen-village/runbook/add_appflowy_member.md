# Adding a new AppFlowy member (bypassing the 1-seat cap)

AppFlowy Cloud self-hosted free build hard-caps workspace Members at 1. The `/invite` API and `/api/user/verify` both return code 1120 once you hit the cap. **This runbook bypasses the check via direct DB provisioning.** Only works on self-hosted; not applicable to AppFlowy's hosted cloud.

**Before you start:** confirm the person actually needs UI access. Telegram + Claude Desktop cover 95% of workflows without an AppFlowy seat. Skip this entire runbook if they don't.

---

## Recipe (copy/paste, 3 minutes)

SSH to `162.0.208.88` and run:

```bash
ssh root@162.0.208.88

# --- fill these in ---
NEW_EMAIL="teammate@example.com"
NEW_NAME="Firstname"
NEW_PW="AlphanumericOnlyNoSpecialChars20chars"   # NO !@#$ — bash history + shell quoting will mangle them
# ---------------------

GOTRUE_SECRET=$(docker exec appflowy-cloud-gotrue-1 env | grep ^GOTRUE_JWT_SECRET= | cut -d= -f2-)
export S="$GOTRUE_SECRET"
WORKSPACE_ID="3ca578c1-6a08-42d5-9f41-3b261787ace7"
NEW_UID=$(python3 -c "import time; print(int(time.time() * 1000) + 583887033164000000)")

ADMIN_JWT=$(python3 -c "
import jwt, time, os
print(jwt.encode({'role': 'supabase_admin', 'exp': int(time.time())+300}, os.environ['S'], algorithm='HS256'))
")

# 1) Create in gotrue (aud and role MUST be empty to match gotrue's configured audience)
cat > /tmp/new.json <<EOF
{"email":"$NEW_EMAIL","password":"$NEW_PW","email_confirm":true,"aud":"","role":""}
EOF
docker cp /tmp/new.json appflowy-cloud-gotrue-1:/tmp/new.json
RESP=$(docker exec appflowy-cloud-gotrue-1 sh -c "curl -sS -X POST http://localhost:9999/admin/users -H 'Authorization: Bearer $ADMIN_JWT' -H 'Content-Type: application/json' -d @/tmp/new.json")
NEW_ID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "Created uuid: $NEW_ID"

# If the aud/role still look wrong, force empty:
docker exec appflowy-cloud-postgres-1 psql -U postgres -d postgres \
  -c "UPDATE auth.users SET aud='', role='' WHERE id='$NEW_ID';"

# 2) Provision af_user + workspace membership (role_id=2 = Member, role_id=3 = Guest)
cat > /tmp/prov.sql <<SQL
INSERT INTO public.af_user (uid, uuid, email, password, name, metadata)
VALUES ($NEW_UID, '$NEW_ID'::uuid, '$NEW_EMAIL', '', '$NEW_NAME',
        '{"timezone": {"timezone": null, "default_timezone": "America/Costa_Rica"}}'::jsonb)
ON CONFLICT (uid) DO NOTHING;

INSERT INTO public.af_workspace_member (uid, role_id, workspace_id)
VALUES ($NEW_UID, 2, '$WORKSPACE_ID'::uuid)
ON CONFLICT (uid, workspace_id) DO NOTHING;
SQL
docker cp /tmp/prov.sql appflowy-cloud-postgres-1:/tmp/prov.sql
docker exec appflowy-cloud-postgres-1 psql -U postgres -d postgres -f /tmp/prov.sql

# 3) Flush permission cache (otherwise they show up as Guest for ~forever)
docker restart appflowy-cloud-appflowy_cloud-1
sleep 8

# 4) Verify
LOGIN=$(curl -sS -X POST "https://brain.zenvillagecr.com/gotrue/token?grant_type=password" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$NEW_EMAIL\",\"password\":\"$NEW_PW\"}")
TOKEN=$(echo "$LOGIN" | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
curl -sS "https://brain.zenvillagecr.com/api/workspace" -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

If workspace shows up with `role: Member` and `member_count` matches, you're done. Send the user their password via a secure channel (Signal, 1Password). Have them rotate on first login.

---

## Why this works

- The seat cap (`code 1120`) lives in two handlers: `POST /api/workspace/<id>/invite` and `POST /api/user/verify/<token>`. Skipping them via direct DB insert leaves no code path to trigger the check.
- `af_workspace_member` is the source of truth for access. `af_role_permissions` maps role_id to capability level.
- The permission enforcer inside `appflowy_cloud` loads role mappings into memory at startup and does **not** always listen for `af_workspace_member_change_trigger` notifications (not investigated thoroughly). A container restart is the reliable flush.
- Login requires `auth.users.aud=''` and `auth.users.role=''` on our instance because gotrue is configured with an empty expected audience. The `/admin/users` endpoint defaults to `aud=authenticated` which causes silent login failures.

## Known gotchas

- **Never put `!`, `$`, or backticks in passwords you set via bash/SSH** — history expansion and parameter substitution will mangle them silently, and the bcrypt hash saved in the DB will not match what you think you set. Alphanumeric + safe punctuation (`-`, `.`, `_`) only.
- **Always verify with a fresh curl login immediately** after provisioning. If gotrue returns `invalid_credentials`, the bcrypt hash in `auth.users.encrypted_password` usually does NOT match the intended password — a shell expansion bug.
- **Don't skip the `appflowy_cloud` restart** — the user will be `Member` in SQL but appear as `Guest` to the enforcer, producing confusing 1012 errors.

## Rollback / remove member

```bash
ssh root@162.0.208.88
# Replace email below
docker exec appflowy-cloud-postgres-1 psql -U postgres -d postgres <<SQL
DELETE FROM public.af_workspace_member
  WHERE uid = (SELECT uid FROM public.af_user WHERE email='teammate@example.com');
DELETE FROM public.af_user WHERE email='teammate@example.com';
DELETE FROM auth.users WHERE email='teammate@example.com';
SQL
docker restart appflowy-cloud-appflowy_cloud-1
```
