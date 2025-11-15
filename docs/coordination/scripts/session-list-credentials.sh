#!/bin/bash

# 🔐 List Credentials - Show all stored credentials
# Usage: ./session-list-credentials.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT_SCRIPT="$SCRIPT_DIR/credential_vault.py"

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if FPAI_CREDENTIALS_KEY is set
if [ -z "$FPAI_CREDENTIALS_KEY" ]; then
    echo -e "${RED}❌ FPAI_CREDENTIALS_KEY not set${NC}"
    echo ""
    echo "Set your master key in your shell profile:"
    echo "export FPAI_CREDENTIALS_KEY=your_key"
    exit 1
fi

# List credentials
python3 "$VAULT_SCRIPT" list

exit 0
