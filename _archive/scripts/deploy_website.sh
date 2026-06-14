#!/bin/bash
# Deploy website-ai static assets (index + services) to the live server.
# Usage: ./deploy_website.sh

set -euo pipefail

SERVER_IP="198.54.123.234"
USER="root"
REMOTE_ROOT="/opt/fpai/core/applications/website-ai/frontend"
LOCAL_ROOT="fullpotential_ai/fullpotential_core/core/applications/website-ai/frontend"

echo "🌐 Deploying website frontend to $SERVER_IP ..."

echo "📦 Uploading root HTML artifacts"
scp "$LOCAL_ROOT/index.html" "$LOCAL_ROOT/research.html" "$LOCAL_ROOT/apprentice.html" "$LOCAL_ROOT/papers.json" \
  "$USER@$SERVER_IP:$REMOTE_ROOT/"

echo "📦 Uploading services directory"
scp -r "$LOCAL_ROOT/services" "$USER@$SERVER_IP:$REMOTE_ROOT/"

echo "✅ Deployment complete. Verify:"
echo "   https://fullpotential.ai/"
echo "   https://fullpotential.ai/apprentice"
echo "   https://fullpotential.ai/services/"
echo "   https://fullpotential.ai/services/whaletrack/"
echo "   https://fullpotential.ai/services/harvester"

