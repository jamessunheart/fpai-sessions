#!/bin/bash
# GitHub Repository Creation Script
# Automates creating repos for FPAI droplets

set -e  # Exit on error

ORG_NAME="fpai-track-b"
REPO_NAME=$1
DESCRIPTION=$2

if [ -z "$REPO_NAME" ]; then
    echo "Usage: $0 <repo-name> [description]"
    echo ""
    echo "Example:"
    echo "  $0 dashboard \"Public dashboard and marketing site\""
    exit 1
fi

if [ -z "$DESCRIPTION" ]; then
    DESCRIPTION="FPAI Droplet: $REPO_NAME"
fi

echo "=========================================="
echo "  Creating GitHub Repository"
echo "=========================================="
echo "Organization: $ORG_NAME"
echo "Repository:   $REPO_NAME"
echo "Description:  $DESCRIPTION"
echo ""

# Check if gh is authenticated
if ! gh auth status > /dev/null 2>&1; then
    echo "⚠️  GitHub CLI not authenticated."
    echo "Please authenticate now..."
    echo ""
    gh auth login
fi

# Create the repository
echo "Creating repository..."
gh repo create "$ORG_NAME/$REPO_NAME" \
    --public \
    --description "$DESCRIPTION" \
    --confirm

echo ""
echo "✅ Repository created: https://github.com/$ORG_NAME/$REPO_NAME"
echo ""

# If we're in a git directory, offer to add remote
if [ -d ".git" ]; then
    echo "Git repository detected in current directory."
    read -p "Add remote and push? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Check if origin already exists
        if git remote get-url origin > /dev/null 2>&1; then
            echo "Remote 'origin' already exists. Updating..."
            git remote set-url origin "https://github.com/$ORG_NAME/$REPO_NAME.git"
        else
            git remote add origin "https://github.com/$ORG_NAME/$REPO_NAME.git"
        fi

        # Push to GitHub
        echo "Pushing to GitHub..."
        git push -u origin main

        echo ""
        echo "✅ Code pushed to GitHub!"
        echo "View at: https://github.com/$ORG_NAME/$REPO_NAME"
    fi
fi

echo ""
echo "=========================================="
echo "  Repository Ready!"
echo "=========================================="
echo ""
echo "Clone URL: https://github.com/$ORG_NAME/$REPO_NAME.git"
echo "SSH URL:   git@github.com:$ORG_NAME/$REPO_NAME.git"
echo ""
