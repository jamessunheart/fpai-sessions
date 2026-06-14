#!/bin/bash
# Session Broadcast Tool - Send messages to all active sessions
# Usage: ./session-broadcast.sh "message" ["priority: normal|high|urgent"]

MESSAGE="$1"
PRIORITY="${2:-normal}"
SESSION_ID="${3:-session-5-orchestration}"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

if [ -z "$MESSAGE" ]; then
    echo "Usage: ./session-broadcast.sh \"message\" [priority]"
    echo "Priority: normal, high, urgent (default: normal)"
    exit 1
fi

# Priority emoji
case "$PRIORITY" in
    urgent) EMOJI="🚨" ;;
    high)   EMOJI="⚠️" ;;
    *)      EMOJI="📬" ;;
esac

cat >> MESSAGES.md << EOF

---

**From:** $SESSION_ID
**Time:** $TIMESTAMP
**Priority:** $EMOJI $PRIORITY
**Subject:** Broadcast Message

$MESSAGE

EOF

echo "$EMOJI Message broadcast to all sessions!"
echo "Check MESSAGES.md to see your message"
