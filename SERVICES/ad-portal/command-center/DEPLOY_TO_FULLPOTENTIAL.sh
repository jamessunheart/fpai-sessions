#!/bin/bash
# ============================================
# Deploy Ad Portal Command Center to fullpotential.ai/projects/advertising
# ============================================
# 
# Run this script from your LOCAL machine:
#   ./DEPLOY_TO_FULLPOTENTIAL.sh
#
# After running, access at:
#   https://fullpotential.ai/projects/advertising
#
# ============================================

set -euo pipefail

SERVER_IP="198.54.123.234"
USER="root"
LOCAL_DIR="$(dirname "$0")"
REMOTE_DIR="/opt/fpai/core/applications/website-ai/frontend/projects/advertising"

echo "🚀 Deploying Ad Portal Command Center to fullpotential.ai..."
echo ""

# Step 1: Create remote directory
echo "📁 Creating remote directory..."
ssh $USER@$SERVER_IP "mkdir -p $REMOTE_DIR"

# Step 2: Upload files
echo "📤 Uploading files..."
scp "$LOCAL_DIR/index.html" "$USER@$SERVER_IP:$REMOTE_DIR/"
scp "$LOCAL_DIR/tasks.json" "$USER@$SERVER_IP:$REMOTE_DIR/"
scp "$LOCAL_DIR/README.md" "$USER@$SERVER_IP:$REMOTE_DIR/"

# Step 3: Create projects index if it doesn't exist
echo "📄 Setting up projects directory..."
ssh $USER@$SERVER_IP "cat > /opt/fpai/core/applications/website-ai/frontend/projects/index.html << 'EOF'
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Full Potential AI - Projects</title>
    <script src=\"https://cdn.tailwindcss.com\"></script>
    <style>
        body { font-family: system-ui, sans-serif; }
        .gradient-bg { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); }
    </style>
</head>
<body class=\"gradient-bg min-h-screen text-white\">
    <div class=\"max-w-4xl mx-auto p-8\">
        <h1 class=\"text-4xl font-bold mb-8\">🚀 Active Projects</h1>
        <div class=\"space-y-4\">
            <a href=\"/projects/advertising\" class=\"block bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:bg-slate-800 transition\">
                <h2 class=\"text-xl font-semibold text-emerald-400\">📡 Ad Portal</h2>
                <p class=\"text-slate-400 mt-2\">Advertising campaign management system for coaching offers. Track ROAS to profits.</p>
                <p class=\"text-sm text-slate-500 mt-2\">Status: Setup & Deployment Phase</p>
            </a>
        </div>
        <p class=\"text-slate-500 text-sm mt-8\">Full Potential AI Project Hub</p>
    </div>
</body>
</html>
EOF"

# Step 4: Verify deployment
echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access at:"
echo "   https://fullpotential.ai/projects/advertising"
echo "   https://fullpotential.ai/projects/ (project hub)"
echo ""
echo "🧪 Testing..."
curl -s -o /dev/null -w "   HTTP Status: %{http_code}\n" "https://fullpotential.ai/projects/advertising/" || echo "   (Test after nginx is configured)"


