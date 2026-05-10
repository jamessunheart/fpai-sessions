#!/bin/bash

# GOD_MODE.sh
# The single entry point to the Full Potential OS Control Center.

echo "🏛️  Initializing THE COUNCIL (God Mode)..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed."
    exit 1
fi

# Ensure Directories Exist (Self-Healing)
mkdir -p docs/coordination/intents
mkdir -p docs/coordination/claims
mkdir -p docs/coordination/heartbeats
mkdir -p STAGING/incoming

echo "✅ Environment Verified."
echo "🚀 Launching Dashboard..."
sleep 1

# Run the Interactive CLI
python3 cli_dashboard.py

