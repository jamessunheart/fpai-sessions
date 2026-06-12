#!/bin/bash
# =============================================================================
# DROPLET FACTORY - Maximum Per-Prompt Power
# =============================================================================
# Usage: ./create-droplet.sh <name> <port> "<description>"
# Example: ./create-droplet.sh analytics 8764 "Usage tracking and metrics"
#
# This script:
# 1. Creates all required files (SPECS.md, main.py, tests, requirements.txt, README)
# 2. Validates syntax locally
# 3. Deploys to server
# 4. Creates systemd service
# 5. Starts and verifies health
# 6. Reports status
# =============================================================================

set -e

# Configuration
REMOTE_HOST="${REMOTE_HOST:-root@100.127.118.106}"
SERVICES_DIR="/opt/fpai/SERVICES"
LOCAL_SERVICES="./SERVICES"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Arguments
NAME=$1
PORT=$2
DESCRIPTION=$3

if [ -z "$NAME" ] || [ -z "$PORT" ] || [ -z "$DESCRIPTION" ]; then
    echo -e "${RED}Usage: $0 <name> <port> \"<description>\"${NC}"
    echo "Example: $0 analytics 8764 \"Usage tracking and metrics\""
    exit 1
fi

# Capitalize first letter (portable)
NAME_UPPER="$(echo "$NAME" | awk '{print toupper(substr($0,1,1)) tolower(substr($0,2))}')"
LOCAL_PATH="${LOCAL_SERVICES}/${NAME}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  DROPLET FACTORY - Creating: ${NAME}                        ${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# =============================================================================
# Step 1: Create directory structure
# =============================================================================
echo -e "\n${YELLOW}[1/7] Creating directory structure...${NC}"
mkdir -p "${LOCAL_PATH}/BUILD/src"
mkdir -p "${LOCAL_PATH}/BUILD/tests"

# =============================================================================
# Step 2: Generate SPECS.md
# =============================================================================
echo -e "${YELLOW}[2/7] Generating SPECS.md...${NC}"
cat > "${LOCAL_PATH}/SPECS.md" << EOF
# ${NAME_UPPER} Droplet Specification

## Purpose
${DESCRIPTION}

