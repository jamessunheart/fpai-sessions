#!/bin/bash

# Full Potential AI Tools - Setup Script

echo "🌐 Full Potential AI - Tools Setup"
echo "======================================"
echo ""

# Check Python version
echo "📋 Checking prerequisites..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    echo "   Install with: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION found"

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not installed"
    exit 1
fi
echo "✅ pip3 found"

# Check for gh CLI (optional)
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI found"
    GH_STATUS=$(gh auth status 2>&1 | grep "Logged in" || echo "not logged in")
    if [[ $GH_STATUS == *"Logged in"* ]]; then
        echo "   ✅ Authenticated to GitHub"
    else
        echo "   ⚠️  Not authenticated. Run: gh auth login"
    fi
else
    echo "⚠️  GitHub CLI not found (optional)"
    echo "   Install with: brew install gh"
fi

echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "🔧 Setting up directories..."
mkdir -p output/snapshots
mkdir -p output/gap-analyses
mkdir -p output/specs
mkdir -p config
mkdir -p templates

echo "✅ Directories created"

echo ""
echo "🔒 Making CLI executable..."
chmod +x bin/fp-tools
echo "✅ CLI is executable"

echo ""
echo "✅ SETUP COMPLETE!"
echo ""
echo "Next steps:"
echo "  1. Add to PATH (optional):"
echo "     echo 'export PATH=\"\$PATH:$(pwd)/bin\"' >> ~/.zshrc"
echo "     source ~/.zshrc"
echo ""
echo "  2. Test the CLI:"
echo "     ./bin/fp-tools --help"
echo ""
echo "  3. Run your first workflow:"
echo "     ./bin/fp-tools workflow"
echo ""
echo "  4. View the README:"
echo "     cat README.md"
echo ""
echo "🌐⚡💎"
