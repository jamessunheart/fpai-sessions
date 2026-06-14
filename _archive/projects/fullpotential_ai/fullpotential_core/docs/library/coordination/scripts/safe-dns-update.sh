#!/bin/bash
# safe-dns-update.sh - Enforced safe DNS updates with backups and validation
# Usage: ./safe-dns-update.sh <domain> <action>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../dns_backups"
SAFEGUARDS_DOC="$SCRIPT_DIR/../DNS_SAFEGUARDS.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Protected domains
PROTECTED_DOMAINS=("fullpotential.com" "coravida.com" "globalsky.com" "jamesrick.com")

error() {
    echo -e "${RED}❌ ERROR: $1${NC}" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}" >&2
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

info() {
    echo -e "ℹ️  $1"
}

check_protected_domain() {
    local domain=$1
    for protected in "${PROTECTED_DOMAINS[@]}"; do
        if [[ "$domain" == "$protected" ]]; then
            return 0
        fi
    done
    return 1
}

backup_dns() {
    local domain=$1
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="$BACKUP_DIR/${domain}_${timestamp}.xml"

    info "Creating backup for $domain..."

    # Extract SLD and TLD
    local sld="${domain%.*}"
    local tld="${domain##*.}"

    # Fetch current DNS via API
    ssh root@198.54.123.234 "curl -s 'https://api.namecheap.com/xml.response?ApiUser=globalskypower&ApiKey=1970bffd68144b08a4bea27acbac0854&UserName=globalskypower&Command=namecheap.domains.dns.getHosts&ClientIp=198.54.123.234&SLD=${sld}&TLD=${tld}'" > "$backup_file"

    if [[ -f "$backup_file" ]] && [[ -s "$backup_file" ]]; then
        success "Backup created: $backup_file"

        # Show current records
        echo ""
        info "Current DNS records for $domain:"
        grep -oP 'Name="[^"]*".*?Address="[^"]*"' "$backup_file" | head -10 || echo "  (parsing failed - check XML backup)"
        echo ""

        return 0
    else
        error "Failed to create backup for $domain"
    fi
}

confirm_changes() {
    local domain=$1
    local action=$2

    echo ""
    echo "════════════════════════════════════════════════════"
    warning "ABOUT TO MODIFY DNS FOR: $domain"
    echo "════════════════════════════════════════════════════"
    echo "Action: $action"
    echo ""

    if check_protected_domain "$domain"; then
        warning "This is a PROTECTED domain with critical email/website!"
        echo ""
    fi

    echo -n "Type 'yes' to proceed, anything else to cancel: "
    read -r response

    if [[ "$response" != "yes" ]]; then
        error "Cancelled by user"
    fi

    success "User confirmed - proceeding with changes"
    echo ""
}

show_safeguards() {
    if [[ -f "$SAFEGUARDS_DOC" ]]; then
        info "Safeguards documentation: $SAFEGUARDS_DOC"
        echo ""
    else
        warning "Safeguards document not found at $SAFEGUARDS_DOC"
    fi
}

# Main script
main() {
    local domain=$1
    local action=$2

    if [[ -z "$domain" ]]; then
        error "Usage: $0 <domain> <action>"
    fi

    echo "════════════════════════════════════════════════════"
    echo "🛡️  SAFE DNS UPDATE - Protected by Safeguards"
    echo "════════════════════════════════════════════════════"
    echo ""

    # Check if safeguards doc exists
    show_safeguards

    # Create backup
    backup_dns "$domain"

    # Confirm with user
    confirm_changes "$domain" "$action"

    # At this point, the calling script should perform the actual DNS update
    # This script just handles the safety checks and backups

    success "Pre-flight checks complete - safe to proceed with DNS update"
    echo ""
    echo "NEXT STEPS:"
    echo "1. Make your DNS changes"
    echo "2. Verify changes propagated: dig $domain +short"
    echo "3. Test email/website functionality"
    echo "4. Document changes in DNS_SAFEGUARDS.md"
    echo ""
}

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Run main
main "$@"
