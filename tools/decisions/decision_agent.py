#!/usr/bin/env python3
"""Spec-facing wrapper for the deployed curator Decision Agent.

The live service deploys `SERVICES/sunheart-brain`, so the implementation lives
inside `curator.decision_agent`. This wrapper preserves the requested
`tools/decisions/decision_agent.py` entry point for tests and repo tooling.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[2] / "SERVICES" / "sunheart-brain"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from curator.decision_agent import (  # noqa: E402,F401
    JAMES_PROFILE_STUB,
    NEVER_AUTO_RISK_CLASSES,
    REVERSIBLE_RISK_CLASSES,
    THRESHOLD,
    build_prompt,
    is_reversible,
    load_context,
    normalize_risk,
    score_decision,
)


if __name__ == "__main__":
    payload = json.loads(sys.stdin.read() or "{}") if len(sys.argv) == 1 else json.loads(sys.argv[1])
    print(json.dumps(score_decision(payload), indent=2, sort_keys=True))
