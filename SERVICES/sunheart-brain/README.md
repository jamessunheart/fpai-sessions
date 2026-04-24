# Sunheart Brain

> **Your personal second brain.** Self-hosted AppFlowy at `brain.sunheart.com` + a
> pgvector semantic layer + MCP server + ingestion pipeline for Bear notes,
> ChatGPT exports, Claude exports, and Cursor agent transcripts.

**Status:** under construction (see `docs/zen-village/deploy_log.yaml` for the
sibling Zen Village Brain that this was forked from).

**Host:** Secondary `162.0.208.88`, second docker stack (ports `28080/28081`).

## Architecture

```
                 ┌────────────────────────────────────────────────┐
                 │   Claude Desktop · Cursor · ChatGPT · agents   │
                 └──────────────────────┬─────────────────────────┘
                                        │ MCP (SSE) / OpenAPI
                                        ▼
              ┌────────────────────────────────────────────────────┐
              │ nginx (brain.sunheart.com, TLS via Let's Encrypt)  │
              │  /              → appflowy UI                       │
              │  /mcp/sse       → sh-mcp-http      (bearer auth)    │
              │  /mcp/messages/ → sh-mcp-http                       │
              │  /index/*       → brain-index      (internal)       │
              └──┬─────────────────┬─────────────────┬──────────────┘
                 │                 │                 │
                 ▼                 ▼                 ▼
        ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
        │ appflowy     │   │ sh-mcp-http  │   │ brain-index      │
        │ cloud stack  │   │ (port 28091) │   │ (port 28090)     │
        │ port 28080   │   │ MCP tools    │   │ embed / search   │
        └──────┬───────┘   └──────┬───────┘   │ pgvector wrapper │
               │                  │           └──────────┬───────┘
               │                  └──────── REST ────────┘
               ▼
        ┌──────────────────────────────────┐
        │ postgres 15 + pgvector           │
        │ (schema: appflowy_cloud)         │
        │ (schema: brain_index)            │
        └──────────────────────────────────┘
```

## Directory layout

```
SERVICES/sunheart-brain/
├── compose/           # docker-compose stack (appflowy cloud + pgvector postgres + gotrue + minio + appflowy_web)
├── nginx/             # nginx vhost for brain.sunheart.com
├── schema/            # sh_schema.json + build_schema.py  (5 DBs: Notes / Concepts / Conversations / Sources / Tags)
├── index/             # brain-index FastAPI service (embed + upsert + cosine search + dedup)
├── mcp/               # sh_mcp_server.py (stdio) + sh_mcp_http.py (SSE) + tokens template
├── ingest/            # brain-ingest CLI: adapters for bear / chatgpt / claude / cursor transcripts
├── scripts/           # deploy helpers, backup extension, systemd units
└── runbook/           # onboarding, troubleshooting, token rotation
```

## 5 databases

1. **01 · Notes** — every atom of content you've ever written, one row each. This is
   the raw firehose from all sources, searchable verbatim.
2. **02 · Concepts** — the AI-deduped canonical layer. Many notes → one concept.
   This is what's actually searchable by meaning.
3. **03 · Conversations** — AI chat threads (ChatGPT, Claude, Cursor). A conversation
   has many notes (one per useful message).
4. **04 · Sources** — provenance registry (Bear app, ChatGPT export, Claude export,
   Cursor transcripts, manual).
5. **05 · Tags** — controlled vocabulary, AI-proposed + user-curated.

## Deploy flow

See `runbook/deploy.md`. The short version:

1. DNS: `brain.sunheart.com` A → `162.0.208.88` (manual step at Namecheap).
2. `./scripts/bootstrap.sh` on Secondary (brings up compose, certbot, nginx).
3. `./scripts/provision_user.sh` (GoTrue admin API: creates owner, skips SMTP).
4. `python3 schema/build_schema.py` (creates 5 DBs via AppFlowy REST).
5. `systemctl enable --now sh-brain-index sh-mcp-http`.
6. `brain-ingest dry-run --all` then `brain-ingest run --all` from your Mac.
