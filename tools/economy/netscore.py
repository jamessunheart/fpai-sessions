#!/usr/bin/env python3
"""Network value score calculator."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class NetworkValueScore:
    identifier: str
    value_given_cora: float
    value_received_cora: float
    score: float
    tier: str
    private: bool = True

    def row(self) -> dict[str, Any]:
        data = asdict(self)
        data["value_given_cora"] = round(self.value_given_cora, 4)
        data["value_received_cora"] = round(self.value_received_cora, 4)
        data["score"] = round(self.score, 4)
        return data


def calculate_nvs(identifier: str, ledger_rows: Iterable[dict[str, Any]]) -> NetworkValueScore:
    given = 0.0
    received = 0.0
    for row in ledger_rows:
        cora_value = _cora_equivalent(row)
        if str(row.get("from_identifier")) == identifier:
            given += cora_value
        if str(row.get("to_identifier")) == identifier:
            received += cora_value
    score = given / (received + 1.0)
    return NetworkValueScore(
        identifier=identifier,
        value_given_cora=given,
        value_received_cora=received,
        score=score,
        tier=_tier(score),
    )


def contribution_prompt(score: NetworkValueScore | dict[str, Any]) -> str:
    value = score.score if isinstance(score, NetworkValueScore) else float(score.get("score") or 0.0)
    if value > 1.0:
        return "Net contributor: route higher-trust opportunities when relevant."
    if value < 0.5:
        return "Surface one low-friction way to contribute before routing more extraction."
    return "Balanced: keep routing reciprocal exchanges."


def _cora_equivalent(row: dict[str, Any]) -> float:
    if "cora_equivalent" in row:
        return max(0.0, float(row.get("cora_equivalent") or 0.0))
    return max(0.0, float(row.get("amount") or 0.0) * float(row.get("exchange_rate_to_cora") or 0.0))


def _tier(score: float) -> str:
    if score > 1.0:
        return "net_contributor"
    if score < 0.5:
        return "net_extractor"
    return "balanced"

