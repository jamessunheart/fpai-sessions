#!/bin/bash

# DROPLET INITIALIZER
# Blueprint: 1-SYSTEM-BLUEPRINT.txt - Section 3 (System Architecture)
# Purpose: Scaffold new droplet repositories with UDC compliance
# Usage: ./droplet-init.sh <droplet-id> <droplet-name>

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Check arguments
if [ $# -lt 2 ]; then
    print_error "Usage: $0 <droplet-id> <droplet-name>"
    echo "Example: $0 1 registry"
    exit 1
fi

DROPLET_ID=$1
DROPLET_NAME=$2
REPO_NAME="droplet-${DROPLET_ID}-${DROPLET_NAME}"
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DROPLET_DIR="${BASE_DIR}/${REPO_NAME}"

print_info "Initializing Droplet #${DROPLET_ID}: ${DROPLET_NAME}"
print_info "Repository: ${REPO_NAME}"

# Check if directory already exists
if [ -d "$DROPLET_DIR" ]; then
    print_error "Directory ${REPO_NAME} already exists!"
    exit 1
fi

# Create directory structure
print_info "Creating directory structure..."
mkdir -p "${DROPLET_DIR}"/{app/{api,models,services,core},tests,docs,.github/workflows}

# Create main app files
print_info "Creating application files..."

# main.py - FastAPI application with UDC endpoints
cat > "${DROPLET_DIR}/app/main.py" << 'EOF'
"""
Droplet #${DROPLET_ID} - ${DROPLET_NAME}
Full Potential AI System
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Dict
import os

app = FastAPI(
    title="Droplet #${DROPLET_ID} - ${DROPLET_NAME}",
    description="Full Potential AI - ${DROPLET_NAME} Service",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# UDC REQUIRED ENDPOINTS

@app.get("/health")
async def health():
    """Health check endpoint (UDC required)"""
    return {
        "status": "active",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "${DROPLET_NAME}",
        "droplet_id": ${DROPLET_ID}
    }

@app.get("/capabilities")
async def capabilities():
    """List droplet capabilities (UDC required)"""
    return {
        "capabilities": [
            "health_check",
            "state_reporting",
            "message_handling"
        ],
        "droplet_id": ${DROPLET_ID},
        "service": "${DROPLET_NAME}"
    }

@app.get("/state")
async def state():
    """Current droplet state (UDC required)"""
    return {
        "state": "operational",
        "droplet_id": ${DROPLET_ID},
        "service": "${DROPLET_NAME}",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/dependencies")
async def dependencies():
    """List dependencies (UDC required)"""
    return {
        "dependencies": [
            {"service": "registry", "required": True},
            {"service": "orchestrator", "required": True}
        ],
        "droplet_id": ${DROPLET_ID}
    }

@app.post("/message")
async def message(payload: Dict):
    """Receive messages from Orchestrator (UDC required)"""
    return {
        "status": "received",
        "message_id": payload.get("message_id"),
        "timestamp": datetime.utcnow().isoformat()
    }

# DROPLET-SPECIFIC ENDPOINTS
# Add your custom endpoints here

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "${DROPLET_NAME}",
        "droplet_id": ${DROPLET_ID},
        "status": "active",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000 + ${DROPLET_ID}))
    uvicorn.run(app, host="0.0.0.0", port=port)
EOF

# Replace template variables
sed -i '' "s/\${DROPLET_ID}/${DROPLET_ID}/g" "${DROPLET_DIR}/app/main.py"
sed -i '' "s/\${DROPLET_NAME}/${DROPLET_NAME}/g" "${DROPLET_DIR}/app/main.py"

# __init__.py files
touch "${DROPLET_DIR}/app/__init__.py"
touch "${DROPLET_DIR}/app/api/__init__.py"
touch "${DROPLET_DIR}/app/models/__init__.py"
touch "${DROPLET_DIR}/app/services/__init__.py"
touch "${DROPLET_DIR}/app/core/__init__.py"
touch "${DROPLET_DIR}/tests/__init__.py"

# requirements.txt
cat > "${DROPLET_DIR}/requirements.txt" << 'EOF'
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
pydantic>=2.4.0
python-multipart>=0.0.6
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-dotenv>=1.0.0
requests>=2.31.0
httpx>=0.25.0

# Database (if needed)
# sqlalchemy>=2.0.0
# psycopg2-binary>=2.9.0
# alembic>=1.12.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0

# Code quality
black>=23.10.0
ruff>=0.1.0
mypy>=1.6.0
EOF

# Dockerfile
cat > "${DROPLET_DIR}/Dockerfile" << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# docker-compose.yml
cat > "${DROPLET_DIR}/docker-compose.yml" << EOF
version: '3.8'

services:
  ${DROPLET_NAME}:
    build: .
    ports:
      - "800${DROPLET_ID}:8000"
    environment:
      - DROPLET_ID=${DROPLET_ID}
      - DROPLET_NAME=${DROPLET_NAME}
      - REGISTRY_URL=http://registry:8001
    volumes:
      - ./app:/app/app
    restart: unless-stopped
EOF

# .env.example
cat > "${DROPLET_DIR}/.env.example" << EOF
DROPLET_ID=${DROPLET_ID}
DROPLET_NAME=${DROPLET_NAME}
PORT=800${DROPLET_ID}
REGISTRY_URL=http://localhost:8001
ORCHESTRATOR_URL=http://localhost:8010
DATABASE_URL=postgresql://user:password@localhost/droplet_${DROPLET_NAME}
JWT_SECRET_KEY=your-secret-key-here
EOF

# .gitignore
cat > "${DROPLET_DIR}/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt

# Testing
.pytest_cache/
.coverage
htmlcov/
*.cover

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local

# Database
*.db
*.sqlite

# Logs
*.log

# OS
.DS_Store
Thumbs.db
EOF

# README.md
cat > "${DROPLET_DIR}/README.md" << EOF
# Droplet #${DROPLET_ID} - ${DROPLET_NAME}

**Full Potential AI System**

## Overview

This droplet is part of the Full Potential AI system following the Sacred Loop architecture.

**Droplet ID:** #${DROPLET_ID}
**Service Name:** ${DROPLET_NAME}
**Status:** In Development

## Features

- ✅ UDC Compliant (Universal Droplet Contract)
- ✅ FastAPI backend
- ✅ Docker containerized
- ✅ Health monitoring
- ✅ Registry integration ready

## Quick Start

### Local Development

\`\`\`bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python -m app.main

# Or with uvicorn
uvicorn app.main:app --reload --port 800${DROPLET_ID}
\`\`\`

### Docker

\`\`\`bash
# Build image
docker build -t droplet-${DROPLET_ID}-${DROPLET_NAME} .

# Run container
docker run -p 800${DROPLET_ID}:8000 droplet-${DROPLET_ID}-${DROPLET_NAME}

# Or use docker-compose
docker-compose up
\`\`\`

## API Endpoints

### UDC Required Endpoints

- \`GET /health\` - Health check
- \`GET /capabilities\` - List capabilities
- \`GET /state\` - Current state
- \`GET /dependencies\` - List dependencies
- \`POST /message\` - Receive messages

### Custom Endpoints

- \`GET /\` - Root endpoint

## Testing

\`\`\`bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
\`\`\`

## Code Standards

\`\`\`bash
# Format code
black app/ tests/

# Lint
ruff app/ tests/

# Type check
mypy app/
\`\`\`

## Deployment

See \`../fpai-ops/deploy-droplet.sh\` for deployment automation.

## Integration

This droplet integrates with:
- **Registry** (#1) - Identity and JWT tokens
- **Orchestrator** (#10) - Task routing and messaging

## Development

Built following:
- Foundation Files standards
- UDC compliance requirements
- Security requirements
- Code standards

## License

Full Potential AI

---

🌐⚡💎
EOF

# Test file
cat > "${DROPLET_DIR}/tests/test_main.py" << 'EOF'
"""
Tests for Droplet main endpoints
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test /health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "timestamp" in data


def test_capabilities_endpoint():
    """Test /capabilities endpoint"""
    response = client.get("/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "capabilities" in data
    assert isinstance(data["capabilities"], list)


def test_state_endpoint():
    """Test /state endpoint"""
    response = client.get("/state")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data


def test_dependencies_endpoint():
    """Test /dependencies endpoint"""
    response = client.get("/dependencies")
    assert response.status_code == 200
    data = response.json()
    assert "dependencies" in data
    assert isinstance(data["dependencies"], list)


def test_message_endpoint():
    """Test /message endpoint"""
    payload = {"message_id": "test-123", "content": "test message"}
    response = client.post("/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "status" in data
EOF

# pytest.ini
cat > "${DROPLET_DIR}/pytest.ini" << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts =
    --verbose
    --cov=app
    --cov-report=html
    --cov-report=term
EOF

# GitHub Actions workflow
cat > "${DROPLET_DIR}/.github/workflows/test.yml" << 'EOF'
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run tests
      run: |
        pytest --cov=app tests/

    - name: Check code formatting
      run: |
        black --check app/ tests/

    - name: Lint
      run: |
        ruff app/ tests/
EOF

print_success "Directory structure created"
print_success "Application files created"
print_success "Configuration files created"
print_success "Tests created"

# Initialize git repository
print_info "Initializing Git repository..."
cd "${DROPLET_DIR}"
git init
git add .
git commit -m "Initial commit - Droplet #${DROPLET_ID} (${DROPLET_NAME})

🌐 Generated with Full Potential AI - Droplet Initializer

- UDC compliant endpoints
- FastAPI backend
- Docker configuration
- Tests included

Co-Authored-By: Claude <noreply@anthropic.com>"

print_success "Git repository initialized"

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "Droplet #${DROPLET_ID} (${DROPLET_NAME}) initialized!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📁 Location: ${DROPLET_DIR}"
echo "🌐 Port: 800${DROPLET_ID}"
echo ""
echo "Next steps:"
echo "  1. cd ${REPO_NAME}"
echo "  2. cp .env.example .env"
echo "  3. pip install -r requirements.txt"
echo "  4. python -m app.main"
echo ""
echo "Or run with Docker:"
echo "  docker-compose up"
echo ""
echo "🌐⚡💎"
