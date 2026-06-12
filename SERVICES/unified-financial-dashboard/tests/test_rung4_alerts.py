import importlib.util
import sys
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app" / "main.py"
SPEC = importlib.util.spec_from_file_location("financial_hub_main", APP_PATH)
main = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = main
SPEC.loader.exec_module(main)


def test_burn_spike_warning_and_critical_thresholds():
    history = [{"summary": {"monthly_burn_usd": 1000}} for _ in range(7)]
    sources = []
    risk = {"nearest_liquidation": {"distance_percent": None}}

    warning = main.build_alerts(
        {"monthly_burn_usd": 1300, "daily_cost_usd": 0},
        risk,
        sources,
        history=history,
    )
    critical = main.build_alerts(
        {"monthly_burn_usd": 1600, "daily_cost_usd": 0},
        risk,
        sources,
        history=history,
    )

    assert any(alert["type"] == "burn_spike" and alert["severity"] == "warning" for alert in warning)
    assert any(alert["type"] == "burn_spike" and alert["severity"] == "critical" for alert in critical)


def test_liquidation_distance_alert_thresholds():
    sources = []
    history = [{"summary": {"monthly_burn_usd": 1000}} for _ in range(7)]

    warning = main.build_alerts(
        {"monthly_burn_usd": 1000, "daily_cost_usd": 0},
        {"nearest_liquidation": {"asset": "BTC", "distance_percent": 25}},
        sources,
        history=history,
    )
    critical = main.build_alerts(
        {"monthly_burn_usd": 1000, "daily_cost_usd": 0},
        {"nearest_liquidation": {"asset": "BTC", "distance_percent": 10}},
        sources,
        history=history,
    )

    assert any(alert["type"] == "liquidation_distance" and alert["severity"] == "warning" for alert in warning)
    assert any(alert["type"] == "liquidation_distance" and alert["severity"] == "critical" for alert in critical)


def test_stale_snapshot_alert_thresholds():
    history = [{"summary": {"monthly_burn_usd": 1000}} for _ in range(7)]
    risk = {"nearest_liquidation": {"distance_percent": None}}

    alerts = main.build_alerts(
        {"monthly_burn_usd": 1000, "daily_cost_usd": 0},
        risk,
        [
            {
                "source_id": "core-state-treasury",
                "label": "Core Treasury State",
                "freshness_seconds": 7 * 60 * 60,
            }
        ],
        history=history,
    )

    assert any(alert["type"] == "stale_snapshot" and alert["severity"] == "critical" for alert in alerts)


def test_cost_cap_alert_thresholds():
    history = [{"summary": {"monthly_burn_usd": 1000}} for _ in range(7)]
    risk = {"nearest_liquidation": {"distance_percent": None}}

    warning = main.build_alerts(
        {"monthly_burn_usd": 1000, "daily_cost_usd": 16},
        risk,
        [],
        history=history,
    )
    critical = main.build_alerts(
        {"monthly_burn_usd": 1000, "daily_cost_usd": 20},
        risk,
        [],
        history=history,
    )

    assert any(alert["type"] == "cost_cap" and alert["severity"] == "warning" for alert in warning)
    assert any(alert["type"] == "cost_cap" and alert["severity"] == "critical" for alert in critical)


def test_today_cost_ignores_old_usage_events():
    current_time = main.datetime(2026, 6, 12, tzinfo=main.timezone.utc)
    cost, count = main.usage_costs_today(
        [
            {"timestamp": "2026-06-12T01:00:00Z", "cost_usd": 1.25},
            {"timestamp": "2026-06-11T23:59:00Z", "cost_usd": 100},
        ],
        current_time=current_time,
    )

    assert cost == 1.25
    assert count == 1


def test_manual_inputs_override_cash_and_burn():
    liquidity, liquidity_confidence = main.derive_liquidity(
        {"cash_on_hand_usd": 50000},
        {"cash": 120000},
    )
    burn, burn_confidence = main.derive_monthly_burn(
        {"monthly_burn_usd": 30000},
        {"monthly_burn": 1000},
        daily_cost=0,
    )

    assert liquidity == 50000
    assert liquidity_confidence == "high"
    assert burn == 30000
    assert burn_confidence == "high"


def test_missing_monthly_burn_creates_manual_input_alert():
    alerts = main.build_alerts(
        {"monthly_burn_usd": None, "daily_cost_usd": 0},
        {"nearest_liquidation": {"distance_percent": None}},
        [
            {
                "source_id": "manual-financial-inputs",
                "label": "Manual Financial Inputs",
                "status": "missing",
                "freshness_seconds": None,
            }
        ],
        history=[],
    )

    assert any(alert["type"] == "manual_input" and alert["severity"] == "warning" for alert in alerts)


def test_canonical_financial_snapshot_distills_money_state():
    snapshot = {
        "generated_at": "2026-06-12T12:00:00Z",
        "currency": "USD",
        "summary": {
            "liquidity_usd": 120000,
            "portfolio_value_usd": 373261,
            "total_capital_usd": 373261,
            "monthly_burn_usd": None,
            "daily_burn_usd": None,
            "runway_days": None,
            "pnl_usd": -31041,
            "pnl_percent": -8.32,
            "daily_cost_usd": 0,
            "daily_cost_cap_usd": 20,
        },
        "confidence": {"liquidity": "medium", "burn": "unavailable"},
        "risk": {
            "nearest_liquidation": {
                "asset": "BTC",
                "distance_percent": 24.42,
                "distance_usd": 23441,
                "liquidation_price": 72559,
                "margin_at_risk_usd": 10000,
                "severity": "warning",
            }
        },
        "alerts": [
            {
                "id": "alert-liquidation_distance-warning",
                "severity": "warning",
                "type": "liquidation_distance",
            }
        ],
        "sources": [
            {"source_id": "core-state-treasury", "freshness_seconds": 60},
            {"source_id": "treasury-data", "freshness_seconds": 120},
        ],
        "paid_polling_frozen": False,
    }

    canonical = main.build_canonical_financial_snapshot(snapshot)

    assert canonical["schema"] == "financial_snapshot.v1"
    assert canonical["read_only"] is True
    assert canonical["status"] == "warning"
    assert canonical["cash_on_hand_usd"] == 120000
    assert canonical["nearest_liquidation"]["asset"] == "BTC"
    assert canonical["alert_counts"]["attention"] == 1
    assert "monthly_burn_usd" in canonical["missing_fields"]


def test_attention_feed_only_contains_warning_and_critical_alerts():
    snapshot = {
        "generated_at": "2026-06-12T12:00:00Z",
        "alerts": [
            {
                "id": "alert-cost_cap-info",
                "severity": "info",
                "type": "cost_cap",
                "title": "Daily cost is under the cap",
                "message": "Cost is fine.",
                "source_ids": ["api-gateway-usage"],
                "detected_at": "2026-06-12T12:00:00Z",
            },
            {
                "id": "alert-liquidation_distance-warning",
                "severity": "warning",
                "type": "liquidation_distance",
                "title": "Position is within liquidation warning range",
                "message": "BTC is 24.42% from liquidation.",
                "source_ids": ["treasury-data"],
                "detected_at": "2026-06-12T12:00:00Z",
            },
        ],
    }

    feed = main.build_attention_feed(snapshot)
    markdown = main.attention_feed_markdown(feed)

    assert feed["schema"] == "financial_attention_feed.v1"
    assert feed["status"] == "attention_required"
    assert feed["count"] == 1
    assert feed["items"][0]["delivery_status"] == "not_sent"
    assert feed["items"][0]["read_only"] is True
    assert "BTC is 24.42% from liquidation." in markdown
