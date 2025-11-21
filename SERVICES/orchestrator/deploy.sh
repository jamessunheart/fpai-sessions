#!/bin/bash
# Orchestrator Deployment Script
# Usage: ./deploy.sh [environment]
# Example: ./deploy.sh production

set -e  # Exit on error

ENV=${1:-development}
echo "🚀 Deploying Orchestrator to $ENV environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Pre-deployment checks
echo "📋 Running pre-deployment checks..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi
print_status "Docker is installed"

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi
print_status "Docker Compose is installed"

# 2. Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found, creating from template..."
    cat > .env <<EOF
ENVIRONMENT=$ENV
LOG_LEVEL=INFO
REGISTRY_URL=http://registry:8000
CACHE_DIR=/var/cache/fpai
REGISTRY_SYNC_INTERVAL=60
TASK_TIMEOUT=30
TASK_MAX_RETRIES=3
HOST=0.0.0.0
PORT=8001
EOF
    print_status "Created .env file"
else
    print_status ".env file exists"
fi

# 3. Run tests
echo "🧪 Running tests..."
if [ -d ".venv" ]; then
    .venv/bin/pytest -v --tb=short
    if [ $? -eq 0 ]; then
        print_status "All tests passed"
    else
        print_error "Tests failed"
        exit 1
    fi
else
    print_warning "Virtual environment not found, skipping tests"
fi

# 4. Build Docker image
echo "🔨 Building Docker image..."
docker compose build orchestrator
print_status "Docker image built"

# 5. Stop existing container (if running)
echo "🛑 Stopping existing container..."
docker compose stop orchestrator 2>/dev/null || true
print_status "Existing container stopped"

# 6. Start new container
echo "▶️  Starting new container..."
docker compose up -d orchestrator
print_status "Container started"

# 7. Wait for container to be healthy
echo "⏳ Waiting for container to be healthy..."
sleep 5

# 8. Health check
echo "🏥 Running health check..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8001/orchestrator/health &> /dev/null; then
        print_status "Health check passed"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Health check failed after $MAX_RETRIES attempts"
    echo "📋 Container logs:"
    docker compose logs --tail=50 orchestrator
    exit 1
fi

# 9. Test endpoints
echo "🔍 Testing endpoints..."

# Test info endpoint
if curl -f http://localhost:8001/orchestrator/info &> /dev/null; then
    print_status "Info endpoint working"
else
    print_warning "Info endpoint not responding"
fi

# Test metrics endpoint
if curl -f http://localhost:8001/orchestrator/metrics &> /dev/null; then
    print_status "Metrics endpoint working"
else
    print_warning "Metrics endpoint not responding"
fi

# 10. Show status
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Deployment complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Container status:"
docker compose ps orchestrator
echo ""
echo "🔗 Endpoints:"
echo "   Health:   http://localhost:8001/orchestrator/health"
echo "   Info:     http://localhost:8001/orchestrator/info"
echo "   Droplets: http://localhost:8001/orchestrator/droplets"
echo "   Metrics:  http://localhost:8001/orchestrator/metrics"
echo ""
echo "📝 View logs:"
echo "   docker compose logs -f orchestrator"
echo ""
echo "🔄 Restart service:"
echo "   docker compose restart orchestrator"
echo ""

# 11. Show recent logs
echo "📋 Recent logs:"
docker compose logs --tail=20 orchestrator
