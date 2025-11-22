#!/bin/bash

# 🔐 Get Server Credential - Fetch credential from credentials-manager service
# Usage: ./session-get-server-credential.sh <credential_id> [server_url]

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get parameters
CREDENTIAL_ID="$1"
SERVER_URL="${2:-http://198.54.123.234:8025}"

# Validate
if [ -z "$CREDENTIAL_ID" ]; then
    echo "Usage: $0 <credential_id> [server_url]"
    echo ""
    echo "Examples:"
    echo "  $0 1                                    # Get credential ID 1 from default server"
    echo "  $0 5 http://localhost:8025              # Get from local server"
    echo "  $0 anthropic_api_key                    # Get by name (if server supports it)"
    echo ""
    echo "Requires: CREDENTIALS_MANAGER_TOKEN environment variable"
    exit 1
fi

# Check if token is set
if [ -z "$CREDENTIALS_MANAGER_TOKEN" ]; then
    echo -e "${RED}❌ CREDENTIALS_MANAGER_TOKEN not set${NC}" >&2
    echo "" >&2
    echo "Get admin token from credentials-manager:" >&2
    echo "  curl -X POST http://server:8025/auth/admin \\" >&2
    echo "    -d 'username=admin&password=your_password'" >&2
    echo "" >&2
    echo "Then set:" >&2
    echo "  export CREDENTIALS_MANAGER_TOKEN=your_token" >&2
    exit 1
fi

# Fetch credential from server
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "Authorization: Bearer $CREDENTIALS_MANAGER_TOKEN" \
    "$SERVER_URL/credentials/$CREDENTIAL_ID")

# Split response into body and status code
HTTP_BODY=$(echo "$RESPONSE" | head -n -1)
HTTP_STATUS=$(echo "$RESPONSE" | tail -n 1)

if [ "$HTTP_STATUS" -eq 200 ]; then
    # Extract value from JSON (requires jq)
    if command -v jq &> /dev/null; then
        echo "$HTTP_BODY" | jq -r '.value'
    else
        # Fallback: output full JSON
        echo "$HTTP_BODY"
        echo -e "${YELLOW}💡 Install jq for cleaner output: brew install jq${NC}" >&2
    fi
else
    echo -e "${RED}❌ Failed to fetch credential (HTTP $HTTP_STATUS)${NC}" >&2
    echo "$HTTP_BODY" >&2
    exit 1
fi

exit 0
