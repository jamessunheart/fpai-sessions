# Atlas — Zen Village Brain access (15-minute setup)

This gets Atlas's Claude Desktop (or Cursor) talking to the same brain
Sunheart uses. Atlas will be able to read every database and write new
rows, all from natural-language chat.

## What Atlas needs from you (once, securely)

Send Atlas this bundle via Signal / 1Password / a secure channel:

```
AppFlowy URL:   https://brain.zenvillagecr.com
Service email:  james.rick.stinson@gmail.com
Service pass:   HdhOgoRE6BghKnvCS0co      ← rotate after he's done
Workspace ID:   3ca578c1-6a08-42d5-9f41-3b261787ace7
```

> **Why a shared service account?** AppFlowy Cloud's self-host free tier
> caps the workspace at 1 Member/Owner seat, so everyone's writes flow
> through Sunheart's identity for now. Audit happens via the `[via ...]`
> prefix that the Claude Project Instructions tell each agent to stamp
> onto rows.
>
> When we move off the free tier (or switch to the per-user access token
> flow in Phase 10), Atlas gets his own account. Until then: rotate the
> password if anyone's laptop gets lost/stolen.

## Step 1 — Clone the MCP server on Atlas's laptop

```bash
git clone https://github.com/fpai/FPAI_Cockpit.git
cd FPAI_Cockpit/docs/zen-village/mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Step 2 — Wire Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(create it if missing):

```json
{
  "mcpServers": {
    "zen-village-brain": {
      "command": "/ABSOLUTE/PATH/TO/FPAI_Cockpit/docs/zen-village/mcp/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/FPAI_Cockpit/docs/zen-village/mcp/zv_mcp_server.py"],
      "env": {
        "ZV_APPFLOWY_BASE": "https://brain.zenvillagecr.com",
        "ZV_MCP_USER":      "james.rick.stinson@gmail.com",
        "ZV_MCP_PASSWORD":  "HdhOgoRE6BghKnvCS0co",
        "ZV_WORKSPACE_ID":  "3ca578c1-6a08-42d5-9f41-3b261787ace7",
        "ZV_MCP_AGENT":     "atlas"
      }
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/` with the actual clone path. The
`ZV_MCP_AGENT` value is how every row Atlas creates gets tagged in the
audit log — set it to his first name.

## Step 3 — Restart Claude Desktop, trust the server

1. Fully quit Claude (`⌘Q`) and reopen.
2. In any chat, ask: *"Show me the status of the Zen Village Brain."*
3. On the first permission prompt, click **"Always allow for this chat"**
   (or find the MCP server in Settings → Developer and toggle trust on).

## Step 4 — Paste the Project Instructions

1. Create a new Claude Project called **"Zen Village Operator"**.
2. Paste everything from `claude_project_instructions.md` into the
   Project Instructions field.
3. Upload `docs/zen-village/schema/zv_schema.json` as a Project File so
   Claude sees the exact column names.

That's it — Atlas now has a Claude that lives inside the brain.

## Sanity checks Atlas can run

- *"What's in the brain right now?"* → expects `zv_status` call, 7 rows
- *"Who's on the ground team?"* → expects `zv_search` or `zv_list` on people
- *"Log a decision: we're shipping Telegram bot Friday. Rationale: MCP works."* → expects `zv_add_decision`
- *"Capture for master list: need to finalize the May property rental. High priority."* → expects `zv_add_master_list_item`

## If something breaks

- **Claude says the server isn't available** → tail
  `~/Library/Logs/Claude/mcp-server-zen-village-brain.log` and send me the
  last 30 lines.
- **Writes fail with "unknown field"** → the row schema drifted. Screenshot
  the error, we'll patch.
- **Everything returns "blank rows"** → Atlas passed `include_blanks: true`
  somewhere; remove it.
