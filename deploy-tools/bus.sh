#!/bin/bash
# Shared Memory Bus — Read/write to the single source of truth
# Usage:
#   bus.sh read [agent]       — Read unread messages for agent (default: adam)
#   bus.sh write <to> <type> <content>  — Write a message
#   bus.sh caps [agent]       — List capabilities
#   bus.sh agents             — List all agents
#   bus.sh stats              — Bus statistics
#   bus.sh intel              — Latest intelligence digest

BUS="http://127.0.0.1:8195"

case "${1:-help}" in
    read)
        AGENT="${2:-adam}"
        curl -s "$BUS/bus/messages/unread/$AGENT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
msgs = data.get('messages', [])
print(f'{len(msgs)} unread messages')
for m in msgs:
    frm = m.get('from_agent','?')
    tp = m.get('type','?')
    pri = m.get('priority','?')
    content = json.dumps(m.get('content',''))[:150]
    print(f'  [{pri}] {frm} ({tp}): {content}')
"
        ;;
    write)
        TO="${2:-all}"
        TYPE="${3:-message}"
        CONTENT="${4:-no content}"
        python3 -c "
import requests, json
r = requests.post('$BUS/bus/messages', json={
    'from': 'adam', 'to': '$TO', 'type': '$TYPE',
    'content': {'text': '''$CONTENT'''}
}, timeout=5)
print(r.json())
"
        ;;
    caps)
        AGENT="$2"
        URL="$BUS/bus/capabilities"
        [ -n "$AGENT" ] && URL="$BUS/bus/capabilities/$AGENT"
        curl -s "$URL" | python3 -c "
import json, sys
data = json.load(sys.stdin)
caps = data.get('capabilities', [])
by_agent = {}
for c in caps:
    by_agent.setdefault(c['agent'], []).append(c)
for agent, agent_caps in sorted(by_agent.items()):
    print(f'\n  {agent} ({len(agent_caps)} capabilities):')
    for c in agent_caps:
        perm = c.get('permission','?')
        doc = (c.get('documentation') or '')[:60]
        print(f'    [{perm:18s}] {c[\"capability\"]}: {doc}')
"
        ;;
    agents)
        curl -s "$BUS/bus/agents" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for a in data.get('agents', []):
    hb = (a.get('last_heartbeat') or 'never')[:19]
    role = (a.get('role') or '')[:50]
    print(f'  {a[\"name\"]:<15} [{a.get(\"status\",\"?\")}] last:{hb}  {role}')
"
        ;;
    stats)
        curl -s "$BUS/bus/stats" | python3 -m json.tool
        ;;
    intel)
        python3 /opt/fpai/memory-bus/intel-scanner.py latest
        ;;
    *)
        echo "Memory Bus Tool"
        echo "  read [agent]          — Unread messages (default: adam)"
        echo "  write <to> <type> <text> — Write a message"
        echo "  caps [agent]          — Capability registry"
        echo "  agents                — All agents"
        echo "  stats                 — Bus statistics"
        echo "  intel                 — Latest AI intelligence digest"
        ;;
esac
