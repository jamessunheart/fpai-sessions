#!/usr/bin/env python3
"""
Financial Hub Rung 4

Secret-free, read-only financial pane with anomaly alerts.
"""

from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates


SERVICE_VERSION = "0.4.0"
DAILY_COST_CAP_USD = float(os.getenv("FINANCIAL_HUB_DAILY_COST_CAP_USD", "20"))

BASE_DIR = Path(__file__).resolve().parent
SERVICE_DIR = BASE_DIR.parent
REPO_ROOT = SERVICE_DIR.parent.parent
VAR_DIR = REPO_ROOT / "var" / "financial-hub"
SNAPSHOT_DIR = VAR_DIR / "snapshots"
ALERT_DIR = VAR_DIR / "alerts"
CANONICAL_SNAPSHOT_PATH = VAR_DIR / "financial_snapshot.json"
ATTENTION_FEED_PATH = ALERT_DIR / "attention-feed.json"
ATTENTION_FEED_MD_PATH = ALERT_DIR / "attention-feed.md"
MANUAL_INPUT_PATH = VAR_DIR / "manual_financial_inputs.json"

CORE_TREASURY_PATH = REPO_ROOT / "core" / "STATE" / "TREASURY.json"
USAGE_PATH = REPO_ROOT / "SERVICES" / "api-gateway" / "data" / "usage.json"
TREASURY_DATA_CANDIDATES = [
    REPO_ROOT / "treasury_data.json",
    REPO_ROOT / "white-rock-landing" / "treasury_data.json",
]

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app = FastAPI(title="Financial Hub Rung 4", version=SERVICE_VERSION)


@dataclass
class SourceRecord:
    source_id: str
    label: str
    path_or_url: str
    last_observed_at: Optional[str]
    freshness_seconds: Optional[int]
    status: str
    confidence: str
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "label": self.label,
            "path_or_url": self.path_or_url,
            "last_observed_at": self.last_observed_at,
            "freshness_seconds": self.freshness_seconds,
            "status": self.status,
            "confidence": self.confidence,
            "notes": self.notes,
        }


class ReadOnlyFinancialSource:
    source_id: str
    source_type: str

    def read_snapshot(self) -> Dict[str, Any]:
        raise NotImplementedError

    def health(self) -> Dict[str, Any]:
        raise NotImplementedError