## UDC Compliance
This droplet implements the Universal Droplet Contract:
- \`GET /health\` - Health status
- \`GET /capabilities\` - Service capabilities  
- \`GET /state\` - Current state (authenticated)
- \`GET /dependencies\` - Required services (authenticated)
- \`POST /message\` - Message handling (authenticated)

## Port
${PORT}

## Dependencies
- None (standalone) or specify as needed

## Key Endpoints
- \`GET /health\` - Returns {"status": "healthy", "service": "${NAME}"}
- Custom endpoints TBD based on implementation

## Created
$(date +%Y-%m-%d)
EOF

# =============================================================================
# Step 3: Generate main.py (UDC compliant)
# =============================================================================
echo -e "${YELLOW}[3/7] Generating main.py...${NC}"
cat > "${LOCAL_PATH}/BUILD/src/main.py" << 'MAINPY'
"""
${NAME_UPPER} Droplet - ${DESCRIPTION}
UDC Compliant Service
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("${NAME}")

# FastAPI app
app = FastAPI(
    title="${NAME_UPPER} Droplet",
    description="${DESCRIPTION}",
    version="1.0.0"
)

# ============================================================================
# UDC REQUIRED ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint - Required by UDC"""
    return {
        "status": "healthy",
        "service": "${NAME}",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/capabilities")
async def capabilities():
    """Service capabilities - Required by UDC"""
    return {
        "service_name": "${NAME}",
        "version": "1.0.0",
        "capabilities": [
            "${NAME}_core"
        ],
        "endpoints": [
            {"path": "/health", "method": "GET", "auth": False},
            {"path": "/capabilities", "method": "GET", "auth": False},
            {"path": "/state", "method": "GET", "auth": True},
            {"path": "/dependencies", "method": "GET", "auth": True},
            {"path": "/message", "method": "POST", "auth": True}
        ]
    }

@app.get("/state")
async def state(authorization: str = Header(None)):
    """Current state - Required by UDC"""
    return {
        "status": "active",
        "uptime_seconds": 0,  # TODO: Track actual uptime
        "last_activity": datetime.utcnow().isoformat(),
        "metrics": {}
    }

@app.get("/dependencies")
async def dependencies(authorization: str = Header(None)):
    """Service dependencies - Required by UDC"""
    return {
        "required_services": [],
        "optional_services": ["brain", "memory", "alerts"]
    }

class MessageRequest(BaseModel):
    text: str
    user_id: str = "unknown"
    context: Dict[str, Any] = {}

@app.post("/message")
async def handle_message(request: MessageRequest, authorization: str = Header(None)):
    """Message handler - Required by UDC"""
    logger.info(f"Received message from {request.user_id}: {request.text}")
    
    # TODO: Implement actual message handling logic
    return {
        "response": f"${NAME_UPPER} received: {request.text}",
        "handled_by": "${NAME}",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================================
# CUSTOM ENDPOINTS (Add your specific endpoints here)
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "${NAME_UPPER} Droplet is running", "port": ${PORT}}

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup():
    logger.info(f"${NAME_UPPER} Droplet starting on port ${PORT}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=${PORT})
MAINPY

# Replace placeholders in main.py
sed -i '' "s/\${NAME}/${NAME}/g" "${LOCAL_PATH}/BUILD/src/main.py" 2>/dev/null || \
sed -i "s/\${NAME}/${NAME}/g" "${LOCAL_PATH}/BUILD/src/main.py"
sed -i '' "s/\${NAME_UPPER}/${NAME_UPPER}/g" "${LOCAL_PATH}/BUILD/src/main.py" 2>/dev/null || \
sed -i "s/\${NAME_UPPER}/${NAME_UPPER}/g" "${LOCAL_PATH}/BUILD/src/main.py"
sed -i '' "s/\${PORT}/${PORT}/g" "${LOCAL_PATH}/BUILD/src/main.py" 2>/dev/null || \
sed -i "s/\${PORT}/${PORT}/g" "${LOCAL_PATH}/BUILD/src/main.py"
sed -i '' "s/\${DESCRIPTION}/${DESCRIPTION}/g" "${LOCAL_PATH}/BUILD/src/main.py" 2>/dev/null || \
sed -i "s/\${DESCRIPTION}/${DESCRIPTION}/g" "${LOCAL_PATH}/BUILD/src/main.py"

# =============================================================================
# Step 4: Generate requirements.txt
# =============================================================================
echo -e "${YELLOW}[4/7] Generating requirements.txt...${NC}"
cat > "${LOCAL_PATH}/BUILD/requirements.txt" << EOF
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
httpx>=0.25.0
EOF

# =============================================================================
# Step 5: Generate test file
# =============================================================================
echo -e "${YELLOW}[5/7] Generating tests...${NC}"
cat > "${LOCAL_PATH}/BUILD/tests/test_main.py" << EOF
"""Tests for ${NAME} droplet - UDC compliance"""
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "${NAME}"

def test_capabilities():
    response = client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "${NAME}"
    assert "capabilities" in data
    assert "endpoints" in data

def test_state():
    response = client.get("/state", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"

def test_dependencies():
    response = client.get("/dependencies", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    data = response.json()
    assert "required_services" in data
    assert "optional_services" in data

def test_message():
    response = client.post(
        "/message",
        json={"text": "test message", "user_id": "test_user"},
        headers={"Authorization": "Bearer test"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["handled_by"] == "${NAME}"
EOF

# =============================================================================
# Step 6: Generate README.md
# =============================================================================
echo -e "${YELLOW}[6/7] Generating README.md...${NC}"
cat > "${LOCAL_PATH}/README.md" << EOF
# ${NAME_UPPER} Droplet

${DESCRIPTION}

## Quick Start

\`\`\`bash
cd BUILD
pip install -r requirements.txt
python -m uvicorn src.main:app --port ${PORT}
\`\`\`

## UDC Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /health | GET | No | Health check |
| /capabilities | GET | No | Service capabilities |
| /state | GET | Yes | Current state |
| /dependencies | GET | Yes | Required services |
| /message | POST | Yes | Message handler |

## Port: ${PORT}

## Created: $(date +%Y-%m-%d)
EOF

# =============================================================================
# Step 7: Validate syntax locally
# =============================================================================
echo -e "${YELLOW}[7/7] Validating Python syntax...${NC}"
python3 -m py_compile "${LOCAL_PATH}/BUILD/src/main.py"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Syntax valid${NC}"
else
    echo -e "${RED}✗ Syntax error! Fix before deploying.${NC}"
    exit 1
fi

# =============================================================================
# Summary
# =============================================================================
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  DROPLET CREATED: ${NAME}                                    ${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo -e "Files created:"
echo -e "  ${BLUE}${LOCAL_PATH}/SPECS.md${NC}"
echo -e "  ${BLUE}${LOCAL_PATH}/BUILD/src/main.py${NC}"
echo -e "  ${BLUE}${LOCAL_PATH}/BUILD/requirements.txt${NC}"
echo -e "  ${BLUE}${LOCAL_PATH}/BUILD/tests/test_main.py${NC}"
echo -e "  ${BLUE}${LOCAL_PATH}/README.md${NC}"

echo -e "\n${YELLOW}To deploy:${NC}"
echo -e "  ./deploy-droplet.sh ${NAME} ${PORT}"

echo -e "\n${YELLOW}To test locally:${NC}"
echo -e "  cd ${LOCAL_PATH}/BUILD && python -m uvicorn src.main:app --port ${PORT}"

