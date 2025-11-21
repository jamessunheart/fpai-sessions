#!/bin/bash

# DEPLOY TO SERVER - Automated Deployment Pipeline
# Purpose: Seamless local → GitHub → server deployment with automated verification
# Usage: ./deploy-to-server.sh <service-name> [commit-message]
# Example: ./deploy-to-server.sh orchestrator "Add new feature"

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() { echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${CYAN}$1${NC}"; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
print_step() { echo -e "${BLUE}[$1/$TOTAL_STEPS]${NC} $2"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Configuration
SERVER_IP="198.54.123.234"
SERVER_USER="root"
SERVER="${SERVER_USER}@${SERVER_IP}"
DEPLOY_BASE_PATH="/opt/fpai/apps"

# SSH Configuration
SSH_KEY="$HOME/.ssh/fpai_deploy_ed25519"
SSH_OPTS="-i ${SSH_KEY} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

# Check if SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    print_error "SSH key not found: $SSH_KEY"
    print_info "Run ./setup-ssh-access.sh to configure SSH access"
    exit 1
fi

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_NAME="$1"
COMMIT_MSG="${2:-Update $SERVICE_NAME deployment}"

TOTAL_STEPS=8

# Validate arguments
if [ -z "$SERVICE_NAME" ]; then
    print_error "Usage: $0 <service-name> [commit-message]"
    echo ""
    echo "Arguments:"
    echo "  service-name      Name of the service to deploy (orchestrator, registry, etc.)"
    echo "  commit-message    Optional commit message (default: 'Update <service> deployment')"
    echo ""
    echo "Examples:"
    echo "  $0 orchestrator"
    echo "  $0 orchestrator 'Fix critical bug in routing'"
    echo ""
    exit 1
fi

# Determine service directory
SERVICE_DIR="${BASE_DIR}/${SERVICE_NAME}"

if [ ! -d "$SERVICE_DIR" ]; then
    print_error "Service directory not found: $SERVICE_DIR"
    exit 1
fi

# Determine service configuration
case "$SERVICE_NAME" in
    orchestrator)
        SERVICE_PORT=8001
        HEALTH_ENDPOINT="/orchestrator/health"
        ;;
    registry)
        SERVICE_PORT=8000
        HEALTH_ENDPOINT="/health"
        ;;
    dashboard)
        SERVICE_PORT=8002
        HEALTH_ENDPOINT="/health"
        ;;
    *)
        SERVICE_PORT=8000
        HEALTH_ENDPOINT="/health"
        print_warning "Unknown service, using default port 8000 and /health endpoint"
        ;;
esac

HEALTH_URL="http://${SERVER_IP}:${SERVICE_PORT}${HEALTH_ENDPOINT}"

print_header "🚀 FULL POTENTIAL AI - AUTOMATED DEPLOYMENT"
echo ""
print_info "Service: $SERVICE_NAME"
print_info "Service Directory: $SERVICE_DIR"
print_info "Target Server: $SERVER"
print_info "Deploy Path: $DEPLOY_BASE_PATH/$SERVICE_NAME"
print_info "Health Check: $HEALTH_URL"
echo ""

# ============================================================================
# STEP 1: Pre-deployment checks
# ============================================================================
print_step 1 "Running pre-deployment checks..."

cd "$SERVICE_DIR"

# Check if git repo
if [ ! -d ".git" ]; then
    print_error "Not a git repository: $SERVICE_DIR"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD -- 2>/dev/null; then
    print_warning "Uncommitted changes detected"
    HAS_CHANGES=true
else
    HAS_CHANGES=false
fi

print_success "Pre-deployment checks passed"
echo ""

# ============================================================================
# STEP 2: Run tests locally
# ============================================================================
print_step 2 "Running tests locally..."

if [ -d "test" ] || [ -d "tests" ]; then
    # Activate virtual environment if it exists
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi

    # Run pytest
    if pytest -v --tb=short 2>&1 | tee /tmp/pytest-output.log; then
        print_success "All tests passed"
    else
        print_error "Tests failed - deployment aborted"
        echo ""
        print_info "Fix the failing tests before deploying"
        exit 1
    fi
else
    print_warning "No tests found - skipping test phase"
fi
echo ""

# ============================================================================
# STEP 3: Commit and push to GitHub (SSOT)
# ============================================================================
print_step 3 "Syncing with GitHub (SSOT)..."

