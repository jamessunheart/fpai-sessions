#!/bin/bash
# sync-logs-to-server.sh - Sync session logs to server

set -e

SERVER="root@198.54.123.234"
LOCAL_SESSIONS="/Users/jamessunheart/Development/docs/coordination/sessions"
LOCAL_KNOWLEDGE="/Users/jamessunheart/Development/docs/coordination/shared-knowledge"
SERVER_BASE="/root/coordination"

echo "📤 Syncing session logs to server..."

# Create server directories if they don't exist
ssh $SERVER "mkdir -p $SERVER_BASE/sessions/ACTIVE $SERVER_BASE/sessions/ARCHIVE $SERVER_BASE/shared-knowledge $SERVER_BASE/DAILY_SUMMARIES"

# Sync session logs
echo "   → Syncing ACTIVE session logs..."
rsync -avz --delete "$LOCAL_SESSIONS/ACTIVE/" "$SERVER:$SERVER_BASE/sessions/ACTIVE/" 2>/dev/null || echo "   ⚠️  No ACTIVE logs to sync"

echo "   → Syncing ARCHIVE session logs..."
rsync -avz "$LOCAL_SESSIONS/ARCHIVE/" "$SERVER:$SERVER_BASE/sessions/ARCHIVE/" 2>/dev/null || echo "   ⚠️  No ARCHIVE logs to sync"

# Sync shared knowledge
echo "   → Syncing shared knowledge..."
rsync -avz "$LOCAL_KNOWLEDGE/" "$SERVER:$SERVER_BASE/shared-knowledge/" 2>/dev/null || echo "   ⚠️  No shared knowledge to sync"

# Sync SSOT.json for reference
echo "   → Syncing SSOT.json..."
rsync -avz /Users/jamessunheart/Development/docs/coordination/SSOT.json "$SERVER:$SERVER_BASE/" 2>/dev/null || echo "   ⚠️  SSOT.json not available"

echo "✅ Sync complete!"
echo ""
echo "📊 Server location: $SERVER:$SERVER_BASE"
echo ""
echo "🔍 View on server:"
echo "   ssh $SERVER 'ls -lh $SERVER_BASE/sessions/ACTIVE/'"
