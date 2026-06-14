#!/bin/bash
# Create GitHub repos for all services in SERVICE_REGISTRY.json
# Usage: ./create-service-repos.sh

set -e

REGISTRY="/Users/jamessunheart/Development/SERVICES/SERVICE_REGISTRY.json"
SERVICES_DIR="/Users/jamessunheart/Development/SERVICES"
ORG="fullpotentialai"

echo "🚀 GitHub Repo Creation for All Services"
echo "=========================================="
echo ""

# Check if gh is installed and authenticated
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not installed"
    exit 1
fi

if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Read services from registry
services=$(python3 -c "
import json
with open('$REGISTRY') as f:
    data = json.load(f)
    for service in data['services']:
        print(f\"{service['name']}|{service['description']}|{service.get('path_local', '')}\")
")

created=0
skipped=0
failed=0

while IFS='|' read -r name description path_local; do
    echo "📦 Processing: $name"

    # Skip if path doesn't exist
    if [ -z "$path_local" ] || [ ! -d "$path_local" ]; then
        echo "   ⚠️  Path not found: $path_local"
        echo "   Skipping..."
        echo ""
        ((skipped++))
        continue
    fi

    # Check if repo already exists
    if gh repo view "$ORG/$name" &> /dev/null; then
        echo "   ✓ Repo already exists: $ORG/$name"
        echo ""
        ((skipped++))
        continue
    fi

    # Create repo
    echo "   Creating repo: $ORG/$name"
    if gh repo create "$ORG/$name" \
        --private \
        --description "$description" \
        --source "$path_local" \
        --remote "origin" \
        --push; then

        echo "   ✅ Created and pushed: $ORG/$name"
        ((created++))
    else
        echo "   ❌ Failed to create repo"
        ((failed++))
    fi

    echo ""
done <<< "$services"

echo "=========================================="
echo "📊 Summary:"
echo "   Created: $created"
echo "   Skipped: $skipped"
echo "   Failed:  $failed"
echo ""
echo "✅ GitHub repo creation complete!"
