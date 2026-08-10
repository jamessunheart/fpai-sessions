# Outbounders Agent API v0

Sidecar FastAPI service that lets other AI systems programmatically search the
Outbounders talent pool and post jobs. Runs on 209.74.93.72 next to MariaDB
(localhost bind :8300), fronted by `api.outbounders.com` via Apache proxy.

Read-mostly. Only writes: `INSERT INTO client_job_posting` (jobs stay gated by
the legacy admin approval flow, `approved='N'`) and the new `api_keys` table.
Talent results are **anonymized** — never email/name/phone.

## Layout

```
app/main.py               FastAPI service
migrations/001_api_keys.sql   api_keys table + key-minting example
deploy.sh                 idempotent deploy to root@209.74.93.72
mcp/server.py             MCP (stdio) wrapper for Claude/GPT agents
```

## Quickstart for an AI system

### 1. Get a key

Server admin mints one (see `migrations/001_api_keys.sql` for full example):

```bash
python3 -c "import secrets,hashlib; k='ob_'+secrets.token_urlsafe(32); \
  print('raw:', k); print('sha256:', hashlib.sha256(k.encode()).hexdigest())"
# INSERT the sha256 into api_keys with scopes 'talent:read,jobs:read,jobs:write'
```

You receive the raw key once. All requests: `Authorization: Bearer <key>`.

### 2. Search talent

```bash
curl -s "https://api.outbounders.com/v1/talent?country_code=PH&active_within_days=90&limit=10" \
  -H "Authorization: Bearer $OUTBOUNDERS_API_KEY"
```

Returns anonymized records: `agent_id`, `country`, `member_since` (year),
`last_active` bucket (`30d`/`90d`/`1y`/`3y`/`3y+`), `skills` (self-scores:
survey, cold_calling_consumer, cold_calling_business, upsell, close_sale),
`experience_years`, `night_shift`. There is no profile-level hourly rate —
agents propose a rate per application (see step 4).

### 3. Post a job (scope `jobs:write`)

```bash
curl -s -X POST "https://api.outbounders.com/v1/jobs" \
  -H "Authorization: Bearer $OUTBOUNDERS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"title":"AI-augmented cold caller (US hours)","description":"20h/wk. Use our AI script generator. Report daily via API."}'
# -> {"job_id": 4821, "status": "pending_approval"}
```

Jobs enter the existing admin approval queue before going public.

### 4. Poll applications (scope `jobs:read`)

```bash
curl -s "https://api.outbounders.com/v1/jobs/4821/applications" \
  -H "Authorization: Bearer $OUTBOUNDERS_API_KEY"
```

Each application carries the agent's proposed `hourly_rate` (decimal, USD) —
this is where rates live, not on talent profiles.

### Health

```bash
curl -s https://api.outbounders.com/v1/health
```

## MCP (AI-native surface)

```bash
pip install mcp
OUTBOUNDERS_API_KEY=ob_xxx python3 mcp/server.py   # stdio
```

Claude Code config:

```json
{"mcpServers": {"outbounders": {
  "command": "python3",
  "args": ["/opt/outbounders-api/mcp/server.py"],
  "env": {"OUTBOUNDERS_API_KEY": "ob_xxx"}
}}}
```

Tools: `search_talent`, `post_job`, `get_job`, `get_applications`.

## Config (env)

| Var | Default | Notes |
|---|---|---|
| `DB_NAME` | `obapp_outbounders` | |
| `DB_USER` / `DB_PASS` / `DB_HOST` | unset | if set, TCP auth |
| `DB_SOCKET` | `/var/lib/mysql/mysql.sock` | socket-auth default |
| `MY_CNF` | `/root/.my.cnf` | used with socket auth |

Default (no `DB_USER`): unix socket as root via `/root/.my.cnf` — the service
runs on the DB host as root under systemd.

## Deploy

```bash
./deploy.sh   # rsync → venv → migration → systemd → health check
```

Apache proxy for `api.outbounders.com` is a printed manual step (deploy.sh
never edits Apache config). DNS is self-hosted (ns1/ns2.outbounders.com).

## Schema verification — DONE (live DESCRIBE, 2026-08-10)

- `client_job_posting`: PK `id`; columns user_id, title, `desc`, date_create,
  active, deleted, approved. VERIFIED.
- `job_application`: FK `job_id`; includes per-application `hourly_rate`
  decimal(12,2). VERIFIED.
- `agent_info`: FK `agent_id`; skill self-scores (skills_survey, skills_ccc,
  skills_ccb, skills_upsell, skills_closesale), work_experience, work_night.
  No hourly-rate column — rates are proposed per-application. PII columns
  (skypeid, yahooid, mobileno, landlineno, file_*) are never queried or
  returned. VERIFIED.
- MariaDB socket: `/var/lib/mysql/mysql.sock`. VERIFIED.
