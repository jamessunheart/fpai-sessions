"""
Policy Engine
=============
Maps state + predictions + goals into action decisions.
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional
from pydantic import BaseModel


class SystemGoals(BaseModel):
    primary_goal: str = "maximize_long_term_pnl"
    pnl_target_annual: float = 0.0
    max_drawdown_pct: float = 0.2
    max_risk_per_trade_pct: float = 0.02
    risk_appetite: str = "medium"  # low | medium | high


class StateSnapshot(BaseModel):
    timestamp: datetime
    capital: float
    open_positions: List[Dict] = []
    recent_pnl_pct_30d: float = 0.0
    volatility_index: float = 0.0


class ActionDecision(BaseModel):
    action: str  # "enter_trade" | "exit_trade" | "hold" | "reduce_risk"
    rationale: str
    linked_prediction_id: Optional[str] = None
    expected_value: float = 0.0
    risk_score: float = 0.0
    requires_human_approval: bool = False


def decide(state: StateSnapshot, predictions: List[Dict], goals: SystemGoals) -> List[ActionDecision]:
    """
    Simple rules-based decisioning:
    - Enforce drawdown guard
    - Use only confirmed, calibrated predictions (confidence >= 0.7)
    - Respect risk appetite
    """
    decisions: List[ActionDecision] = []

    # 1) Hard risk guard: if drawdown breached, only exit/reduce
    if goals.max_drawdown_pct and state.recent_pnl_pct_30d <= -goals.max_drawdown_pct:
        decisions.append(ActionDecision(
            action="reduce_risk",
            rationale="Max drawdown breached; reduce exposure",
            risk_score=0.1,
            requires_human_approval=False
        ))
        return decisions

    for pred in predictions:
        if pred.get("status") not in ["pending", "confirmed", "CONFIRM"]:
            continue

        confidence = float(pred.get("confidence", 0))
        if confidence < 0.7:
            continue

        # If adversarial verdict exists, apply
        adv = pred.get("adversarial", {})
        verdict = adv.get("verdict") if isinstance(adv, dict) else getattr(adv, "verdict", None)
        if verdict == "reject":
            continue
        if verdict == "flag" and goals.risk_appetite == "low":
            continue

        # Risk score: inverse of confidence, adjusted by appetite
        risk_score = max(0.0, 1 - confidence)
        if goals.risk_appetite == "low":
            risk_score *= 1.2
        elif goals.risk_appetite == "high":
            risk_score *= 0.8

        decisions.append(ActionDecision(
            action="enter_trade",
            rationale=f"Prediction {pred.get('target_metric')} {pred.get('predicted_direction')} @ conf {confidence:.2f}",
            linked_prediction_id=pred.get("id"),
            expected_value=confidence - risk_score,
            risk_score=risk_score,
            requires_human_approval=(verdict == "flag" or risk_score > 0.4)
        ))

    return decisions












