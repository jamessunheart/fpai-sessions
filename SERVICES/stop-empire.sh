#!/bin/bash
# 🛑 Stop All FPAI Empire Services

echo "🛑 Stopping FPAI Empire..."
echo ""

# Kill FPAI Hub
if [ -f /tmp/fpai-hub.pid ]; then
    PID=$(cat /tmp/fpai-hub.pid)
    if ps -p $PID > /dev/null 2>&1; then
        kill $PID
        echo "✅ Stopped FPAI Hub (PID: $PID)"
    fi
    rm /tmp/fpai-hub.pid
fi

# Kill all agents
pkill -f "defi_yield_agent.py" && echo "✅ Stopped DeFi Yield Agent" || true
pkill -f "gas_optimizer_agent.py" && echo "✅ Stopped Gas Optimizer" || true
pkill -f "arbitrage_agent.py" && echo "✅ Stopped Arbitrage Agent" || true
pkill -f "human_recruiter_agent.py" && echo "✅ Stopped Human Recruiter" || true
pkill -f "resource_monitor_agent.py" && echo "✅ Stopped Resource Monitor" || true

echo ""
echo "🛑 All empire services stopped"
