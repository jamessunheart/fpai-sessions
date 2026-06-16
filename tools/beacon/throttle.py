#!/usr/bin/env python3
"""Advisory Beacon traffic pacing policy.

This never adjusts spend or campaign status. It only returns a signal.
"""
from __future__ import annotations

from typing import Any


def _falling(last_7: list[float], prior_7: list[float]) -> bool:
    if not last_7 or not prior_7:
        return False
    return sum(last_7) / len(last_7) < sum(prior_7) / len(prior_7)


def _rising_three(values: list[float]) -> bool:
    return len(values) >= 3 and values[-3] < values[-2] < values[-1]


def should_scale_traffic(signal: dict[str, Any] | None = None) -> dict[str, Any]:
    signal = signal or {}
    completion = float(signal.get("onboarding_completion_rate", 0))
    day7 = float(signal.get("day7_return_rate", 0))
    redemption = float(signal.get("cora_redemption_rate", 1))
    support_load = float(signal.get("support_load", 0))
    support_threshold = float(signal.get("support_threshold", 1))
    last_7 = [float(v) for v in signal.get("cost_per_proof_last_7", [])]
    prior_7 = [float(v) for v in signal.get("cost_per_proof_prior_7", [])]
    recent_cpp = [float(v) for v in signal.get("cost_per_proof_recent", last_7)]
    click_chat_ratio = float(signal.get("click_chat_ratio", 0))

    if completion < 0.30:
        return {"scale": False, "reason": "pause: onboarding_completion_rate below 0.30", "signal": signal}
    if redemption < 0.10:
        return {"scale": False, "reason": "pause: CORA redemption rate below 0.10", "signal": signal}
    if _rising_three(recent_cpp):
        return {"scale": False, "reason": "pause: cost_per_proof rising 3 days in a row", "signal": signal}
    if click_chat_ratio and click_chat_ratio > 10:
        return {"scale": False, "reason": "pause: clicks are not converting to chat starts", "signal": signal}

    if completion > 0.60 and day7 > 0.30 and _falling(last_7, prior_7) and support_load < support_threshold:
        return {"scale": True, "reason": "scale: proof economics and retention are improving", "signal": signal}

    return {"scale": False, "reason": "hold: proof and retention signal not strong enough", "signal": signal}


if __name__ == "__main__":
    import json
    import sys

    payload = json.loads(sys.stdin.read() or "{}")
    print(json.dumps(should_scale_traffic(payload), indent=2, sort_keys=True))
