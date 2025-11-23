#!/bin/bash
set -e

# FPAI SATELLITE GENERATOR
# Creates an isolated workspace for safe autonomous development.
# Usage: ./create_satellite.sh [mission_id] [satellite_name]

MISSION_ID=$1
SATELLITE_NAME=$2

if [ -z "$MISSION_ID" ] || [ -z "$SATELLITE_NAME" ]; then
    echo "Usage: $0 [mission_id] [satellite_name]"
    echo "Example: $0 M009 calculator_app"
    exit 1
fi

# Configuration
CORE_ROOT=$(pwd)
SATELLITES_DIR="$CORE_ROOT/_satellites"
TARGET_DIR="$SATELLITES_DIR/$SATELLITE_NAME"
TEMPLATE_DIR="$CORE_ROOT/_templates/satellite_base" # We will need to create this or mock it

echo "🛰️  Initiating Satellite Launch Sequence..."
echo "   Mission: $MISSION_ID"
echo "   Target:  $TARGET_DIR"

# 1. Create Satellites Directory if not exists
mkdir -p "$SATELLITES_DIR"

# 2. Check for collision
if [ -d "$TARGET_DIR" ]; then
    echo "❌ Error: Satellite '$SATELLITE_NAME' already exists."
    exit 1
fi

# 3. Initialize Satellite
mkdir -p "$TARGET_DIR"
cd "$TARGET_DIR"

# 4. Setup Git (Isolated)
git init
git branch -m main

# 5. Scaffold Basic Structure (Mocking a template for now)
mkdir -p app tests docs
touch README.md
touch requirements.txt

# Create a basic README
cat <<EOF > README.md
# Satellite: $SATELLITE_NAME
**Mission:** $MISSION_ID
**Created:** $(date)

This is an isolated development environment.
All code must pass local tests before harvesting.
EOF

# Create a basic .gitignore
cat <<EOF > .gitignore
__pycache__/
*.pyc
.env
venv/
.pytest_cache/
EOF

# Create a basic pytest configuration
cat <<EOF > pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
EOF

# 6. Link back to Core (Symbolic link for reference, effectively read-only for the agent conceptually)
# In a real scenario, we might copy specific libs. For now, we keep it clean.

# 7. Initial Commit
git add .
git commit -m "Initial commit: Satellite launch for $MISSION_ID"

echo ""
echo "✅ Satellite Deployed Successfully!"
echo "   Path: $TARGET_DIR"
echo "   Command: cd $TARGET_DIR"
echo ""
echo "🔍 Next Steps for Apprentice:"
echo "   1. cd $TARGET_DIR"
echo "   2. Create virtualenv: python3 -m venv venv && source venv/bin/activate"
echo "   3. Build & Test"
echo "   4. Signal Ready for Harvest"

