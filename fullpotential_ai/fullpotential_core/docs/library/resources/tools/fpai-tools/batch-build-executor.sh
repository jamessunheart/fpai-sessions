#!/bin/bash

# BATCH BUILD EXECUTOR
# Purpose: Auto-execute BUILD_GUIDE prompts sequentially with zero copy-paste
# Usage: ./batch-build-executor.sh <droplet-directory>
# Eliminates manual prompt hunting and copying

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n${CYAN}${BOLD}$1${NC}\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_prompt() { echo -e "${MAGENTA}🎯 $1${NC}"; }

if [ -z "$1" ]; then
    print_error "Usage: $0 <droplet-directory>"
    echo ""
    echo "Examples:"
    echo "  $0 /path/to/droplet-15-recruiter"
    echo "  $0 ../droplet-10-orchestrator"
    exit 1
fi

DROPLET_DIR="$1"

if [ ! -d "$DROPLET_DIR" ]; then
    print_error "Directory not found: $DROPLET_DIR"
    exit 1
fi

DROPLET_DIR="$(cd "$DROPLET_DIR" && pwd)"
DROPLET_NAME="$(basename "$DROPLET_DIR")"
BUILD_GUIDE="${DROPLET_DIR}/BUILD_GUIDE.md"
PROGRESS_FILE="${DROPLET_DIR}/.build-progress"

print_header "Batch Build Executor"
echo ""
print_info "Droplet: $DROPLET_NAME"
print_info "Directory: $DROPLET_DIR"
echo ""

# Check for BUILD_GUIDE.md
if [ ! -f "$BUILD_GUIDE" ]; then
    print_error "BUILD_GUIDE.md not found at: $BUILD_GUIDE"
    print_info "Generate it with: ./generate-build-guide.sh $DROPLET_DIR"
    exit 1
fi

# Check for clipboard command (macOS)
CLIPBOARD_CMD=""
if command -v pbcopy &> /dev/null; then
    CLIPBOARD_CMD="pbcopy"
    print_success "Clipboard available (macOS pbcopy)"
elif command -v xclip &> /dev/null; then
    CLIPBOARD_CMD="xclip -selection clipboard"
    print_success "Clipboard available (xclip)"
elif command -v xsel &> /dev/null; then
    CLIPBOARD_CMD="xsel --clipboard --input"
    print_success "Clipboard available (xsel)"
else
    print_warning "No clipboard command found - prompts will be displayed only"
fi

# Define the 6 build prompts
declare -a PROMPT_TITLES=(
    "Project Setup & Models"
    "UDC Compliance Endpoints"
    "Core Business Logic"
    "Testing"
    "Docker & Deployment"
    "Code Quality & Standards"
)

# Load progress if exists
CURRENT_STEP=1
if [ -f "$PROGRESS_FILE" ]; then
    CURRENT_STEP=$(cat "$PROGRESS_FILE")
    print_info "Resuming from Prompt $CURRENT_STEP: ${PROMPT_TITLES[$((CURRENT_STEP-1))]}"
    echo ""
    read -p "Resume from Prompt $CURRENT_STEP? (Y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        print_info "Restarting from beginning"
        CURRENT_STEP=1
        echo "1" > "$PROGRESS_FILE"
    fi
else
    echo "1" > "$PROGRESS_FILE"
fi

echo ""
print_header "How Batch Execution Works"
echo ""
print_info "📋 6 Sequential Prompts:"
for i in "${!PROMPT_TITLES[@]}"; do
    step=$((i + 1))
    if [ $step -lt $CURRENT_STEP ]; then
        echo "  ✅ Prompt $step: ${PROMPT_TITLES[$i]} (completed)"
    elif [ $step -eq $CURRENT_STEP ]; then
        echo "  ▶️  Prompt $step: ${PROMPT_TITLES[$i]} (current)"
    else
        echo "  ⏳ Prompt $step: ${PROMPT_TITLES[$i]} (pending)"
    fi
done

echo ""
print_info "🔄 Workflow for Each Prompt:"
echo "  1. Script displays prompt"
if [ -n "$CLIPBOARD_CMD" ]; then
    echo "  2. Prompt auto-copied to clipboard"
    echo "  3. You paste (Cmd+V / Ctrl+V) into Claude Code"
else
    echo "  2. You copy the prompt manually"
    echo "  3. You paste into Claude Code"
fi
echo "  4. Claude Code implements the prompt"
echo "  5. You test the implementation"
echo "  6. You return here and press 'Next'"
echo "  7. Repeat for next prompt"

echo ""
print_success "Zero hunting for prompts - everything automated!"
echo ""

read -p "Start batch execution? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Cancelled"
    exit 0
fi

# Function to extract prompt from BUILD_GUIDE.md
extract_prompt() {
    local prompt_num=$1
    local prompt_title="${PROMPT_TITLES[$((prompt_num-1))]}"

    # Extract the prompt section from BUILD_GUIDE.md
    # Prompts are in format: "### Prompt N: Title" followed by code block
    awk "/### Prompt ${prompt_num}: ${prompt_title}/,/^---$|^### Prompt/" "$BUILD_GUIDE" | \
        sed -n '/```/,/```/p' | \
        sed '1d;$d' || echo "Error extracting prompt"
}

