#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

tick_script="$(pwd)/scripts/comms-hub-cron-tick.sh"

echo "This script does not install cron."
echo "Review and install manually only after diagnostics pass:"
echo "*/5 * * * * COMMS_HUB_DRY_RUN=1 $tick_script >> $(pwd)/var/cron.log 2>&1"

