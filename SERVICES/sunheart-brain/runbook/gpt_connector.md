# GPT Connector — wire in Sunheart Brain

OpenAI's **ChatGPT Custom Connectors** (Pro / Team / Enterprise, late 2025)
speak OpenAPI, not MCP. We expose the same tool surface via the
`brain-index` REST API at `https://brain.sunheart.com/index/*` plus an
OpenAPI spec at `/openapi.json`, so GPT can import it directly.

## Option A: ChatGPT Custom Connector (Pro/Team/Enterprise)

1. **ChatGPT** → **Settings** → **Connectors** → **Add custom connector**.
2. **OpenAPI schema URL:** `https://brain.sunheart.com/openapi.json`
3. **Authentication:**
   - Type: **API key / Bearer**
   - Header: `Authorization`
   - Value: `Bearer sh_YOUR_GPT_TOKEN_HERE`  *(from `issue_token.sh gpt-connector`)*
4. **Privacy policy URL:** `https://sunheart.com/privacy` *(or a placeholder
   if you don't have one yet)*.
5. Save.

In any new chat, hit **+ → Connectors → Sunheart Brain** before sending.
GPT will now call `/search`, `/upsert`, `/dedup`, `/ingest/add_note`,
`/ingest/ensure_conversation` directly.

## Option B: Custom GPT with Actions (available on Plus)

1. **ChatGPT** → **Create a GPT** → **Configure** → **Actions** → **Create
   new action**.
2. **Import from URL:** `https://brain.sunheart.com/openapi.json`
3. **Authentication:** API Key → **Custom** header `Authorization` →
   `Bearer sh_YOUR_GPT_TOKEN_HERE`.
4. Save.

This GPT can now read + write the brain. Share privately or publicly.

## What the token can do

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | Unauth — liveness |
| `POST /embed` | Embed 1–N strings |
| `POST /upsert` | Add a chunk to pgvector |
| `POST /search` | Semantic search (cosine over pgvector) |
| `POST /dedup` | Find near-duplicates |
| `POST /ingest/add_note` | Create an AppFlowy note + embed |
| `POST /ingest/ensure_conversation` | Get-or-create a Conversation row |

All require `Authorization: Bearer <token>` except `/healthz`.

## Troubleshooting

**GPT says "couldn't reach the connector"** — CORS + HTTPS required. If you
hit it, set `APPFLOWY_BASE_URL` in `brain.env` to ensure nginx is serving
the openapi.json with `Access-Control-Allow-Origin: *` (already in the
vhost; double-check with `curl -I https://brain.sunheart.com/openapi.json`).

**GPT calls return 401** — token rotated? Re-issue with
`./scripts/issue_token.sh gpt-connector --rotate` and update the connector.
