#!/bin/bash
# UDC COMPLIANCE DEPLOYMENT - Optimized One-Command Deploy
# Created: 2025-11-14
# Purpose: Deploy UDC-compliant Orchestrator + Registry to server

set -e

SERVER="198.54.123.234"
USER="root"

echo "🚀 UDC COMPLIANCE DEPLOYMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Deploying to: ${USER}@${SERVER}"
echo ""

# Check if packages exist
if [ ! -f "orchestrator-udc-update.tar.gz" ]; then
    echo "❌ orchestrator-udc-update.tar.gz not found"
    exit 1
fi

if [ ! -f "registry-udc-complete.tar.gz" ]; then
    echo "❌ registry-udc-complete.tar.gz not found"
    exit 1
fi

echo "📦 Deployment packages found"
echo ""

# Deploy Orchestrator
echo "1️⃣  Deploying Orchestrator UDC updates..."
scp orchestrator-udc-update.tar.gz ${USER}@${SERVER}:/tmp/
ssh ${USER}@${SERVER} << 'EOF'
cd /opt/fpai/apps/orchestrator
tar -xzf /tmp/orchestrator-udc-update.tar.gz
source .venv/bin/activate 2>/dev/null || true
pip install -q -r requirements.txt
systemctl restart orchestrator
sleep 2
curl -sf http://localhost:8001/orchestrator/capabilities > /dev/null && echo "✅ Orchestrator UDC endpoints live" || echo "⚠️  Orchestrator may need manual restart"
EOF

echo ""

# Deploy Registry
echo "2️⃣  Deploying Registry UDC updates..."
scp registry-udc-complete.tar.gz ${USER}@${SERVER}:/tmp/
ssh ${USER}@${SERVER} << 'EOF'
cd /opt/fpai/apps/registry
tar -xzf /tmp/registry-udc-complete.tar.gz
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt
systemctl restart registry
sleep 2
curl -sf http://localhost:8000/capabilities > /dev/null && echo "✅ Registry UDC endpoints live" || echo "⚠️  Registry may need manual restart"
EOF

echo ""
echo "3️⃣  Verifying UDC compliance..."
ssh ${USER}@${SERVER} << 'EOF'
echo ""
echo "Registry UDC Endpoints:"
curl -s http://localhost:8000/capabilities | python3 -m json.tool | head -10
echo ""
echo "Orchestrator UDC Endpoints:"
curl -s http://localhost:8001/orchestrator/capabilities | python3 -m json.tool | head -10
EOF

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ UDC COMPLIANCE DEPLOYMENT COMPLETE"
echo ""
echo "Test externally:"
echo "  curl http://${SERVER}:8000/capabilities"
echo "  curl http://${SERVER}:8000/state"
echo "  curl http://${SERVER}:8001/orchestrator/capabilities"
echo "  curl http://${SERVER}:8001/orchestrator/state"
echo ""
