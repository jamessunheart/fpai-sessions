# Cursor — wire in Sunheart Brain

## Option A: User-wide (recommended)

`~/.cursor/mcp.json`:

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

## Option B: This workspace only

`.cursor/mcp.json` (at the root of `FPAI_Cockpit`):

```json
{
  "mcpServers": {
    "full-potential-intelligence": { "url": "https://fullpotential.ai/mcp" },
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

## Refresh

Reload Cursor (Cmd-Shift-P → "Developer: Reload Window"). In any chat, type
`@sunheart-brain` or ask "what brain tools do I have?" — Cursor will list the
11 tools.
