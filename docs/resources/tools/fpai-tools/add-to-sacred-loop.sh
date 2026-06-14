#!/bin/bash

# SACRED LOOP INTEGRATION HELPER
# Purpose: Easily add new automation steps to Sacred Loop
# Usage: ./add-to-sacred-loop.sh <step-number> <script-path> <description>
# Makes integrating new features into Sacred Loop trivial

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n${CYAN}$1${NC}\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
    print_error "Usage: $0 <step-number> <script-path> <description>"
    echo ""
    echo "Examples:"
    echo "  $0 5 ./ai-cross-verify.sh 'AI cross-verification'"
    echo "  $0 7 ./register-with-registry.sh 'Registry registration'"
    echo ""
    echo "Sacred Loop Steps:"
    echo "  Step 1: Architect provides intent (Manual)"
    echo "  Step 2: AI generates SPEC (Automated)"
    echo "  Step 3: Coordinator packages (Automated)"
    echo "  Step 4: Apprentice builds (AI-assisted)"
    echo "  Step 5: Verifier checks quality (Automated)"
    echo "  Step 6: Deployer deploys (Automated)"
    echo "  Step 7: Registry updates (Automated)"
    echo "  Step 8: Architect decides next (Manual)"
    exit 1
fi

STEP_NUMBER="$1"
SCRIPT_PATH="$2"
DESCRIPTION="$3"

SACRED_LOOP="/Users/jamessunheart/Development/SERVICES/ops/sacred-loop.sh"

if [ ! -f "$SACRED_LOOP" ]; then
    print_error "Sacred Loop not found: $SACRED_LOOP"
    exit 1
fi

if [ ! -f "$SCRIPT_PATH" ]; then
    print_error "Script not found: $SCRIPT_PATH"
    exit 1
fi

# Get absolute path
SCRIPT_PATH=$(cd "$(dirname "$SCRIPT_PATH")" && pwd)/$(basename "$SCRIPT_PATH")

print_header "Sacred Loop Integration Helper"
echo ""
print_info "Step: $STEP_NUMBER"
print_info "Script: $SCRIPT_PATH"
print_info "Description: $DESCRIPTION"
echo ""

# Backup Sacred Loop
BACKUP_FILE="${SACRED_LOOP}.backup.$(date +%Y%m%d-%H%M%S)"
cp "$SACRED_LOOP" "$BACKUP_FILE"
print_info "Backup created: $BACKUP_FILE"

# Find the step section in sacred-loop.sh
STEP_MARKER="# STEP ${STEP_NUMBER}:"

if ! grep -q "$STEP_MARKER" "$SACRED_LOOP"; then
    print_error "Step $STEP_NUMBER not found in Sacred Loop"
    print_info "Available steps:"
    grep "# STEP [0-9]:" "$SACRED_LOOP" | head -10
    exit 1
fi

# Generate integration code
INTEGRATION_CODE="
# ${DESCRIPTION^^}
${DESCRIPTION^^}_SCRIPT=\"${SCRIPT_PATH}\"

if [ -x \"\$${DESCRIPTION^^}_SCRIPT\" ]; then
    print_info \"Running ${DESCRIPTION}...\"

    if \"\$${DESCRIPTION^^}_SCRIPT\" \"\$REPO_DIR\"; then
        print_success \"${DESCRIPTION} complete\"
    else
        print_warning \"${DESCRIPTION} found issues\"

        read -p \"Continue anyway? (y/N) \" -n 1 -r
        echo
        if [[ ! \$REPLY =~ ^[Yy]$ ]]; then
            print_error \"Stopped by ${DESCRIPTION}\"
            exit 1
        fi
    fi
else
    print_warning \"${DESCRIPTION} not available (skipping)\"
fi
"

# Show what will be added
print_info "Integration code to add:"
echo ""
echo "$INTEGRATION_CODE"
echo ""

read -p "Add this to Sacred Loop Step ${STEP_NUMBER}? (y/N) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Cancelled"
    rm "$BACKUP_FILE"
    exit 0
fi

# Create temporary file with integration
TEMP_FILE=$(mktemp)

# Find line number where step starts
STEP_LINE=$(grep -n "$STEP_MARKER" "$SACRED_LOOP" | cut -d: -f1)

# Add integration after step header
{
    head -n "$STEP_LINE" "$SACRED_LOOP"
    echo ""
    echo "$INTEGRATION_CODE"
    tail -n +"$((STEP_LINE + 1))" "$SACRED_LOOP"
} > "$TEMP_FILE"

# Replace original
mv "$TEMP_FILE" "$SACRED_LOOP"
chmod +x "$SACRED_LOOP"

print_success "Integration complete!"
echo ""
print_info "Changes:"
echo "  - Added ${DESCRIPTION} to Step ${STEP_NUMBER}"
echo "  - Backup: $BACKUP_FILE"
echo ""
print_info "Test the integration:"
echo "  ./sacred-loop.sh <droplet-id> <droplet-name>"
echo ""
print_success "Sacred Loop enhanced! 🚀"
echo ""
