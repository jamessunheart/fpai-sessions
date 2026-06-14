#!/bin/bash

# AI CROSS-VERIFICATION SYSTEM
# Purpose: Multi-AI verification that code matches SPEC
# Usage: ./ai-cross-verify.sh <droplet-directory>
# Adds peer review by different AI models for quality assurance

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
print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_ai() { echo -e "${MAGENTA}🤖 $1${NC}"; }

# Check arguments
if [ -z "$1" ]; then
    print_error "Usage: $0 <droplet-directory>"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/droplet-10-orchestrator"
    echo "  $0 ../droplet-15-recruiter"
    exit 1
fi

DROPLET_DIR="$1"

if [ ! -d "$DROPLET_DIR" ]; then
    print_error "Directory not found: $DROPLET_DIR"
    exit 1
fi

DROPLET_DIR="$(cd "$DROPLET_DIR" && pwd)"
DROPLET_NAME="$(basename "$DROPLET_DIR")"

print_header "AI Cross-Verification System"
echo ""
print_info "Droplet: $DROPLET_NAME"
print_info "Multi-AI peer review: Code vs SPEC validation"
echo ""

# Check for required files
SPEC_FILE="${DROPLET_DIR}/docs/SPEC.md"
CODE_DIR="${DROPLET_DIR}/app"

if [ ! -f "$SPEC_FILE" ]; then
    print_error "SPEC.md not found at: $SPEC_FILE"
    exit 1
fi

if [ ! -d "$CODE_DIR" ]; then
    print_error "app/ directory not found at: $CODE_DIR"
    print_warning "Has the code been implemented yet?"
    exit 1
fi

# Create verification report directory
REPORT_DIR="${DROPLET_DIR}/verification-reports"
mkdir -p "$REPORT_DIR"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
REPORT_FILE="${REPORT_DIR}/ai-verification-${TIMESTAMP}.md"

print_info "Generating verification report: ${REPORT_FILE}"
echo ""

# Start building verification prompt
VERIFICATION_PROMPT="# AI Cross-Verification Task

You are an expert code reviewer. Your task is to verify if the implemented code matches the SPEC requirements.

## SPEC Requirements

$(cat "$SPEC_FILE")

## Implemented Code

### File Structure
$(find "$CODE_DIR" -type f -name "*.py" | sed "s|$CODE_DIR/||")

"

# Add code files to prompt
print_info "Analyzing code files..."
for file in $(find "$CODE_DIR" -type f -name "*.py"); do
    filename=$(basename "$file")
    VERIFICATION_PROMPT+="
