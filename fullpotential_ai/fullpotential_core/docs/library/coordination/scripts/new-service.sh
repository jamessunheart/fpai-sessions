#!/bin/bash
# Scaffold a new service with GitHub + server setup
# Usage: ./new-service.sh [service-name] "Description" [port]

set -e

SERVICE_NAME=$1
DESCRIPTION=$2
PORT=$3

SERVICES_DIR="/Users/jamessunheart/Development/SERVICES"
REGISTRY="$SERVICES_DIR/SERVICE_REGISTRY.json"
TEMPLATE="$SERVICES_DIR/_TEMPLATE"
ORG="fullpotentialai"
SERVER="root@198.54.123.234"

if [ -z "$SERVICE_NAME" ] || [ -z "$DESCRIPTION" ] || [ -z "$PORT" ]; then
    echo "Usage: ./new-service.sh [service-name] \"Description\" [port]"
    echo ""
    echo "Example:"
    echo "  ./new-service.sh my-service \"My awesome service\" 8500"
    exit 1
fi

echo "🚀 Creating New Service: $SERVICE_NAME"
echo "======================================="
echo ""
echo "Name:        $SERVICE_NAME"
echo "Description: $DESCRIPTION"
echo "Port:        $PORT"
echo ""

SERVICE_PATH="$SERVICES_DIR/$SERVICE_NAME"

# Step 1: Check if service already exists
if [ -d "$SERVICE_PATH" ]; then
    echo "❌ Service already exists: $SERVICE_PATH"
    exit 1
fi

# Step 2: Copy template
echo "Step 1/7: Copying template..."
cp -r "$TEMPLATE" "$SERVICE_PATH"
echo "   ✅ Template copied"

# Step 3: Initialize git
echo ""
echo "Step 2/7: Initializing git..."
cd "$SERVICE_PATH"
git init
git add .
git commit -m "Initial commit from template"
echo "   ✅ Git initialized"

# Step 4: Create GitHub repo
echo ""
echo "Step 3/7: Creating GitHub repo..."
if gh repo create "$ORG/$SERVICE_NAME" \
    --private \
    --description "$DESCRIPTION" \
    --source . \
    --remote "origin" \
    --push; then
    REPO_URL="https://github.com/$ORG/$SERVICE_NAME"
    echo "   ✅ GitHub repo created: $REPO_URL"
else
    echo "   ❌ Failed to create GitHub repo"
    REPO_URL=""
fi

# Step 5: Create directory on server
echo ""
echo "Step 4/7: Creating server directory..."
ssh $SERVER "mkdir -p /opt/fpai/$SERVICE_NAME"
echo "   ✅ Server directory created"

# Step 6: Update SERVICE_REGISTRY.json
echo ""
echo "Step 5/7: Updating SERVICE_REGISTRY.json..."

python3 << EOF
import json
from datetime import datetime

with open('$REGISTRY', 'r') as f:
    registry = json.load(f)

new_service = {
    "name": "$SERVICE_NAME",
    "description": "$DESCRIPTION",
    "status": "development",
    "responsible_session": None,
    "port": $PORT,
    "url_local": "http://localhost:$PORT",
    "url_production": "https://fullpotential.com/$SERVICE_NAME",
    "path_local": "$SERVICE_PATH",
    "path_production": "/opt/fpai/$SERVICE_NAME",
    "repo": "$REPO_URL",
    "tech_stack": ["Python", "FastAPI"],
    "dependencies": ["fastapi", "uvicorn"],
    "created_at": datetime.utcnow().isoformat() + "Z",
    "last_deployed": None,
    "revenue_potential": "TBD",
    "priority": "medium"
}

registry['services'].append(new_service)
registry['total_services'] = len(registry['services'])
registry['last_updated'] = datetime.utcnow().isoformat() + "Z"

with open('$REGISTRY', 'w') as f:
    json.dump(registry, f, indent=4)

