#!/bin/bash

# SNAPSHOT AUTOMATION
# Blueprint: 1-SYSTEM-BLUEPRINT.txt - Section 2 (Sacred Loop Step 7: Registry + Dashboard update)
# Purpose: Automated daily SSOT snapshots and gap analyses
# Usage: ./snapshot-daily.sh [--email recipient@email.com]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FP_TOOLS="${BASE_DIR}/fullpotential-tools/bin/fp-tools"

# Configuration
EMAIL_TO=""
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --email)
            EMAIL_TO="$2"
            shift 2
            ;;
        --slack)
            SLACK_WEBHOOK="$2"
            shift 2
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_info "Full Potential AI - Daily Snapshot Automation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if fp-tools exists
if [ ! -x "$FP_TOOLS" ]; then
    print_error "Full Potential Tools not found at: $FP_TOOLS"
    exit 1
fi

# Run workflow
print_info "Running snapshot + gap analysis workflow..."

if "$FP_TOOLS" workflow --scan-github; then
    print_success "Workflow completed"
else
    print_error "Workflow failed"
    exit 1
fi

# Get latest files
SNAPSHOT_DIR="${BASE_DIR}/fullpotential-tools/output/snapshots"
GAP_DIR="${BASE_DIR}/fullpotential-tools/output/gap-analyses"

LATEST_SNAPSHOT=$(ls -t "$SNAPSHOT_DIR"/SSOT_SNAPSHOT_*.md 2>/dev/null | head -1)
LATEST_GAP=$(ls -t "$GAP_DIR"/GAP_ANALYSIS_*.md 2>/dev/null | head -1)

if [ -z "$LATEST_SNAPSHOT" ] || [ -z "$LATEST_GAP" ]; then
    print_error "Snapshot or gap analysis files not found"
    exit 1
fi

print_info "Generated files:"
echo "  📄 Snapshot: $(basename "$LATEST_SNAPSHOT")"
echo "  📄 Gap Analysis: $(basename "$LATEST_GAP")"
echo ""

# Extract summary from gap analysis
print_info "Extracting summary..."

CRITICAL_GAPS=$(grep "🟥 CRITICAL" "$LATEST_GAP" | wc -l | tr -d ' ')
HIGH_GAPS=$(grep "🟧 HIGH" "$LATEST_GAP" | wc -l | tr -d ' ')
MEDIUM_GAPS=$(grep "🟨 MEDIUM" "$LATEST_GAP" | wc -l | tr -d ' ')

SUMMARY=$(cat <<EOF
Full Potential AI - Daily Snapshot Summary
$(date +"%Y-%m-%d %H:%M UTC")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

GAP ANALYSIS SUMMARY

🟥 Critical Gaps: $CRITICAL_GAPS
🟧 High Priority: $HIGH_GAPS
🟨 Medium Priority: $MEDIUM_GAPS

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files generated:
- Snapshot: $(basename "$LATEST_SNAPSHOT")
- Gap Analysis: $(basename "$LATEST_GAP")

View full reports:
- $LATEST_SNAPSHOT
- $LATEST_GAP

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐⚡💎
EOF
)

echo "$SUMMARY"

# Send email if configured
if [ -n "$EMAIL_TO" ]; then
    print_info "Sending email to: $EMAIL_TO"

    if command -v mail >/dev/null 2>&1; then
        echo "$SUMMARY" | mail -s "FPAI Daily Snapshot - $(date +%Y-%m-%d)" "$EMAIL_TO"
        print_success "Email sent"
    else
        print_warning "mail command not found - skipping email"
    fi
fi

# Send Slack notification if configured
if [ -n "$SLACK_WEBHOOK" ]; then
    print_info "Sending Slack notification..."

    SLACK_MSG=$(cat <<EOF
{
  "text": "📊 *FPAI Daily Snapshot - $(date +%Y-%m-%d)*",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Gap Analysis Summary*\n🟥 Critical: $CRITICAL_GAPS\n🟧 High: $HIGH_GAPS\n🟨 Medium: $MEDIUM_GAPS"
      }
    }
  ]
}
EOF
)

    if curl -X POST -H 'Content-type: application/json' --data "$SLACK_MSG" "$SLACK_WEBHOOK" >/dev/null 2>&1; then
        print_success "Slack notification sent"
    else
        print_warning "Failed to send Slack notification"
    fi
fi

print_success "Daily snapshot automation complete! 🌐⚡💎"
