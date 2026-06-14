#!/bin/bash
# Start Financial Hub Rung 4

cd "$(dirname "$0")"

echo "Starting Financial Hub Rung 4..."
echo ""
echo "  Port: 8100"
echo "  Mode: read-only"
echo "  Cache: ../../var/financial-hub"
echo ""

# Start the service
python3 app/main.py
