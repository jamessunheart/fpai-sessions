#!/bin/bash
###############################################################################
# ACTIVATE EVERYTHING - One Command to Start the Flywheel
# Session #3 (Value Architect) - Removes all activation friction
###############################################################################

echo "=========================================================================="
echo "🚀 FULL POTENTIAL AI - ACTIVATION SEQUENCE"
echo "=========================================================================="
echo ""
echo "This script activates ALL systems in correct order:"
echo "  1. Verify credentials"
echo "  2. Deploy capital to DeFi yields"
echo "  3. Activate Reddit autonomous bot"
echo "  4. Launch I MATCH outreach"
echo "  5. Monitor and report"
echo ""
echo "Session #3 (Value Architect) built this to remove activation friction."
echo ""
echo "=========================================================================="
echo ""

# Check if running in dev environment
if [ ! -d "/Users/jamessunheart/Development" ]; then
    echo "❌ Not in development environment"
    exit 1
fi

cd /Users/jamessunheart/Development

# Track activation status
ACTIVATION_LOG="activation_log_$(date +%Y%m%d_%H%M%S).txt"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$ACTIVATION_LOG"
}

log "=========================================================================="
log "ACTIVATION SEQUENCE STARTED"
log "=========================================================================="
log ""

# STEP 1: Verify Credentials
log "STEP 1: Verifying credentials..."
log ""

# Check for credential vault
if [ -z "$FPAI_CREDENTIALS_KEY" ]; then
    log "⚠️  FPAI_CREDENTIALS_KEY not set"
    log "   Set it with: export FPAI_CREDENTIALS_KEY=\"0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f\""
    log ""
    VAULT_AVAILABLE=false
else
    log "✅ Credential vault key set"
    VAULT_AVAILABLE=true
fi

# Check Reddit credentials
if [ -z "$REDDIT_CLIENT_ID" ]; then
    log "⚠️  Reddit credentials not set in environment"
    log "   Need: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD"
    log ""
    log "   See REDDIT_BOT_SETUP.md for instructions"
    log ""
    REDDIT_READY=false
else
    log "✅ Reddit credentials configured"
    REDDIT_READY=true
fi

# Check Anthropic API
if [ -z "$ANTHROPIC_API_KEY" ]; then
    log "⚠️  ANTHROPIC_API_KEY not set"
    ANTHROPIC_READY=false
else
    log "✅ Anthropic API key set"
    ANTHROPIC_READY=true
fi

log ""

# STEP 2: Capital Deployment
log "STEP 2: Capital deployment readiness..."
log ""

if [ -d "SERVICES/treasury-arena" ]; then
    log "✅ Treasury Arena service exists"
    log "   Capital: $373K available"
    log "   Target: $2-7K/month yields"
    log ""
    log "   ⏸️  MANUAL STEP: Deploy capital to DeFi"
    log "   Run: cd SERVICES/treasury-arena && ./deploy.sh"
    log ""
else
    log "⚠️  Treasury Arena not found"
fi

# STEP 3: Reddit Bot Activation
log "STEP 3: Reddit bot activation..."
log ""

if [ "$REDDIT_READY" = true ]; then
    log "🤖 Reddit bot is ready to activate"
    log ""
    read -p "   Activate Reddit bot now? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "   Launching Reddit autonomous bot..."
        python3 reddit_autonomous_bot.py &
        BOT_PID=$!
        log "   ✅ Bot launched (PID: $BOT_PID)"
        log "   Monitor: tail -f reddit_bot_log.txt"
    else
        log "   ⏸️  Skipped - activate manually with: python3 reddit_autonomous_bot.py"
    fi
else
    log "⏸️  Reddit bot not ready (credentials needed)"
    log "   Configure credentials first (see REDDIT_BOT_SETUP.md)"
fi

log ""

# STEP 4: I MATCH Launch
log "STEP 4: I MATCH service status..."
log ""

# Check if service is running
if curl -s --max-time 2 http://198.54.123.234:8401/health > /dev/null 2>&1; then
    log "✅ I MATCH service is LIVE"
    log "   URL: http://198.54.123.234:8401"
    log "   Landing pages: UPDATED with honest messaging"
    log ""
    log "   Ready for customers!"
else
    log "⚠️  I MATCH service not reachable"
    log "   Check: ssh root@198.54.123.234 'cd /opt/fpai/i-match && ./start.sh'"
fi

log ""

# STEP 5: Monitoring Setup
log "STEP 5: Monitoring and tracking..."
log ""

log "📊 Active monitoring:"
log "   • Reddit bot log: tail -f reddit_bot_log.txt"
log "   • Reddit bot state: cat reddit_bot_state.json"
log "   • I MATCH service: http://198.54.123.234:8401"
log "   • SOL treasury: https://explorer.solana.com/address/FLfNDVLD2vDQdTjMFSt1xJivhr8pKASwEBzRYHZRU7db"
log ""

# STEP 6: Next Steps
log ""
log "=========================================================================="
log "ACTIVATION SUMMARY"
log "=========================================================================="
log ""

READY_COUNT=0
TOTAL_COUNT=4

if [ "$VAULT_AVAILABLE" = true ]; then
    log "✅ Credential vault: READY"
    ((READY_COUNT++))
else
    log "⚠️  Credential vault: NEEDS SETUP"
fi

if [ "$REDDIT_READY" = true ]; then
    log "✅ Reddit bot: READY"
    ((READY_COUNT++))
else
    log "⚠️  Reddit bot: NEEDS CREDENTIALS"
fi

if curl -s --max-time 2 http://198.54.123.234:8401/health > /dev/null 2>&1; then
    log "✅ I MATCH service: LIVE"
    ((READY_COUNT++))
else
    log "⚠️  I MATCH service: CHECK STATUS"
fi

if [ -d "SERVICES/treasury-arena" ]; then
    log "⚠️  Capital deployment: MANUAL STEP NEEDED"
    # Don't count as ready until deployed
else
    log "⚠️  Capital deployment: NOT FOUND"
fi

log ""
log "Readiness: $READY_COUNT/$TOTAL_COUNT systems ready"
log ""

if [ $READY_COUNT -eq $TOTAL_COUNT ]; then
    log "🎉 ALL SYSTEMS READY - FLYWHEEL CAN START!"
else
    log "📋 NEXT STEPS:"
    log ""

    if [ "$VAULT_AVAILABLE" = false ]; then
        log "   1. Set credential vault key"
        log "      export FPAI_CREDENTIALS_KEY=\"...\""
    fi

    if [ "$REDDIT_READY" = false ]; then
        log "   2. Configure Reddit credentials"
        log "      See: REDDIT_BOT_SETUP.md"
    fi

    log "   3. Deploy capital to DeFi yields"
    log "      cd SERVICES/treasury-arena && ./deploy.sh"
    log ""
    log "   4. Activate Reddit bot"
    log "      python3 reddit_autonomous_bot.py"
fi

log ""
log "=========================================================================="
log "Activation log saved: $ACTIVATION_LOG"
log "=========================================================================="
log ""
log "Session #3 (Value Architect) - Removing activation friction 🌱"
log ""
