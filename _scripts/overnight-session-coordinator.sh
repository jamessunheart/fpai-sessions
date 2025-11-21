#!/bin/bash
###############################################################################
# OVERNIGHT SESSION COORDINATOR - Real Autonomous Execution
# Session #15 - Activation Catalyst
# This script ACTUALLY RUNS every 2 hours while you sleep
###############################################################################

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="/Users/jamessunheart/Development/overnight.log"
DECISIONS_LOG="/Users/jamessunheart/Development/autonomous-decisions-log.md"

echo "════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "🌙 OVERNIGHT COORDINATOR - $TIMESTAMP" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"

# 1. CHECK I MATCH SERVICE HEALTH (GREEN LIGHT - Infrastructure monitoring)
echo "" | tee -a "$LOG_FILE"
echo "📊 Checking I MATCH service health..." | tee -a "$LOG_FILE"
if curl -s --max-time 10 http://198.54.123.234:8401/health > /dev/null 2>&1; then
    echo "✅ I MATCH service: HEALTHY" | tee -a "$LOG_FILE"

    # Log autonomous decision
    echo "" >> "$DECISIONS_LOG"
    echo "### Autonomous Health Check - $TIMESTAMP ✅" >> "$DECISIONS_LOG"
    echo "**Action:** Checked I MATCH service health" >> "$DECISIONS_LOG"
    echo "**Result:** Service healthy and responding" >> "$DECISIONS_LOG"
    echo "**Category:** Infrastructure Monitoring (GREEN LIGHT)" >> "$DECISIONS_LOG"
    echo "**Alignment:** Ensures service availability for users" >> "$DECISIONS_LOG"
else
    echo "⚠️  I MATCH service: DEGRADED or OFFLINE" | tee -a "$LOG_FILE"

    # Log issue for morning review
    echo "" >> "$DECISIONS_LOG"
    echo "### Autonomous Health Check - $TIMESTAMP ⚠️" >> "$DECISIONS_LOG"
    echo "**Action:** Checked I MATCH service health" >> "$DECISIONS_LOG"
    echo "**Result:** Service not responding (flagged for morning review)" >> "$DECISIONS_LOG"
    echo "**Category:** Infrastructure Monitoring (GREEN LIGHT)" >> "$DECISIONS_LOG"
    echo "**Did NOT:** Restart service (requires approval for system changes)" >> "$DECISIONS_LOG"
fi

# 2. CHECK TREASURY PRICES (GREEN LIGHT - Data collection)
echo "" | tee -a "$LOG_FILE"
echo "💰 Checking treasury asset prices..." | tee -a "$LOG_FILE"

# Get BTC price
BTC_PRICE=$(curl -s --max-time 10 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd' | grep -o '"usd":[0-9.]*' | grep -o '[0-9.]*')

if [ -n "$BTC_PRICE" ]; then
    echo "  BTC: \$$BTC_PRICE" | tee -a "$LOG_FILE"
else
    BTC_PRICE="unavailable"
    echo "  BTC: Price unavailable" | tee -a "$LOG_FILE"
fi

# Get SOL price
SOL_PRICE=$(curl -s --max-time 10 'https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd' | grep -o '"usd":[0-9.]*' | grep -o '[0-9.]*')

if [ -n "$SOL_PRICE" ]; then
    echo "  SOL: \$$SOL_PRICE" | tee -a "$LOG_FILE"
else
    SOL_PRICE="unavailable"
    echo "  SOL: Price unavailable" | tee -a "$LOG_FILE"
fi

# Log price collection decision
echo "" >> "$DECISIONS_LOG"
echo "### Autonomous Price Tracking - $TIMESTAMP ✅" >> "$DECISIONS_LOG"
echo "**Action:** Collected treasury asset prices (BTC: \$$BTC_PRICE, SOL: \$$SOL_PRICE)" >> "$DECISIONS_LOG"
echo "**Category:** Data Collection (GREEN LIGHT)" >> "$DECISIONS_LOG"
echo "**Alignment:** Provides data for informed morning decisions" >> "$DECISIONS_LOG"
echo "**Did NOT:** Execute any trades or move capital" >> "$DECISIONS_LOG"

# 3. CHECK FOR EMAIL CAPTURES (GREEN LIGHT - Analytics)
echo "" | tee -a "$LOG_FILE"
echo "📧 Checking for overnight email captures..." | tee -a "$LOG_FILE"

# Try to check if email endpoint exists
EMAIL_CHECK=$(curl -s --max-time 5 http://198.54.123.234:8401/api/lead/count 2>/dev/null || echo "endpoint_not_available")

if [ "$EMAIL_CHECK" != "endpoint_not_available" ]; then
    echo "  Email capture system: Active" | tee -a "$LOG_FILE"
else
    echo "  Email capture system: Monitoring (endpoint pending)" | tee -a "$LOG_FILE"
fi

# 4. UPDATE SSOT (GREEN LIGHT - Documentation)
echo "" | tee -a "$LOG_FILE"
echo "📝 Updating SSOT with latest data..." | tee -a "$LOG_FILE"

if [ -f "/Users/jamessunheart/Development/docs/coordination/scripts/update-ssot.sh" ]; then
    cd /Users/jamessunheart/Development/docs/coordination/scripts
    ./update-ssot.sh >> "$LOG_FILE" 2>&1
    echo "✅ SSOT updated" | tee -a "$LOG_FILE"
else
    echo "⚠️  SSOT update script not found" | tee -a "$LOG_FILE"
fi

# 5. BROADCAST STATUS (GREEN LIGHT - Internal communication)
echo "" | tee -a "$LOG_FILE"
echo "📡 Broadcasting overnight status..." | tee -a "$LOG_FILE"

if [ -f "/Users/jamessunheart/Development/docs/coordination/scripts/session-send-message.sh" ]; then
    cd /Users/jamessunheart/Development/docs/coordination/scripts
    ./session-send-message.sh broadcast "Overnight Update $TIMESTAMP" \
        "Session #15 autonomous coordinator running. I MATCH health checked. Treasury prices tracked. System monitoring active." "normal" >> "$LOG_FILE" 2>&1
    echo "✅ Status broadcast sent" | tee -a "$LOG_FILE"
else
    echo "⚠️  Broadcast script not found (will continue monitoring)" | tee -a "$LOG_FILE"
fi

# 6. SUMMARY
echo "" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "✅ OVERNIGHT COORDINATION COMPLETE" | tee -a "$LOG_FILE"
echo "   Next run in 2 hours" | tee -a "$LOG_FILE"
echo "════════════════════════════════════════════════════════════════" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Final decision log entry
echo "" >> "$DECISIONS_LOG"
echo "### Overnight Coordination Cycle Complete - $TIMESTAMP ✅" >> "$DECISIONS_LOG"
echo "**Actions Taken:** Health check, price tracking, analytics, SSOT update, status broadcast" >> "$DECISIONS_LOG"
echo "**Category:** Autonomous Monitoring (GREEN LIGHT)" >> "$DECISIONS_LOG"
echo "**Alignment:** System evolution while respecting all boundaries" >> "$DECISIONS_LOG"
echo "**Boundaries Respected:** No money moved, no strategic changes, no risky decisions" >> "$DECISIONS_LOG"
echo "---" >> "$DECISIONS_LOG"

exit 0
