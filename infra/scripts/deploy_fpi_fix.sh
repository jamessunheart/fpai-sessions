#!/usr/bin/env bash
# Deploy the FPI MCP-bridge fix (3 bugs: key passthrough, select import, enum) to 198.
# Copies only the two changed files, backs up remote originals, restarts the service,
# and smoke-checks. Rollback: the .bak files + restart.
set -euo pipefail
SERVER=root@198.54.123.234
REMOTE=/opt/fpai/services/fp-index
LOCAL=/Users/jamessunheart/FullPotentialOS/SERVICES/fp-index
STAMP=$(date +%Y%m%d%H%M)

ssh "$SERVER" "cp $REMOTE/app/main.py $REMOTE/app/main.py.bak_$STAMP && cp $REMOTE/app/mcp_server.py $REMOTE/app/mcp_server.py.bak_$STAMP"
scp "$LOCAL/app/main.py" "$SERVER:$REMOTE/app/main.py"
scp "$LOCAL/app/mcp_server.py" "$SERVER:$REMOTE/app/mcp_server.py"
ssh "$SERVER" "systemctl restart fpai-fp-index && sleep 3 && systemctl is-active fpai-fp-index && curl -s -o /dev/null -w 'health %{http_code}\n' http://localhost:8550/health || curl -s -o /dev/null -w 'root %{http_code}\n' http://localhost:8550/"
echo "Deployed. Rollback: ssh $SERVER 'cp $REMOTE/app/main.py.bak_$STAMP $REMOTE/app/main.py; cp $REMOTE/app/mcp_server.py.bak_$STAMP $REMOTE/app/mcp_server.py; systemctl restart fpai-fp-index'"
