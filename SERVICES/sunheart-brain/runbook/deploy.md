# Sunheart Brain — Deploy Runbook

End-to-end, first-time deploy. Every step is idempotent; re-running after a
failure is safe.

**Target:** `brain.sunheart.com` on Secondary `162.0.208.88`, alongside the
existing Zen Village Brain stack on the same box.

**Total wall time** (excluding first ingest): ~25 minutes.

---

## Phase 0 — Prereqs (do this before SSH'ing)

- [x] DNS: `brain.sunheart.com` A → `162.0.208.88`. Verify with
  `dig +short brain.sunheart.com @1.1.1.1`.
- [x] You have root on Secondary.
- [x] Secondary already has: docker, docker compose plugin, nginx, certbot,
  ollama at `:11434` with `nomic-embed-text` pulled
  (`ollama pull nomic-embed-text` if not).
- [x] Port `28080`, `28090`, `28091` are free
  (`ss -tnlp | grep -E '2808[0-9]|28091'` should be empty).

## Phase 1 — Copy the repo onto Secondary

From your Mac:

```bash
rsync -a --delete \
  --exclude '.venv' --exclude '__pycache__' \
  SERVICES/sunheart-brain/ \
  root@162.0.208.88:/opt/sh-brain-src/
```

## Phase 2 — Bootstrap the docker stack + cert

On Secondary:

```bash
cd /opt/sh-brain-src
./scripts/bootstrap.sh
```

This:

1. Generates `/root/sh-brain-secrets/brain.env` with random passwords.
2. `docker compose up -d` → postgres (pgvector), redis, minio, gotrue,
   appflowy_cloud, admin_frontend, appflowy_web, internal nginx.
3. Installs `/etc/nginx/sites-enabled/brain.sunheart.com.conf`.
4. Issues the Let's Encrypt cert (assumes DNS is live).

**Verify:**

```bash
curl -I https://brain.sunheart.com/         # → 200 or 302 (AppFlowy web UI)
docker ps --filter name=sh-brain             # 7 containers, all healthy
```

## Phase 3 — Provision the owner + capture workspace_id

```bash
./scripts/provision_user.sh
```

This creates `james.rick.stinson@gmail.com` via GoTrue's admin API (skips
SMTP), logs in once, renames the workspace to "Sunheart Brain", and writes
`SH_WORKSPACE_ID=…` back into `brain.env`.

**Verify:** open `https://brain.sunheart.com` in a browser → "Continue with
password" → log in with the email + `SH_OWNER_PASSWORD` from `brain.env`.
You should land in the Sunheart Brain workspace.

## Phase 4 — Build the 5 databases

```bash
python3 schema/build_schema.py --purge-defaults
```

This:

- Trashes the default "To-dos" / "Grid" pages.
- Creates **01 · Notes**, **02 · Concepts**, **03 · Conversations**,
  **04 · Sources**, **05 · Tags** with all fields + cross-DB relations.

**Verify:** refresh the AppFlowy UI → General space has 5 numbered DBs.
Click "01 · Notes" → grid opens with the full column set.

## Phase 5 — Install systemd units (brain-index + sh-mcp-http)

```bash
./scripts/install_systemd.sh
```

**Verify:**

```bash
curl -s http://127.0.0.1:28090/healthz | jq    # brain-index
curl -s http://127.0.0.1:28091/healthz | jq    # sh-mcp-http
curl -s https://brain.sunheart.com/mcp/healthz | jq
curl -s https://brain.sunheart.com/index/healthz | jq
```

All four should return `{"ok": true, …}`.

## Phase 6 — Issue your first MCP token

```bash
./scripts/issue_token.sh sunheart
```

Copy the printed token. Save it in 1Password.

Repeat for each client:

```bash
./scripts/issue_token.sh cursor
./scripts/issue_token.sh claude-desktop
./scripts/issue_token.sh gpt-connector
./scripts/issue_token.sh ingest        # used by the brain-ingest CLI
```

## Phase 7 — Wire clients

- **Claude Desktop:** `runbook/claude_desktop.md`
- **Cursor:** `runbook/cursor.md`
- **GPT Custom Connector:** `runbook/gpt_connector.md`

## Phase 8 — First ingest (from your Mac)

```bash
cd SERVICES/sunheart-brain/ingest
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export SH_BRAIN_BASE=https://brain.sunheart.com
export SH_INGEST_TOKEN=sh_…           # the ingest token from Phase 6
export SH_DATA_DIR=~/SunheartBrainData

# 1. Dry run everything — see counts + samples
./brain_ingest.py dry-run --all

# 2. Start with Bear only (smallest, fastest feedback)
./brain_ingest.py run --source bear

# 3. ChatGPT + Claude (put exports in ~/SunheartBrainData/)
./brain_ingest.py run --source chatgpt
./brain_ingest.py run --source claude

# 4. Cursor transcripts (already local)
./brain_ingest.py run --source cursor
```

### Where to put AI export files

```
~/SunheartBrainData/
├── chatgpt-export/
│   └── conversations.json          # from chatgpt.com → Settings → Data Controls → Export data
└── claude-export/
    └── conversations.json          # from claude.ai → Settings → Privacy → Export data
```

## Phase 9 — First semantic search

From Claude Desktop (with the MCP attached):

> Use `brain_status`. Then `brain_search_semantic` with query "what have I
> written about purpose and meaning" — pull 10 hits.

From the REST surface:

```bash
curl -s https://brain.sunheart.com/index/search \
  -H "Authorization: Bearer $SH_INGEST_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"query":"purpose and meaning","k":10,"prefer":"local"}' | jq
```

## Phase 10 — Enable daily backups

```bash
ln -s /opt/sh-brain-src/scripts/backup.sh /usr/local/bin/sh-brain-backup.sh
echo "15 3 * * * /usr/local/bin/sh-brain-backup.sh" | crontab -l | ( cat; echo; ) | crontab -
```

Verify tomorrow: `ls /root/backups/sunheart-brain/`.

---

## Rollback

Everything is isolated to the `sh-brain` docker project + the
`brain.sunheart.com` nginx vhost + `/opt/sh-brain*` + `/etc/sh-brain`. To
tear down:

```bash
docker compose -p sh-brain -f /opt/sh-brain/compose/docker-compose.yml down -v
rm -f /etc/nginx/sites-enabled/brain.sunheart.com.conf
systemctl reload nginx
systemctl disable --now sh-brain-index sh-mcp-http
rm -rf /opt/sh-brain* /etc/sh-brain
```

The zen-village stack is untouched.
