#!/bin/bash
# ============================================================
# Deploy Chief of Staff → Secondary Server (162.0.208.88)
# ============================================================
# Deploys daily_briefing.py and sets up a 7am cron job.
# No Mac Mini required — runs directly on the AI server.
#
# Usage: ./deploy.sh
# ============================================================

set -e

SERVER="162.0.208.88"
REMOTE_DIR="/opt/fpai/chief-of-staff"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "🚀 Deploying Chief of Staff to $SERVER..."

# Step 1: Create remote directory
echo "📁 Creating $REMOTE_DIR on server..."
ssh root@$SERVER "mkdir -p $REMOTE_DIR"

# Step 2: Copy the briefing script
echo "📤 Uploading daily_briefing.py..."
scp "$SCRIPT_DIR/daily_briefing.py" root@$SERVER:$REMOTE_DIR/daily_briefing.py

# Step 3: Ensure httpx is installed
echo "📦 Installing Python dependencies..."
ssh root@$SERVER "pip3 install httpx 2>/dev/null || pip install httpx 2>/dev/null"

# Step 4: Dry-run test on server
echo "🧪 Running dry-run on server..."
ssh root@$SERVER "cd $REMOTE_DIR && python3 daily_briefing.py --dry-run"

# Step 5: Set up cron job (7am daily, server timezone)
echo "⏰ Setting up cron job (7am daily)..."
CRON_CMD="0 7 * * * cd $REMOTE_DIR && python3 daily_briefing.py >> /var/log/fpai-briefing.log 2>&1"
ssh root@$SERVER "
    (crontab -l 2>/dev/null | grep -v 'daily_briefing.py'; echo '$CRON_CMD') | crontab -
"
echo "  ✅ Cron installed: $CRON_CMD"

# Step 6: Notify Shared Brain
echo "🧠 Registering with Shared Brain..."
curl -s -X POST "http://$SERVER:8770/memory/store" \
    -H "Content-Type: application/json" \
    -d '{
        "content": "Chief of Staff daily briefing deployed to /opt/fpai/chief-of-staff/. Cron: 7am daily. Sends Telegram to Sunheart with priorities, decisions, progress, alerts.",
        "source": "deploy-script",
        "tags": ["deployment", "chief-of-staff", "cron"]
    }' > /dev/null

echo ""
echo "=============================================="
echo "✅ Chief of Staff deployed!"
echo "=============================================="
echo ""
echo "  Server:  $SERVER"
echo "  Path:    $REMOTE_DIR/daily_briefing.py"
echo "  Cron:    7am daily"
echo "  Logs:    /var/log/fpai-briefing.log"
echo "  Brain:   Syncs to Shared Brain + Mem0"
echo ""
echo "  Manual run:  ssh root@$SERVER 'cd $REMOTE_DIR && python3 daily_briefing.py'"
echo "  Dry run:     ssh root@$SERVER 'cd $REMOTE_DIR && python3 daily_briefing.py --dry-run'"
echo ""
