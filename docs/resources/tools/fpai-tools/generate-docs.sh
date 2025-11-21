#!/bin/bash

# DOCUMENTATION GENERATOR
# Purpose: Auto-generate documentation from code analysis
# Usage: ./generate-docs.sh <script-file> [output-file]
# Analyzes code and creates comprehensive markdown documentation

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
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n${CYAN}$1${NC}\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

if [ -z "$1" ]; then
    print_error "Usage: $0 <script-file> [output-file]"
    echo ""
    echo "Examples:"
    echo "  $0 ai-cross-verify.sh"
    echo "  $0 register-with-registry.sh REGISTRY_DOCS.md"
    exit 1
fi

SCRIPT_FILE="$1"
SCRIPT_NAME=$(basename "$SCRIPT_FILE" .sh)

if [ ! -f "$SCRIPT_FILE" ]; then
    print_error "Script not found: $SCRIPT_FILE"
    exit 1
fi

# Determine output file
if [ -n "$2" ]; then
    OUTPUT_FILE="$2"
else
    OUTPUT_FILE="/Users/jamessunheart/Development/SERVICES/ops/${SCRIPT_NAME^^}_DOCUMENTATION.md"
fi

print_header "Documentation Generator"
echo ""
print_info "Analyzing: $SCRIPT_FILE"
print_info "Output: $OUTPUT_FILE"
echo ""

# Extract metadata from script
PURPOSE=$(grep "^# Purpose:" "$SCRIPT_FILE" | head -1 | sed 's/# Purpose: //')
USAGE=$(grep "^# Usage:" "$SCRIPT_FILE" | head -1 | sed 's/# Usage: //')

# Count lines of code
LOC=$(grep -v "^#" "$SCRIPT_FILE" | grep -v "^$" | wc -l | tr -d ' ')

# Find functions
FUNCTIONS=$(grep "^[a-zA-Z_][a-zA-Z0-9_]*() {" "$SCRIPT_FILE" | sed 's/() {.*//' || echo "None")

# Check for API calls
HAS_API=$(grep -q "curl" "$SCRIPT_FILE" && echo "Yes" || echo "No")

# Check for SSH
HAS_SSH=$(grep -q "ssh" "$SCRIPT_FILE" && echo "Yes" || echo "No")

# Generate documentation
cat > "$OUTPUT_FILE" << HEADER
# ${SCRIPT_NAME^^} Documentation

**Purpose:** ${PURPOSE:-Auto-generated documentation}

**Script:** \`${SCRIPT_FILE}\`
**Generated:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")

---

## Overview

HEADER

# Add purpose section
cat >> "$OUTPUT_FILE" << OVERVIEW
### What It Does

${PURPOSE:-This script performs automated operations for Full Potential AI.}

### Quick Stats

- **Lines of Code:** $LOC
- **Uses API Calls:** $HAS_API
- **Uses SSH:** $HAS_SSH
- **Language:** Bash

---

## Usage

\`\`\`bash
$USAGE
\`\`\`

OVERVIEW

# Extract and document functions
if [ "$FUNCTIONS" != "None" ]; then
    cat >> "$OUTPUT_FILE" << 'FUNCTIONS_HEADER'

---

## Functions

FUNCTIONS_HEADER

    echo "$FUNCTIONS" | while read -r func; do
        [ -z "$func" ] && continue
        cat >> "$OUTPUT_FILE" << FUNCTION_ENTRY

### \`$func()\`

**Purpose:** [Auto-detected function]

FUNCTION_ENTRY
    done
fi

# Add examples section
cat >> "$OUTPUT_FILE" << 'EXAMPLES'

---

## Examples

### Basic Usage

```bash
# Example 1: Basic execution
./SCRIPTNAME

# Example 2: With options
./SCRIPTNAME --option value
```

EXAMPLES

# Replace SCRIPTNAME with actual name
sed -i.bak "s/SCRIPTNAME/${SCRIPT_NAME}.sh/g" "$OUTPUT_FILE" 2>/dev/null || \
    sed -i "" "s/SCRIPTNAME/${SCRIPT_NAME}.sh/g" "$OUTPUT_FILE" 2>/dev/null

# Add integration section
cat >> "$OUTPUT_FILE" << 'INTEGRATION'

---

## Integration

### Sacred Loop

This script can be integrated into the Sacred Loop automation:

```bash
# Add to sacred-loop.sh Step X
if [ -x "./SCRIPTNAME" ]; then
    ./SCRIPTNAME [args]
fi
```

### Manual Execution

```bash
cd /Users/jamessunheart/Development/RESOURCES/tools/fpai-tools
./SCRIPTNAME [args]
```

INTEGRATION

sed -i.bak "s/SCRIPTNAME/${SCRIPT_NAME}.sh/g" "$OUTPUT_FILE" 2>/dev/null || \
    sed -i "" "s/SCRIPTNAME/${SCRIPT_NAME}.sh/g" "$OUTPUT_FILE" 2>/dev/null

# Add troubleshooting
cat >> "$OUTPUT_FILE" << 'TROUBLESHOOTING'

---

## Troubleshooting

### Common Issues

**Issue:** Script fails with permission denied
**Fix:** `chmod +x ./SCRIPTNAME`

**Issue:** Command not found
**Fix:** Run from correct directory or use full path

**Issue:** API calls failing
**Fix:** Check network connectivity and API endpoints

TROUBLESHOOTING

sed -i.bak "s/SCRIPTNAME/${SCRIPT_NAME}.sh/g" "$OUTPUT_FILE" 2>/dev/null || \
    sed -i "" "s/SCRIPTNAME/${SCRIPT_NAME}.sh/g" "$OUTPUT_FILE" 2>/dev/null

# Add footer
cat >> "$OUTPUT_FILE" << 'FOOTER'

---

**Auto-generated documentation**
**Tool:** generate-docs.sh
**Sacred Loop:** Automation support

🌐⚡💎
FOOTER

# Clean up backup files
rm -f "${OUTPUT_FILE}.bak"

print_success "Documentation generated: $OUTPUT_FILE"
echo ""
print_info "Edit the file to add:"
echo "  - Detailed function descriptions"
echo "  - More usage examples"
echo "  - Configuration options"
echo "  - Performance metrics"
echo ""
