# Zen Village Brain — MCP Server

Lets **Claude Desktop**, **Claude Code**, **Cursor**, or any MCP-compatible
client read and write the Zen Village Brain across two backends:
- the 7 self-hosted **AppFlowy** databases (personal-brain layer)
- the **NocoDB** unified CRM + project plane (humans, tasks, events)

## What it exposes (24 tools)

### AppFlowy-backed (personal brain — 12 tools)

| Tool                         | Purpose                                            |
|------------------------------|----------------------------------------------------|
| `zv_status`                  | Health check + row counts for every DB.            |
| `zv_list` / `zv_get_row` / `zv_search` | Read any AppFlowy DB.                    |
| `zv_add_master_list_item`    | Capture anything to 01 · Master List.              |
| `zv_add_weekly_log`          | Log the week to 02 · Weekly Log.                   |
| `zv_add_decision`            | Record a decision in 05 · Decision Log.            |
| `zv_add_event`               | Create a row in 06 · Events (legacy).              |
| `zv_add_person` / `zv_add_property` / `zv_add_metric` / `zv_propose_change` | … |

### NocoDB-backed (unified data plane — 12 tools)

| Tool                          | Purpose                                            |
|-------------------------------|----------------------------------------------------|
| `zv_add_project` / `zv_list_projects` / `zv_update_project` | Project kanban (`Active/On Hold/Done/Cancelled`). |
| `zv_add_task` / `zv_list_tasks` / `zv_update_task`          | Task kanban (`Backlog/Todo/Doing/Blocked/Done`). Auto-stamps `StartedAt` when set to Doing, `CompletedAt` when set to Done. |
| `zv_add_calendar_event` / `zv_list_calendar_events` / `zv_update_calendar_event` | Calendar with `public/internal/admin` visibility. |
| `zv_list_applications` / `zv_list_inquiries` / `zv_list_partners` | Read-only views of CRM tables (already populated by web forms + affiliate signups). |

All write tools auto-stamp the calling agent (from the bearer-token map in
`/etc/zen-village/mcp-tokens.json`) into a Notes/Description field so
multi-agent activity stays attributable through the shared service account.

## Install

```bash
cd docs/zen-village/mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # fill in the 4 values
```

## Wire into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "zen-village-brain": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/docs/zen-village/mcp/zv_mcp_server.py"],
      "env": {
        "ZV_APPFLOWY_BASE": "https://brain.zenvillagecr.com",
        "ZV_MCP_USER":      "james.rick.stinson@gmail.com",
        "ZV_MCP_PASSWORD":  "…",
        "ZV_WORKSPACE_ID":  "…"
      }
    }
  }
}
```

Restart Claude Desktop. You'll see `zen-village-brain` in the hammer icon.

## Wire into Cursor

Edit `~/.cursor/mcp.json` (or the workspace one):

```json
{
  "mcpServers": {
    "zen-village-brain": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/docs/zen-village/mcp/zv_mcp_server.py"],
      "env": { "…same as above…": "" }
    }
  }
}
```

## Quick test from the CLI

```bash
ZV_MCP_PASSWORD=… ZV_WORKSPACE_ID=… python3 zv_mcp_server.py
# (reads MCP messages on stdin; pair with `mcp` CLI to smoke-test)
```

## Production deployment (HTTP/SSE — no local install)

The recommended path for agents (Atlas, etc.) is the **hosted SSE endpoint**
at `https://brain.zenvillagecr.com/mcp/sse`, which runs `zv_mcp_http.py` as
`zv-mcp-http.service` on the secondary server. Each agent gets a bearer
token in `/etc/zen-village/mcp-tokens.json` and connects via `mcp-remote`:

```json
{
  "mcpServers": {
    "zen-village-brain": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote@latest",
        "https://brain.zenvillagecr.com/mcp/sse",
        "--header", "Authorization: Bearer $ZV_TOKEN"
      ],
      "env": { "ZV_TOKEN": "zv_<your-token>" }
    }
  }
}
```

The Atlas installer (`https://brain.zenvillagecr.com/install.sh`) auto-merges
this into `claude_desktop_config.json` — set `ZV_TOKEN` and run.

## Architecture

```
        Claude Desktop / Cursor / Code         (MCP client)
                       │  bearer auth
                       ▼
        https://brain.zenvillagecr.com/mcp/sse  (Starlette + SSE)
                       │
                       ├──► AppFlowy Cloud      (personal brain)
                       │      via service account
                       │
                       └──► NocoDB              (unified CRM + PM)
                              via xc-token (https://crm.zenvillagecr.com)
```

## Troubleshooting

* **`Could not resolve db_id for …`** — workspace folder names drifted from
  spec. Run `zv_status` to see which AppFlowy DBs weren't matched; rename
  the page to match `DB_SPEC` in `zv_mcp_server.py`.
* **401 on `/mcp/sse`** — bearer token is missing or unknown. Add it to
  `/etc/zen-village/mcp-tokens.json` (no service restart needed; tokens are
  re-read each request).
* **`Tasks/Events/Projects table not configured`** — env vars
  `ZV_NOCODB_*_TABLE_ID` are missing from `/etc/zen-village/mcp-http.env`.
  Run `systemctl cat zv-mcp-http` to see what's loaded.
* **`Ignoring unknown field …`** — AppFlowy column name doesn't match
  `zv_schema.json`. The server keeps `"Name"` as a fallback for pre-cleanup
  databases.
