#!/usr/bin/env python3
"""RunPod spend guard for sovereign GLM inference.

The guard is intentionally fail-closed for live GLM calls: if the daily budget is
zero, the API key is missing, or spend cannot be checked, callers should skip GPU
inference and use the flat-rate fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Callable
import urllib.request


RUNPOD_GRAPHQL_URL = os.environ.get("RUNPOD_GRAPHQL_URL", "https://api.runpod.io/graphql")
DEFAULT_OPS_LEDGER = Path(os.environ.get("OPS_LEDGER", "/opt/fpai-build/ops_ledger.jsonl"))


class BudgetGuardError(RuntimeError):
    """Raised when RunPod spend cannot be checked safely."""


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    daily_spend_usd: float
    daily_limit_usd: float
    cutoff_usd: float
    reason: str


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _graphql(api_key: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    req = urllib.request.Request(
        RUNPOD_GRAPHQL_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("errors"):
        raise BudgetGuardError(str(payload["errors"])[:500])
    return payload.get("data") or {}


def _walk_numbers(obj: Any, keys: set[str]) -> list[float]:
    found: list[float] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            lowered = key.lower()
            if lowered in keys and isinstance(value, (int, float, str)):
                try:
                    found.append(float(value))
                except ValueError:
                    pass
            found.extend(_walk_numbers(value, keys))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_walk_numbers(item, keys))
    return found


def fetch_daily_spend_usd(api_key: str, *, now: dt.datetime | None = None) -> float:
    """Fetch today's RunPod spend in USD.

    RunPod's GraphQL schema has changed across examples, so the parser accepts a
    small set of spend-like field names in the returned data. Tests inject this
    function; live callers fall back to Claude if the shape is not recognized.
    """

    if not api_key:
        raise BudgetGuardError("RUNPOD_API_KEY is missing")
    current = now or dt.datetime.now(dt.timezone.utc)
    start = current.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    query = """
    query FpaiRunPodSpend($start: String!) {
      myself {
        id
        spend {
          today
          daily
          amount
          total
        }
      }
      billing {
        spendSince(startTime: $start)
        total
      }
    }
    """
    data = _graphql(api_key, query, {"start": start})
    values = _walk_numbers(
        data,
        {"today", "daily", "dailytotal", "spendsince", "totalusd", "amountusd"},
    )
    if not values:
        raise BudgetGuardError("RunPod spend response did not include a recognized daily spend field")
    return max(values)


def check_budget(
    *,
    api_key: str | None = None,
    daily_limit_usd: float | None = None,
    spend_fetcher: Callable[[str], float] | None = None,
) -> BudgetDecision:
    limit = _float_env("RUNPOD_BUDGET_DAILY_USD", 50.0) if daily_limit_usd is None else daily_limit_usd
    cutoff = max(0.0, limit * 0.9)
    if limit <= 0:
        return BudgetDecision(False, 0.0, limit, cutoff, "RUNPOD_BUDGET_DAILY_USD is 0")
    key = api_key if api_key is not None else os.environ.get("RUNPOD_API_KEY", "")
    if not key:
        return BudgetDecision(False, 0.0, limit, cutoff, "RUNPOD_API_KEY is missing")
    try:
        spend = float((spend_fetcher or fetch_daily_spend_usd)(key))
    except Exception as exc:
        return BudgetDecision(False, 0.0, limit, cutoff, f"spend check failed: {exc}")
    if spend > cutoff:
        return BudgetDecision(False, spend, limit, cutoff, f"daily RunPod spend ${spend:.2f} exceeds ${cutoff:.2f}")
    return BudgetDecision(True, spend, limit, cutoff, "within budget")


def monthly_projection_usd(daily_spend_usd: float, *, day_of_month: int | None = None) -> float:
    day = day_of_month or dt.datetime.now(dt.timezone.utc).day
    if day <= 0:
        return 0.0
    return daily_spend_usd / day * 30.0


def log_budget_alert(
    decision: BudgetDecision,
    *,
    ops_ledger: Path = DEFAULT_OPS_LEDGER,
    monthly_limit_usd: float = 50.0,
) -> bool:
    """Append a local alert row for Telegram/bot surfaces to relay.

    This repo build does not send Telegram messages directly; it records the
    budget event in the ops ledger so the existing live surfaces can pick it up.
    """

    projected = monthly_projection_usd(decision.daily_spend_usd)
    if decision.allowed and projected <= monthly_limit_usd:
        return False
    row = {
        "ts": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "loop": "glm_runpod",
        "event": "budget_alert",
        "detail": decision.reason,
        "daily_spend_usd": decision.daily_spend_usd,
        "daily_limit_usd": decision.daily_limit_usd,
        "monthly_projected_usd": round(projected, 2),
        "monthly_limit_usd": monthly_limit_usd,
        "next": "skip GLM and use claude -p until RunPod budget is reviewed",
        "surface": os.environ.get("FPAI_SURFACE", "auto-loop"),
    }
    try:
        ops_ledger.parent.mkdir(parents=True, exist_ok=True)
        with ops_ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
        return True
    except Exception:
        return False


def main() -> int:
    decision = check_budget()
    print(json.dumps(decision.__dict__, sort_keys=True))
    return 0 if decision.allowed else 2


if __name__ == "__main__":
    raise SystemExit(main())
