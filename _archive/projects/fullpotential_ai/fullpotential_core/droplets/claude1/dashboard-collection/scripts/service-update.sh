#!/bin/bash

# Service Update Script
# Usage: ./service-update.sh "name" "status"

if [ $# -lt 2 ]; then
    echo "Usage: $0 NAME STATUS"
    echo ""
    echo "Example:"
    echo "  $0 email-automation production"
    echo ""
    echo "Status options: development, testing, production, planned, deprecated"
    exit 1
fi

NAME=$1
STATUS=$2
REGISTRY_FILE="/Users/jamessunheart/Development/agents/services/SERVICE_REGISTRY.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

python3 << EOPYTHON
import json
import sys

registry_file = "$REGISTRY_FILE"

with open(registry_file, 'r') as f:
    registry = json.load(f)

# Find service
service = next((s for s in registry.get('services', []) if s['name'] == "$NAME"), None)
if not service:
    print(f"❌ Service '$NAME' not found!")
    sys.exit(1)

# Update status
old_status = service['status']
service['status'] = "$STATUS"

if "$STATUS" == "production":
    service['last_deployed'] = "$TIMESTAMP"

registry['last_updated'] = "$TIMESTAMP"

with open(registry_file, 'w') as f:
    json.dump(registry, f, indent=2)

print(f"✅ Service '$NAME' updated!")
print(f"   Status: {old_status} → $STATUS")
EOPYTHON

if [ $? -eq 0 ]; then
    echo ""
    echo "Next steps:"
    echo "  1. Update registry: python3 ../../agents/services/integrated-registry-system.py"
    echo "  2. Commit: cd ../../SERVICES && git add SERVICE_REGISTRY.json && git commit -m 'Update $NAME to $STATUS'"
fi
