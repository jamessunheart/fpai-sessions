# Claude Desktop — wire in Sunheart Brain

## 1. Install `mcp-remote` once

```bash
npm install -g mcp-remote
```

## 2. Edit Claude's MCP config

`~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sunheart-brain": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://brain.sunheart.com/mcp/sse",
        "--header", "Authorization: Bearer sh_YOUR_TOKEN_HERE"
      ]
    }
  }
}
```

## 3. Quit Claude Desktop fully (Cmd-Q) and reopen

The hammer icon should now show `sunheart-brain` with ~11 tools:
`brain_status`, `brain_search_semantic`, `brain_search_text`, `brain_list`,
`brain_get_note`, `brain_add_note`, `brain_add_concept`,
`brain_add_conversation`, `brain_propose_dedup`, `brain_merge_concepts`,
`brain_propose_tag`.

## 4. First test

Type into Claude:

> Call `brain_status` and show me the row counts, then `brain_search_semantic`
> with query "what matters most to me" and k=5.

## Rotating the token

```bash
ssh root@162.0.208.88 /opt/sh-brain-src/scripts/issue_token.sh claude-desktop --rotate
```

Paste the new token into `claude_desktop_config.json`, restart Claude.
