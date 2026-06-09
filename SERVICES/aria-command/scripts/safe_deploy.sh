#!/bin/bash
#
# SAFE DEPLOY SCRIPT
# ==================
#
# Deploys aria-command with:
# 1. Pre-deploy tests
# 2. Automatic backup
# 3. Post-deploy verification
# 4. Automatic rollback on failure
#
# Usage: ./safe_deploy.sh
#

set -e

SERVER="root@100.127.118.106"
REMOTE_PATH="/opt/fpai/aria-command"
BACKUP_PATH="/opt/fpai/aria-command.backup"
LOCAL_PATH="$(dirname $(dirname $(realpath $0)))"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "  ARIA SAFE DEPLOY"
echo "========================================"
echo ""

# ============================================================================
# STEP 1: Run local tests
# ============================================================================
echo -e "${YELLOW}Step 1: Running local tests...${NC}"

cd "$LOCAL_PATH"
if python3 scripts/test_critical.py; then
    echo -e "${GREEN}Local tests passed${NC}"
else
    echo -e "${RED}Local tests FAILED - Aborting deploy${NC}"
    exit 1
fi

echo ""

# ============================================================================
# STEP 2: Backup current version on server
# ============================================================================
echo -e "${YELLOW}Step 2: Backing up current version...${NC}"

ssh $SERVER "rm -rf $BACKUP_PATH && cp -r $REMOTE_PATH $BACKUP_PATH" || {
    echo -e "${RED}Backup failed${NC}"
    exit 1
}
echo -e "${GREEN}Backup created at $BACKUP_PATH${NC}"

echo ""

# ============================================================================
# STEP 3: Deploy new code
# ============================================================================
echo -e "${YELLOW}Step 3: Deploying new code...${NC}"

rsync -avz --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
    --exclude='state/*.db' --exclude='state/*.json' --exclude='data/*.db' \
    "$LOCAL_PATH/" "$SERVER:$REMOTE_PATH/"

echo -e "${GREEN}Code deployed${NC}"

echo ""

# ============================================================================
# STEP 4: Run remote tests
# ============================================================================
echo -e "${YELLOW}Step 4: Running remote tests...${NC}"

if ssh $SERVER "cd $REMOTE_PATH && python3 scripts/test_critical.py"; then
    echo -e "${GREEN}Remote tests passed${NC}"
else
    echo -e "${RED}Remote tests FAILED - Rolling back...${NC}"
    ssh $SERVER "rm -rf $REMOTE_PATH && mv $BACKUP_PATH $REMOTE_PATH"
    echo -e "${YELLOW}Rollback complete${NC}"
    exit 1
fi

echo ""

# ============================================================================
# STEP 5: Restart service
# ============================================================================
echo -e "${YELLOW}Step 5: Restarting service...${NC}"

ssh $SERVER "systemctl restart aria-command"
sleep 5

echo ""

# ============================================================================
# STEP 6: Verify service health
# ============================================================================
echo -e "${YELLOW}Step 6: Verifying service health...${NC}"

HEALTH=$(ssh $SERVER "curl -sf http://localhost:8750/health 2>/dev/null || echo 'FAILED'")

if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}Service is healthy${NC}"
else
    echo -e "${RED}Health check FAILED - Rolling back...${NC}"
    ssh $SERVER "rm -rf $REMOTE_PATH && mv $BACKUP_PATH $REMOTE_PATH && systemctl restart aria-command"
    echo -e "${YELLOW}Rollback complete${NC}"
    exit 1
fi

echo ""

# ============================================================================
# STEP 7: Quick functionality test
# ============================================================================
echo -e "${YELLOW}Step 7: Testing basic functionality...${NC}"

# Test webhook endpoint
WEBHOOK=$(ssh $SERVER "curl -sf -X POST http://localhost:8750/telegram/webhook -H 'Content-Type: application/json' -d '{\"message\":{\"chat\":{\"id\":0},\"text\":\"test\"}}' 2>/dev/null || echo 'FAILED'")

if echo "$WEBHOOK" | grep -q "ok"; then
    echo -e "${GREEN}Webhook responding${NC}"
else
    echo -e "${YELLOW}Warning: Webhook test inconclusive${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}  DEPLOY SUCCESSFUL${NC}"
echo "========================================"
echo ""
echo "Backup saved at: $BACKUP_PATH"
echo "To rollback manually:"
echo "  ssh $SERVER 'rm -rf $REMOTE_PATH && mv $BACKUP_PATH $REMOTE_PATH && systemctl restart aria-command'"