# Execute each prompt
for prompt_num in $(seq $CURRENT_STEP 6); do
    clear
    print_header "Prompt ${prompt_num}/6: ${PROMPT_TITLES[$((prompt_num-1))]}"
    echo ""

    print_info "📄 Extracting prompt from BUILD_GUIDE.md..."
    PROMPT_TEXT=$(extract_prompt $prompt_num)

    if [ -z "$PROMPT_TEXT" ] || [ "$PROMPT_TEXT" = "Error extracting prompt" ]; then
        print_error "Failed to extract prompt $prompt_num"
        print_info "Falling back to manual extraction"

        # Show section of BUILD_GUIDE
        print_info "Opening BUILD_GUIDE.md at Prompt $prompt_num..."

        # Try to open and highlight the section
        if command -v code &> /dev/null; then
            code -g "${BUILD_GUIDE}:$((150 + (prompt_num - 1) * 80))"
        elif command -v open &> /dev/null; then
            open "$BUILD_GUIDE"
        fi

        print_info "Manually copy Prompt $prompt_num from BUILD_GUIDE.md"
        read -p "Press Enter when you've copied the prompt..."

        # Continue to next step
    else
        print_success "Prompt extracted!"
        echo ""
        print_prompt "PROMPT ${prompt_num}: ${PROMPT_TITLES[$((prompt_num-1))]}"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "$PROMPT_TEXT"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        # Copy to clipboard if available
        if [ -n "$CLIPBOARD_CMD" ]; then
            echo "$PROMPT_TEXT" | eval $CLIPBOARD_CMD
            print_success "✂️  Prompt copied to clipboard!"
            print_info "📋 Paste with: Cmd+V (macOS) or Ctrl+V (Linux)"
        else
            print_warning "Clipboard not available - copy manually from above"
        fi
    fi

    echo ""
    print_info "🎯 Next Steps:"
    echo "  1. Switch to Claude Code (or start it: claude in $DROPLET_DIR)"
    echo "  2. Paste this prompt (Cmd+V / Ctrl+V)"
    echo "  3. Let Claude Code implement it"
    echo "  4. Test the implementation"
    echo "  5. Return here when ready"
    echo ""

    # Wait for user confirmation
    echo ""
    print_warning "⏸️  Paused - Complete Prompt $prompt_num in Claude Code"
    echo ""

    while true; do
        read -p "Prompt $prompt_num complete? (y/n/skip/quit): " -r RESPONSE

        case "$RESPONSE" in
            y|Y)
                print_success "Prompt $prompt_num marked complete!"

                # Update progress
                echo "$((prompt_num + 1))" > "$PROGRESS_FILE"

                # Show what was completed
                echo ""
                print_info "Progress:"
                for i in "${!PROMPT_TITLES[@]}"; do
                    step=$((i + 1))
                    if [ $step -le $prompt_num ]; then
                        echo "  ✅ Prompt $step: ${PROMPT_TITLES[$i]}"
                    else
                        echo "  ⏳ Prompt $step: ${PROMPT_TITLES[$i]}"
                    fi
                done

                echo ""
                sleep 1
                break
                ;;

            n|N)
                print_warning "Prompt $prompt_num not complete yet"
                print_info "Continue working on it, or type 'skip' to move on"
                ;;

            skip|SKIP)
                print_warning "Skipping Prompt $prompt_num"
                echo "$((prompt_num + 1))" > "$PROGRESS_FILE"
                echo ""
                sleep 1
                break
                ;;

            quit|QUIT|q|Q)
                print_info "Quitting batch execution"
                print_info "Progress saved - resume with: $0 $DROPLET_DIR"
                exit 0
                ;;

            *)
                print_error "Invalid response. Enter: y (yes), n (not yet), skip, or quit"
                ;;
        esac
    done
done

# All prompts complete
clear
print_header "🎉 All Prompts Complete!"
echo ""

print_success "Build Guide Execution Complete!"
echo ""

print_info "📊 Summary:"
for i in "${!PROMPT_TITLES[@]}"; do
    step=$((i + 1))
    echo "  ✅ Prompt $step: ${PROMPT_TITLES[$i]}"
done

echo ""
print_info "🔍 Next Steps:"
echo "  1. Verify all files exist:"
echo "     - app/main.py"
echo "     - app/models.py"
echo "     - tests/test_endpoints.py"
echo "     - Dockerfile"
echo "     - requirements.txt"
echo ""
echo "  2. Run tests:"
echo "     cd $DROPLET_DIR"
echo "     pytest tests/"
echo ""
echo "  3. Return to Sacred Loop for verification"
echo ""

# Check if key files exist
print_info "🔍 Checking for required files..."
echo ""

FILES_EXIST=true
check_file() {
    local file="$1"
    if [ -f "${DROPLET_DIR}/${file}" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
        FILES_EXIST=false
    fi
}

check_file "app/main.py"
check_file "app/models.py"
check_file "Dockerfile"
check_file "requirements.txt"
check_file "tests/test_endpoints.py"

echo ""

if [ "$FILES_EXIST" = true ]; then
    print_success "All required files found!"
    echo ""
    print_info "Build appears complete! ✅"
else
    print_warning "Some files are missing"
    print_info "You may need to complete missing parts"
fi

# Clean up progress file
rm -f "$PROGRESS_FILE"

echo ""
print_success "Batch execution complete! Return to Sacred Loop."
echo ""
