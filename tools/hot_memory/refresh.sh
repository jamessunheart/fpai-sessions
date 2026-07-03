#!/usr/bin/env bash
# Refresh HOT_STATE: run the 5 scanners, then synthesize the bounded doc.
# Wired to com.fpai.hot-memory.plist (every 30 min). Manual: bash tools/hot_memory/refresh.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
python3 -m tools.hot_memory.run_all
python3 -m tools.hot_memory.synthesize
