#!/bin/bash

# 🔐 Delete Credential - Remove a stored credential
# Usage: ./session-delete-credential.sh <name>

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

# Validate
if [ -z "$NAME" ]; then
    echo "Usage: $0 <name>"
    echo ""
    echo "Examples:"
    echo "  $0 anthropic_api_key"
    echo "  $0 old_github_token"
    exit 1
fi

# Check if FPAI_CREDENTIALS_KEY is set
if [ -z "$FPAI_CREDENTIALS_KEY" ]; then
    echo -e "${RED}❌ FPAI_CREDENTIALS_KEY not set${NC}"
    exit 1
fi

# Delete credential
python3 "$VAULT_SCRIPT" delete "$NAME"

exit 0
