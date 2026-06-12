#!/bin/bash

# 🔐 Get Credential - Retrieve encrypted credential
# Usage: ./session-get-credential.sh <name>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_SCRIPT="$SCRIPT_DIR/credential_vault.py"

# Colors
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
    echo "  $0 openai_api_key"
    echo "  $0 github_token"
    echo ""
    echo "List all credentials:"
    echo "  ./session-list-credentials.sh"
    exit 1
fi

# Check if FPAI_CREDENTIALS_KEY is set
if [ -z "$FPAI_CREDENTIALS_KEY" ]; then
    echo -e "${RED}❌ FPAI_CREDENTIALS_KEY not set${NC}" >&2
    echo "" >&2
    echo "Set your master key in your shell profile:" >&2
    echo "export FPAI_CREDENTIALS_KEY=your_key" >&2
    exit 1
fi

# Get credential (output only the value, no extra text)
python3 "$VAULT_SCRIPT" get "$NAME"

exit 0
