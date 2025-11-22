#!/bin/bash
# Start Unified Financial Dashboard
# Consolidates: Treasury (8005) + 2X Treasury (8052) + Arena (8035)

cd "$(dirname "$0")"

echo "🚀 Starting Unified Financial Dashboard..."
echo ""
echo "  Port: 8100"
echo "  Consolidates:"
echo "    - Treasury Dashboard (8005)"
echo "    - 2X Treasury (8052)"
echo "    - Treasury Arena (8035)"
echo ""

# Check if treasury_data.json exists
if [ ! -f "/Users/jamessunheart/Development/treasury_data.json" ]; then
    echo "⚠️  Warning: treasury_data.json not found"
    echo "   Dashboard will use default values"
    echo ""
fi

# Start the service
python3 app/main.py
