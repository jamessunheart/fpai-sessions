#!/bin/bash

# AUTO-BUILD WITH CLAUDE CODE
# Purpose: Automatically launch Claude Code with build prompts pre-loaded
# Usage: ./auto-build-claude.sh <droplet-directory>
# Eliminates copy-paste and context switching

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

print_header "Auto-Build with Claude Code"
echo ""
print_info "Droplet: $DROPLET_NAME"
print_info "Directory: $DROPLET_DIR"
echo ""

# Check for required files
SPEC_FILE="${DROPLET_DIR}/docs/SPEC.md"
CLAUDE_README="${DROPLET_DIR}/docs/CLAUDE_PROJECT_README.md"

if [ ! -f "$SPEC_FILE" ]; then
    print_error "SPEC.md not found at: $SPEC_FILE"
    exit 1
fi

# Check if Claude Code is available
if ! command -v claude &> /dev/null; then
    print_warning "Claude Code CLI not found"
    print_info "Install with: npm install -g @anthropic-ai/claude-code"
    echo ""
    print_info "Alternative: Use manual build options"
    exit 1
fi

# Show build options
print_header "Build Options"
echo ""
print_info "Option 1: Full Auto-Launch (Recommended)"
echo "  - Launches Claude Code with project context"
echo "  - Pre-loads build prompt"
echo "  - You just interact naturally"
echo "  - ⏱️  Time: 1-2 hours"
echo ""
print_info "Option 2: Batch Execution (NEW - ZERO COPY-PASTE)"
echo "  - Auto-extracts all 6 prompts from BUILD_GUIDE"
echo "  - Auto-copies each to clipboard"
echo "  - You just paste (Cmd+V) and implement"
echo "  - Tracks progress, resumable"
echo "  - ⏱️  Time: 1.5-2 hours"
echo ""
print_info "Option 3: Claude Projects Upload"
echo "  - Opens browser to claude.ai"
echo "  - You upload docs/ folder"
echo "  - Best for complex projects"
echo "  - ⏱️  Time: 2-3 hours"
echo ""

read -p "Choose option (1/2/3): " -n 1 -r OPTION
echo
echo

case "$OPTION" in
    1)
        print_success "Option 1 selected: Full Auto-Launch"
        echo ""

        # Build the initial prompt
        print_info "Preparing build prompt..."

        INITIAL_PROMPT="I need to build this service. Here's the context:

**Project:** $DROPLET_NAME
**Location:** $DROPLET_DIR

I have the complete SPEC and Foundation Files in the docs/ directory:
- docs/SPEC.md - Complete service specification
- docs/foundation-files/ - UDC compliance, tech stack, standards, security

Let's build this service following these steps:

1. **Project Structure**: Create FastAPI app with proper structure
   - app/__init__.py
   - app/main.py (FastAPI app with UDC endpoints)
   - app/models.py (Pydantic models from SPEC)
   - app/config.py (Configuration)
   - tests/test_endpoints.py
   - requirements.txt
   - Dockerfile
   - .env.example
   - README.md

2. **UDC Compliance**: Implement 5 required endpoints
   - GET /health
   - GET /capabilities
   - GET /state
   - GET /dependencies
   - POST /message

3. **Business Logic**: Implement all features from SPEC

4. **Testing**: Create comprehensive tests (80%+ coverage)

5. **Docker**: Production-ready Dockerfile

6. **Documentation**: Complete README

Follow the SPEC exactly and maintain UDC compliance. Let's start with the project structure and models.

