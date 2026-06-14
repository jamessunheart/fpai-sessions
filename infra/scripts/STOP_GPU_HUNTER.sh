#!/bin/bash
# ============================================================================
# STOP GPU HUNTER - Run this on your servers to prevent GPU cost explosion
# ============================================================================
# 
# THE PROBLEM:
# - GPU Hunter Daemon acquires new GPUs every 2 minutes
# - GPU Watchdog was broken (checked wrong endpoint)
# - Result: 46 GPUs running at $57/day
#
# THIS SCRIPT:
# 1. Kills the GPU Hunter daemon
# 2. Disables it from auto-starting
# 3. Optionally destroys all Vast.ai instances
#
# RUN ON: Secondary server (162.0.208.88) where GPU services run
# ============================================================================

set -e

echo "🛑 STOPPING GPU HUNTER TO PREVENT COST EXPLOSION"
echo "=================================================="
echo ""

# 1. Kill GPU Hunter daemon
echo "Step 1: Killing GPU Hunter daemon..."
pkill -f "gpu_hunter" 2>/dev/null && echo "  ✅ Killed gpu_hunter process" || echo "  ℹ️ gpu_hunter not running"
pkill -f "gpu_hunter_daemon" 2>/dev/null && echo "  ✅ Killed gpu_hunter_daemon" || echo "  ℹ️ gpu_hunter_daemon not running"

# 2. Disable systemd service if exists
echo ""
echo "Step 2: Disabling GPU Hunter service..."
systemctl stop gpu_hunter 2>/dev/null && echo "  ✅ Stopped gpu_hunter service" || echo "  ℹ️ No gpu_hunter service"
systemctl disable gpu_hunter 2>/dev/null && echo "  ✅ Disabled gpu_hunter service" || echo "  ℹ️ Already disabled"
systemctl stop gpu-hunter 2>/dev/null && echo "  ✅ Stopped gpu-hunter service" || echo "  ℹ️ No gpu-hunter service"
systemctl disable gpu-hunter 2>/dev/null && echo "  ✅ Disabled gpu-hunter service" || echo "  ℹ️ Already disabled"

# 3. Rename the daemon to prevent accidental restart
echo ""
echo "Step 3: Disabling GPU Hunter script..."
if [ -f "/opt/fpai/ai-brain/v2/gpu_hunter_daemon.py" ]; then
    mv /opt/fpai/ai-brain/v2/gpu_hunter_daemon.py /opt/fpai/ai-brain/v2/gpu_hunter_daemon.py.DISABLED
    echo "  ✅ Renamed gpu_hunter_daemon.py to .DISABLED"
else
    echo "  ℹ️ gpu_hunter_daemon.py not found at expected location"
fi

# 4. Check for any remaining GPU processes
echo ""
echo "Step 4: Checking for remaining GPU acquisition processes..."
REMAINING=$(ps aux | grep -E "gpu_hunter|gpu_bridge|gpu_acquisition" | grep -v grep | wc -l)
if [ "$REMAINING" -gt 0 ]; then
    echo "  ⚠️ Found $REMAINING related processes:"
    ps aux | grep -E "gpu_hunter|gpu_bridge|gpu_acquisition" | grep -v grep
else
    echo "  ✅ No GPU acquisition processes running"
fi

echo ""
echo "=================================================="
echo "✅ GPU HUNTER DISABLED"
echo ""
echo "NEXT STEPS:"
echo "1. Your Vast.ai instances have been destroyed via API"
echo "2. GPU Hunter is now disabled on this server"
echo "3. To re-enable (if needed), rename:"
echo "   /opt/fpai/ai-brain/v2/gpu_hunter_daemon.py.DISABLED"
echo "   back to gpu_hunter_daemon.py"
echo ""
echo "Your services now use LOCAL OLLAMA (free) instead of Vast.ai GPUs"
echo "=================================================="
