#!/bin/bash
# Auto-restart offline services with known ports

set -e

SERVICES_DIR="/Users/jamessunheart/Development/SERVICES"
CATALOG="$SERVICES_DIR/SERVICE_CATALOG.json"

echo "🔄 Auto-Restart System for Offline Services"
echo "==========================================="
echo

# Extract offline services with ports
offline_services=$(python3 << 'EOF'
import json
with open('/Users/jamessunheart/Development/SERVICES/SERVICE_CATALOG.json') as f:
    catalog = json.load(f)

offline = [s for s in catalog['services'] if s['status'] == 'offline' and s['port']]
for s in offline:
    print(f"{s['name']}|{s['port']}")
EOF
)

echo "Found offline services:"
echo "$offline_services" | while IFS='|' read name port; do
    echo "  • $name (port $port)"
done
echo

# Ask user if they want to restart all or select
echo "Options:"
echo "  1) Restart critical services only (orchestrator, dashboard, jobs)"
echo "  2) Restart all offline services"
echo "  3) Exit (no restart)"
echo
read -p "Choose option (1-3): " choice

case $choice in
    1)
        services_to_restart="orchestrator dashboard jobs i-proactive"
        ;;
    2)
        services_to_restart=$(echo "$offline_services" | cut -d'|' -f1 | tr '\n' ' ')
        ;;
    3)
        echo "Exiting without restart"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo
echo "🚀 Restarting services..."
echo

for service in $services_to_restart; do
    service_dir="$SERVICES_DIR/$service"

    if [ ! -d "$service_dir" ]; then
        echo "⚠️  Service directory not found: $service"
        continue
    fi

    echo "Starting $service..."

    # Check for main.py
    if [ -f "$service_dir/main.py" ]; then
        cd "$service_dir"

        # Try to start with venv if it exists
        if [ -d "venv" ]; then
            nohup ./venv/bin/python3 main.py > logs.txt 2>&1 &
        else
            nohup python3 main.py > logs.txt 2>&1 &
        fi

        sleep 1
        echo "  ✅ Started (PID: $!)"
    else
        echo "  ⚠️  No main.py found"
    fi
done

echo
echo "✅ Restart complete"
echo
echo "Verify services are online:"
echo "  cd $SERVICES_DIR/service-discovery"
echo "  python3 scan_services.py"