Ready to build?"

        # Create a temporary prompt file
        PROMPT_FILE="${DROPLET_DIR}/.build-prompt.txt"
        echo "$INITIAL_PROMPT" > "$PROMPT_FILE"

        print_success "Build prompt prepared"
        echo ""
        print_info "Launching Claude Code..."
        print_info "📁 Working directory: $DROPLET_DIR"
        print_info "📄 Project files: docs/ folder"
        echo ""
        print_warning "Claude Code will open. When ready, paste this prompt:"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        cat "$PROMPT_FILE"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        read -p "Press Enter to launch Claude Code..."

        # Change to droplet directory and launch Claude Code
        cd "$DROPLET_DIR"

        # Launch Claude Code with project context
        print_info "Starting Claude Code with project context..."
        echo ""

        # Try to launch with project context
        if [ -d "docs" ]; then
            # Claude Code should pick up docs/ automatically
            claude
        else
            print_warning "docs/ directory not found, launching without context"
            claude
        fi

        # After Claude Code exits
        echo ""
        print_success "Claude Code session ended"
        echo ""

        # Check if build was successful
        if [ -f "app/main.py" ] && [ -f "Dockerfile" ]; then
            print_success "Build appears complete! Found:"
            echo "  ✅ app/main.py"
            echo "  ✅ Dockerfile"
            [ -f "tests/test_endpoints.py" ] && echo "  ✅ tests/test_endpoints.py"
            [ -f "requirements.txt" ] && echo "  ✅ requirements.txt"
            echo ""
            print_info "Next: Return to Sacred Loop for verification"
        else
            print_warning "Build may be incomplete - missing expected files"
            print_info "Continue building or run this script again"
        fi

        # Clean up
        rm -f "$PROMPT_FILE"
        ;;

    2)
        print_success "Option 2 selected: Batch Execution"
        echo ""

        # Find batch executor script
        BATCH_EXECUTOR="$(dirname "$0")/batch-build-executor.sh"

        if [ -x "$BATCH_EXECUTOR" ]; then
            print_info "Launching batch executor..."
            echo ""

            # Execute batch build executor
            "$BATCH_EXECUTOR" "$DROPLET_DIR"

            echo ""
            print_success "Batch execution complete!"
        else
            print_error "Batch executor not found: $BATCH_EXECUTOR"
            print_info "Falling back to manual BUILD_GUIDE.md"
            echo ""

            BUILD_GUIDE="${DROPLET_DIR}/BUILD_GUIDE.md"

            if [ -f "$BUILD_GUIDE" ]; then
                print_info "Opening BUILD_GUIDE.md..."

                # Try to open in editor
                if command -v code &> /dev/null; then
                    code "$BUILD_GUIDE"
                    print_success "Opened in VS Code"
                elif command -v open &> /dev/null; then
                    open "$BUILD_GUIDE"
                    print_success "Opened in default editor"
                else
                    print_info "View with: cat $BUILD_GUIDE"
                fi

                echo ""
                print_info "Copy each numbered prompt sequentially"
                print_info "Paste into Claude Code and implement"
                print_info "Test after each prompt"
            else
                print_error "BUILD_GUIDE.md not found at: $BUILD_GUIDE"
                exit 1
            fi
        fi
        ;;

    3)
        print_success "Option 3 selected: Claude Projects Upload"
        echo ""

        print_info "Steps to use Claude Projects:"
        echo "  1. Open: https://claude.ai"
        echo "  2. Click: 'Projects'"
        echo "  3. Click: 'New Project'"
        echo "  4. Name: '$DROPLET_NAME'"
        echo "  5. Upload: $DROPLET_DIR/docs/ folder"
        echo "  6. Use prompt from CLAUDE_PROJECT_README.md"
        echo ""

        if [ -f "$CLAUDE_README" ]; then
            print_info "First prompt:"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            grep -A 20 "## First Prompt" "$CLAUDE_README" | tail -n +3
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        fi

        echo ""
        read -p "Open browser to claude.ai? (y/N) " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if command -v open &> /dev/null; then
                open "https://claude.ai"
                print_success "Browser opened"
            else
                print_info "Navigate to: https://claude.ai"
            fi
        fi
        ;;

    *)
        print_error "Invalid option"
        exit 1
        ;;
esac

echo ""
print_success "Auto-build launcher complete!"
echo ""
