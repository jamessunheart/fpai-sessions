#!/bin/bash

# REGISTRY AUTO-REGISTRATION
# Purpose: Automatically register a service with the Full Potential AI Registry
# Usage: ./register-with-registry.sh <service-name> <service-port> [droplet-id]

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
REGISTRY_URL="${REGISTRY_URL:-http://198.54.123.234:8000}"
SERVICE_NAME="$1"
SERVICE_PORT="$2"
DROPLET_ID="$3"

# Validate arguments
if [ -z "$SERVICE_NAME" ] || [ -z "$SERVICE_PORT" ]; then
    print_error "Usage: $0 <service-name> <service-port> [droplet-id]"
    echo ""
    echo "Arguments:"
    echo "  service-name    Name of the service (e.g., orchestrator, dashboard)"
    echo "  service-port    Port number the service runs on"
    echo "  droplet-id      Optional droplet ID (will auto-assign if not provided)"
    echo ""
    echo "Examples:"
    echo "  $0 orchestrator 8001"
    echo "  $0 orchestrator 8001 10"
    echo "  $0 dashboard 8002 2"
    echo ""
    echo "Environment Variables:"
    echo "  REGISTRY_URL    Registry endpoint (default: http://198.54.123.234:8000)"
    echo ""
    exit 1
fi

# Construct service endpoint
SERVER_IP="${SERVER_IP:-198.54.123.234}"
SERVICE_ENDPOINT="http://${SERVER_IP}:${SERVICE_PORT}"

print_info "Registering service with Registry..."
echo "  Service: $SERVICE_NAME"
echo "  Endpoint: $SERVICE_ENDPOINT"
echo "  Registry: $REGISTRY_URL"
[ -n "$DROPLET_ID" ] && echo "  Droplet ID: $DROPLET_ID"
echo ""

# Check if Registry is available
print_info "Checking Registry availability..."
if ! curl -sf "$REGISTRY_URL/health" >/dev/null 2>&1; then
    print_error "Registry not accessible at $REGISTRY_URL"
    print_info "Troubleshooting:"
    echo "  1. Verify Registry is running: curl $REGISTRY_URL/health"
    echo "  2. Check firewall/network: ping ${REGISTRY_URL#http://}"
    echo "  3. Update REGISTRY_URL environment variable if needed"
    exit 1
fi
print_success "Registry is online"

# Get current timestamp
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Build registration payload
if [ -n "$DROPLET_ID" ]; then
    PAYLOAD=$(cat <<EOF
{
  "id": $DROPLET_ID,
  "name": "$SERVICE_NAME",
  "steward": "claude-code-automation",
  "endpoint": "$SERVICE_ENDPOINT",
  "metadata": {
    "deployment_method": "automated",
    "registered_at": "$TIMESTAMP",
    "port": $SERVICE_PORT,
    "server": "$SERVER_IP"
  }
}
EOF
)
else
    PAYLOAD=$(cat <<EOF
{
  "name": "$SERVICE_NAME",
  "steward": "claude-code-automation",
  "endpoint": "$SERVICE_ENDPOINT",
  "metadata": {
    "deployment_method": "automated",
    "registered_at": "$TIMESTAMP",
    "port": $SERVICE_PORT,
    "server": "$SERVER_IP"
  }
}
EOF
)
fi

# Register with Registry
print_info "Sending registration request..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$REGISTRY_URL/droplets" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" 2>&1)

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
    print_success "Service registered successfully!"

    # Extract and display registration details
    if command -v jq >/dev/null 2>&1; then
        REGISTERED_ID=$(echo "$BODY" | jq -r '.droplet.id')
        REGISTERED_NAME=$(echo "$BODY" | jq -r '.droplet.name')
        REGISTERED_ENDPOINT=$(echo "$BODY" | jq -r '.droplet.endpoint')

        echo ""
        print_info "Registration Details:"
        echo "  • Droplet ID: $REGISTERED_ID"
        echo "  • Name: $REGISTERED_NAME"
        echo "  • Endpoint: $REGISTERED_ENDPOINT"
        echo "  • Registry: $REGISTRY_URL/droplets/$REGISTERED_ID"
    else
        echo ""
        print_info "Registration confirmed (install jq for detailed output)"
    fi

    echo ""

elif [ "$HTTP_CODE" = "409" ]; then
    print_warning "Service already registered - updating..."

    # Try to get droplet ID by name
    DROPLET_INFO=$(curl -s "$REGISTRY_URL/droplets/name/$SERVICE_NAME" 2>&1)

    if command -v jq >/dev/null 2>&1; then
        EXISTING_ID=$(echo "$DROPLET_INFO" | jq -r '.droplet.id')

        if [ -n "$EXISTING_ID" ] && [ "$EXISTING_ID" != "null" ]; then
            print_info "Updating existing droplet (ID: $EXISTING_ID)..."

            UPDATE_PAYLOAD=$(cat <<EOF
{
  "endpoint": "$SERVICE_ENDPOINT",
  "status": "active",
  "metadata": {
    "deployment_method": "automated",
    "updated_at": "$TIMESTAMP",
    "port": $SERVICE_PORT,
    "server": "$SERVER_IP"
  }
}
EOF
)

            UPDATE_RESPONSE=$(curl -s -w "\n%{http_code}" -X PATCH "$REGISTRY_URL/droplets/$EXISTING_ID" \
                -H "Content-Type: application/json" \
                -d "$UPDATE_PAYLOAD" 2>&1)

            UPDATE_CODE=$(echo "$UPDATE_RESPONSE" | tail -n1)

            if [ "$UPDATE_CODE" = "200" ]; then
                print_success "Service updated in Registry!"
            else
                print_warning "Update failed (HTTP $UPDATE_CODE) but service is registered"
            fi
        fi
    else
        print_success "Service already registered (install jq for update capability)"
    fi

else
    print_error "Registration failed (HTTP $HTTP_CODE)"
    echo ""
    print_info "Response:"
    echo "$BODY"
    echo ""
    print_info "Troubleshooting:"
    echo "  1. Check Registry logs: ssh fpai-prod 'docker logs registry'"
    echo "  2. Verify payload format is correct"
    echo "  3. Try manual registration: curl -X POST $REGISTRY_URL/droplets -d '$PAYLOAD'"
    exit 1
fi

# Verify registration by querying Registry
print_info "Verifying registration..."

if VERIFY=$(curl -s "$REGISTRY_URL/droplets" 2>&1); then
    if echo "$VERIFY" | grep -q "$SERVICE_NAME"; then
        print_success "Service confirmed in Registry listing"

        # Display total droplets count
        if command -v jq >/dev/null 2>&1; then
            TOTAL=$(echo "$VERIFY" | jq -r '.total')
            echo ""
            print_info "Registry Status: $TOTAL droplet(s) registered"
        fi
    else
        print_warning "Service not found in Registry listing (may need a moment to propagate)"
    fi
else
    print_warning "Could not verify registration (Registry query failed)"
fi

echo ""
print_success "Registry registration complete! 🌐⚡💎"
echo ""
print_info "View in Registry:"
echo "  curl $REGISTRY_URL/droplets"
echo "  curl $REGISTRY_URL/droplets/name/$SERVICE_NAME"
echo ""
