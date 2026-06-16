"""Beacon pacing and anti-farming guards."""
from __future__ import annotations

from dataclasses import dataclass
from math import inf


@dataclass(frozen=True)
class FarmingGuard:
    triggered: bool
    ratio: float
    action: str
    reason: str


def cora_farming_guard(cora_earned: int | float, proofs_created: int | float) -> FarmingGuard:
    earned = max(float(cora_earned or 0), 0.0)
    proofs = max(float(proofs_created or 0), 0.0)
    ratio = inf if earned > 0 and proofs == 0 else (earned / proofs if proofs else 0.0)
    triggered = ratio > 10
    if triggered:
        return FarmingGuard(
            triggered=True,
            ratio=ratio,
            action="tighten_rewards_and_flag_james_review",
            reason="CORA earned/proofs created ratio is above 10; attention may be farmed without proof.",
        )
    return FarmingGuard(
        triggered=False,
        ratio=ratio,
        action="continue",
        reason="CORA earn/proof ratio is inside the pacing gate.",
    )


def evaluate_pacing_signals(metrics: dict[str, int | float]) -> dict[str, object]:
    guard = cora_farming_guard(metrics.get("cora_earned", 0), metrics.get("proofs_created", 0))
    return {
        "cora_farming_guard": {
            "triggered": guard.triggered,
            "ratio": guard.ratio,
            "action": guard.action,
            "reason": guard.reason,
        }
    }

