#!/usr/bin/env python3
"""Render a provenance-first, read-only Finance Hub NOW/attention surface.

The tool reads local evidence, turns stale or unverified financial values into
UNKNOWN, leak-checks both outputs, and writes only derived repo-local renders.
It never calls a network, writes to a source, dispatches an alert, or moves
money.  The embedded North attention contract is deliberately inert.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping

try:  # package import when run via `python -m`
    from .leak_scan import LeakDetected, assert_safe_outputs
    from .sources import (
        UTC,
        SourceConfig,
        SourceEnvelope,
        collect_sources,
        default_source_config,
        isoformat,
        parse_timestamp,
        utc_now,
    )
    from .watch import EVALUATED_RULE_IDS, evaluate_anomalies, update_verified_baseline
except ImportError:  # direct script execution from tools/financial_hub/
    from leak_scan import LeakDetected, assert_safe_outputs
    from sources import (  # type: ignore
        UTC,
        SourceConfig,
        SourceEnvelope,
        collect_sources,
        default_source_config,
        isoformat,
        parse_timestamp,
        utc_now,
    )
    from watch import EVALUATED_RULE_IDS, evaluate_anomalies, update_verified_baseline  # type: ignore


STATE_SCHEMA = "financial_hub_state.v1"
NORTH_ATTENTION_SCHEMA = "north_attention_source.v1"
DEFAULT_DAILY_COST_CAP_USD = 20.0

MODULE_PATH = Path(__file__).resolve()
DEFAULT_REPO_ROOT = MODULE_PATH.parents[2]
DEFAULT_MARKDOWN_OUTPUT = DEFAULT_REPO_ROOT / "core" / "STATE" / "FINANCIAL_HUB.md"
DEFAULT_STATE_OUTPUT = DEFAULT_REPO_ROOT / "core" / "STATE" / ".financial_hub_state.json"

SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _reason_text(reason: str) -> str:
    if reason == "source_missing":
        return "source missing"
    if reason == "source_error":
        return "source could not be read"
    if reason == "source_stale":
        return "source is beyond its freshness contract"
    if reason == "source_as_of_missing":
        return "source has no trustworthy as-of time"
    if reason == "source_time_invalid":
        return "source as-of time is invalid"
    if reason == "metric_missing":
        return "metric is absent from the source"
    if reason.startswith("verification_unacceptable:"):
        state = reason.split(":", 1)[1]
        return f"verification state is {state}"
    return reason.replace("_", " ")


def unknown_metric(
    name: str,
    *,
    unit: str,
    source: SourceEnvelope,
    reason: str,
    measurement_kind: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "state": "unknown",
        "value": None,
        "unit": unit,
        "display": f"UNKNOWN — {_reason_text(reason)}",
        "measurement_kind": measurement_kind,
        "as_of": isoformat(source.as_of),
        "verification_state": source.verification_state,
        "source_ids": [source.source_id],
        "evidence_reference": source.evidence_reference,
        "reason": reason,
    }


def source_metric(
    name: str,
    source: SourceEnvelope,
    field: str,
    *,
    unit: str = "USD",
    allowed_verification: set[str],
    measurement_kind: str,
    precision: int = 0,
) -> dict[str, Any]:
    if source.status == "missing":
        return unknown_metric(
            name, unit=unit, source=source, reason="source_missing", measurement_kind=measurement_kind
        )
    if source.status == "error":
        return unknown_metric(
            name, unit=unit, source=source, reason="source_error", measurement_kind=measurement_kind
        )
    if source.freshness_state == "stale":
        return unknown_metric(
            name, unit=unit, source=source, reason="source_stale", measurement_kind=measurement_kind
        )
    if source.freshness_state == "unknown":
        return unknown_metric(
            name, unit=unit, source=source, reason="source_as_of_missing", measurement_kind=measurement_kind
        )
    if source.freshness_state == "invalid_future":
        return unknown_metric(
            name, unit=unit, source=source, reason="source_time_invalid", measurement_kind=measurement_kind
        )
    if source.verification_state not in allowed_verification:
        return unknown_metric(
            name,
            unit=unit,
            source=source,
            reason=f"verification_unacceptable:{source.verification_state}",
            measurement_kind=measurement_kind,
        )
    value = source.data.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return unknown_metric(
            name, unit=unit, source=source, reason="metric_missing", measurement_kind=measurement_kind
        )

    rounded: int | float
    if precision == 0:
        rounded = int(round(float(value)))
    else:
        rounded = round(float(value), precision)
    if unit == "USD":
        display = f"${rounded:,.{precision}f}" if precision else f"${rounded:,}"
    else:
        display = f"{rounded:,.{precision}f} {unit}" if precision else f"{rounded:,} {unit}"
    if source.verification_state == "estimated":
        display += " estimated"
    elif source.verification_state == "reported":
        display += " reported (not independently verified)"
    elif source.verification_state == "observed":
        display += " observed"
    return {
        "name": name,
        "state": source.verification_state,
        "value": rounded,
        "unit": unit,
        "display": display,
        "measurement_kind": measurement_kind,
        "as_of": isoformat(source.as_of),
        "verification_state": source.verification_state,
        "source_ids": [source.source_id],
        "evidence_reference": source.evidence_reference,
        "reason": None,
    }


def quarantined_sol_positions(source: SourceEnvelope) -> dict[str, Any]:
    present = bool(source.data.get("position_payload_present"))
    return {
        "name": "sol_positions",
        "state": "quarantined",
        "value": None,
        "unit": None,
        "display": "QUARANTINED — public price freshness cannot verify account positions",
        "measurement_kind": "position_state",
        "as_of": isoformat(source.as_of),
        "verification_state": "unverified",
        "source_ids": [source.source_id],
        "evidence_reference": source.evidence_reference,
        "reason": "embedded_position_payload_suppressed" if present else "no_independent_position_source",
    }


def attention_item(
    category: str,
    severity: str,
    title: str,
    summary: str,
    *,
    source_ids: list[str],
    owner: str,
    next_safe_action: str,
    detected_at: str,
    requires_james: bool = False,
) -> dict[str, Any]:
    return {
        "id": f"finance-{_slug(category)}-{'-'.join(_slug(item) for item in source_ids) or 'global'}",
        "severity": severity,
        "category": category,
        "title": title,
        "summary": summary,
        "source_ids": source_ids,
        "owner": owner,
        "next_safe_action": next_safe_action,
        "requires_james": requires_james,
        "delivery_status": "not_sent",
        "detected_at": detected_at,
    }


def source_attention(sources: Mapping[str, SourceEnvelope], generated_at: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for source in sources.values():
        if source.status == "available":
            continue
        if source.status == "error":
            severity = "critical"
            category = "source_error"
            title = f"{source.label} could not be read"
            summary = "No values from this source were admitted to Finance NOW."
        elif source.status == "missing":
            severity = "warning"
            category = "source_missing"
            title = f"{source.label} is missing"
            summary = "The financial picture remains incomplete; missing is not treated as zero."
        elif source.status == "stale":
            severity = "warning"
            category = "source_stale"
            title = f"{source.label} is stale"
            summary = "Its values were changed to UNKNOWN because the semantic as-of time expired."
        elif source.status == "invalid":
            severity = "warning"
            category = "source_time_invalid"
            title = f"{source.label} has an invalid as-of time"
            summary = "Future-dated evidence was not admitted."
        else:
            severity = "warning"
            category = "source_unverified"
            title = f"{source.label} is not verified"
            summary = "The source may be inventoried, but its values do not qualify as verified truth."
        items.append(
            attention_item(
                category,
                severity,
                title,
                summary,
                source_ids=[source.source_id],
                owner="finance_steward",
                next_safe_action="Refresh or verify this source with read-only evidence and an explicit as-of time.",
                detected_at=generated_at,
            )
        )
    return items


def metric_attention(headline: Mapping[str, Mapping[str, Any]], generated_at: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, title in (
        ("net_spendable_usd", "Verified current liquidity is unknown"),
        ("monthly_burn_usd", "Verified monthly burn is unknown"),
    ):
        metric = headline[key]
        if metric.get("state") != "unknown":
            continue
        items.append(
            attention_item(
                f"metric_unknown_{key}",
                "warning",
                title,
                str(metric.get("display") or "Required metric is unknown."),
                source_ids=list(metric.get("source_ids") or []),
                owner="finance_steward",
                next_safe_action="Refresh the canonical local evidence; do not estimate or carry forward this value.",
                detected_at=generated_at,
            )
        )
    return items


def _deduplicate_attention(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in items:
        existing = by_id.get(item["id"])
        if existing is None or SEVERITY_RANK.get(item["severity"], 0) > SEVERITY_RANK.get(existing["severity"], 0):
            by_id[item["id"]] = item
    return sorted(
        by_id.values(),
        key=lambda item: (-SEVERITY_RANK.get(item["severity"], 0), item["id"]),
    )


def select_next_safe_action(items: list[dict[str, Any]]) -> dict[str, Any]:
    preferred = next(
        (
            item
            for item in items
            if "treasury-actuals" in item.get("source_ids", [])
            and item.get("category") in {"source_missing", "source_stale", "source_unverified", "source_error"}
        ),
        items[0] if items else None,
    )
    if preferred:
        return {
            "id": f"resolve-{preferred['id']}",
            "owner": preferred["owner"],
            "action": preferred["next_safe_action"],
            "effect": "read_only",
            "requires_james": False,
            "money_movement": False,
        }
    return {
        "id": "refresh-at-next-cadence",
        "owner": "finance_steward",
        "action": "Refresh the same read-only evidence at the next scheduled cadence.",
        "effect": "read_only",
        "requires_james": False,
        "money_movement": False,
    }


def common_north_envelope(
    sources: Mapping[str, SourceEnvelope],
    headline: Mapping[str, Mapping[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    """Project Finance OS into North's common source-envelope contract.

    Evidence reconciliation is ordinary operational work. It never becomes an
    attention gate merely because a source is stale, missing, or unverified.
    """
    unavailable_source_ids = sorted(
        source.source_id for source in sources.values() if source.status != "available"
    )
    running_now: list[dict[str, Any]] = []
    if unavailable_source_ids:
        running_now.append(
            {
                "id": "refresh-financial-truth",
                "title": "Refresh and reconcile Finance OS source evidence",
                "stage": "reconciling_sources",
                "source_ids": unavailable_source_ids,
            }
        )

    required_metrics_verified = all(
        headline[name].get("state") == "verified"
        for name in ("net_spendable_usd", "monthly_burn_usd")
    )
    review_ready = not unavailable_source_ids and required_metrics_verified
    if review_ready:
        review_reason = (
            "Configured source envelopes satisfy their current data-admission contracts; "
            "the Finance NOW surface remains read-only."
        )
    else:
        review_reason = (
            "Source verification is incomplete; refresh and reconciliation remain operational work."
        )

    return {
        "schema_version": "north-attention-source.v1",
        "project_id": "finance-os",
        "updated_at": generated_at,
        "running_now": running_now,
        "attention_gates": [],
        "review_next": [
            {
                "id": "finance-now",
                "title": "Finance NOW surface",
                "ready": review_ready,
                "reason": review_reason,
                "source_refs": [
                    "financial-hub-state:headline",
                    "financial-hub-state:sources",
                ],
            }
        ],
    }


def build_state(
    sources: Mapping[str, SourceEnvelope],
    *,
    now: dt.datetime,
    previous_state: Mapping[str, Any] | None = None,
    daily_cost_cap_usd: float = DEFAULT_DAILY_COST_CAP_USD,
) -> dict[str, Any]:
    generated_at = isoformat(now.astimezone(UTC)) or ""
    treasury = sources["treasury-actuals"]
    costs = sources["ai-cost-ledger"]
    sol = sources["sol-price-monitor"]

    headline = {
        "net_spendable_usd": source_metric(
            "net_spendable_usd",
            treasury,
            "net_spendable_usd",
            allowed_verification={"verified", "reported"},
            measurement_kind="balance_snapshot",
        ),
        "monthly_burn_usd": source_metric(
            "monthly_burn_usd",
            treasury,
            "monthly_burn_usd",
            allowed_verification={"verified", "reported"},
            measurement_kind="burn_snapshot",
        ),
        "estimated_ai_cost_today_usd": source_metric(
            "estimated_ai_cost_today_usd",
            costs,
            "metered_estimate_today_usd",
            allowed_verification={"estimated"},
            measurement_kind="modelled_estimate",
            precision=2,
        ),
        "sol_public_price_usd": source_metric(
            "sol_public_price_usd",
            sol,
            "sol_price_usd",
            allowed_verification={"observed"},
            measurement_kind="public_market_observation",
            precision=2,
        ),
        "sol_positions": quarantined_sol_positions(sol),
    }

    items = source_attention(sources, generated_at)
    items.extend(metric_attention(headline, generated_at))
    for anomaly in evaluate_anomalies(headline, previous_state, daily_cost_cap_usd):
        items.append(attention_item(detected_at=generated_at, **anomaly))
    if bool(sol.data.get("position_payload_present")):
        items.append(
            attention_item(
                "sol_position_quarantine",
                "warning",
                "Unverified SOL position payload was suppressed",
                "A fresh public price does not make hard-coded or account-unverified position data current.",
                source_ids=[sol.source_id],
                owner="finance_steward",
                next_safe_action="Keep positions hidden until an independent, current, read-only account source verifies them.",
                detected_at=generated_at,
            )
        )
    items = _deduplicate_attention(items)
    decisions = [item for item in items if item.get("requires_james")]
    next_safe_action = select_next_safe_action(items)
    attention_status = "attention_required" if any(
        item["severity"] in {"warning", "critical"} for item in items
    ) else "clear"

    baseline, baseline_status = update_verified_baseline(headline, previous_state)

    estimated_cost = headline["estimated_ai_cost_today_usd"].get("value")
    freeze_recommended = (
        isinstance(estimated_cost, (int, float))
        and not isinstance(estimated_cost, bool)
        and float(estimated_cost) >= daily_cost_cap_usd
    )

    north_fields = common_north_envelope(sources, headline, generated_at)
    return {
        **north_fields,
        "schema": STATE_SCHEMA,
        "generated_at": generated_at,
        "read_only": True,
        "effect_policy": {
            "source_writes": False,
            "network_calls": False,
            "money_movement": False,
            "alert_dispatch": False,
        },
        "headline": headline,
        "sources": [sources[key].public_record() for key in sorted(sources)],
        "attention": {
            "schema": NORTH_ATTENTION_SCHEMA,
            "source_id": "finance_hub",
            "status": attention_status,
            "items": items,
            "count": len(items),
            "decisions": decisions,
            "genuine_decision_count": len(decisions),
            "next_safe_action": next_safe_action,
            "delivery": {
                "mode": "local_inert",
                "delivery_status": "not_sent",
                "dispatch_enabled": False,
                "suggested_consumer": "North",
                "item_ids": [item["id"] for item in items],
                "outbox": {
                    "mode": "disabled_inert",
                    "enqueue_attempted": False,
                    "files_written": 0,
                    "external_dispatch_attempted": False,
                    "reason": "Review-gated patch: anomaly state is rendered locally only.",
                },
            },
        },
        "controls": {
            "daily_estimated_cost_cap_usd": daily_cost_cap_usd,
            "paid_polling_freeze_recommended": freeze_recommended,
            "paid_polling_freeze_enforced_by_hub": False,
            "publication_authorized": False,
        },
        "anomaly_baseline": baseline,
        "anomaly_baseline_status": baseline_status,
        "anomaly_state": {
            "schema": "financial_hub_anomaly_state.v1",
            "evaluated_rule_ids": list(EVALUATED_RULE_IDS),
            "triggered_item_ids": [
                item["id"]
                for item in items
                if item["category"]
                in {"net_spendable_delta", "monthly_burn_delta", "estimated_cost_cap"}
            ],
            "baseline": baseline,
            "baseline_status": baseline_status,
        },
    }


def _age_label(age_seconds: Any) -> str:
    if not isinstance(age_seconds, int):
        return "unknown"
    if age_seconds < 60 * 60:
        return f"{age_seconds // 60}m"
    if age_seconds < 24 * 60 * 60:
        return f"{age_seconds // 3600}h"
    return f"{age_seconds // 86400}d"


def render_markdown(state: Mapping[str, Any]) -> str:
    headline = state["headline"]
    attention = state["attention"]
    lines = [
        "# FINANCIAL HUB",
        "",
        "> Read-only derived view. Stale or unverified values become UNKNOWN. This is not a ledger and cannot move money.",
        f"> Generated: {state['generated_at']}",
        "",
        "## NOW",
        "",
        "| Signal | State | Current read | As of |",
        "|---|---|---|---|",
    ]
    for key, label in (
        ("net_spendable_usd", "Net spendable"),
        ("monthly_burn_usd", "Monthly burn"),
        ("estimated_ai_cost_today_usd", "AI cost today"),
        ("sol_public_price_usd", "SOL public price"),
        ("sol_positions", "SOL positions"),
    ):
        metric = headline[key]
        lines.append(
            f"| {label} | {metric['state']} | {metric['display']} | {metric.get('as_of') or 'unknown'} |"
        )

    lines.extend(["", "## ATTENTION", ""])
    if attention["items"]:
        for item in attention["items"]:
            lines.append(
                f"- **{item['severity'].upper()} — {item['title']}**: {item['summary']} "
                f"Owner: {item['owner']}. Delivery: not sent."
            )
    else:
        lines.append("- No warning or critical finance attention items.")

    lines.extend(["", "## DECISIONS", ""])
    if attention["decisions"]:
        for item in attention["decisions"]:
            lines.append(f"- **{item['title']}** — {item['summary']}")
    else:
        lines.append("- None. Evidence refresh and reconciliation remain downstream work, not James decisions.")

    action = attention["next_safe_action"]
    lines.extend(
        [
            "",
            "## NEXT SAFE ACTION",
            "",
            f"- **Owner:** {action['owner']}",
            f"- **Action:** {action['action']}",
            "- **Boundary:** read-only; no transaction, trade, transfer, provider call, publication, or message send.",
            "",
            "## SOURCE HEALTH",
            "",
            "| Source | Status | Verification | As of | Age |",
            "|---|---|---|---|---|",
        ]
    )
    for source in state["sources"]:
        lines.append(
            f"| {source['label']} | {source['status']} | {source['verification_state']} | "
            f"{source.get('as_of') or 'unknown'} | {_age_label(source.get('age_seconds'))} |"
        )

    delivery = attention["delivery"]
    lines.extend(
        [
            "",
            "## DELIVERY",
            "",
            f"- North source envelope: `{state['schema_version']}`",
            f"- Mode: `{delivery['mode']}`",
            f"- Status: `{delivery['delivery_status']}`",
            "- No outbox, Telegram, email, or other external dispatch occurs in this patch.",
            "",
        ]
    )
    return "\n".join(lines)


def load_previous_state(path: Path) -> Mapping[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, Mapping) or payload.get("schema") != STATE_SCHEMA:
        return None
    return payload


def build_artifacts(
    config: SourceConfig,
    *,
    now: dt.datetime | None = None,
    previous_state: Mapping[str, Any] | None = None,
    daily_cost_cap_usd: float = DEFAULT_DAILY_COST_CAP_USD,
) -> tuple[dict[str, Any], str]:
    current = (now or utc_now()).astimezone(UTC)
    sources = collect_sources(config, current)
    state = build_state(
        sources,
        now=current,
        previous_state=previous_state,
        daily_cost_cap_usd=daily_cost_cap_usd,
    )
    markdown = render_markdown(state)
    assert_safe_outputs(markdown, state)
    return state, markdown


def write_outputs(markdown: str, state: Mapping[str, Any], markdown_path: Path, state_path: Path) -> None:
    """Leak-check both complete outputs before either target is replaced."""
    assert_safe_outputs(markdown, state)
    state_text = json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_tmp = markdown_path.with_name(markdown_path.name + ".tmp")
    state_tmp = state_path.with_name(state_path.name + ".tmp")
    markdown_tmp.write_text(markdown, encoding="utf-8")
    state_tmp.write_text(state_text, encoding="utf-8")
    os.replace(markdown_tmp, markdown_path)
    os.replace(state_tmp, state_path)


def refresh(
    config: SourceConfig,
    *,
    markdown_path: Path,
    state_path: Path,
    now: dt.datetime | None = None,
    write: bool = True,
    daily_cost_cap_usd: float = DEFAULT_DAILY_COST_CAP_USD,
) -> tuple[dict[str, Any], str]:
    previous = load_previous_state(state_path)
    state, markdown = build_artifacts(
        config,
        now=now,
        previous_state=previous,
        daily_cost_cap_usd=daily_cost_cap_usd,
    )
    if write:
        write_outputs(markdown, state, markdown_path, state_path)
    return state, markdown


def parse_cli_timestamp(value: str) -> dt.datetime:
    parsed = parse_timestamp(value)
    if parsed is None:
        raise argparse.ArgumentTypeError("expected ISO-8601 timestamp")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render the read-only, provenance-first Finance Hub.")
    parser.add_argument("--output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    parser.add_argument("--state-output", type=Path, default=DEFAULT_STATE_OUTPUT)
    parser.add_argument("--treasury-source", type=Path)
    parser.add_argument("--cost-ledger", type=Path)
    parser.add_argument("--sol-live", type=Path)
    parser.add_argument("--zen-accounting", type=Path)
    parser.add_argument("--now", type=parse_cli_timestamp, help="Deterministic evaluation time for fixtures/tests.")
    parser.add_argument(
        "--daily-cost-cap-usd",
        type=float,
        default=float(os.environ.get("FINANCIAL_HUB_DAILY_COST_CAP_USD", DEFAULT_DAILY_COST_CAP_USD)),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true", help="Validate inputs/render/leak gate; write nothing.")
    mode.add_argument("--dry-run", action="store_true", help="Print the Markdown render; write nothing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if os.environ.get("FPAI_FINANCIAL_HUB_DISABLE") == "1":
        print("financial_hub=disabled")
        return 0
    if args.daily_cost_cap_usd <= 0:
        print("error=daily cost cap must be positive", file=sys.stderr)
        return 2

    defaults = default_source_config()
    config = SourceConfig(
        treasury_path=args.treasury_source or defaults.treasury_path,
        cost_ledger_path=args.cost_ledger or defaults.cost_ledger_path,
        sol_live_path=args.sol_live or defaults.sol_live_path,
        zen_accounting_path=args.zen_accounting or defaults.zen_accounting_path,
    )
    try:
        state, markdown = refresh(
            config,
            markdown_path=args.output,
            state_path=args.state_output,
            now=args.now,
            write=not (args.check_only or args.dry_run),
            daily_cost_cap_usd=args.daily_cost_cap_usd,
        )
    except LeakDetected as exc:
        categories = sorted({finding.category for finding in exc.findings})
        print("leak_check=fail", file=sys.stderr)
        print("categories=" + ",".join(categories), file=sys.stderr)
        return 3

    if args.dry_run:
        print(markdown, end="")
        return 0
    if args.check_only:
        attention = state["attention"]
        print("leak_check=pass")
        print(f"attention_count={attention['count']}")
        print(f"genuine_decision_count={attention['genuine_decision_count']}")
        print("delivery_status=not_sent")
        for source in state["sources"]:
            print(f"source={source['source_id']} status={source['status']}")
        return 0

    print(f"wrote_markdown={args.output}")
    print(f"wrote_state={args.state_output}")
    print("leak_check=pass")
    print("delivery_status=not_sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
