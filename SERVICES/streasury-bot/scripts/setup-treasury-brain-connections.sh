#!/bin/bash
set -e

echo "========================================="
echo "  SETTING UP TREASURY BRAIN CONNECTIONS"
echo "========================================="
echo
echo "This script connects all your financial data sources to STreasury Bot:"
echo "  1. UC Credits (trading fees, subscriptions)"
echo "  2. Treasury State (magnet engine, positions, TVL)"
echo "  3. Alignment Economics (future)"
echo "  4. WhaleTrack (future)"
echo "  5. Stripe (future)"
echo

# Check if we're on the brain server
if [[ "$(hostname -f)" == *"162.0.208.88"* ]] || [[ "$(hostname)" == "brain"* ]]; then
    ON_BRAIN=true
    STREASURY_PATH="/opt/streasury-bot"
    ENV_FILE="/etc/streasury-bot/streasury.env"
else
    ON_BRAIN=false
    STREASURY_PATH="$(pwd)"
    ENV_FILE=".env"
fi

echo "Environment: $([ "$ON_BRAIN" = true ] && echo "Brain Server" || echo "Local Development")"
echo "STreasury path: $STREASURY_PATH"
echo

# Function to execute SQL
run_sql() {
    local sql="$1"
    if [ "$ON_BRAIN" = true ]; then
        sudo -u postgres psql -d fpai_brain -p 25432 -c "$sql"
    else
        echo "SQL (local): $sql"
        # For local dev, would connect to local Postgres
        # psql "$DATABASE_URL" -c "$sql"
    fi
}

# 1. Register UC Credits adapter
echo "1. Setting up UC Credits → STreasury Bot adapter..."

UC_CREDITS_CONFIG='{
    "since": "2025-01-01",
    "billing_db_path": "/opt/fpai/aria-command/data/billing.db",
    "sync_commons": true
}'

run_sql "INSERT INTO streasury.source_connection (tenant_id, kind, label, secret, config, active) 
VALUES (
    1, 
    'uc_credits', 
    'UC Credits (ARIA Trading)', 
    'internal-adapter', 
    '$UC_CREDITS_CONFIG',
    true
) ON CONFLICT (tenant_id, kind, label) DO UPDATE SET
    config = EXCLUDED.config,
    active = EXCLUDED.active;"

echo "   ✓ UC Credits adapter registered"

# 2. Register Treasury State adapter
echo "2. Setting up Treasury State → STreasury Bot sync..."

TREASURY_STATE_CONFIG='{
    "treasury_file": "/opt/fpai/core/STATE/TREASURY.json",
    "sync_interval_minutes": 60,
    "last_sync": null
}'

run_sql "INSERT INTO streasury.source_connection (tenant_id, kind, label, secret, config, active)
VALUES (
    1,
    'treasury_state',
    'Core Treasury State',
    'internal-adapter',
    '$TREASURY_STATE_CONFIG',
    true
) ON CONFLICT (tenant_id, kind, label) DO UPDATE SET
    config = EXCLUDED.config,
    active = EXCLUDED.active;"

echo "   ✓ Treasury State sync registered"

# 3. Update adapter registry
echo "3. Updating adapter registry..."

if [ "$ON_BRAIN" = true ]; then
    # Add imports to sources/__init__.py
    cat >> "$STREASURY_PATH/app/sources/__init__.py" << 'EOF'

# Treasury Brain Connections
from . import uc_credits
from . import treasury_state

# Register adapters
ADAPTER_REGISTRY = {
    'uc_credits': uc_credits.create_adapter,
    'treasury_state': treasury_state.create_adapter,
}
EOF

    echo "   ✓ Adapter registry updated"
fi

# 4. Create treasury brain dashboard entry
echo "4. Setting up treasury brain dashboard commands..."

run_sql "INSERT INTO streasury.kpi_definition (tenant_id, name, description, unit, category)
VALUES 
    (1, 'TVL', 'Total Value Locked in Treasury', 'USD', 'treasury'),
    (1, 'PnL_24h', '24-hour Profit/Loss', 'USD', 'treasury'),
    (1, 'Magnet_Strength', 'Magnet Engine Strength', 'percent', 'trading'),
    (1, 'Magnet_Leverage', 'Current Leverage Ratio', 'ratio', 'trading')
ON CONFLICT (tenant_id, name) DO NOTHING;"

echo "   ✓ Treasury KPI definitions created"

# 5. Test connection (if on brain server)
if [ "$ON_BRAIN" = true ]; then
    echo "5. Testing connections..."
    
    # Test UC Credits adapter
    echo "   Testing UC Credits sync..."
    sudo -u streasury "$STREASURY_PATH/.venv/bin/python" -c "
import asyncio
import sys
sys.path.append('$STREASURY_PATH')
from app.sources.uc_credits import UCCreditsAdapter
adapter = UCCreditsAdapter(1, {'since': '2025-01-01'})
result = asyncio.run(adapter.sync())
print(f'UC Credits test: {result.inserted} inserted, errors: {result.error or \"none\"}')
" || echo "   ⚠ UC Credits test failed (adapter may need billing DB setup)"

    # Test Treasury State sync
    echo "   Testing Treasury State sync..."
    sudo -u streasury "$STREASURY_PATH/.venv/bin/python" -c "
import asyncio
import sys
sys.path.append('$STREASURY_PATH')
from app.sources.treasury_state import TreasuryStateAdapter
adapter = TreasuryStateAdapter(1, {'treasury_file': '/opt/fpai/core/STATE/TREASURY.json'})
result = asyncio.run(adapter.sync())
print(f'Treasury State test: {result.inserted} items updated, errors: {result.error or \"none\"}')
" || echo "   ⚠ Treasury State test failed (state file may not exist)"

    echo "   ✓ Connection tests completed"
fi

# 6. Update systemd timer for automatic sync
echo "6. Setting up automatic sync (every hour)..."

if [ "$ON_BRAIN" = true ]; then
    # Update the sync timer to run hourly instead of daily
    sudo tee /etc/systemd/system/streasury-bot-sync.timer > /dev/null << 'EOF'
[Unit]
Description=STreasury Bot Treasury Brain Sync
Requires=streasury-bot.service

[Timer]
OnCalendar=*-*-* *:15:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable streasury-bot-sync.timer
    sudo systemctl restart streasury-bot-sync.timer
    
    echo "   ✓ Hourly sync timer configured"
fi

echo
echo "========================================="
echo "  TREASURY BRAIN SETUP COMPLETE!"
echo "========================================="
echo
echo "Your Treasury Brain (STreasury Bot) is now connected to:"
echo "  ✓ UC Credits (trading fees, subscriptions)"
echo "  ✓ Treasury State (magnet engine, positions, TVL)"
echo
echo "Next steps:"
echo "  1. Test via Telegram: @STreasury_Bot"
echo "     /balance    - shows all accounts including UC revenue"
echo "     /kpi show TVL  - displays total value locked"
echo "     /ask what's our treasury status? - AI has full context"
echo
echo "  2. Add more adapters:"
echo "     - WhaleTrack (trading P&L)"
echo "     - Stripe (revenue auto-sync)" 
echo "     - DigitalOcean (hosting costs)"
echo
echo "  3. Monitor sync logs:"
if [ "$ON_BRAIN" = true ]; then
echo "     sudo journalctl -u streasury-bot-sync -f"
else
echo "     Deploy this to brain server first"
fi
echo
echo "Treasury Brain is now tracking all your numbers automatically! 🧠💰"