print("   ✅ Registry updated")
EOF

# Step 7: Create basic FastAPI app
echo ""
echo "Step 6/7: Creating basic FastAPI app..."
mkdir -p "$SERVICE_PATH/src"
cat > "$SERVICE_PATH/src/main.py" << 'PYTHON_EOF'
"""
Main FastAPI application
"""
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="SERVICE_NAME_PLACEHOLDER",
    description="SERVICE_DESC_PLACEHOLDER",
    version="1.0.0"
)

@app.get("/health")
async def health():
    """UDC Endpoint 1: Health check"""
    return {
        "status": "active",
        "service": "SERVICE_NAME_PLACEHOLDER",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/capabilities")
async def capabilities():
    """UDC Endpoint 2: Service capabilities"""
    return {
        "version": "1.0.0",
        "features": [],
        "dependencies": [],
        "udc_version": "1.0",
        "metadata": {}
    }

@app.get("/state")
async def state():
    """UDC Endpoint 3: Resource usage"""
    return {
        "uptime_seconds": 0,
        "requests_total": 0,
        "requests_per_minute": 0.0,
        "errors_last_hour": 0,
        "last_restart": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/dependencies")
async def dependencies():
    """UDC Endpoint 4: Service dependencies"""
    return {
        "required": [],
        "optional": [],
        "missing": []
    }

@app.post("/message")
async def message(payload: dict):
    """UDC Endpoint 5: Inter-service messaging"""
    return {
        "status": "received",
        "message_id": "msg-001"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SERVICE_NAME_PLACEHOLDER",
        "description": "SERVICE_DESC_PLACEHOLDER",
        "status": "operational",
        "endpoints": ["/health", "/capabilities", "/state", "/dependencies", "/message"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT_PLACEHOLDER)
PYTHON_EOF

# Replace placeholders
sed -i '' "s/SERVICE_NAME_PLACEHOLDER/$SERVICE_NAME/g" "$SERVICE_PATH/src/main.py"
sed -i '' "s/SERVICE_DESC_PLACEHOLDER/$DESCRIPTION/g" "$SERVICE_PATH/src/main.py"
sed -i '' "s/PORT_PLACEHOLDER/$PORT/g" "$SERVICE_PATH/src/main.py"

# Create requirements.txt
cat > "$SERVICE_PATH/requirements.txt" << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
EOF

# Create start.sh
cat > "$SERVICE_PATH/start.sh" << 'BASH_EOF'
#!/bin/bash
# Start the service
cd "$(dirname "$0")"
source venv/bin/activate 2>/dev/null || python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port PORT_PLACEHOLDER --reload
BASH_EOF

sed -i '' "s/PORT_PLACEHOLDER/$PORT/g" "$SERVICE_PATH/start.sh"
chmod +x "$SERVICE_PATH/start.sh"

echo "   ✅ FastAPI app created with UDC endpoints"

# Step 8: Commit and push
echo ""
echo "Step 7/7: Committing and pushing..."
cd "$SERVICE_PATH"
git add .
git commit -m "Add FastAPI app with UDC compliance"
git push origin main || git push origin master || echo "   ⚠️  Push skipped"
echo "   ✅ Pushed to GitHub"

echo ""
echo "======================================="
echo "✅ Service created: $SERVICE_NAME"
echo ""
echo "📂 Location: $SERVICE_PATH"
echo "🐙 GitHub:   $REPO_URL"
echo "🖥️  Server:   /opt/fpai/$SERVICE_NAME"
echo "🌐 Port:     $PORT"
echo ""
echo "Next steps:"
echo "  1. cd $SERVICE_PATH"
echo "  2. ./start.sh  # Test locally"
echo "  3. ./sync-service.sh $SERVICE_NAME  # Deploy to server"
echo ""
echo "Test endpoints:"
echo "  curl http://localhost:$PORT/health"
echo "  curl http://198.54.123.234:$PORT/health  # After deploy"
