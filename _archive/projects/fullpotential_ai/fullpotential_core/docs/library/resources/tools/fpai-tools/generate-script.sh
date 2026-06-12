#!/bin/bash

# SCRIPT GENERATOR - Meta-tool for creating new bash scripts
# Purpose: Generate production-ready bash scripts from simple specs
# Usage: ./generate-script.sh <script-name> <purpose> [options]
# Makes implementing new features 10x faster

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n${CYAN}$1${NC}\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# Check arguments
if [ -z "$1" ] || [ -z "$2" ]; then
    print_error "Usage: $0 <script-name> <purpose> [options]"
    echo ""
    echo "Examples:"
    echo "  $0 verify-deployment 'Verify service is running correctly'"
    echo "  $0 backup-database 'Backup production database' --with-api"
    echo "  $0 monitor-health 'Monitor service health' --cron"
    echo ""
    echo "Options:"
    echo "  --with-api      Include API call helpers"
    echo "  --with-ssh      Include SSH helpers"
    echo "  --cron          Optimize for cron jobs (no interactive prompts)"
    echo "  --sacred-loop   Include Sacred Loop integration"
    exit 1
fi

SCRIPT_NAME="$1"
PURPOSE="$2"
shift 2

# Parse options
WITH_API=false
WITH_SSH=false
CRON_MODE=false
SACRED_LOOP=false

while [ $# -gt 0 ]; do
    case "$1" in
        --with-api) WITH_API=true ;;
        --with-ssh) WITH_SSH=true ;;
        --cron) CRON_MODE=true ;;
        --sacred-loop) SACRED_LOOP=true ;;
        *) print_warning "Unknown option: $1" ;;
    esac
    shift
done

print_header "Script Generator"
echo ""
print_info "Script: $SCRIPT_NAME.sh"
print_info "Purpose: $PURPOSE"
echo ""

# Determine output location
OUTPUT_DIR="/Users/jamessunheart/Development/RESOURCES/tools/fpai-tools"
OUTPUT_FILE="${OUTPUT_DIR}/${SCRIPT_NAME}.sh"

if [ -f "$OUTPUT_FILE" ]; then
    print_error "Script already exists: $OUTPUT_FILE"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Cancelled"
        exit 0
    fi
fi

print_info "Generating script..."

# Generate script header
cat > "$OUTPUT_FILE" << 'HEADER'
#!/bin/bash

# AUTO-GENERATED SCRIPT
HEADER

# Add metadata
cat >> "$OUTPUT_FILE" << METADATA
# Purpose: ${PURPOSE}
# Generated: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
# Usage: ./${SCRIPT_NAME}.sh [arguments]

set -e

# Colors
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
YELLOW='\\033[1;33m'
RED='\\033[0;31m'
CYAN='\\033[0;36m'
MAGENTA='\\033[0;35m'
NC='\\033[0m'

print_info() { echo -e "\${BLUE}ℹ️  \$1\${NC}"; }
print_success() { echo -e "\${GREEN}✅ \$1\${NC}"; }
print_warning() { echo -e "\${YELLOW}⚠️  \$1\${NC}"; }
print_error() { echo -e "\${RED}❌ \$1\${NC}"; }
print_header() { echo -e "\${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\${NC}"; echo -e "\${CYAN}\$1\${NC}"; echo -e "\${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\${NC}"; }

print_header "${PURPOSE}"
echo ""

METADATA

# Add SSH helpers if requested
if [ "$WITH_SSH" = true ]; then
    cat >> "$OUTPUT_FILE" << 'SSH_HELPERS'
# SSH Configuration
SERVER="${SERVER:-198.54.123.234}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/fpai_deploy_ed25519}"
SSH_OPTS="-i ${SSH_KEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

if [ ! -f "$SSH_KEY" ]; then
    print_error "SSH key not found: $SSH_KEY"
    print_info "Run ./setup-ssh-access.sh first"
    exit 1
fi

print_info "SSH configured: $SERVER"

# SSH helper function
run_remote() {
    local cmd="$1"
    ssh $SSH_OPTS "$SERVER" "$cmd"
}

SSH_HELPERS
fi

# Add API helpers if requested
if [ "$WITH_API" = true ]; then
    cat >> "$OUTPUT_FILE" << 'API_HELPERS'
# API Configuration
REGISTRY_URL="${REGISTRY_URL:-http://198.54.123.234:8000}"
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://198.54.123.234:8001}"

# API helper function
call_api() {
    local method="$1"
    local url="$2"
    local data="${3:-}"

    if [ -n "$data" ]; then
        curl -s -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$url"
    fi
}

# Health check helper
check_health() {
    local service_url="$1"
    local response=$(curl -s "${service_url}/health" 2>/dev/null || echo "FAILED")

    if echo "$response" | grep -q '"status":"active"'; then
        return 0
    else
        return 1
    fi
}

API_HELPERS
fi

# Add main logic placeholder
cat >> "$OUTPUT_FILE" << 'MAIN_LOGIC'

# Main Logic
main() {
    # TODO: Implement main functionality here

    print_info "Starting..."

    # Your code here

    print_success "Complete!"
}

MAIN_LOGIC

# Add error handling
if [ "$CRON_MODE" = false ]; then
    cat >> "$OUTPUT_FILE" << 'ERROR_HANDLING'
# Error handling
trap 'print_error "Script failed at line $LINENO"' ERR

ERROR_HANDLING
fi

# Add Sacred Loop integration if requested
if [ "$SACRED_LOOP" = true ]; then
    cat >> "$OUTPUT_FILE" << 'SACRED_LOOP_INTEGRATION'
# Sacred Loop Integration
SACRED_LOOP_STEP="${SACRED_LOOP_STEP:-}"

if [ -n "$SACRED_LOOP_STEP" ]; then
    print_info "Running as Sacred Loop Step $SACRED_LOOP_STEP"
fi

SACRED_LOOP_INTEGRATION
fi

# Add execution
cat >> "$OUTPUT_FILE" << 'EXECUTION'

# Execute main function
main "$@"

EXECUTION

# Make executable
chmod +x "$OUTPUT_FILE"

print_success "Script generated: $OUTPUT_FILE"
echo ""

# Show what was included
print_info "Features included:"
echo "  - Standard error handling"
echo "  - Color output helpers"
[ "$WITH_SSH" = true ] && echo "  - SSH helpers (run_remote function)"
[ "$WITH_API" = true ] && echo "  - API helpers (call_api, check_health)"
[ "$CRON_MODE" = true ] && echo "  - Cron mode (no interactive prompts)"
[ "$SACRED_LOOP" = true ] && echo "  - Sacred Loop integration"

echo ""
print_info "Next steps:"
echo "  1. Edit: $OUTPUT_FILE"
echo "  2. Implement main() function"
echo "  3. Test: ./$SCRIPT_NAME.sh"
echo "  4. Document: Add to relevant .md file"

echo ""
print_success "Ready to implement! 🚀"
echo ""
