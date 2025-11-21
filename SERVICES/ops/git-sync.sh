#!/bin/bash

# GIT SYNC - GitHub Workflow Helper
# Blueprint: 1-SYSTEM-BLUEPRINT.txt - Section 4.5 (GitHub-First Principle)
# Purpose: Automate GitHub workflow with Sacred Loop commit standards
# Usage: ./git-sync.sh <service-name> "commit message"

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

# Check arguments
if [ $# -lt 2 ]; then
    print_error "Usage: $0 <service-name> \"commit message\""
    echo ""
    echo "Examples:"
    echo "  $0 registry \"Add JWT token validation\""
    echo "  $0 orchestrator \"Fix heartbeat handling bug\""
    exit 1
fi

SERVICE_NAME="$1"
COMMIT_MSG="$2"

# Find service directory
find_service_dir() {
    local service=$1

    if [ -d "${BASE_DIR}/${service}" ]; then
        echo "${BASE_DIR}/${service}"
        return 0
    fi

    for dir in "${BASE_DIR}"/droplet-*-${service}; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done

    return 1
}

SERVICE_DIR=$(find_service_dir "$SERVICE_NAME")

if [ -z "$SERVICE_DIR" ]; then
    print_error "Service directory not found for: $SERVICE_NAME"
    exit 1
fi

print_info "Git sync for: $SERVICE_NAME"
print_info "Directory: $SERVICE_DIR"

cd "$SERVICE_DIR"

# Check if it's a git repository
if [ ! -d ".git" ]; then
    print_error "Not a git repository. Initialize with: git init"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_info "Uncommitted changes detected"
else
    print_warning "No changes to commit"
    exit 0
fi

# Run code standards check
print_info "Running code standards check..."
if command -v black >/dev/null 2>&1; then
    black app/ tests/ --quiet 2>/dev/null || true
fi

# Run tests
if [ -d "tests" ]; then
    print_info "Running tests..."

    if pytest tests/ --quiet 2>/dev/null; then
        print_success "Tests passed"
    else
        print_error "Tests failed - commit aborted"
        print_info "Fix tests before committing or use git commit directly"
        exit 1
    fi
fi

# Show status
print_info "Git status:"
git status --short

# Stage all changes
print_info "Staging changes..."
git add .

# Create commit with Sacred Loop format
print_info "Creating commit..."

FULL_COMMIT_MSG=$(cat <<EOF
$COMMIT_MSG

🌐 Generated with Full Potential AI - Sacred Loop

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)

git commit -m "$FULL_COMMIT_MSG"

print_success "Commit created"

# Push to GitHub (if remote exists)
if git remote | grep -q origin; then
    print_info "Pushing to GitHub..."

    if git push origin $(git branch --show-current); then
        print_success "Pushed to GitHub"
    else
        print_error "Push failed"
        print_info "Pull latest changes first: git pull --rebase"
        exit 1
    fi
else
    print_warning "No remote 'origin' configured"
    print_info "Add remote with: git remote add origin <url>"
fi

echo ""
print_success "Git sync complete! 🌐⚡💎"
echo ""
print_info "Next steps:"
echo "  1. Review commit: git log -1"
echo "  2. Create PR: gh pr create (if using GitHub CLI)"