class JsonFileSource(ReadOnlyFinancialSource):
    source_type = "json_file"

    def __init__(self, source_id: str, label: str, path: Path):
        self.source_id = source_id
        self.label = label
        self.path = path
        self._error: Optional[str] = None

    def read_snapshot(self) -> Dict[str, Any]:
        self._error = None
        if not self.path.exists():
            return {}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive path
            self._error = str(exc)
            return {}

    def health(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {
                "exists": False,
                "record": SourceRecord(
                    source_id=self.source_id,
                    label=self.label,
                    path_or_url=str(self.path.relative_to(REPO_ROOT)),
                    last_observed_at=None,
                    freshness_seconds=None,
                    status="missing",
                    confidence="unavailable",
                    notes="Source file not present.",
                ).to_dict(),
            }

        observed = datetime.fromtimestamp(self.path.stat().st_mtime, tz=timezone.utc)
        age = max(0, int((now_utc() - observed).total_seconds()))
        status = freshness_status(age)
        confidence = "medium" if status in {"fresh", "aging"} else "low"
        notes = "Read-only local JSON source."
        if self._error:
            status = "error"
            confidence = "unavailable"
            notes = f"JSON parse failed: {self._error}"

        return {
            "exists": True,
            "record": SourceRecord(
                source_id=self.source_id,
                label=self.label,
                path_or_url=str(self.path.relative_to(REPO_ROOT)),
                last_observed_at=observed.isoformat().replace("+00:00", "Z"),
                freshness_seconds=age,
                status=status,
                confidence=confidence,
                notes=notes,
            ).to_dict(),
        }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat().replace("+00:00", "Z")


def freshness_status(age_seconds: Optional[int]) -> str:
    if age_seconds is None:
        return "missing"
    if age_seconds <= 30 * 60:
        return "fresh"
    if age_seconds <= 60 * 60:
        return "aging"
    if age_seconds <= 6 * 60 * 60:
        return "stale"
    return "critical_stale"


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace("$", "").replace(",", "").replace("%", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def money_or_none(*values: Any) -> Optional[float]:
    for value in values:
        parsed = safe_float(value)
        if parsed is not None:
            return parsed
    return None


def parse_timestamp(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    cleaned = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_json_source(source_id: str, label: str, path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    source = JsonFileSource(source_id, label, path)
    data = source.read_snapshot()
    return data, source.health()["record"]


def first_existing_treasury_data() -> Optional[Path]:
    for path in TREASURY_DATA_CANDIDATES:
        if path.exists():
            return path
    return None


def collect_sources() -> Tuple[Dict[str, Any], Dict[str, Any], Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    sources: List[Dict[str, Any]] = []

    manual_inputs, manual_record = load_json_source(
        "manual-financial-inputs", "Manual Financial Inputs", MANUAL_INPUT_PATH
    )
    if manual_record["status"] != "missing":
        manual_record["notes"] = "Human-maintained redacted cash and burn input."
    sources.append(manual_record)

    core_treasury, core_record = load_json_source(
        "core-state-treasury", "Core Treasury State", CORE_TREASURY_PATH
    )
    sources.append(core_record)

    treasury_path = first_existing_treasury_data()
    treasury_data: Optional[Dict[str, Any]] = None
    if treasury_path:
        treasury_data, treasury_record = load_json_source(
            "treasury-data", "Treasury Position Snapshot", treasury_path
        )
        sources.append(treasury_record)
    else:
        sources.append(
            SourceRecord(
                source_id="treasury-data",
                label="Treasury Position Snapshot",
                path_or_url="treasury_data.json",
                last_observed_at=None,
                freshness_seconds=None,
                status="missing",
                confidence="unavailable",
                notes="No treasury_data.json candidate found.",
            ).to_dict()
        )

    usage_events, usage_record = load_json_source(
        "api-gateway-usage", "API Gateway Usage Costs", USAGE_PATH
    )
    sources.append(usage_record)
    if not isinstance(usage_events, list):
        usage_events = []

    return manual_inputs, core_treasury, treasury_data, usage_events, sources


def derive_liquidity(manual_inputs: Dict[str, Any], core_treasury: Dict[str, Any]) -> Tuple[Optional[float], str]:
    manual_liquidity = money_or_none(
        manual_inputs.get("liquidity_usd"),
        manual_inputs.get("cash_on_hand_usd"),
        manual_inputs.get("cash_on_hand"),
    )
    if manual_liquidity is not None:
        return manual_liquidity, "high"

    cash = money_or_none(core_treasury.get("cash_on_hand"), core_treasury.get("cash"))
    stripe = money_or_none(core_treasury.get("stripe_balance"))
    if cash is None and stripe is None:
        return None, "unavailable"
    return (cash or 0) + (stripe or 0), "medium"


def derive_monthly_burn(manual_inputs: Dict[str, Any], core_treasury: Dict[str, Any], daily_cost: float) -> Tuple[Optional[float], str]:
    manual_burn = money_or_none(manual_inputs.get("monthly_burn_usd"), manual_inputs.get("monthly_burn"))
    if manual_burn is not None:
        return manual_burn, "high"

    monthly_burn = money_or_none(core_treasury.get("monthly_burn"))
    if monthly_burn is not None:
        return monthly_burn, "medium"
    if daily_cost > 0:
        return daily_cost * 30.4375, "low"
    return None, "unavailable"


def derive_portfolio_value(core_treasury: Dict[str, Any], treasury_data: Optional[Dict[str, Any]]) -> Tuple[Optional[float], str]:
    if treasury_data:
        capital = money_or_none(
            treasury_data.get("summary", {}).get("total", {}).get("capital"),
            treasury_data.get("summary", {}).get("total_capital"),
        )
        if capital is not None:
            return capital, "medium"
    tvl = money_or_none(core_treasury.get("tvl"))
    if tvl is not None:
        return tvl, "medium"
    return None, "unavailable"


def derive_pnl(core_treasury: Dict[str, Any], treasury_data: Optional[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float], str]:
    if treasury_data:
        total = treasury_data.get("summary", {}).get("total", {})
        pnl = money_or_none(total.get("pnl"), total.get("pnl_usd"))
        pnl_pct = money_or_none(total.get("pnl_percent"))
        if pnl is not None or pnl_pct is not None:
            return pnl, pnl_pct, "medium"

    pnl = money_or_none(core_treasury.get("pnl_24h"))
    pnl_pct = money_or_none(core_treasury.get("pnl_percent"))
    if pnl is not None or pnl_pct is not None:
        return pnl, pnl_pct, "medium"
    return None, None, "unavailable"


def usage_costs_today(usage_events: Iterable[Dict[str, Any]], current_time: Optional[datetime] = None) -> Tuple[float, int]:
    current_time = current_time or now_utc()
    total = 0.0
    count = 0
    for event in usage_events:
        timestamp = parse_timestamp(event.get("timestamp"))
        if not timestamp or timestamp.date() != current_time.date():
            continue
        cost = safe_float(event.get("cost_usd")) or 0.0
        total += cost
        count += 1
    return round(total, 6), count


def nearest_liquidation(treasury_data: Optional[Dict[str, Any]]) -> Tuple[Dict[str, Any], int]:
    empty = {
        "asset": None,
        "distance_percent": None,
        "distance_usd": None,
        "liquidation_price": None,
        "margin_at_risk_usd": None,
        "severity": "none",
    }
    if not treasury_data:
        return empty, 0

    report = treasury_data.get("liquidation_report", [])
    if not isinstance(report, list) or not report:
        leveraged = treasury_data.get("leveraged_positions", [])
        return empty, len(leveraged) if isinstance(leveraged, list) else 0

    best: Optional[Dict[str, Any]] = None
    best_distance: Optional[float] = None
    for position in report:
        distance = safe_float(position.get("distance_percent"))
        if distance is None:
            continue
        if best is None or distance < (best_distance if best_distance is not None else float("inf")):
            best = position
            best_distance = distance

    if best is None or best_distance is None:
        return empty, len(report)

    severity = "info"
    if best_distance < 15:
        severity = "critical"
    elif best_distance < 30:
        severity = "warning"
    if best_distance < 0:
        severity = "critical"

    return {
        "asset": best.get("asset"),
        "distance_percent": best_distance,
        "distance_usd": money_or_none(best.get("distance_usd")),
        "liquidation_price": money_or_none(best.get("liquidation_price")),
        "margin_at_risk_usd": money_or_none(best.get("margin_at_risk")),
        "severity": severity,
    }, len(report)


def load_historical_snapshots() -> List[Dict[str, Any]]:
    latest = SNAPSHOT_DIR / "latest.json"
    if not latest.exists():
        return []

    history: List[Dict[str, Any]] = []
    for path in sorted(SNAPSHOT_DIR.glob("*.jsonl"))[-14:]:
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    history.append(json.loads(line))
        except Exception:
            continue
    return history[-200:]


def add_alert(
    alerts: List[Dict[str, Any]],
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    observed_value: Optional[float],
    threshold: Optional[float],
    source_ids: List[str],
) -> None:
    source_suffix = "-".join(source_ids) if source_ids else "global"
    alerts.append(
        {
            "id": f"alert-{alert_type}-{severity}-{source_suffix}",
            "type": alert_type,
            "severity": severity,
            "title": title,
            "message": message,
            "observed_value": observed_value,
            "threshold": threshold,
            "source_ids": source_ids,
            "detected_at": iso_now(),
            "read_only": True,
        }
    )


def build_alerts(
    summary: Dict[str, Any],
    risk: Dict[str, Any],
    sources: List[Dict[str, Any]],
    history: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    history = history if history is not None else load_historical_snapshots()
    sources_by_id = {source.get("source_id"): source for source in sources}
    manual_source = sources_by_id.get("manual-financial-inputs", {})

    current_burn = summary.get("monthly_burn_usd")
    manual_age = manual_source.get("freshness_seconds")
    if not isinstance(current_burn, (int, float)):
        add_alert(
            alerts,
            "manual_input",
            "warning",
            "Monthly burn input is missing",
            "Add monthly_burn_usd to var/financial-hub/manual_financial_inputs.json to calculate runway.",
            None,
            None,
            ["manual-financial-inputs"],
        )
    elif isinstance(manual_age, int) and manual_age > 30 * 24 * 60 * 60:
        add_alert(
            alerts,
            "manual_input",
            "critical",
            "Manual financial input is very stale",
            f"Manual burn/cash input is {manual_age // 86400} days old.",
            manual_age,
            30 * 24 * 60 * 60,
            ["manual-financial-inputs"],
        )
    elif isinstance(manual_age, int) and manual_age > 7 * 24 * 60 * 60:
        add_alert(
            alerts,
            "manual_input",
            "warning",
            "Manual financial input is stale",
            f"Manual burn/cash input is {manual_age // 86400} days old.",
            manual_age,
            7 * 24 * 60 * 60,
            ["manual-financial-inputs"],
        )

    baseline_values = [
        item.get("summary", {}).get("monthly_burn_usd")
        for item in history
        if isinstance(item.get("summary", {}).get("monthly_burn_usd"), (int, float))
    ]
    if isinstance(current_burn, (int, float)):
        if len(baseline_values) < 3:
            add_alert(
                alerts,
                "burn_spike",
                "info",
                "Burn baseline is still forming",
                "Current burn is available, but there is not enough history for a 7-day median.",
                current_burn,
                None,
                ["core-state-treasury"],
            )
        else:
            baseline = statistics.median(baseline_values[-7:])
            increase = current_burn - baseline
            if baseline > 0 and current_burn >= baseline * 1.5 and increase >= 500:
                add_alert(
                    alerts,
                    "burn_spike",
                    "critical",
                    "Monthly burn spiked",
                    f"Monthly burn is ${current_burn:,.2f}, above the ${baseline:,.2f} recent median.",
                    current_burn,
                    baseline * 1.5,
                    ["core-state-treasury"],
                )
            elif baseline > 0 and current_burn >= baseline * 1.25 and increase >= 100:
                add_alert(
                    alerts,
                    "burn_spike",
                    "warning",
                    "Monthly burn is elevated",
                    f"Monthly burn is ${current_burn:,.2f}, above the ${baseline:,.2f} recent median.",
                    current_burn,
                    baseline * 1.25,
                    ["core-state-treasury"],
                )

    nearest = risk.get("nearest_liquidation", {})
    distance = nearest.get("distance_percent")
    if isinstance(distance, (int, float)):
        if distance < 0:
            add_alert(
                alerts,
                "liquidation_distance",
                "critical",
                "Liquidation distance is negative",
                f"{nearest.get('asset') or 'A position'} reports {distance:.2f}% distance to liquidation.",
                distance,
                0,
                ["treasury-data"],
            )
        elif distance < 15:
            add_alert(
                alerts,
                "liquidation_distance",
                "critical",
                "Position is close to liquidation",
                f"{nearest.get('asset') or 'A position'} is {distance:.2f}% from liquidation.",
                distance,
                15,
                ["treasury-data"],
            )
        elif distance < 30:
            add_alert(
                alerts,
                "liquidation_distance",
                "warning",
                "Position is within liquidation warning range",
                f"{nearest.get('asset') or 'A position'} is {distance:.2f}% from liquidation.",
                distance,
                30,
                ["treasury-data"],
            )

    for source in sources:
        age = source.get("freshness_seconds")
        source_id = source.get("source_id", "unknown-source")
        if source_id == "manual-financial-inputs":
            continue
        label = source.get("label", source_id)
        if isinstance(age, int) and age > 6 * 60 * 60:
            add_alert(
                alerts,
                "stale_snapshot",
                "critical",
                "Money source is critically stale",
                f"{label} has not changed in {age // 3600} hours.",
                age,
                6 * 60 * 60,
                [source_id],
            )
        elif isinstance(age, int) and age > 60 * 60:
            add_alert(
                alerts,
                "stale_snapshot",
                "warning",
                "Money source is stale",
                f"{label} is older than 60 minutes.",
                age,
                60 * 60,
                [source_id],
            )
        elif isinstance(age, int) and age > 30 * 60:
            add_alert(
                alerts,
                "stale_snapshot",
                "info",
                "Money source is aging",
                f"{label} is older than 30 minutes.",
                age,
                30 * 60,
                [source_id],
            )

    daily_cost = summary.get("daily_cost_usd") or 0
    if daily_cost >= DAILY_COST_CAP_USD:
        add_alert(
            alerts,
            "cost_cap",
            "critical",
            "Daily cost cap reached",
            f"Estimated cost is ${daily_cost:,.2f} of the ${DAILY_COST_CAP_USD:,.2f} daily cap.",
            daily_cost,
            DAILY_COST_CAP_USD,
            ["api-gateway-usage"],
        )
    elif daily_cost >= DAILY_COST_CAP_USD * 0.8:
        add_alert(
            alerts,
            "cost_cap",
            "warning",
            "Daily cost is near the cap",
            f"Estimated cost is ${daily_cost:,.2f} of the ${DAILY_COST_CAP_USD:,.2f} daily cap.",
            daily_cost,
            DAILY_COST_CAP_USD * 0.8,
            ["api-gateway-usage"],
        )
    else:
        add_alert(
            alerts,
            "cost_cap",
            "info",
            "Daily cost is under the cap",
            f"Estimated cost is ${daily_cost:,.2f} of the ${DAILY_COST_CAP_USD:,.2f} daily cap.",
            daily_cost,
            DAILY_COST_CAP_USD * 0.8,
            ["api-gateway-usage"],
        )

    return alerts


def alert_rank(severity: str) -> int:
    return {"critical": 3, "warning": 2, "info": 1}.get(severity, 0)


def alert_type_rank(alert_type: str) -> int:
    return {
        "liquidation_distance": 4,
        "cost_cap": 3,
        "burn_spike": 2,
        "manual_input": 2,
        "stale_snapshot": 1,
    }.get(alert_type, 0)


def top_alert_state(alerts: List[Dict[str, Any]]) -> str:
    if any(alert.get("severity") == "critical" for alert in alerts):
        return "critical"
    if any(alert.get("severity") == "warning" for alert in alerts):
        return "warning"
    if any(alert.get("severity") == "info" for alert in alerts):
        return "info"
    return "clear"


def build_canonical_financial_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    summary = snapshot["summary"]
    risk = snapshot["risk"]
    nearest = risk["nearest_liquidation"]
    alerts = snapshot["alerts"]
    warning_alerts = [alert for alert in alerts if alert.get("severity") in {"warning", "critical"}]
    missing_fields = [
        key
        for key in [
            "liquidity_usd",
            "monthly_burn_usd",
            "daily_burn_usd",
            "runway_days",
            "portfolio_value_usd",
            "pnl_usd",
            "pnl_percent",
            "daily_cost_usd",
        ]
        if summary.get(key) is None
    ]
    freshest_source = min(
        (source for source in snapshot["sources"] if isinstance(source.get("freshness_seconds"), int)),
        key=lambda source: source["freshness_seconds"],
        default=None,
    )
    stalest_source = max(
        (source for source in snapshot["sources"] if isinstance(source.get("freshness_seconds"), int)),
        key=lambda source: source["freshness_seconds"],
        default=None,
    )

    return {
        "schema": "financial_snapshot.v1",
        "generated_at": snapshot["generated_at"],
        "currency": snapshot["currency"],
        "read_only": True,
        "status": top_alert_state(alerts),
        "liquidity_usd": summary["liquidity_usd"],
        "cash_on_hand_usd": summary["liquidity_usd"],
        "portfolio_value_usd": summary["portfolio_value_usd"],
        "total_capital_usd": summary["total_capital_usd"],
        "monthly_burn_usd": summary["monthly_burn_usd"],
        "daily_burn_usd": summary["daily_burn_usd"],
        "runway_days": summary["runway_days"],
        "pnl_usd": summary["pnl_usd"],
        "pnl_percent": summary["pnl_percent"],
        "daily_cost_usd": summary["daily_cost_usd"],
        "daily_cost_cap_usd": summary["daily_cost_cap_usd"],
        "nearest_liquidation": {
            "asset": nearest.get("asset"),
            "distance_percent": nearest.get("distance_percent"),
            "distance_usd": nearest.get("distance_usd"),
            "liquidation_price": nearest.get("liquidation_price"),
            "margin_at_risk_usd": nearest.get("margin_at_risk_usd"),
            "severity": nearest.get("severity"),
        },
        "alert_counts": {
            "critical": sum(1 for alert in alerts if alert.get("severity") == "critical"),
            "warning": sum(1 for alert in alerts if alert.get("severity") == "warning"),
            "info": sum(1 for alert in alerts if alert.get("severity") == "info"),
            "attention": len(warning_alerts),
        },
        "attention_alert_ids": [
            alert["id"]
            for alert in sorted(
                warning_alerts,
                key=lambda item: (alert_rank(item["severity"]), alert_type_rank(item["type"])),
                reverse=True,
            )
        ],
        "missing_fields": missing_fields,
        "confidence": snapshot["confidence"],
        "source_freshness": {
            "freshest_source_id": freshest_source.get("source_id") if freshest_source else None,
            "freshest_age_seconds": freshest_source.get("freshness_seconds") if freshest_source else None,
            "stalest_source_id": stalest_source.get("source_id") if stalest_source else None,
            "stalest_age_seconds": stalest_source.get("freshness_seconds") if stalest_source else None,
        },
        "paid_polling_frozen": snapshot["paid_polling_frozen"],
    }


def build_attention_feed(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    attention_alerts = sorted(
        [alert for alert in snapshot["alerts"] if alert.get("severity") in {"warning", "critical"}],
        key=lambda item: (alert_rank(item["severity"]), alert_type_rank(item["type"])),
        reverse=True,
    )
    items = [
        {
            "id": alert["id"],
            "severity": alert["severity"],
            "type": alert["type"],
            "title": alert["title"],
            "message": alert["message"],
            "source_ids": alert["source_ids"],
            "detected_at": alert["detected_at"],
            "delivery_status": "not_sent",
            "suggested_channels": ["daily_brief", "coordination_feed", "telegram"],
            "read_only": True,
        }
        for alert in attention_alerts
    ]
    return {
        "schema": "financial_attention_feed.v1",
        "generated_at": snapshot["generated_at"],
        "status": "attention_required" if items else "clear",
        "delivery": "local_outbox_only",
        "read_only": True,
        "items": items,
        "count": len(items),
    }


def attention_feed_markdown(feed: Dict[str, Any]) -> str:
    lines = [
        "# Financial Attention Feed",
        f"Generated: {feed['generated_at']}",
        f"Status: {feed['status']}",
        "",
    ]
    if not feed["items"]:
        lines.append("No warning or critical financial alerts.")
        return "\n".join(lines) + "\n"

    for item in feed["items"]:
        lines.extend(
            [
                f"## {item['severity'].upper()}: {item['title']}",
                item["message"],
                f"Source IDs: {', '.join(item['source_ids'])}",
                f"Delivery: {item['delivery_status']} ({feed['delivery']})",
                "",
            ]
        )
    return "\n".join(lines)


def write_derived_snapshot(snapshot: Dict[str, Any]) -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ALERT_DIR.mkdir(parents=True, exist_ok=True)
    latest = SNAPSHOT_DIR / "latest.json"
    day_log = SNAPSHOT_DIR / f"{now_utc().date().isoformat()}.jsonl"
    active_alerts = ALERT_DIR / "active.json"
    alert_history = ALERT_DIR / "history.jsonl"

    latest.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    with day_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(snapshot, separators=(",", ":")) + "\n")

    active = {"generated_at": snapshot["generated_at"], "alerts": snapshot["alerts"]}
    active_alerts.write_text(json.dumps(active, indent=2), encoding="utf-8")
    with alert_history.open("a", encoding="utf-8") as handle:
        for alert in snapshot["alerts"]:
            handle.write(json.dumps(alert, separators=(",", ":")) + "\n")

    canonical = build_canonical_financial_snapshot(snapshot)
    CANONICAL_SNAPSHOT_PATH.write_text(json.dumps(canonical, indent=2), encoding="utf-8")

    attention_feed = build_attention_feed(snapshot)
    ATTENTION_FEED_PATH.write_text(json.dumps(attention_feed, indent=2), encoding="utf-8")
    ATTENTION_FEED_MD_PATH.write_text(attention_feed_markdown(attention_feed), encoding="utf-8")


def build_money_pane(write_cache: bool = True) -> Dict[str, Any]:
    manual_inputs, core_treasury, treasury_data, usage_events, sources = collect_sources()
    daily_cost, usage_count = usage_costs_today(usage_events)
    liquidity, liquidity_confidence = derive_liquidity(manual_inputs, core_treasury)
    monthly_burn, burn_confidence = derive_monthly_burn(manual_inputs, core_treasury, daily_cost)
    daily_burn = monthly_burn / 30.4375 if monthly_burn is not None else None
    portfolio_value, portfolio_confidence = derive_portfolio_value(core_treasury, treasury_data)
    pnl_usd, pnl_percent, pnl_confidence = derive_pnl(core_treasury, treasury_data)
    nearest, open_leveraged = nearest_liquidation(treasury_data)

    total_capital = portfolio_value
    runway_days = None
    if liquidity is not None and daily_burn and daily_burn > 0:
        runway_days = liquidity / daily_burn

    summary = {
        "liquidity_usd": liquidity,
        "portfolio_value_usd": portfolio_value,
        "total_capital_usd": total_capital,
        "monthly_burn_usd": monthly_burn,
        "daily_burn_usd": daily_burn,
        "runway_days": runway_days,
        "pnl_usd": pnl_usd,
        "pnl_percent": pnl_percent,
        "daily_cost_usd": daily_cost,
        "daily_cost_cap_usd": DAILY_COST_CAP_USD,
        "usage_events_today": usage_count,
    }
    confidence = {
        "liquidity": liquidity_confidence,
        "burn": burn_confidence,
        "portfolio": portfolio_confidence,
        "pnl": pnl_confidence,
        "daily_cost": "medium" if usage_events else "unavailable",
    }
    risk = {
        "nearest_liquidation": nearest,
        "open_leveraged_positions": open_leveraged,
    }
    alerts = build_alerts(summary, risk, sources)
    paid_polling_frozen = daily_cost >= DAILY_COST_CAP_USD

    snapshot = {
        "generated_at": iso_now(),
        "currency": core_treasury.get("currency", "USD") or "USD",
        "summary": summary,
        "confidence": confidence,
        "risk": risk,
        "alerts": alerts,
        "sources": sources,
        "read_only": True,
        "paid_polling_frozen": paid_polling_frozen,
    }

    if write_cache:
        write_derived_snapshot(snapshot)
    return snapshot


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "service": "financial-hub",
        "version": SERVICE_VERSION,
        "read_only": True,
        "timestamp": iso_now(),
    }


@app.get("/capabilities")
async def capabilities() -> Dict[str, Any]:
    return {
        "service": "financial-hub",
        "rung": 4,
        "capabilities": [
            "money_pane",
            "burn_spike_alerts",
            "liquidation_distance_alerts",
            "stale_snapshot_alerts",
            "daily_cost_cap_alerts",
            "source_freshness",
            "canonical_financial_snapshot",
            "attention_feed_outbox",
            "manual_financial_inputs",
        ],
        "forbidden_capabilities": [
            "trading",
            "rebalancing",
            "credential_storage",
            "fund_transfer",
            "upstream_mutation",
        ],
    }


@app.get("/state")
async def state() -> Dict[str, Any]:
    snapshot = build_money_pane()
    active_alerts = [alert for alert in snapshot["alerts"] if alert["severity"] in {"warning", "critical"}]
    status = "degraded" if active_alerts else "active"
    return {
        "status": status,
        "mode": "read_only",
        "last_snapshot_at": snapshot["generated_at"],
        "active_alerts": len(active_alerts),
        "daily_cost_usd": snapshot["summary"]["daily_cost_usd"],
        "daily_cost_cap_usd": snapshot["summary"]["daily_cost_cap_usd"],
        "paid_polling_frozen": snapshot["paid_polling_frozen"],
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Financial Hub Rung 4"},
    )


@app.get("/api/v1/money-pane")
async def money_pane() -> Dict[str, Any]:
    return build_money_pane()


@app.get("/api/v1/alerts")
async def alerts(
    severity: Optional[str] = Query(None),
    include_resolved: bool = Query(False),
) -> Dict[str, Any]:
    snapshot = build_money_pane()
    active = snapshot["alerts"]
    if severity:
        active = [alert for alert in active if alert["severity"] == severity]
    return {
        "generated_at": snapshot["generated_at"],
        "alerts": active,
        "count": len(active),
        "include_resolved": include_resolved,
    }


@app.get("/api/v1/sources")
async def sources() -> Dict[str, Any]:
    snapshot = build_money_pane()
    return {
        "generated_at": snapshot["generated_at"],
        "sources": snapshot["sources"],
        "count": len(snapshot["sources"]),
    }


@app.get("/api/v1/financial-snapshot")
async def financial_snapshot() -> Dict[str, Any]:
    snapshot = build_money_pane()
    return build_canonical_financial_snapshot(snapshot)


@app.get("/api/v1/attention-feed")
async def attention_feed() -> Dict[str, Any]:
    snapshot = build_money_pane()
    return build_attention_feed(snapshot)


@app.get("/api/v1/manual-input-template")
async def manual_input_template() -> Dict[str, Any]:
    return {
        "path": str(MANUAL_INPUT_PATH.relative_to(REPO_ROOT)),
        "schema": "manual_financial_inputs.v1",
        "instructions": "Create this local file with redacted non-secret values only. The hub reads it but never writes it.",
        "example": {
            "schema": "manual_financial_inputs.v1",
            "updated_at": iso_now(),
            "updated_by": "human",
            "cash_on_hand_usd": None,
            "monthly_burn_usd": None,
            "notes": "No account numbers, credentials, wallet secrets, or payment-provider tokens.",
        },
    }


@app.get("/api/unified-metrics")
async def unified_metrics() -> Dict[str, Any]:
    snapshot = build_money_pane()
    nearest = snapshot["risk"]["nearest_liquidation"]
    return {
        "total_capital": snapshot["summary"]["total_capital_usd"],
        "current_pnl": snapshot["summary"]["pnl_usd"],
        "pnl_percent": snapshot["summary"]["pnl_percent"],
        "monthly_burn": snapshot["summary"]["monthly_burn_usd"],
        "runway_days": snapshot["summary"]["runway_days"],
        "daily_cost": snapshot["summary"]["daily_cost_usd"],
        "daily_cost_cap": snapshot["summary"]["daily_cost_cap_usd"],
        "risk_score": nearest.get("severity", "none"),
        "liquidation_risks": snapshot["risk"]["open_leveraged_positions"],
        "last_updated": snapshot["generated_at"],
    }


@app.get("/api/portfolio")
async def portfolio() -> Dict[str, Any]:
    _, _, treasury_data, _, _ = collect_sources()
    treasury_data = treasury_data or {}
    return {
        "spot_positions": treasury_data.get("spot_positions", []),
        "leveraged_positions": treasury_data.get("leveraged_positions", []),
        "summary": treasury_data.get("summary", {}),
        "liquidation_report": treasury_data.get("liquidation_report", []),
        "read_only": True,
    }


@app.get("/api/alerts")
async def legacy_alerts() -> Dict[str, Any]:
    snapshot = build_money_pane()
    return {
        "generated_at": snapshot["generated_at"],
        "alerts": snapshot["alerts"],
        "count": len(snapshot["alerts"]),
        "include_resolved": False,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8100)
