#!/usr/bin/env bash
# Print a read-only one-glance report for the local build queue.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 -B -m tools.build_loop.build_state --repo "$REPO_ROOT"
