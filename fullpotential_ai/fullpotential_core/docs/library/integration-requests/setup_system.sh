#!/bin/bash
# Setup the Integration Request System

cd /Users/jamessunheart/Development/INTEGRATION_REQUESTS

echo "🔧 Setting up External Integration Request System..."

# Create directory structure
mkdir -p IN_PROGRESS
mkdir -p COMPLETED
mkdir -p TEMPLATES

echo "✅ Directory structure created"

# Create status checker script
cat > check_status.sh << 'EOF'
#!/bin/bash
# Check status of all integration requests

echo "📋 INTEGRATION REQUEST STATUS"
echo "=============================="
echo ""

echo "🟡 OPEN REQUESTS:"
ls -1 OPEN_REQUESTS/ 2>/dev/null | sed 's/\.md$//' | while read req; do
    echo "  • $req"
done
echo ""

echo "🔵 IN PROGRESS:"
ls -1 IN_PROGRESS/ 2>/dev/null | sed 's/\.md$//' | while read req; do
    helper=$(grep "In Progress (Helper:" "IN_PROGRESS/$req.md" 2>/dev/null | sed 's/.*Helper: \(.*\))/\1/' | tr -d '_')
    echo "  • $req ${helper:+(by $helper)}"
done
echo ""

echo "✅ COMPLETED (Ready to Integrate):"
ls -1d COMPLETED/*/ 2>/dev/null | xargs -n1 basename | while read req; do
    echo "  • $req"
done
echo ""

total_open=$(ls -1 OPEN_REQUESTS/ 2>/dev/null | wc -l | tr -d ' ')
total_progress=$(ls -1 IN_PROGRESS/ 2>/dev/null | wc -l | tr -d ' ')
total_complete=$(ls -1d COMPLETED/*/ 2>/dev/null | wc -l | tr -d ' ')

echo "Summary: $total_open open | $total_progress in progress | $total_complete completed"
EOF

chmod +x check_status.sh

echo "✅ Status checker created (./check_status.sh)"

# Create helper for posting new requests
cat > new_request.sh << 'EOF'
#!/bin/bash
# Create a new integration request

if [ -z "$1" ]; then
    echo "Usage: ./new_request.sh <request-name>"
    echo "Example: ./new_request.sh github_api"
    exit 1
fi

REQUEST_NAME=$1
cp TEMPLATES/api_request_template.md "OPEN_REQUESTS/${REQUEST_NAME}.md"
echo "✅ Created new request: OPEN_REQUESTS/${REQUEST_NAME}.md"
echo "Edit the file to fill in details, then helpers can pick it up!"
EOF

chmod +x new_request.sh

echo "✅ Request creator created (./new_request.sh <name>)"
echo ""
echo "🎉 System ready!"
echo ""
echo "Next steps:"
echo "  1. Run ./check_status.sh to see current requests"
echo "  2. Share OPEN_REQUESTS/ with helpers (humans or AI agents)"
echo "  3. Helpers deliver to COMPLETED/"
echo "  4. You integrate without leaving the command center"
echo ""
echo "Current request: Unsplash API (see OPEN_REQUESTS/unsplash_api.md)"
