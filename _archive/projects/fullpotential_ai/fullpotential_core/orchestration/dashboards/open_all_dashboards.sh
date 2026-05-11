#!/bin/bash
# Quick Dashboard Launcher - Open consolidated dashboards

echo "🚀 Opening consolidated dashboards..."
echo ""
echo "🎯 RECOMMENDED WORKFLOW:"
echo "  1. Start with Visual Coordination (8031) - Shows all sessions & services"
echo "  2. Use navigation panel to access other dashboards"
echo ""

echo "  ⭐ PRIMARY: Visual Coordination (8031)"
open http://localhost:8031 &
sleep 1

echo "  💰 NEW: Unified Financial (8101) - Consolidates Treasury + 2X + Arena"
open http://localhost:8101 &
sleep 1

echo ""
echo "✅ Opening 2 consolidated dashboards"
echo ""
echo "📊 All other dashboards accessible via navigation panel:"
echo "  - Jobs (8008)"
echo "  - FPAI Hub (8010)"
echo "  - Treasury (8005) - Legacy"
echo "  - 2X Treasury (8052) - Legacy"
echo "  - Arena (8035) - Legacy"
echo ""
echo "Start here → http://localhost:8031"
echo ""
