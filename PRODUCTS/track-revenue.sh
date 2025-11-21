#!/bin/bash

# 💰 REVENUE TRACKING - Path to $400
# Updates treasury dashboard with each sale

REVENUE_FILE="/Users/jamessunheart/Development/PRODUCTS/revenue-tracking.json"
TREASURY_FILE="/opt/fpai/coordination/treasury/data/positions.json"

# Initialize revenue file if doesn't exist
if [ ! -f "$REVENUE_FILE" ]; then
    cat > "$REVENUE_FILE" <<'EOF'
{
  "launch_date": "2025-11-16T02:00:00Z",
  "target": 400,
  "total_revenue": 0,
  "sales": []
}
EOF
    echo "✅ Revenue tracking initialized"
fi

echo "💰 REVENUE TRACKER - Path to \$400"
echo "=================================="
echo ""

# Read current revenue
current=$(grep -o '"total_revenue": [0-9.]*' "$REVENUE_FILE" | cut -d' ' -f2)
target=400
remaining=$((target - current))

# Display current status
echo "Current Revenue: \$$current"
echo "Target: \$$target"
echo "Remaining: \$$remaining"
echo ""

# Calculate progress percentage
progress=$((current * 100 / target))
echo "Progress: $progress%"
echo ""

# Visual progress bar
bar_length=40
filled=$((progress * bar_length / 100))
bar=$(printf '%*s' "$filled" | tr ' ' '█')
empty=$(printf '%*s' "$((bar_length - filled))" | tr ' ' '░')
echo "[$bar$empty] $progress%"
echo ""

# Ask if there's a new sale to record
echo "Record a new sale? (y/n)"
read -p "> " record

if [[ $record =~ ^[Yy]$ ]]; then
    echo ""
    echo "Product sold:"
    echo "1. Crypto Portfolio Tracker (\$49)"
    echo "2. Multi-Session AI Coordinator (\$79)"
    echo "3. AI Automation Playbook (\$39)"
    echo "4. Treasury Management System (\$129)"
    echo "5. Dashboard Collection (\$99)"
    echo "6. Automation Scripts (\$29)"
    echo "7. FULL BUNDLE (\$199)"
    echo "8. Custom amount"
    echo ""
    read -p "Choose (1-8): " product

    case $product in
        1) amount=49; name="Crypto Portfolio Tracker" ;;
        2) amount=79; name="Multi-Session AI Coordinator" ;;
        3) amount=39; name="AI Automation Playbook" ;;
        4) amount=129; name="Treasury Management System" ;;
        5) amount=99; name="Dashboard Collection" ;;
        6) amount=29; name="Automation Scripts" ;;
        7) amount=199; name="FULL BUNDLE" ;;
        8)
            read -p "Enter amount: \$" amount
            read -p "Enter product name: " name
            ;;
        *)
            echo "❌ Invalid choice"
            exit 1
            ;;
    esac

    echo ""
    read -p "Customer email (or 'anonymous'): " customer
    read -p "Platform (Gumroad/Direct/Other): " platform

    # Update revenue file
    new_total=$((current + amount))
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Add sale to JSON (simple append)
    python3 <<PYTHON
import json
from datetime import datetime

with open('$REVENUE_FILE', 'r') as f:
    data = json.load(f)

data['total_revenue'] = $new_total
data['sales'].append({
    'timestamp': '$timestamp',
    'product': '$name',
    'amount': $amount,
    'customer': '$customer',
    'platform': '$platform'
})

with open('$REVENUE_FILE', 'w') as f:
    json.dump(data, f, indent=2)

print('✅ Sale recorded!')
PYTHON

    # Update treasury dashboard data
    if [ -f "$TREASURY_FILE" ]; then
        python3 <<PYTHON
import json

# Read treasury data
with open('$TREASURY_FILE', 'r') as f:
    treasury = json.load(f)

# Add revenue event
if 'revenue_events' not in treasury:
    treasury['revenue_events'] = []

treasury['revenue_events'].append({
    'date': '$(date +%Y-%m-%d)',
    'source': 'Product Sales - $name',
    'amount': $amount,
    'type': 'product_sale',
    'customer': '$customer',
    'platform': '$platform'
})

# Update summary
if 'summary' not in treasury:
    treasury['summary'] = {'total': {}}

if 'product_revenue' not in treasury['summary']:
    treasury['summary']['product_revenue'] = 0

treasury['summary']['product_revenue'] = $new_total

# Save
with open('$TREASURY_FILE', 'w') as f:
    json.dump(treasury, f, indent=2)

print('✅ Treasury dashboard updated!')
PYTHON
    fi

    echo ""
    echo "🎉 NEW SALE RECORDED!"
    echo ""
    echo "Product: $name"
    echo "Amount: \$$amount"
    echo "New Total: \$$new_total"
    echo ""

    # Check if target reached
    if [ $new_total -ge $target ]; then
        echo "🎯🎯🎯 TARGET REACHED! 🎯🎯🎯"
        echo ""
        echo "Congratulations! You hit \$$target in revenue!"
        echo "🚀 MISSION COMPLETE!"
        echo ""
        echo "Next steps:"
        echo "1. Tweet the victory!"
        echo "2. Share case study"
        echo "3. Deploy AI Marketing Engine (\$200 budget unlocked)"
        echo "4. Continue to \$1,000+"
        echo ""
    else
        remaining=$((target - new_total))
        echo "💪 Keep going! \$$remaining to target"
        echo ""

        # Calculate what's needed
        if [ $remaining -le 199 ]; then
            echo "Just 1 bundle sale away! (\$$remaining remaining)"
        elif [ $remaining -le 398 ]; then
            echo "Just 2 bundle sales away! (\$$remaining remaining)"
        fi
    fi
fi

echo ""
echo "📊 View full stats:"
echo "   cat $REVENUE_FILE"
echo ""
echo "🌐 Treasury dashboard:"
echo "   https://fullpotential.com/dashboard/money"
echo ""