### $filename
\`\`\`python
$(cat "$file")
\`\`\`

"
done

VERIFICATION_PROMPT+="

## Verification Tasks

Please perform the following verification:

1. **SPEC Completeness Check**
   - Are all required endpoints from SPEC implemented?
   - Are all data models from SPEC present?
   - Are all business logic requirements met?
   - List any SPEC requirements that are MISSING in code

2. **UDC Compliance Check**
   - Are all 5 UDC endpoints implemented? (/health, /capabilities, /state, /dependencies, /message)
   - Do responses match UDC-compliant models?
   - Are UDC status values correct (active/inactive/error)?

3. **Code Quality Check**
   - Are there proper error handlers?
   - Is input validation present?
   - Are there security issues (SQL injection, XSS, etc.)?
   - Is logging implemented?

4. **Data Model Consistency**
   - Do request/response models match SPEC?
   - Are field types correct?
   - Are optional vs required fields correct?

5. **Business Logic Correctness**
   - Does the logic match SPEC description?
   - Are edge cases handled?
   - Are there obvious bugs or logic errors?

## Output Format

Provide verification results in this format:

### ✅ Implemented Correctly
- [List features that match SPEC exactly]

### ⚠️ Partially Implemented
- [List features that are present but incomplete or incorrect]
- [Explain what's missing or wrong]

### ❌ Missing from Code
- [List SPEC requirements not found in code]

### 🐛 Potential Issues
- [List any bugs, security issues, or logic errors]

### 📊 Overall Assessment
- **Completeness Score:** X/10
- **Quality Score:** X/10
- **Confidence Level:** High/Medium/Low
- **Ready for Deployment:** Yes/No
- **Recommendation:** [Deploy / Fix issues first / Major rework needed]

### 🔧 Required Fixes
1. [Specific fix needed]
2. [Specific fix needed]
...
"

# Save prompt to file for manual review if needed
PROMPT_FILE="${REPORT_DIR}/verification-prompt-${TIMESTAMP}.txt"
echo "$VERIFICATION_PROMPT" > "$PROMPT_FILE"
print_success "Verification prompt saved: $PROMPT_FILE"

# Try to use Claude API if available
print_info "Attempting AI verification..."
echo ""

if command -v claude >/dev/null 2>&1 && [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    print_ai "Using Claude API for verification..."

    # Use Claude API for verification
    CLAUDE_RESPONSE=$(echo "$VERIFICATION_PROMPT" | claude --model claude-3-5-sonnet-20241022 2>&1 || echo "FAILED")

    if [ "$CLAUDE_RESPONSE" != "FAILED" ]; then
        echo "$CLAUDE_RESPONSE" > "${REPORT_DIR}/claude-verification-${TIMESTAMP}.md"
        print_success "Claude verification complete"

        # Add to main report
        cat > "$REPORT_FILE" << EOF
# AI Cross-Verification Report

**Droplet:** $DROPLET_NAME
**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Verified By:** Claude AI + Code Quality Tools

---

## Claude AI Verification

$CLAUDE_RESPONSE

---

EOF
    else
        print_warning "Claude API verification failed"
    fi
fi

# Try OpenAI if available (for cross-verification)
if command -v gpt >/dev/null 2>&1 && [ -n "${OPENAI_API_KEY:-}" ]; then
    print_ai "Using GPT-4 for cross-verification..."

    GPT_RESPONSE=$(echo "$VERIFICATION_PROMPT" | gpt --model gpt-4 2>&1 || echo "FAILED")

    if [ "$GPT_RESPONSE" != "FAILED" ]; then
        echo "$GPT_RESPONSE" > "${REPORT_DIR}/gpt-verification-${TIMESTAMP}.md"
        print_success "GPT-4 verification complete"

        # Add to main report
        cat >> "$REPORT_FILE" << EOF

## GPT-4 Cross-Verification

$GPT_RESPONSE

---

EOF
    else
        print_warning "GPT-4 API verification failed"
    fi
fi

# Fallback: Create template report for manual AI verification
if [ ! -f "$REPORT_FILE" ]; then
    print_warning "No AI APIs available - creating manual verification template"

    cat > "$REPORT_FILE" << EOF
# AI Cross-Verification Report

**Droplet:** $DROPLET_NAME
**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Status:** Manual Verification Required

---

## Instructions

1. Copy the verification prompt from: $PROMPT_FILE
2. Paste into your preferred AI:
   - Claude (claude.ai)
   - ChatGPT (chat.openai.com)
   - Other LLM
3. Copy the AI response back here
4. Act on the recommendations

---

## Verification Prompt

Prompt saved at: $PROMPT_FILE

To verify manually:
\`\`\`bash
# Option 1: Use Claude Web
cat $PROMPT_FILE
# Copy output and paste to claude.ai

# Option 2: Use ChatGPT
cat $PROMPT_FILE
# Copy output and paste to chat.openai.com

# Option 3: Use API directly
cat $PROMPT_FILE | claude --model claude-3-5-sonnet-20241022
\`\`\`

---

## Verification Results

[PASTE AI VERIFICATION RESULTS HERE]

---

EOF
fi

# Add static code analysis
print_info "Running static code analysis..."

cat >> "$REPORT_FILE" << EOF

## Static Code Analysis

EOF

# Count endpoints
ENDPOINT_COUNT=$(grep -r "@app\." "$CODE_DIR" | grep -E "(get|post|put|delete|patch)" | wc -l | tr -d ' ')
cat >> "$REPORT_FILE" << EOF
### Code Statistics
- **Total Endpoints:** $ENDPOINT_COUNT
- **Python Files:** $(find "$CODE_DIR" -name "*.py" | wc -l | tr -d ' ')
- **Lines of Code:** $(find "$CODE_DIR" -name "*.py" -exec cat {} \; | wc -l | tr -d ' ')

EOF

# Check for UDC endpoints
cat >> "$REPORT_FILE" << EOF
### UDC Endpoint Check
EOF

for endpoint in "/health" "/capabilities" "/state" "/dependencies" "/message"; do
    if grep -r "$endpoint" "$CODE_DIR" >/dev/null 2>&1; then
        echo "- ✅ $endpoint found" >> "$REPORT_FILE"
    else
        echo "- ❌ $endpoint MISSING" >> "$REPORT_FILE"
    fi
done

# Check for common patterns
cat >> "$REPORT_FILE" << EOF

### Code Quality Patterns
EOF

if grep -r "try:" "$CODE_DIR" >/dev/null 2>&1; then
    echo "- ✅ Error handling present (try/except blocks)" >> "$REPORT_FILE"
else
    echo "- ⚠️ No error handling found" >> "$REPORT_FILE"
fi

if grep -r "logger\." "$CODE_DIR" >/dev/null 2>&1; then
    echo "- ✅ Logging implemented" >> "$REPORT_FILE"
else
    echo "- ⚠️ No logging found" >> "$REPORT_FILE"
fi

if grep -r "HTTPException" "$CODE_DIR" >/dev/null 2>&1; then
    echo "- ✅ HTTP exception handling" >> "$REPORT_FILE"
else
    echo "- ⚠️ No HTTP exception handling" >> "$REPORT_FILE"
fi

if grep -r "BaseModel" "$CODE_DIR" >/dev/null 2>&1; then
    echo "- ✅ Pydantic models used" >> "$REPORT_FILE"
else
    echo "- ⚠️ No Pydantic models found" >> "$REPORT_FILE"
fi

# Final summary
cat >> "$REPORT_FILE" << EOF

---

## Next Steps

1. **Review AI Verification Results** - Address any issues flagged
2. **Fix Missing Requirements** - Implement any SPEC items marked as missing
3. **Address Security Issues** - Fix any vulnerabilities identified
4. **Improve Code Quality** - Apply recommendations
5. **Re-verify** - Run this script again after fixes

---

**Generated by:** AI Cross-Verification System
**Sacred Loop:** Step 5 (Verifier) - Multi-AI validation

🌐⚡💎
EOF

# Display summary
echo ""
print_header "Verification Complete"
echo ""
print_success "Report generated: $REPORT_FILE"
print_info "Verification prompt: $PROMPT_FILE"
echo ""

# Show quick summary
if grep -q "❌" "$REPORT_FILE"; then
    print_warning "Issues found - review report for details"
    echo ""
    print_info "Quick summary:"
    grep "❌" "$REPORT_FILE" | head -5
else
    print_success "No critical issues detected in automated checks"
fi

echo ""
print_info "Review full report for AI verification results"
print_info "Act on recommendations before deploying"
echo ""

# Return exit code based on findings
if grep -q "❌.*MISSING" "$REPORT_FILE"; then
    exit 1
else
    exit 0
fi
