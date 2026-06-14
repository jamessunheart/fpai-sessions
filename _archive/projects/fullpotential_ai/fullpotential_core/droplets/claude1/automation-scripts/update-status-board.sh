#!/bin/bash

# 🤝 Update Status Board - Generate human-readable status board
# Auto-called by heartbeat, can also be called manually

cd "$(dirname "$0")/../.."

# Enable nullglob so patterns that don't match expand to empty string
shopt -s nullglob

# Count active sessions
SESSION_COUNT=0
for session in COORDINATION/sessions/*.json; do
    [ -f "$session" ] || continue
    STATUS=$(python3 -c "import json; print(json.load(open('$session')).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    if [ "$STATUS" = "active" ]; then
        SESSION_COUNT=$((SESSION_COUNT + 1))
    fi
done

# Generate STATUS_BOARD.md header
cat > COORDINATION/STATUS_BOARD.md <<EOF
# 🤝 Multi-Session Status Board

**Last Updated:** $(date -u +"%Y-%m-%d %H:%M UTC")
**Active Sessions:** $SESSION_COUNT

---

## 🟢 Active Sessions

EOF

# Add active sessions
FOUND_ACTIVE=false
for session in COORDINATION/sessions/*.json; do
    [ -f "$session" ] || continue

    SID=$(python3 -c "import json; print(json.load(open('$session')).get('session_id', 'unknown'))" 2>/dev/null || echo "unknown")
    STATUS=$(python3 -c "import json; print(json.load(open('$session')).get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    WORK=$(python3 -c "import json; print(json.load(open('$session')).get('current_work', 'idle'))" 2>/dev/null || echo "idle")
    STARTED=$(python3 -c "import json; print(json.load(open('$session')).get('started_at', ''))" 2>/dev/null || echo "")

    if [ "$STATUS" = "active" ]; then
        FOUND_ACTIVE=true
        # Get latest heartbeat for this session
        LATEST_HB=$(ls -t COORDINATION/heartbeats/*-${SID}.json 2>/dev/null | head -1 || echo "")
        if [ -f "$LATEST_HB" ]; then
            ACTION=$(python3 -c "import json; print(json.load(open('$LATEST_HB')).get('action', ''))" 2>/dev/null || echo "")
            PHASE=$(python3 -c "import json; print(json.load(open('$LATEST_HB')).get('phase', ''))" 2>/dev/null || echo "")
            PROGRESS=$(python3 -c "import json; print(json.load(open('$LATEST_HB')).get('progress', ''))" 2>/dev/null || echo "")
            NEXT=$(python3 -c "import json; print(json.load(open('$LATEST_HB')).get('next_action', ''))" 2>/dev/null || echo "")
        else
            ACTION="unknown"
            PHASE=""
            PROGRESS=""
            NEXT=""
        fi

        cat >> COORDINATION/STATUS_BOARD.md <<EOF

### $SID (Started: $STARTED)
- **Status:** $STATUS
- **Action:** $ACTION
- **Working On:** $WORK
EOF
        [ -n "$PHASE" ] && echo "- **Phase:** $PHASE" >> COORDINATION/STATUS_BOARD.md
        [ -n "$PROGRESS" ] && echo "- **Progress:** $PROGRESS" >> COORDINATION/STATUS_BOARD.md
        [ -n "$NEXT" ] && echo "- **Next:** $NEXT" >> COORDINATION/STATUS_BOARD.md
    fi
done

if [ "$FOUND_ACTIVE" = false ]; then
    echo "(No active sessions)" >> COORDINATION/STATUS_BOARD.md
fi

# Add claims section
cat >> COORDINATION/STATUS_BOARD.md <<'EOF'

---

## 🔒 Active Claims

EOF

CLAIM_COUNT=0
for claim in COORDINATION/claims/*.claim; do
    [ -f "$claim" ] || continue

    CLAIMED_BY=$(python3 -c "import json; print(json.load(open('$claim')).get('claimed_by', 'unknown'))" 2>/dev/null || echo "unknown")
    RESOURCE=$(python3 -c "import json; print(json.load(open('$claim')).get('resource_name', 'unknown'))" 2>/dev/null || echo "unknown")
    TYPE=$(python3 -c "import json; print(json.load(open('$claim')).get('resource_type', 'unknown'))" 2>/dev/null || echo "unknown")
    EXPIRES=$(python3 -c "import json; print(json.load(open('$claim')).get('expires_at', ''))" 2>/dev/null || echo "")

    echo "- **$TYPE/$RESOURCE** - $CLAIMED_BY (expires $EXPIRES)" >> COORDINATION/STATUS_BOARD.md
    CLAIM_COUNT=$((CLAIM_COUNT + 1))
done

if [ $CLAIM_COUNT -eq 0 ]; then
    echo "(No active claims)" >> COORDINATION/STATUS_BOARD.md
fi

# Add recent messages
cat >> COORDINATION/STATUS_BOARD.md <<'EOF'

---

## 📬 Recent Messages (Last 5)

EOF

MSG_COUNT=0
for msg in $(ls -t COORDINATION/messages/broadcast/*.json 2>/dev/null | head -5); do
    [ -f "$msg" ] || continue

    FROM=$(python3 -c "import json; print(json.load(open('$msg')).get('from', 'unknown'))" 2>/dev/null || echo "unknown")
    SUBJECT=$(python3 -c "import json; print(json.load(open('$msg')).get('subject', ''))" 2>/dev/null || echo "")
    TIME=$(python3 -c "import json; print(json.load(open('$msg')).get('timestamp', ''))" 2>/dev/null || echo "")

    echo "- **$TIME** - $FROM → broadcast: \"$SUBJECT\"" >> COORDINATION/STATUS_BOARD.md
    MSG_COUNT=$((MSG_COUNT + 1))
done

if [ $MSG_COUNT -eq 0 ]; then
    echo "(No recent messages)" >> COORDINATION/STATUS_BOARD.md
fi

# Add footer
cat >> COORDINATION/STATUS_BOARD.md <<'EOF'

---

**Auto-refreshes:** Every heartbeat
**View:** `cat COORDINATION/STATUS_BOARD.md`
**Detailed Status:** `./COORDINATION/scripts/session-status.sh`
**Check Messages:** `./COORDINATION/scripts/session-check-messages.sh`

🤝⚡📊
EOF

# Silent success
