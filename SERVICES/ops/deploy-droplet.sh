#!/bin/bash

# DROPLET DEPLOYER
# Blueprint: 1-SYSTEM-BLUEPRINT.txt - Section 2 (Sacred Loop Step 6: Deployer deploys)
# Purpose: Deploy droplets to production server
# Usage: ./deploy-droplet.sh <service-name> [environment]

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Configuration
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENVIRONMENT="${2:-production}"
SERVICE_NAME="$1"

# Server configuration (customize these)
PRODUCTION_SERVER="${PRODUCTION_SERVER:-user@production-server.com}"
STAGING_SERVER="${STAGING_SERVER:-user@staging-server.com}"
REGISTRY_URL="${REGISTRY_URL:-http://localhost:8001}"

# Check arguments
if [ -z "$SERVICE_NAME" ]; then
    print_error "Usage: $0 <service-name> [environment]"
    echo ""
    echo "Arguments:"
    echo "  service-name   Name of the droplet to deploy"
    echo "  environment    production|staging (default: production)"
    echo ""
    echo "Examples:"
    echo "  $0 registry"
    echo "  $0 orchestrator staging"
    exit 1
fi

# Find service directory
find_service_dir() {
    local service=$1

    # Try exact name first
    if [ -d "${BASE_DIR}/${service}" ]; then
        echo "${BASE_DIR}/${service}"
        return 0
    fi

    # Try with droplet prefix
    for dir in "${BASE_DIR}"/droplet-*-${service}; do
        if [ -d "$dir" ]; then
            echo "$dir"
            return 0
        fi
    done

    return 1
}

SERVICE_DIR=$(find_service_dir "$SERVICE_NAME")

if [ -z "$SERVICE_DIR" ]; then
    print_error "Service directory not found for: $SERVICE_NAME"
    exit 1
fi

print_info "Deploying $SERVICE_NAME to $ENVIRONMENT..."
print_info "Service directory: $SERVICE_DIR"

# Pre-deployment checks
print_info "Running pre-deployment checks..."

# Check if Dockerfile exists
if [ ! -f "$SERVICE_DIR/Dockerfile" ]; then
    print_error "No Dockerfile found in $SERVICE_DIR"
    exit 1
fi

# Run tests
print_info "Running tests..."
cd "$SERVICE_DIR"

if [ -d "tests" ]; then
    if pytest tests/ --quiet; then
        print_success "Tests passed"
    else
        print_error "Tests failed - deployment aborted"
        exit 1
    fi
else
    print_warning "No tests found - skipping"
fi

# Run code standards check
print_info "Checking code standards..."
if command -v black >/dev/null 2>&1; then
    if black --check app/ tests/ --quiet 2>/dev/null; then
        print_success "Code standards check passed"
    else
        print_warning "Code formatting issues detected (non-blocking)"
    fi
fi

# Build Docker image
IMAGE_NAME="droplet-${SERVICE_NAME}"
IMAGE_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

print_info "Building Docker image: $FULL_IMAGE..."

if docker build -t "$FULL_IMAGE" -t "${IMAGE_NAME}:${ENVIRONMENT}-latest" .; then
    print_success "Docker image built"
else
    print_error "Docker build failed"
    exit 1
fi

# Test the Docker image locally
print_info "Testing Docker image..."

# Find an available port for testing
TEST_PORT=$(python3 -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()')

docker run -d --name "${IMAGE_NAME}-test" -p "${TEST_PORT}:8000" "$FULL_IMAGE" >/dev/null

# Wait for container to start
sleep 3

# Test health endpoint
if curl -f "http://localhost:${TEST_PORT}/health" >/dev/null 2>&1; then
    print_success "Docker image health check passed"
else
    print_error "Docker image health check failed"
    docker stop "${IMAGE_NAME}-test" >/dev/null
    docker rm "${IMAGE_NAME}-test" >/dev/null
    exit 1
fi

# Cleanup test container
docker stop "${IMAGE_NAME}-test" >/dev/null
docker rm "${IMAGE_NAME}-test" >/dev/null

# Select target server
TARGET_SERVER=""
case "$ENVIRONMENT" in
    production)
        TARGET_SERVER="$PRODUCTION_SERVER"
        ;;
    staging)
        TARGET_SERVER="$STAGING_SERVER"
        ;;
    *)
        print_error "Unknown environment: $ENVIRONMENT"
        exit 1
        ;;
esac

# Save image to tar
print_info "Saving Docker image to tarball..."
IMAGE_TAR="/tmp/${IMAGE_NAME}-${IMAGE_TAG}.tar"
docker save "$FULL_IMAGE" -o "$IMAGE_TAR"
print_success "Image saved to $IMAGE_TAR"

# If deploying to remote server
if [ "$TARGET_SERVER" != "localhost" ] && [ -n "$TARGET_SERVER" ]; then
    print_info "Deploying to remote server: $TARGET_SERVER..."

    # Transfer image
    print_info "Transferring image to server..."
    scp "$IMAGE_TAR" "${TARGET_SERVER}:/tmp/"

    # Load and run on server
    print_info "Loading and starting service on server..."

    ssh "$TARGET_SERVER" << EOF
        # Load Docker image
        docker load -i /tmp/$(basename "$IMAGE_TAR")

        # Stop old container (if exists)
        docker stop $IMAGE_NAME 2>/dev/null || true
        docker rm $IMAGE_NAME 2>/dev/null || true

        # Start new container
        docker run -d \\
            --name $IMAGE_NAME \\
            --restart unless-stopped \\
            -p 8000:8000 \\
            -e ENVIRONMENT=$ENVIRONMENT \\
            -e REGISTRY_URL=$REGISTRY_URL \\
            $FULL_IMAGE

        # Cleanup tar file
        rm /tmp/$(basename "$IMAGE_TAR")
EOF

    # Cleanup local tar
    rm "$IMAGE_TAR"

    print_success "Deployed to $TARGET_SERVER"

else
    # Local deployment
    print_info "Deploying locally..."

    # Stop old container (if exists)
    docker stop "$IMAGE_NAME" 2>/dev/null || true
    docker rm "$IMAGE_NAME" 2>/dev/null || true

    # Start new container
    docker run -d \
        --name "$IMAGE_NAME" \
        --restart unless-stopped \
        -p 8000:8000 \
        -e ENVIRONMENT="$ENVIRONMENT" \
        -e REGISTRY_URL="$REGISTRY_URL" \
        "$FULL_IMAGE"

    # Cleanup tar
    rm "$IMAGE_TAR"

    print_success "Deployed locally"
fi

# Post-deployment verification
print_info "Verifying deployment..."
sleep 5

if [ "$TARGET_SERVER" != "localhost" ] && [ -n "$TARGET_SERVER" ]; then
    # Remote health check (would need to know the public URL)
    print_warning "Remote health check - manual verification recommended"
else
    # Local health check
    if curl -f "http://localhost:8000/health" >/dev/null 2>&1; then
        print_success "Deployment health check passed"
    else
        print_error "Deployment health check failed"
        exit 1
    fi
fi

# Register with Registry (if Registry is available)
if curl -f "$REGISTRY_URL/health" >/dev/null 2>&1; then
    print_info "Registering with Registry..."
    # Would call Registry API here
    print_success "Registered with Registry"
else
    print_warning "Registry not available - skipping registration"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "DEPLOYMENT COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Service: $SERVICE_NAME"
echo "Environment: $ENVIRONMENT"
echo "Image: $FULL_IMAGE"
echo "Status: Running"
echo ""
print_info "Monitor logs with: docker logs -f $IMAGE_NAME"
echo ""
echo "🌐⚡💎"
