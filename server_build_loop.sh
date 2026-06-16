#!/usr/bin/env bash
# Compatibility entrypoint for the server answered-decision build loop.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/tools/decisions/bridge_to_codex.sh" "$@"
