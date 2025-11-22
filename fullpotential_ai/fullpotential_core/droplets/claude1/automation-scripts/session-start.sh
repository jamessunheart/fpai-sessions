#!/bin/bash

# 🤝 Session Start - Register new session
# Creates session file and announces presence

set -e

cd "$(dirname "$0")/../.."

# Generate unique session ID
SESSION_ID="session-$(date +%s)"

# Save current session ID
echo "$SESSION_ID" > COORDINATION/.current_session

# Create session file
cat > "COORDINATION/sessions/${SESSION_ID}.json" <<EOF
{
  "session_id": "$SESSION_ID",
  "started_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "status": "active",
  "current_work": null,
  "capabilities": ["general-purpose", "build", "debug", "deploy"],
  "last_heartbeat": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "heartbeat_count": 0
}
EOF

# Send initial heartbeat
COORDINATION/scripts/session-heartbeat.sh "started" "session initialization" "ACTIVE"

# Auto-confirm pending sessions in REGISTRY.json
REGISTRY_FILE="COORDINATION/sessions/REGISTRY.json"
if [ -f "$REGISTRY_FILE" ]; then
    # Check for pending proposals (sessions with agreed: false)
    PENDING_COUNT=$(grep -c '"agreed": false' "$REGISTRY_FILE" || echo "0")

    if [ "$PENDING_COUNT" -gt 0 ]; then
        echo "🔍 Found $PENDING_COUNT pending session(s) in registry..."
        echo "   Auto-confirming pending sessions..."

        # Update all pending sessions to agreed: true
        if command -v jq &> /dev/null; then
            # Use jq if available (cleaner)
            jq '(.sessions[] | select(.agreed == false)) |= (.agreed = true | .confirmed_at = now | .awaiting_confirmation = false)' "$REGISTRY_FILE" > "${REGISTRY_FILE}.tmp" && mv "${REGISTRY_FILE}.tmp" "$REGISTRY_FILE"
        else
            # Fallback to sed
            sed -i.bak 's/"agreed": false/"agreed": true/g' "$REGISTRY_FILE"
            sed -i.bak 's/"awaiting_confirmation": true/"awaiting_confirmation": false/g' "$REGISTRY_FILE"
            # Add confirmation timestamp
            TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
            sed -i.bak "s/\"agreed\": true/\"agreed\": true,\n      \"confirmed_at\": \"$TIMESTAMP\"/g" "$REGISTRY_FILE"
            rm -f "${REGISTRY_FILE}.bak"
        fi

        # Update last_updated timestamp
        TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")
        sed -i.bak "s/\"last_updated\": \".*\"/\"last_updated\": \"$TIMESTAMP\"/g" "$REGISTRY_FILE"
        rm -f "${REGISTRY_FILE}.bak"

        echo "   ✅ Auto-confirmed pending sessions in REGISTRY"
    fi
fi

# Load and announce known facts
VAULT_URL="https://fullpotential.com/vault"
if [ -f "COORDINATION/KNOWN_FACTS.json" ] || [ -f "docs/coordination/KNOWN_FACTS.json" ]; then
    FACTS_MSG="$SESSION_ID is online. I KNOW: credential_vault=$VAULT_URL, server_ip=198.54.123.234. Ready to work! 🔐⚡"
else
    FACTS_MSG="$SESSION_ID is online and ready to work"
fi

# Send broadcast message
COORDINATION/scripts/session-send-message.sh broadcast "New session started" "$FACTS_MSG"

echo "✅ Session registered: $SESSION_ID"
echo ""
echo "📊 View status: ./COORDINATION/scripts/session-status.sh"
echo "📬 Check messages: ./COORDINATION/scripts/session-check-messages.sh"
echo "🔒 Claim work: ./COORDINATION/scripts/session-claim.sh [type] [name]"
