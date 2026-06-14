# Deploy Treasury Brain Connections

## Quick Deploy (recommended)

```bash
# Deploy STreasury Bot with new treasury connections
SERVICES/streasury-bot/scripts/deploy.sh

# Once deployed, run the connection setup on brain server
ssh root@162.0.208.88
cd /opt/streasury-bot
./scripts/setup-treasury-brain-connections.sh
```

## What This Gives You

### Telegram Commands with Full Context

```
@STreasury_Bot

/balance
→ Shows all accounts including UC revenue streams

/kpi show TVL
→ Displays $405,230.50 total value locked

/kpi show Magnet_Strength  
→ Shows 72.5% magnet engine strength

/report month
→ P&L including trading fees, subscriptions, treasury yields

/ask what's our cash runway at current burn?
→ AI has full treasury context: positions, revenue, expenses

/council should we increase leverage on the magnet engine?
→ Claude + OpenAI analyze with complete treasury state
```

### Automatic Sync (every hour)

- **UC Credits**: Trading fees, subscription revenue, performance fees
- **Treasury Positions**: ETH/USDC positions, yields, protocol status  
- **Magnet Engine**: Leverage, strength, distance, conflicts
- **KPIs**: TVL, PnL, allocation percentages

### Treasury Brain Dashboard

STreasury Bot becomes your **single source of truth** for:
- All revenue streams (UC credits, trading, subscriptions)
- All treasury positions (DeFi, magnet engine, cash)  
- All KPIs in one chat interface
- AI that understands your complete financial picture

## Test After Deploy

```bash
# On Telegram: @STreasury_Bot
/balance   # Should show UC revenue accounts
/kpi list  # Should show TVL, PnL, magnet metrics  
/ask what's our treasury status?  # AI has full context
```

Your Treasury Brain is now **autonomous** — tracking every number automatically!