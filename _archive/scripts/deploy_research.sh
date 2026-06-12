#!/bin/bash
# Deploy Research Library to Live Server
# Usage: ./deploy_research.sh

SERVER_IP="198.54.123.234"
USER="root"
REMOTE_PATH="/opt/fpai/research"  # Updated to correct path

echo "🚀 Deploying Research Library to $SERVER_IP..."

# 1. Upload papers.json
echo "📦 Uploading papers.json..."
scp fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/papers.json $USER@$SERVER_IP:$REMOTE_PATH/

# 2. Upload research.html
echo "📦 Uploading research.html..."
scp fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/research.html $USER@$SERVER_IP:$REMOTE_PATH/

# 3. Upload updated index.html
echo "📦 Uploading index.html..."
scp fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend/index.html $USER@$SERVER_IP:$REMOTE_PATH/

echo "✅ Deployment Complete!"
echo "👉 Verify at https://fullpotential.ai/research"

