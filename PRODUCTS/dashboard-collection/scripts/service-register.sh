#!/bin/bash

# Service Registration Script
# Usage: ./service-register.sh "name" "description" PORT "status"

if [ $# -lt 4 ]; then
    echo "Usage: $0 NAME \"DESCRIPTION\" PORT STATUS"
    echo ""
    echo "Example:"
    echo "  $0 email-automation \"Automated email campaigns\" 8500 development"
    echo ""
    echo "Status options: development, testing, production, planned, deprecated"
    exit 1
fi

NAME=$1
DESCRIPTION=$2
PORT=$3
STATUS=$4
SESSION_ID=${5:-"auto"}

REGISTRY_FILE="/Users/jamessunheart/Development/SERVICES/SERVICE_REGISTRY.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Add service using Python
python3 << EOPYTHON
import json
import sys

registry_file = "$REGISTRY_FILE"

try:
    with open(registry_file, 'r') as f:
        registry = json.load(f)
except FileNotFoundError:
    registry = {
        "registry_version": "1.0",
        "last_updated": "$TIMESTAMP",
        "total_services": 0,
        "services": [],
        "planned_services": []
    }

# Check if service already exists
existing = next((s for s in registry.get('services', []) if s['name'] == "$NAME"), None)
if existing:
    print(f"❌ Service '$NAME' already exists!")
    sys.exit(1)

# Create new service
new_service = {
    "name": "$NAME",
    "description": "$DESCRIPTION",
    "status": "$STATUS",
    "responsible_session": "$SESSION_ID",
    "port": int($PORT),
    "url_local": f"http://localhost:$PORT",
    "url_production": f"https://fullpotential.com/{NAME.replace('_', '-')}",
    "path_local": f"/Users/jamessunheart/Development/SERVICES/$NAME",
    "path_production": f"/root/SERVICES/$NAME",
    "tech_stack": [],
    "dependencies": [],
    "created_at": "$TIMESTAMP",
    "last_deployed": None,
    "revenue_potential": "TBD",
    "priority": "medium"
}

registry['services'].append(new_service)
registry['total_services'] = len(registry['services'])
registry['last_updated'] = "$TIMESTAMP"

with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)

print(f"✅ Service '$NAME' registered successfully!")
print(f"   Port: $PORT")
print(f"   Status: $STATUS")
print(f"   Total services: {registry['total_services']}")
EOPYTHON

if [ $? -eq 0 ]; then
    echo ""
    echo "Next steps:"
    echo "  1. Service will appear in SSOT.json within 5 seconds"
    echo "  2. Update registry: python3 ../../SERVICES/integrated-registry-system.py"
    echo "  3. Commit to git: cd ../../SERVICES && git add SERVICE_REGISTRY.json && git commit -m 'Add $NAME'"
fi
