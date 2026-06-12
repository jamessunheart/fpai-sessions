# Brain Mesh Gateway

Secure cross-brain gateway for Adam and other agents.

## What it does

- Centralizes access to multiple brains (Zen Village, Sunheart, others later).
- Enforces per-token tiered access:
  - which brains a user/agent can see
  - read/write permissions
  - allowed section namespaces (for example: `adam-openclaw/*`, `shared/*`)
  - optional wildcard access for owners
- Provides a simple cross-brain index endpoint (`/brain-index`) so Adam can ask one question across allowed brains.
- Keeps an activity trail (`/activity`) for "what happened there" visibility.

## Why this is safer

- Adam no longer needs direct raw credentials for each brain.
- Access is managed in one policy file with role + scope.
- Per-brain upstream credentials stay server-side (env vars), never sent to client.

## API

- `GET /healthz`
- `GET /brains` (auth required)
- `POST /read` (auth required)
- `POST /write` (auth required, write permission required)
- `POST /brain-index` (auth required)
- `GET /activity` (auth required; owner sees all, others see self)
- `GET /status` (auth required; per-brain health summary)

Adapter routes (no raw MCP session handling needed):

- `POST /adapters/zv/search`
- `POST /adapters/zv/log`
- `POST /adapters/sunheart/search`
- `POST /adapters/sunheart/add-note`
- `GET /adapters/brief`

## Policy file

Copy `config/policy.example.json` to `config/policy.json`, then:

1. Replace token strings with long random values.
2. Set user/agent roles and allowed brains.
3. Configure each brain base URL + auth env var.
4. Configure `read_sections` / `write_sections` for namespace-level isolation.
5. Add `created_at` / `expires_at` per token for rotation hygiene.

Environment:

- `BRAIN_MESH_POLICY_FILE` (default `config/policy.json`)
- `BRAIN_MESH_TIMEOUT_SECONDS` (default `25`)
- `BRAIN_MESH_AUDIT_LOG_FILE` (default `/var/log/brain-mesh-gateway/audit.jsonl`)
- Brain tokens via env vars in policy (`token_env_var`), e.g.:
  - `ZV_MCP_TOKEN`
  - `SH_MCP_TOKEN`

## Run local

```bash
cd SERVICES/brain-mesh-gateway
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config/policy.example.json config/policy.json
uvicorn app.main:app --host 0.0.0.0 --port 8860
```

## Example calls

```bash
TOKEN="replace-with-adam-token"

curl -s http://127.0.0.1:8860/brains \
  -H "Authorization: Bearer ${TOKEN}"

curl -s http://127.0.0.1:8860/brain-index \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query":"What changed today?","per_brain_limit":3}'
```

## Next hardening recommended

- Move policy + service env to encrypted secrets (`sops` + `age`).
- Persist activity logs to append-only file / DB.
- Add per-token rate limits and token expiry.
- Add stronger request schemas per brain tool (allowlist tool names).
