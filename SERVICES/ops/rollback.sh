#!/bin/bash

# ROLLBACK SCRIPT
# Blueprint: 1-SYSTEM-BLUEPRINT.txt - Deployment safety
# Purpose: Quick rollback to previous version
# Usage: ./rollback.sh <service-name>

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

# Check arguments
if [ -z "$1" ]; then
    print_error "Usage: $0 <service-name>"
    echo ""
    echo "Examples:"
    echo "  $0 registry"
    echo "  $0 orchestrator"
    exit 1
fi

SERVICE_NAME="$1"
IMAGE_NAME="droplet-${SERVICE_NAME}"

print_info "Rolling back: $SERVICE_NAME"
echo ""

# List available Docker images
print_info "Available versions:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}" | grep "$IMAGE_NAME" || {
    print_error "No Docker images found for $SERVICE_NAME"
    exit 1
}

echo ""

# Get current running version
CURRENT_IMAGE=$(docker inspect "$IMAGE_NAME" --format='{{.Config.Image}}' 2>/dev/null || echo "Not running")

print_info "Current version: $CURRENT_IMAGE"

# Find previous version
PREVIOUS_IMAGE=$(docker images "$IMAGE_NAME" --format "{{.Repository}}:{{.Tag}}" | grep -v "latest" | sed -n '2p')

if [ -z "$PREVIOUS_IMAGE" ]; then
    print_error "No previous version found"
    exit 1
fi

print_info "Rolling back to: $PREVIOUS_IMAGE"
echo ""

# Confirm rollback
read -p "Continue with rollback? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Rollback cancelled"
    exit 0
fi

# Stop current container
print_info "Stopping current container..."
docker stop "$IMAGE_NAME" 2>/dev/null || true
docker rm "$IMAGE_NAME" 2>/dev/null || true

# Start previous version
print_info "Starting previous version..."

docker run -d \
    --name "$IMAGE_NAME" \
    --restart unless-stopped \
    -p 8000:8000 \
    "$PREVIOUS_IMAGE"

# Wait for container to start
sleep 3

# Health check
print_info "Verifying rollback..."

if docker ps | grep -q "$IMAGE_NAME"; then
    if curl -f "http://localhost:8000/health" >/dev/null 2>&1; then
        print_success "Rollback successful!"
        print_info "Service is healthy at: http://localhost:8000"
    else
        print_warning "Container running but health check failed"
        print_info "Check logs: docker logs $IMAGE_NAME"
    fi
else
    print_error "Container failed to start"
    print_info "Check logs: docker logs $IMAGE_NAME"
    exit 1
fi

echo ""
print_success "Rollback complete! 🌐⚡💎"
echo ""
print_info "Monitor logs: docker logs -f $IMAGE_NAME"