if [ "$HAS_CHANGES" = true ]; then
    print_info "Committing local changes..."
    git add .
    git commit -m "$COMMIT_MSG

🤖 Automated deployment to production

Co-Authored-By: Claude Code <noreply@anthropic.com>"
    print_success "Changes committed"
fi

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
print_info "Pushing to origin/$CURRENT_BRANCH..."

if git push origin "$CURRENT_BRANCH"; then
    print_success "Pushed to GitHub"
else
    print_error "Failed to push to GitHub"
    exit 1
fi

# Get latest commit hash for verification
COMMIT_HASH=$(git rev-parse --short HEAD)
print_info "Commit: $COMMIT_HASH"
echo ""

# ============================================================================
# STEP 4: Create backup on server
# ============================================================================
print_step 4 "Creating backup on server..."

BACKUP_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="backup-${BACKUP_TIMESTAMP}.tar.gz"

ssh $SSH_OPTS "$SERVER" "
    cd $DEPLOY_BASE_PATH/$SERVICE_NAME 2>/dev/null || exit 0
    if [ -d .git ]; then
        tar -czf $BACKUP_NAME --exclude='.git' --exclude='__pycache__' --exclude='.venv' --exclude='*.pyc' . 2>/dev/null || true
        echo 'Backup created: $BACKUP_NAME'
    fi
" && print_success "Backup created on server" || print_warning "No existing deployment to backup"
echo ""

# ============================================================================
# STEP 5: Pull latest code from GitHub on server
# ============================================================================
print_step 5 "Pulling latest code on server..."

ssh $SSH_OPTS "$SERVER" "
    set -e
    cd $DEPLOY_BASE_PATH/$SERVICE_NAME

    # Pull latest changes
    git fetch origin
    git pull origin $CURRENT_BRANCH

    # Verify commit hash
    SERVER_COMMIT=\$(git rev-parse --short HEAD)
    echo \"Server now at commit: \$SERVER_COMMIT\"

    # Install/update dependencies if requirements.txt exists
    if [ -f requirements.txt ]; then
        if [ -d .venv ]; then
            source .venv/bin/activate
            pip install -q -r requirements.txt
            echo 'Dependencies updated'
        fi
    fi
"

print_success "Code updated on server"
echo ""

# ============================================================================
# STEP 6: Run tests on server
# ============================================================================
print_step 6 "Running tests on server..."

ssh $SSH_OPTS "$SERVER" "
    cd $DEPLOY_BASE_PATH/$SERVICE_NAME

    if [ -d test ] || [ -d tests ]; then
        if [ -d .venv ]; then
            source .venv/bin/activate
            pytest -v --tb=short || exit 1
            echo 'Tests passed on server'
        fi
    else
        echo 'No tests found on server'
    fi
" && print_success "Server tests passed" || {
    print_error "Tests failed on server - rolling back..."
    # Attempt rollback
    ssh $SSH_OPTS "$SERVER" "
        cd $DEPLOY_BASE_PATH/$SERVICE_NAME
        if [ -f $BACKUP_NAME ]; then
            tar -xzf $BACKUP_NAME
            echo 'Rollback complete'
        fi
    "
    exit 1
}
echo ""

# ============================================================================
# STEP 7: Restart service gracefully
# ============================================================================
print_step 7 "Restarting service on server..."

# Check if systemd service exists
if ssh $SSH_OPTS "$SERVER" "systemctl list-units --type=service --all | grep -q fpai-$SERVICE_NAME"; then
    print_info "Using systemd service: fpai-$SERVICE_NAME"
    ssh $SSH_OPTS "$SERVER" "systemctl restart fpai-$SERVICE_NAME"
    print_success "Service restarted via systemd"
elif ssh $SSH_OPTS "$SERVER" "docker ps -a --format '{{.Names}}' | grep -q '^${SERVICE_NAME}\$'"; then
    print_info "Using Docker container: $SERVICE_NAME"
    ssh $SSH_OPTS "$SERVER" "docker restart $SERVICE_NAME"
    print_success "Service restarted via Docker"
else
    print_warning "No systemd service or Docker container found"
    print_info "Manual restart may be required"
fi

# Wait for service to start
print_info "Waiting for service to initialize..."
sleep 5
echo ""

# ============================================================================
# STEP 8: Verify deployment with health check
# ============================================================================
print_step 8 "Verifying deployment..."

MAX_RETRIES=12
RETRY_COUNT=0
RETRY_DELAY=5

