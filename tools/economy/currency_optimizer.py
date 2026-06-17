#!/usr/bin/env python3
"""Currency routing for value-retaining network exchanges."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

FIAT_REQUIRED_EXCHANGE_TYPES = {
    "payroll",
    "legal",
    "tax",
    "external_vendor",
    "external vendor",
    "rent",
    "regulated_payment",
}
USDC_MINIMUM_USD = 10.0
USDC_NETWORK_FEE = 0.01
FIAT_DEFAULT_EXTRACTION_RATE = 0.03
FIAT_HIGH_EXTRACTION_RATE = 0.30


@dataclass(frozen=True)
class CurrencyRecommendation:
    recommended_currency: str
    reasoning: str
    estimated_friction: str
    estimated_extraction: float
    internal_flag: bool

    def row(self) -> dict[str, Any]:
        data = asdict(self)
        data["estimated_extraction"] = round(float(self.estimated_extraction), 4)
        return data


def recommend_currency(
    *,
    exchange_type: str,
    amount: float,
    from_identifier: str,
    to_identifier: str,
    participants: dict[str, dict[str, Any]] | None = None,
    route_history: Iterable[dict[str, Any]] | None = None,
) -> CurrencyRecommendation:
    """Choose the lowest-extraction currency path for an exchange.

    ``participants`` is keyed by identifier. Recognized keys include
    ``cora_balance``, ``accepts_cora``, ``wants_cora``, and wallet fields such
    as ``wallet`` or ``wallet_address``. No balances are mutated here.
    """
    kind = _clean(exchange_type)
    value = max(0.0, float(amount or 0.0))
    people = participants or {}
    sender = people.get(from_identifier, {})
    recipient = people.get(to_identifier, {})

    if _requires_fiat(kind):
        extraction = _learned_fiat_extraction(kind, route_history) or max(1.0, value * FIAT_DEFAULT_EXTRACTION_RATE)
        return CurrencyRecommendation(
            recommended_currency="fiat",
            reasoning=f"{exchange_type} is marked as requiring an external fiat rail.",
            estimated_friction="high",
            estimated_extraction=extraction,
            internal_flag=False,
        )

    if _can_use_cora(sender=sender, recipient=recipient, amount=value):
        return CurrencyRecommendation(
            recommended_currency="cora",
            reasoning="Both sides can settle in CORA credits, so the exchange stays internal with zero extraction.",
            estimated_friction="zero",
            estimated_extraction=0.0,
            internal_flag=True,
        )

    if _can_use_usdc(sender=sender, recipient=recipient, amount=value):
        return CurrencyRecommendation(
            recommended_currency="usdc",
            reasoning="CORA path is unavailable, but both sides have wallets and the amount clears the USDC threshold.",
            estimated_friction="low",
            estimated_extraction=USDC_NETWORK_FEE,
            internal_flag=False,
        )

    extraction = max(1.0, min(value * FIAT_HIGH_EXTRACTION_RATE, value * FIAT_DEFAULT_EXTRACTION_RATE if value else 1.0))
    return CurrencyRecommendation(
        recommended_currency="fiat",
        reasoning="No internal CORA path or wallet-compatible USDC path is available.",
        estimated_friction="high",
        estimated_extraction=extraction,
        internal_flag=False,
    )


def value_ledger_entry(
    *,
    from_identifier: str,
    to_identifier: str,
    value_type: str,
    amount: float,
    currency: str,
    exchange_rate_to_cora: float,
    description: str,
    external_extraction: float = 0.0,
    internal_flag: bool = True,
    at: str | None = None,
) -> dict[str, Any]:
    """Return a DB-shaped ``brain_index.value_ledger`` row without persisting it."""
    value = float(amount or 0.0)
    rate = float(exchange_rate_to_cora or 0.0)
    return {
        "at": at or datetime.now(timezone.utc).isoformat(),
        "from_identifier": str(from_identifier),
        "to_identifier": str(to_identifier),
        "value_type": _clean(value_type),
        "amount": value,
        "currency": _clean(currency),
        "exchange_rate_to_cora": rate,
        "cora_equivalent": round(value * rate, 4),
        "description": str(description or ""),
        "external_extraction": max(0.0, float(external_extraction or 0.0)),
        "internal_flag": bool(internal_flag),
    }


def record_recommendation_outcome(
    *,
    recommendation: CurrencyRecommendation | dict[str, Any],
    accepted: bool,
    outcome_score: float,
    exchange_type: str,
    at: str | None = None,
) -> dict[str, Any]:
    """Shape an optimizer learning row; callers decide where to persist it."""
    if isinstance(recommendation, CurrencyRecommendation):
        rec = recommendation.row()
    else:
        rec = dict(recommendation)
    return {
        "event": "currency_optimizer_outcome",
        "at": at or datetime.now(timezone.utc).isoformat(),
        "exchange_type": _clean(exchange_type),
        "recommended_currency": rec.get("recommended_currency"),
        "accepted": bool(accepted),
        "outcome_score": max(0.0, min(1.0, float(outcome_score or 0.0))),
        "estimated_extraction": float(rec.get("estimated_extraction") or 0.0),
        "estimated_friction": rec.get("estimated_friction"),
    }


def _can_use_cora(*, sender: dict[str, Any], recipient: dict[str, Any], amount: float) -> bool:
    sender_balance = float(sender.get("cora_balance") or sender.get("cora_credits") or 0.0)
    sender_can_pay = sender_balance >= amount
    recipient_wants = bool(recipient.get("wants_cora", recipient.get("accepts_cora", True)))
    sender_wants = bool(sender.get("wants_cora", sender.get("accepts_cora", True)))
    return sender_can_pay and recipient_wants and sender_wants


def _can_use_usdc(*, sender: dict[str, Any], recipient: dict[str, Any], amount: float) -> bool:
    return amount >= USDC_MINIMUM_USD and _has_wallet(sender) and _has_wallet(recipient)


def _has_wallet(row: dict[str, Any]) -> bool:
    return bool(row.get("wallet") or row.get("wallet_address") or row.get("usdc_wallet"))


def _requires_fiat(exchange_type: str) -> bool:
    return exchange_type in FIAT_REQUIRED_EXCHANGE_TYPES


def _learned_fiat_extraction(exchange_type: str, route_history: Iterable[dict[str, Any]] | None) -> float | None:
    samples = [
        float(row.get("estimated_extraction") or row.get("actual_extraction") or 0.0)
        for row in (route_history or [])
        if _clean(row.get("exchange_type")) == exchange_type and _clean(row.get("recommended_currency")) == "fiat"
    ]
    if not samples:
        return None
    return sum(samples) / len(samples)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())

