#!/bin/bash
# Treasury Rebalance - One-Click Safety Deployment
# Closes risky leveraged positions, deploys to Aave for 6.5% APY

set -e

TREASURY_DATA="treasury_data.json"
LOG_FILE="treasury_rebalance_log.txt"

echo "=============================================="
echo "🔐 TREASURY SAFETY REBALANCE"
echo "=============================================="
echo ""

# Check if treasury data exists
if [ ! -f "$TREASURY_DATA" ]; then
    echo "❌ Error: $TREASURY_DATA not found"
    echo "   Run treasury status update first"
    exit 1
fi

# Parse current state
TOTAL_CAPITAL=$(jq -r '.summary.total.capital' $TREASURY_DATA)
CURRENT_PNL=$(jq -r '.summary.total.pnl' $TREASURY_DATA)
MARGIN_DEPLOYED=$(jq -r '.summary.leveraged.margin_deployed' $TREASURY_DATA)

echo "📊 CURRENT TREASURY STATUS:"
echo "   Total Capital: \$$(printf "%.2f" $TOTAL_CAPITAL)"
echo "   Current P&L: \$$(printf "%.2f" $CURRENT_PNL)"
echo "   Leveraged Margin: \$$(printf "%.0f" $MARGIN_DEPLOYED)"
echo ""

# Calculate rebalance
REALIZED_CAPITAL=$(echo "$TOTAL_CAPITAL + $CURRENT_PNL" | bc)
AAVE_DEPLOYMENT=$(echo "$REALIZED_CAPITAL * 0.8" | bc)
MONTHLY_YIELD=$(echo "$AAVE_DEPLOYMENT * 0.065 / 12" | bc)

echo "🎯 REBALANCE PLAN (Option A - Conservative):"
echo "   1. Close all 3 leveraged positions"
echo "   2. Realize loss: \$$(printf "%.0f" $CURRENT_PNL)"
echo "   3. Remaining capital: \$$(printf "%.0f" $REALIZED_CAPITAL)"
echo "   4. Deploy to Aave: \$$(printf "%.0f" $AAVE_DEPLOYMENT) USDC"
echo "   5. Monthly yield: \$$(printf "%.0f" $MONTHLY_YIELD) (6.5% APY)"
echo ""

# Show positions to close
echo "📋 POSITIONS TO CLOSE:"
echo ""

jq -r '.leveraged_positions[] | "   \(.asset) \(.leverage)x Leverage
   Entry: $\(.entry_price) → Current: $\(.current_price)
   Liquidation: $\(.liquidation_price)
   Margin: $\(.margin_deployed)
   Exchange: \(.exchange)
   "' $TREASURY_DATA

echo ""
echo "⚠️  WARNING: This will realize a \$$(printf "%.0f" $CURRENT_PNL) loss"
echo "   BUT it eliminates liquidation risk and starts earning yield"
echo ""

# Ask for confirmation
read -p "Do you want to proceed? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo ""
    echo "❌ Rebalance cancelled. No changes made."
    echo ""
    echo "💡 TIP: Review TREASURY_SAFETY_DASHBOARD.md for detailed analysis"
    exit 0
fi

echo ""
echo "=============================================="
echo "🚀 EXECUTING REBALANCE"
echo "=============================================="
echo ""

# Log start
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Rebalance started" >> $LOG_FILE
echo "Current state:" >> $LOG_FILE
cat $TREASURY_DATA >> $LOG_FILE

echo "Step 1/5: Generate Exchange Commands..."
echo ""

# Generate BTrue exchange commands
echo "📱 MANUAL EXECUTION REQUIRED:"
echo ""
echo "🔗 Log into BTrue Exchange: https://www.btrue.com"
echo ""
echo "   Execute these trades:"
echo "   1. Close BTC 3x position (Margin: \$10,000)"
echo "      → Futures → Close Position → Confirm"
echo ""
echo "   2. Close BTC 2x position (Margin: \$63,653)"
echo "      → Futures → Close Position → Confirm"
echo ""
echo "   3. Close SOL 2x position (Margin: \$135,000)"
echo "      → Futures → Close Position → Confirm"
echo ""

