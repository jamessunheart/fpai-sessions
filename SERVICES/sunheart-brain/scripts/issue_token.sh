#!/usr/bin/env bash
#
# Issue (or rotate) an MCP bearer token for an agent, with scoped permissions.
#
# Usage:
#   ./issue_token.sh <agent> <scopes>           e.g.  claude-desktop public,personal
#   ./issue_token.sh <agent> <scopes> --rotate  replace existing token
#
# Scopes:
#   public    Read 🟢 Public Notes/Concepts (default, every token should have this)
#   personal  Also read 🟡 Personal Notes (and embed queries locally only)
#   ingest    Write rows; run dedup/merge; used by brain-ingest and sh-mcp-http's own token
#   admin     Bypass all scope checks. Keep this only on the MCP's internal token.
#
# Recommended pairings:
#   sunheart          public,personal,ingest     me, full access
#   claude-personal   public,personal            Claude Desktop, sees everything personal
#   claude-public     public                     Claude on a shared laptop
#   cursor            public,personal,ingest     in-editor agent, can write new notes
#   gpt-connector     public                     ChatGPT Custom Connector (hard-limited)
#   ingest            ingest                     brain-ingest CLI from your Mac
#   sh-mcp-http       admin                      the MCP-to-index trust token
#
# Tokens go into /etc/sh-brain/mcp-tokens.json as
#     { "<token>": { "agent": "<name>", "scopes": ["public", ...] } }

set -euo pipefail

AGENT="${1:-}"
SCOPES="${2:-public}"
FLAG="${3:-}"
TOKENS=/etc/sh-brain/mcp-tokens.json

if [ -z "$AGENT" ]; then
  cat <<USAGE
Usage: $0 <agent> <scopes> [--rotate]
  scopes: comma-separated subset of {public,personal,ingest,admin}

Examples:
  $0 sunheart        public,personal,ingest
  $0 claude-personal public,personal
  $0 claude-public   public
  $0 gpt-connector   public
  $0 ingest          ingest
USAGE
  exit 1
fi

[ -f "$TOKENS" ] || echo "{}" > "$TOKENS"
chmod 600 "$TOKENS"

TOKEN="sh_$(openssl rand -hex 24)"

python3 - "$TOKENS" "$AGENT" "$SCOPES" "$TOKEN" "$FLAG" <<'PY'
import json, sys
path, agent, scopes_csv, token, flag = sys.argv[1:]
rotate = flag == "--rotate"
scopes = [s.strip() for s in scopes_csv.split(",") if s.strip()]
if not scopes:
    scopes = ["public"]

data = json.load(open(path))

existing = []
for k, v in list(data.items()):
    if isinstance(v, dict) and v.get("agent") == agent:
        existing.append(k)
    elif isinstance(v, str) and (v == agent):
        existing.append(k)

if existing and not rotate:
    print(f"Token for agent {agent!r} already exists:", file=sys.stderr)
    for t in existing: print("  " + t, file=sys.stderr)
    print("Pass --rotate to replace.", file=sys.stderr)
    sys.exit(1)

for t in existing:
    del data[t]

data[token] = {"agent": agent, "scopes": scopes}
json.dump(data, open(path, "w"), indent=2, sort_keys=True)
PY

echo "Agent:  $AGENT"
echo "Scopes: $SCOPES"
echo "Token:  $TOKEN"
echo

# The brain-index service has its OWN tokens file; mirror ingest/admin tokens there too
# so brain-ingest (CLI) and sh-mcp-http can both authenticate against /index endpoints.
INDEX_TOKENS=/etc/sh-brain/index-tokens.json
[ -f "$INDEX_TOKENS" ] || echo "{}" > "$INDEX_TOKENS"
chmod 600 "$INDEX_TOKENS"
# Mirror any token that might talk to brain-index (ingest, admin, personal).
case ",$SCOPES," in
  *,ingest,*|*,admin,*|*,personal,*)
    python3 - "$INDEX_TOKENS" "$AGENT" "$SCOPES" "$TOKEN" <<'PY'
import json, sys
path, agent, scopes_csv, token = sys.argv[1:]
scopes = [s.strip() for s in scopes_csv.split(",") if s.strip()]
data = json.load(open(path))
for k, v in list(data.items()):
    if isinstance(v, dict) and v.get("agent") == agent:
        del data[k]
    elif isinstance(v, str) and v == agent:
        del data[k]
data[token] = {"agent": agent, "scopes": scopes}
json.dump(data, open(path, "w"), indent=2, sort_keys=True)
PY
    echo "(also mirrored into $INDEX_TOKENS)"
    ;;
esac

echo
echo "Client config (mcp-remote pattern, works for Claude Desktop + Cursor):"
cat <<EOF
{
  "mcpServers": {
    "sunheart-brain": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote",
        "https://brain.sunheart.com/mcp/sse",
        "--header", "Authorization: Bearer $TOKEN"
      ]
    }
  }
}
EOF
