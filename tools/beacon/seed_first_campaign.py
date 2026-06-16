#!/usr/bin/env python3
"""Seed the first organic Beacon experiment."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVICE_ROOT = ROOT / "SERVICES" / "sunheart-brain"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from curator.beacon.campaign import BeaconCampaign


def main() -> int:
    campaign = BeaconCampaign()
    campaign_id = campaign.create(
        channel="telegram",
        cta_concept="Earn CORA for attention",
        audience="curious founders and seekers",
        intent_lane="curious",
    )
    print(campaign_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