read -p "Press Enter when all positions are closed..."

echo ""
echo "Step 2/5: Calculate Final Capital..."
echo ""

read -p "Enter your total balance after closing positions: $" FINAL_BALANCE

USDC_TO_BUY=$(echo "$FINAL_BALANCE * 0.8" | bc | xargs printf "%.0f")

echo "   Final balance: \$$FINAL_BALANCE"
echo "   USDC to buy: \$$USDC_TO_BUY"
echo ""

echo "Step 3/5: Buy USDC..."
echo ""
echo "   Execute on BTrue:"
echo "   → Spot Trading → Buy USDC"
echo "   → Amount: \$$USDC_TO_BUY"
echo "   → Confirm trade"
echo ""

read -p "Press Enter when USDC purchase is complete..."

echo ""
echo "Step 4/5: Transfer to MetaMask..."
echo ""
echo "   1. BTrue → Withdraw → USDC"
echo "   2. Network: Ethereum (ERC-20)"
echo "   3. Amount: $USDC_TO_BUY USDC"
echo "   4. Destination: [Your MetaMask address]"
echo ""

read -p "Enter your MetaMask address: " METAMASK_ADDRESS

echo ""
echo "   Withdrawal command:"
echo "   Address: $METAMASK_ADDRESS"
echo "   Amount: $USDC_TO_BUY USDC"
echo "   Network: Ethereum"
echo ""

read -p "Press Enter when withdrawal is complete and confirmed..."

echo ""
echo "Step 5/5: Deploy to Aave..."
echo ""
echo "   1. Open Aave: https://app.aave.com"
echo "   2. Connect MetaMask ($METAMASK_ADDRESS)"
echo "   3. Supply → USDC"
echo "   4. Amount: $USDC_TO_BUY USDC"
echo "   5. Confirm transaction"
echo ""

read -p "Press Enter when Aave deployment is complete..."

echo ""
echo "=============================================="
echo "✅ REBALANCE COMPLETE"
echo "=============================================="
echo ""

# Calculate final metrics
MONTHLY_INCOME=$(echo "$USDC_TO_BUY * 0.065 / 12" | bc)
ANNUAL_INCOME=$(echo "$USDC_TO_BUY * 0.065" | bc)

echo "📊 NEW TREASURY STATUS:"
echo "   Capital in Aave: \$$USDC_TO_BUY USDC"
echo "   APY: 6.5%"
echo "   Monthly income: \$$(printf "%.2f" $MONTHLY_INCOME)"
echo "   Annual income: \$$(printf "%.2f" $ANNUAL_INCOME)"
echo "   Liquidation risk: ZERO"
echo ""

echo "💰 INCOME PROJECTION:"
echo "   Month 1: \$$(printf "%.2f" $MONTHLY_INCOME)"
echo "   Month 6: \$$(echo "$MONTHLY_INCOME * 6" | bc)"
echo "   Year 1: \$$(printf "%.2f" $ANNUAL_INCOME)"
echo ""

# Log completion
echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") - Rebalance completed" >> $LOG_FILE
echo "Final balance: $USDC_TO_BUY USDC in Aave" >> $LOG_FILE

echo "🎉 SUCCESS! Your treasury is now:"
echo "   ✅ Safe (no liquidation risk)"
echo "   ✅ Earning passive income"
echo "   ✅ Growing every block"
echo ""

echo "📝 Next steps:"
echo "   1. Monitor Aave dashboard: https://app.aave.com"
echo "   2. Track yield in treasury_data.json (update manually)"
echo "   3. Focus on I MATCH revenue generation"
echo ""

echo "🌐⚡💎 Treasury rebalance complete!"
echo ""
