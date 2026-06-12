#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

: "${COMMS_HUB_DRY_RUN:=1}"

scripts/comms-hub tick
