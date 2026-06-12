#!/bin/bash

# 🔐 Set Credential - Store encrypted credential locally
# Usage: ./session-set-credential.sh <name> <value> [type] [service]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_SCRIPT="$SCRIPT_DIR/credential_vault.py"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get parameters
NAME="$1"
VALUE="$2"
TYPE="${3:-api_key}"
SERVICE="${4:-}"

# Validate
if [ -z "$NAME" ] || [ -z "$VALUE" ]; then
    echo "Usage: $0 <name> <value> [type] [service]"
    echo ""
    echo "Examples:"
    echo "  $0 anthropic_api_key sk-ant-xxxxx api_key anthropic"
    echo "  $0 openai_api_key sk-xxxxx api_key openai"
    echo "  $0 github_token ghp_xxxxx access_token github"
    echo "  $0 database_url postgresql://... connection_string postgres"
    echo ""
    echo "Types: api_key, access_token, password, connection_string, secret"
    exit 1
fi

# Check if FPAI_CREDENTIALS_KEY is set
if [ -z "$FPAI_CREDENTIALS_KEY" ]; then
    echo -e "${RED}❌ FPAI_CREDENTIALS_KEY not set${NC}"
    echo ""
    echo "Generate a master key and set it in your shell profile:"
    echo ""
    echo -e "${YELLOW}# Generate key${NC}"
    echo "python3 -c 'import secrets; print(secrets.token_hex(32))'"
    echo ""
    echo -e "${YELLOW}# Add to ~/.zshrc or ~/.bashrc:${NC}"
    echo "export FPAI_CREDENTIALS_KEY=your_generated_key"
    echo ""
    echo -e "${YELLOW}# Then reload:${NC}"
    echo "source ~/.zshrc  # or source ~/.bashrc"
    exit 1
fi

# Store credential
if [ -n "$SERVICE" ]; then
    python3 "$VAULT_SCRIPT" set "$NAME" "$VALUE" "$TYPE" "$SERVICE"
else
    python3 "$VAULT_SCRIPT" set "$NAME" "$VALUE" "$TYPE"
fi

echo -e "${GREEN}✅ Credential stored: $NAME${NC}"
echo -e "${YELLOW}🔍 Retrieve with: ./session-get-credential.sh $NAME${NC}"

exit 0
