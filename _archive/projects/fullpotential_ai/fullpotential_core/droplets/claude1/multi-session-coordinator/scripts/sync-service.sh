#!/bin/bash
# Three-way sync: Local → GitHub → Server
# Usage: ./sync-service.sh [service-name]

set -e

SERVICE_NAME=$1
REGISTRY="/Users/jamessunheart/Development/agents/services/SERVICE_REGISTRY.json"
SERVER="root@198.54.123.234"

if [ -z "$SERVICE_NAME" ]; then
    echo "Usage: ./sync-service.sh [service-name]"
    echo ""
    echo "Available services:"
    python3 -c "
import json
with open('$REGISTRY') as f:
    for s in json.load(f)['services']:
        print(f\"  - {s['name']}\")
"
    exit 1
fi

echo "🔄 Three-Way Sync: $SERVICE_NAME"
echo "=================================="
echo ""

# Get service info from registry
SERVICE_INFO=$(python3 -c "
import json, sys
with open('$REGISTRY') as f:
    for s in json.load(f)['services']:
        if s['name'] == '$SERVICE_NAME':
            print(f\"{s.get('path_local', '')}|{s.get('path_production', '')}|{s.get('repo', '')}\")
            sys.exit(0)
print('||')
")

IFS='|' read -r PATH_LOCAL PATH_PROD REPO <<< "$SERVICE_INFO"

if [ -z "$PATH_LOCAL" ]; then
    echo "❌ Service not found in registry: $SERVICE_NAME"
    exit 1
fi

if [ ! -d "$PATH_LOCAL" ]; then
    echo "❌ Local path not found: $PATH_LOCAL"
    exit 1
fi

echo "📂 Local:  $PATH_LOCAL"
echo "🐙 GitHub: $REPO"
echo "🖥️  Server: $SERVER:$PATH_PROD"
echo ""

# Step 1: Commit local changes
echo "Step 1/4: Committing local changes..."
cd "$PATH_LOCAL"

if git diff --quiet && git diff --cached --quiet; then
    echo "   ✓ No local changes to commit"
else
    git add .
    git commit -m "Auto-sync: $(date +'%Y-%m-%d %H:%M:%S')" || echo "   ⚠️  Nothing to commit"
fi

# Step 2: Push to GitHub
echo ""
echo "Step 2/4: Pushing to GitHub..."
if [ -n "$REPO" ]; then
    git push origin main || git push origin master || echo "   ⚠️  Push failed (may not have remote)"
    echo "   ✅ Pushed to GitHub"
else
    echo "   ⚠️  No repo URL in registry - skipping GitHub push"
fi

# Step 3: Sync to server
echo ""
echo "Step 3/4: Syncing to server..."
if [ -n "$PATH_PROD" ]; then
    # Create directory on server if it doesn't exist
    ssh $SERVER "mkdir -p $PATH_PROD"

    # Sync files
    rsync -av --delete \
        --exclude 'venv' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.git' \
        --exclude 'node_modules' \
        "$PATH_LOCAL/" "$SERVER:$PATH_PROD/"

    echo "   ✅ Synced to server"
else
    echo "   ⚠️  No production path in registry - skipping server sync"
fi

# Step 4: Restart service on server (if applicable)
echo ""
echo "Step 4/4: Restarting service..."
SERVICE_PORT=$(python3 -c "
import json
with open('$REGISTRY') as f:
    for s in json.load(f)['services']:
        if s['name'] == '$SERVICE_NAME':
            print(s.get('port', ''))
")

if [ -n "$SERVICE_PORT" ]; then
    ssh $SERVER "
        # Kill old process
        pkill -f ':$SERVICE_PORT' || true

        # Start new process (if there's a start script)
        if [ -f $PATH_PROD/start.sh ]; then
            cd $PATH_PROD && nohup ./start.sh > logs/service.log 2>&1 &
            echo '   ✅ Service restarted on port $SERVICE_PORT'
        elif [ -f $PATH_PROD/deploy.sh ]; then
            cd $PATH_PROD && ./deploy.sh
            echo '   ✅ Deployed via deploy.sh'
        else
            echo '   ⚠️  No start.sh or deploy.sh found'
        fi
    "
else
    echo "   ⚠️  No port configured - skipping restart"
fi

echo ""
echo "=================================="
echo "✅ Sync complete: $SERVICE_NAME"
echo ""
echo "Next steps:"
echo "  - Local → GitHub → Server: ✅"
if [ -n "$SERVICE_PORT" ]; then
    echo "  - Test: curl http://198.54.123.234:$SERVICE_PORT/health"
fi