print_info "Health check URL: $HEALTH_URL"
print_info "Max retries: $MAX_RETRIES (${RETRY_DELAY}s interval)"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f -s "$HEALTH_URL" > /dev/null 2>&1; then
        print_success "Health check passed!"

        # Get health response
        HEALTH_RESPONSE=$(curl -s "$HEALTH_URL")
        echo ""
        print_info "Health Response:"
        echo "$HEALTH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_RESPONSE"

        DEPLOYMENT_SUCCESS=true
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))

    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "   Attempt $RETRY_COUNT/$MAX_RETRIES - retrying in ${RETRY_DELAY}s..."
        sleep $RETRY_DELAY
    fi
done

if [ "${DEPLOYMENT_SUCCESS:-false}" != "true" ]; then
    print_error "Health check failed after $MAX_RETRIES attempts"
    echo ""
    print_info "Fetching service logs from server..."

    # Try to get logs
    if ssh $SSH_OPTS "$SERVER" "systemctl is-active --quiet fpai-$SERVICE_NAME"; then
        echo ""
        print_info "Last 30 lines of service logs:"
        ssh $SSH_OPTS "$SERVER" "journalctl -u fpai-$SERVICE_NAME -n 30 --no-pager"
    elif ssh $SSH_OPTS "$SERVER" "docker ps -a --format '{{.Names}}' | grep -q '^${SERVICE_NAME}\$'"; then
        echo ""
        print_info "Last 30 lines of Docker logs:"
        ssh $SSH_OPTS "$SERVER" "docker logs --tail 30 $SERVICE_NAME"
    fi

    echo ""
    print_error "DEPLOYMENT FAILED"
    print_info "Backup available on server: $BACKUP_NAME"
    exit 1
fi

echo ""

# ============================================================================
# REGISTER WITH REGISTRY (Sacred Loop Step 7)
# ============================================================================
print_step "$CURRENT_STEP" "Registering service with Registry..."
CURRENT_STEP=$((CURRENT_STEP + 1))

REGISTRATION_SCRIPT="$(dirname "$0")/register-with-registry.sh"

if [ -x "$REGISTRATION_SCRIPT" ]; then
    # Determine droplet ID based on service name
    case "$SERVICE_NAME" in
        registry) DROPLET_ID=1 ;;
        dashboard) DROPLET_ID=2 ;;
        proxy-manager) DROPLET_ID=3 ;;
        verifier) DROPLET_ID=8 ;;
        orchestrator) DROPLET_ID=10 ;;
        coordinator) DROPLET_ID=11 ;;
        recruiter) DROPLET_ID=15 ;;
        self-optimizer) DROPLET_ID=16 ;;
        deployer) DROPLET_ID=17 ;;
        meta-architect) DROPLET_ID=18 ;;
        mesh-expander) DROPLET_ID=19 ;;
        *) DROPLET_ID="" ;;
    esac

    # Don't register registry with itself
    if [ "$SERVICE_NAME" != "registry" ]; then
        print_info "Attempting automatic Registry registration..."

        if [ -n "$DROPLET_ID" ]; then
            "$REGISTRATION_SCRIPT" "$SERVICE_NAME" "$SERVICE_PORT" "$DROPLET_ID" || print_warning "Registry registration failed (non-critical)"
        else
            "$REGISTRATION_SCRIPT" "$SERVICE_NAME" "$SERVICE_PORT" || print_warning "Registry registration failed (non-critical)"
        fi
    else
        print_info "Registry service doesn't register with itself"
    fi
else
    print_warning "Registry registration script not found (skipping auto-registration)"
    print_info "Register manually: curl -X POST http://198.54.123.234:8000/droplets -d '{...}'"
fi

echo ""

# ============================================================================
# DEPLOYMENT COMPLETE
# ============================================================================
print_header "✅ DEPLOYMENT COMPLETE"
echo ""
print_success "Service: $SERVICE_NAME"
print_success "Commit: $COMMIT_HASH"
print_success "Server: $SERVER_IP"
print_success "Status: Healthy"
echo ""
print_info "Next steps:"
echo "   1. Run comprehensive health check: ./fpai-ops/server-health-monitor.sh"
echo "   2. Monitor logs: ssh $SERVER 'journalctl -u fpai-$SERVICE_NAME -f'"
echo "   3. Update MEMORY/CURRENT_STATE.md with deployment notes"
echo ""
echo "🌐⚡💎"
