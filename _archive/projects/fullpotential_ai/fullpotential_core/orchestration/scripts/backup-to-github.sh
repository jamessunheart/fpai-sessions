#!/bin/bash
#
# Automated GitHub Backup Script
# Syncs server work to local machine and pushes to GitHub
#
# Usage: ./backup-to-github.sh
# Cron: 0 2 * * * cd /Users/jamessunheart/Development && ./backup-to-github.sh >> /tmp/backup.log 2>&1
#

set -e

# Configuration
SERVER="root@198.54.123.234"
SERVER_SERVICES="/root/agents/services/"
LOCAL_DIR="/Users/jamessunheart/Development"
SERVICES_DIR="$LOCAL_DIR/SERVICES"
BACKUP_DIR="$LOCAL_DIR/backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

echo "========================================="
echo "GitHub Backup - $DATE"
echo "========================================="

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Step 1: Sync SERVICES from server to local
echo ""
echo "[1/6] Syncing SERVICES from server..."
rsync -av --delete \
  --exclude '.git' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '*.log' \
  --exclude '*.db' \
  --exclude 'credentials/' \
  --exclude '.env' \
  "$SERVER:$SERVER_SERVICES" "$SERVICES_DIR/" \
  && echo "✅ Sync complete" || echo "❌ Sync failed"

# Step 2: Check for changes
echo ""
echo "[2/6] Checking for changes..."
cd "$LOCAL_DIR"

if git diff --quiet && git diff --cached --quiet; then
  echo "No changes detected - backup not needed"
  exit 0
fi

echo "Changes detected:"
git status --short | head -20

# Step 3: Stage changes
echo ""
echo "[3/6] Staging changes..."
git add agents/services/

# Step 4: Commit changes
echo ""
echo "[4/6] Creating commit..."
COMMIT_MSG="Automated backup - $DATE

Changes:
$(git status --short | head -10)

🤖 Automated via backup-to-github.sh
"

git commit -m "$COMMIT_MSG" && echo "✅ Commit created" || echo "❌ Commit failed"

# Step 5: Push to GitHub
echo ""
echo "[5/6] Pushing to GitHub..."
git push origin main && echo "✅ Pushed to GitHub" || echo "❌ Push failed"

# Step 6: Create local archive backup
echo ""
echo "[6/6] Creating local archive backup..."
ARCHIVE_NAME="fpai-services-$DATE.tar.gz"
tar czf "$BACKUP_DIR/$ARCHIVE_NAME" -C "$LOCAL_DIR" agents/services/ \
  && echo "✅ Archive created: $BACKUP_DIR/$ARCHIVE_NAME" \
  || echo "❌ Archive creation failed"

# Clean up old archives (keep last 7 days)
echo ""
echo "Cleaning up old archives..."
find "$BACKUP_DIR" -name "fpai-services-*.tar.gz" -mtime +7 -delete
echo "Archive cleanup complete"

echo ""
echo "========================================="
echo "Backup Complete!"
echo "========================================="
echo "GitHub: https://github.com/jamessunheart/fpai-sessions"
echo "Local archive: $BACKUP_DIR/$ARCHIVE_NAME"
echo ""
