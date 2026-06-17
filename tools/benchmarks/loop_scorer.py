from __future__ import annotations

import datetime as dt
from typing import Any

from tools.benchmarks import parse_time, rate, rows_for, score_result

AGENT = "loop"


def _as_number(value: Any) -> float | None:
    if isinstance(value, dict):
        values = [float(v) for v in value.values() if isinstance(v, (int, float))]
        return sum(values) / len(values) if values else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def score(data: dict[str, Any] | None = None, *, now: dt.datetime | None = None) -> dict[str, Any]:
    current = now or dt.datetime.now(dt.timezone.utc)
    rows = rows_for(data, "per_agent_scores")
    by_agent: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_agent.setdefault(str(row.get("agent") or "unknown"), []).append(row)
    velocity: dict[str, float] = {}
    flat_agents: list[str] = []
    for agent, agent_rows in by_agent.items():
        dated = sorted(
            [(parse_time(row.get("run_date") or row.get("ts")), _as_number(row.get("primary_metric"))) for row in agent_rows],
            key=lambda item: item[0] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
        )
        dated = [(ts, value) for ts, value in dated if ts and value is not None]
        if len(dated) < 2:
            velocity[agent] = 0.0
            continue
        latest_ts, latest = dated[-1]
        prior_candidates = [(ts, value) for ts, value in dated[:-1] if (latest_ts - ts).days >= 7]
        prior = prior_candidates[-1][1] if prior_candidates else dated[0][1]
        delta = round(latest - prior, 4)
        velocity[agent] = delta
        flatline_candidates = [(ts, value) for ts, value in dated[:-1] if (latest_ts - ts).days >= 14]
        if flatline_candidates and abs(latest - flatline_candidates[-1][1]) < 0.02:
            flat_agents.append(agent)
    ops_rows = rows_for(data, "ops_ledger")
    costs = sum(float(row.get("cost_usd") or 0) for row in ops_rows if row.get("event") == "cost" or row.get("cost_usd") is not None)
    accepted = sum(1 for row in rows_for(data, "registry_builds") if str(row.get("status") or "").lower() in {"done", "merged"})
    recursive_depth = {
        agent: sum(
            1
            for row in rows_for(data, "registry_builds")
            if str(row.get("status") or "").lower() in {"done", "merged"}
            and f"auto-queued:{agent}" in str(row.get("notes") or "")
        )
        for agent in by_agent
    }
    avg_velocity = round(sum(velocity.values()) / len(velocity), 4) if velocity else 0.0
    metrics = {
        "improvement_velocity": velocity,
        "recursive_depth": recursive_depth,
        "north_star_cost_per_task": round(costs / accepted, 4) if accepted else 0.0,
    }
    return score_result(
        AGENT,
        primary_metric=avg_velocity,
        metrics=metrics,
        trigger_fired=bool(flat_agents),
        trigger_metric="improvement_velocity" if flat_agents else None,
        trigger_reason=f"flat improvement velocity for {', '.join(flat_agents)}" if flat_agents else None,
    )
