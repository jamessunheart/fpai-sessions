# Atlas — Zen Village Brain access (zero-install, 2 minutes)

This is the **hosted MCP** flow — Atlas doesn't install Python, doesn't
clone anything, doesn't edit any venvs. He just pastes a config block
into Claude Desktop and restarts.

## What you send Atlas (securely — Signal / 1Password / encrypted)

A single bundle:

```
Claude config block (paste into claude_desktop_config.json):

{
  "mcpServers": {
    "zen-village-brain": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://brain.zenvillagecr.com/mcp/sse",
        "--header", "Authorization: Bearer <ATLAS_TOKEN>"
      ]
    }
  }
}
```

Plus his **bearer token** (never paste this in plaintext chat — use the
secure channel above):
```
<ATLAS_TOKEN>
```

## What Atlas does (the whole thing)

**Easiest (recommended):** one Terminal command merges Claude Desktop config
and, if needed, installs a **private** Node LTS under his home folder (no
Homebrew required):

```bash
ZV_TOKEN=<ATLAS_TOKEN> bash <(curl -sS https://brain.zenvillagecr.com/install.sh)
```

Use the real token in place of `<ATLAS_TOKEN>` (same value as in the JSON
block above, without angle brackets). After it prints “Done”, continue from
step 3 below.

**Manual alternative:** if he prefers not to run the script:

1. Node.js ≥ 18 on PATH (`node -v`), or `brew install node` on Mac.

2. Open `~/Library/Application Support/Claude/claude_desktop_config.json`
   (create it if it doesn't exist). Merge in the `zen-village-brain` block
   from above, replacing `<ATLAS_TOKEN>` with the token.

   If he already has other MCP servers, his file looks like:
   ```json
   {
     "mcpServers": {
       "existing-server": { ... },
       "zen-village-brain": {
         "command": "npx",
         "args": ["-y", "mcp-remote",
                  "https://brain.zenvillagecr.com/mcp/sse",
                  "--header", "Authorization: Bearer <ATLAS_TOKEN>"]
       }
     }
   }
   ```

3. Quit Claude Desktop completely (⌘Q) and reopen.

4. In any chat: *"Show me the status of the Zen Village Brain."*
   On the first permission prompt, click **"Always allow for this chat"**.

5. Create a Claude Project called **"Zen Village Operator"**, paste the
   contents of `claude_project_instructions.md` into the Instructions
   field, and upload `zv_schema.json` as a Project File. (Send both files
   with the token; they're in the repo under `docs/zen-village/runbook/`
   and `docs/zen-village/schema/`.)

That's it. Total time: ~2 min with the installer if Node is already there,
or ~5–10 min the first time while it downloads a private Node build.

## How this works under the hood

- `mcp-remote` is an npm package that auto-installs via `npx` on first run
- It bridges Claude Desktop's local stdio MCP transport to a remote
  SSE-based MCP server over HTTPS
- Our server at `brain.zenvillagecr.com/mcp/sse` is behind bearer-token
  auth; the token maps to an agent name (`atlas`) server-side
- Every row Atlas creates gets stamped `[via atlas @ <timestamp>]` in the
  Notes/Rationale field — so the shared AppFlowy service account writes
  stay individually attributable

## Rotating Atlas's token

If his laptop gets lost/stolen or the token leaks:

```bash
ssh root@162.0.208.88
NEW="zv_$(openssl rand -hex 24)"
# Update /etc/zen-village/mcp-tokens.json (swap atlas's token for $NEW)
python3 -c "
import json, os
p = '/etc/zen-village/mcp-tokens.json'
d = json.load(open(p))
# find the atlas token and replace
for tok in list(d):
    if d[tok] == 'atlas':
        del d[tok]
d['$NEW'] = 'atlas'
open(p,'w').write(json.dumps(d, indent=2))
"
# Also update secrets
sed -i "s|^ZV_MCP_TOKEN_ATLAS=.*|ZV_MCP_TOKEN_ATLAS=${NEW}|" /root/zen-village-secrets/appflowy.env.secrets
# No service restart needed — tokens file is re-read on every request.
echo "New Atlas token: ${NEW}"
```

Send the new token to Atlas via secure channel; he swaps it in his
config block.

## Adding a new person (Maya, Kai, anyone)

```bash
ssh root@162.0.208.88
NAME=maya
NEW="zv_$(openssl rand -hex 24)"
python3 -c "
import json
p = '/etc/zen-village/mcp-tokens.json'
d = json.load(open(p))
d['$NEW'] = '$NAME'
open(p,'w').write(json.dumps(d, indent=2))
"
echo "ZV_MCP_TOKEN_${NAME^^}=${NEW}" >> /root/zen-village-secrets/appflowy.env.secrets
echo "Token for ${NAME}: ${NEW}"
```

Send them this onboarding doc with their token filled in. 30 seconds of
ops work per new person.

## Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| Claude says "couldn't connect to MCP server" | `npx` missing Node | install Node ≥18 |
| 401 from Claude's logs | token typo'd or revoked | double-check token, rotate if needed |
| Tools work but writes fail with "unknown field" | schema drift | screenshot error, we patch |
| "mcp-remote" command hangs | firewall blocking HTTPS to brain.zenvillagecr.com | check his network |

## Cost

$0 ongoing. `mcp-remote` is free, the server runs on our existing
Secondary host. Each new user is a tokens.json edit.
