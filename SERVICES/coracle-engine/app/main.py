"""
Coracle Prediction Engine - Main Application
=============================================
High-frequency quantitative engine for probability-weighted trading contracts.

Base URL: http://localhost:8650
"""
import time
from contextlib import asynccontextmanager
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

import os
import logging
import httpx

from app.config import get_settings, SIGNAL_TIERS
from app.models import HealthResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# APPLICATION SETUP
# ============================================================================

settings = get_settings()
START_TIME = time.time()

# Telegram config from environment (token must not live in source)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1759822075")
ALERTS_ENABLED = os.environ.get("CORACLE_ALERTS_ENABLED", "true").lower() == "true"

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info(f"🔮 Coracle Prediction Engine v1.0.0 starting...")
    logger.info(f"   Port: {settings.port}")
    logger.info(f"   WhaleTrack URL: {settings.whaletrack_url}")
    logger.info(f"   Tracked Assets: {', '.join(settings.tracked_assets)}")
    logger.info(f"   Signal Tiers: {len(SIGNAL_TIERS)}")
    
    # Initialize components (lazy import to avoid circular dependencies)
    from engine.ingestor import SignalIngestor
    from engine.processor import SignalProcessor
    from engine.sacred_gate import SacredGate
    from engine.confluence import ConfluenceEngine
    from engine.contract_generator import ContractGenerator
    from engine.alerter import configure_alerter, get_alerter
    from engine.monitor import get_monitor
    
    app.state.ingestor = SignalIngestor(settings)
    app.state.processor = SignalProcessor(settings)
    app.state.sacred_gate = SacredGate(settings)
    app.state.confluence = ConfluenceEngine(settings)
    app.state.contract_generator = ContractGenerator(settings)
    
    # Configure Telegram alerter
    if ALERTS_ENABLED and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        alerter = configure_alerter(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, enabled=True)
        app.state.alerter = alerter
        logger.info(f"📱 Telegram alerts ENABLED (chat: {TELEGRAM_CHAT_ID})")
        
        # Send startup notification
        await alerter.send_startup_message()
        
        # Start the background monitor
        monitor = get_monitor()
        monitor.start()
        app.state.monitor = monitor
        logger.info(f"👁️ Contract Monitor started (30s interval)")
        
        # Start hourly oracle reports
        from engine.hourly_oracle import get_hourly_oracle
        oracle = get_hourly_oracle()
        oracle.start(alerter)
        app.state.hourly_oracle = oracle
        logger.info(f"⏰ Hourly Oracle started (reports on the hour)")
        
        # Start prediction tracker for learning loop
        from engine.prediction_tracker import get_prediction_tracker
        tracker = get_prediction_tracker()
        tracker.start()
        app.state.prediction_tracker = tracker
        logger.info(f"📈 Prediction Tracker started (learning loop active)")
        
        # Start locked prediction tracker
        from engine.locked_predictions import get_locked_tracker
        locked_tracker = get_locked_tracker()
        locked_tracker.start()
        app.state.locked_tracker = locked_tracker
        logger.info(f"🔒 Locked Prediction Tracker started")
    else:
        logger.info(f"📱 Telegram alerts DISABLED")
        app.state.alerter = None
        app.state.monitor = None
        app.state.hourly_oracle = None
    
    logger.info(f"✅ Coracle Engine initialized successfully")
    
    yield
    
    # Shutdown
    logger.info(f"🔮 Coracle Prediction Engine shutting down...")
    if app.state.monitor:
        app.state.monitor.stop()
    if getattr(app.state, 'hourly_oracle', None):
        app.state.hourly_oracle.stop()
    if getattr(app.state, 'prediction_tracker', None):
        app.state.prediction_tracker.stop()
    if getattr(app.state, 'locked_tracker', None):
        app.state.locked_tracker.stop()


app = FastAPI(
    title="Coracle Prediction Engine",
    description="""
    High-frequency quantitative engine that processes multi-timeframe signals 
    to generate probability-weighted trading contracts with adaptive risk management.
    
    ## Features
    - 60+ signal processing across 4 assets (BTC, ETH, XRP, SOL)
    - Sacred Three-Key Gate validation
    - Non-linear confluence engine
    - Dynamic stop-loss with liquidity buffer
    - Multi-target take profit system
    - Real-time WebSocket streaming
    
    ## Signal Tiers
    - **LIQUIDITY** (35%): BAI, SDS, BAR, OBS, LV, LCP
    - **WHALE** (25%): WADI, WC, SD, ENF, SFR
    - **DERIVATIVES** (20%): GEX, OID, PCR, CVD, MP
    - **FUNDING** (15%): FR, FRM, CEFS, FW
    - **ON_CHAIN** (10%): SOPR, MVRV, NUPL, DF
    - **TECHNICAL** (10%): MS, BOS, VRC, HHL
    - **SENTIMENT** (5%): FGI, BTCD
    """,
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# CORE ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(request: Request) -> HealthResponse:
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns service status, data source connectivity, and active contracts.
    """
    uptime = time.time() - START_TIME
    
    # Check data source connectivity
    data_sources = {
        "whaletrack": False,
        "hyperliquid": False,
        "coingecko": False,
    }
    
    # Try to check WhaleTrack
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.whaletrack_url}/health")
            data_sources["whaletrack"] = resp.status_code == 200
    except:
        pass
    
    # Try to check Hyperliquid
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.post(
                settings.hyperliquid_url,
                json={"type": "allMids"}
            )
            data_sources["hyperliquid"] = resp.status_code == 200
    except:
        pass
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime,
        data_sources=data_sources,
        tracked_assets=settings.tracked_assets,
        active_contracts=0  # Will be updated when database is connected
    )


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Coracle Prediction Engine",
        "version": "1.0.0",
        "description": "High-frequency quantitative trading signal processor",
        "documentation": "/docs",
        "health": "/health",
        "endpoints": {
            "analyze": "POST /analyze - Generate trading contract",
            "contracts": "GET /contracts - List active contracts",
            "signals": "GET /signals/{symbol} - Get signal snapshot",
            "stream": "WS /ws/stream - Real-time signal stream"
        },
        "tracked_assets": settings.tracked_assets,
        "signal_tiers": list(SIGNAL_TIERS.keys())
    }


@app.get("/config", tags=["System"])
async def get_config():
    """Get current engine configuration (non-sensitive)."""
    return {
        "tracked_assets": settings.tracked_assets,
        "signal_tiers": SIGNAL_TIERS,
        "volatility_regimes": settings.volatility_regimes,
        "take_profit_config": {
            "tp1": {"size": settings.tp1_size, "rr": settings.tp1_rr},
            "tp2": {"size": settings.tp2_size, "rr": settings.tp2_rr},
            "tp3": {"size": settings.tp3_size, "rr": settings.tp3_rr},
        },
        "sacred_gate_thresholds": {
            "whale": settings.whale_threshold,
            "liquidity": settings.liquidity_threshold
        }
    }


# ============================================================================
# ALERT MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/alerts/status", tags=["Alerts"])
async def get_alert_status(request: Request):
    """Get current alert system status."""
    alerter = getattr(request.app.state, 'alerter', None)
    monitor = getattr(request.app.state, 'monitor', None)
    
    return {
        "alerts_enabled": alerter is not None and alerter.config.enabled,
        "monitor_running": monitor is not None and monitor.running,
        "telegram_chat_id": TELEGRAM_CHAT_ID if alerter else None,
        "check_interval_seconds": monitor.check_interval if monitor else None,
        "cooldown_minutes": alerter.config.cooldown_minutes if alerter else None,
        "last_alerts": dict(alerter.state.last_alert_time) if alerter else {},
        "contracts_sent": len(alerter.state.sent_contract_ids) if alerter else 0
    }


@app.post("/api/alerts/test", tags=["Alerts"])
async def send_test_alert(request: Request):
    """Send a test alert to verify Telegram is working."""
    alerter = getattr(request.app.state, 'alerter', None)
    
    if not alerter:
        return {"success": False, "error": "Alerter not configured"}
    
    success = await alerter.send_startup_message()
    return {"success": success, "message": "Test alert sent" if success else "Failed to send"}


@app.post("/api/alerts/call", tags=["Alerts"])
async def send_test_call(request: Request):
    """
    Make a test phone call to verify Twilio is working.
    This will call James at +1-925-239-7291 with a test message.
    """
    alerter = getattr(request.app.state, 'alerter', None)
    
    if not alerter:
        return {"success": False, "error": "Alerter not configured"}
    
    if not alerter.twilio_client:
        return {"success": False, "error": "Twilio not configured - install twilio package"}
    
    message = """
        This is Coracle, your trading oracle.
        Phone alerts are now active.
        You will receive a call when a high probability trade setup is detected.
        Trade smart.
    """
    
    success = await alerter.call_now(message)
    return {
        "success": success, 
        "message": "Test call initiated" if success else "Call failed",
        "phone": alerter.config.phone_number
    }


@app.get("/api/oracle/predictions", tags=["Oracle"])
async def get_oracle_predictions(request: Request):
    """
    Get current predictions for all tracked tokens.
    Shows direction probabilities, contract setups, and target hit probabilities.
    """
    from engine.hourly_oracle import get_hourly_oracle
    
    oracle = get_hourly_oracle()
    report = await oracle.generate_report()
    
    # Convert dataclass predictions to dicts
    predictions = []
    for pred in report.get("predictions", []):
        c = pred.contract
        predictions.append({
            "symbol": pred.symbol,
            "price": pred.price,
            "probabilities": {
                "long": pred.long_probability,
                "short": pred.short_probability,
                "neutral": pred.neutral_probability
            },
            "contract": {
                "direction": c.direction,
                "direction_probability": c.direction_probability,
                "entry": c.entry,
                "stop_loss": c.stop_loss,
                "risk_percent": c.risk_percent,
                "take_profits": [
                    {"target": c.tp1, "probability": c.tp1_probability, "rr_ratio": c.tp1_rr},
                    {"target": c.tp2, "probability": c.tp2_probability, "rr_ratio": c.tp2_rr},
                    {"target": c.tp3, "probability": c.tp3_probability, "rr_ratio": c.tp3_rr}
                ],
                "expected_value": c.expected_value,
                "grade": c.grade
            },
            "targets": {
                "bullish": {"price": pred.bullish_target, "probability": pred.bullish_probability},
                "bearish": {"price": pred.bearish_target, "probability": pred.bearish_probability}
            },
            "range": {
                "low": pred.range_low,
                "high": pred.range_high
            },
            "signals": pred.key_signals,
            "gate": {"passed": pred.gate_passed, "keys": pred.gate_keys}
        })
    
    # Find best setup
    best = max(predictions, key=lambda p: p["contract"]["expected_value"]) if predictions else None
    
    return {
        "timestamp": report["timestamp"],
        "predictions": predictions,
        "best_setup": best["symbol"] if best else None,
        "market_bias": "LONG" if sum(p["probabilities"]["long"] for p in predictions) > sum(p["probabilities"]["short"] for p in predictions) else "SHORT"
    }


@app.post("/api/oracle/send-now", tags=["Oracle"])
async def send_oracle_now(request: Request):
    """
    Immediately send an oracle report via Telegram.
    Useful for testing or getting an update before the hour.
    """
    alerter = getattr(request.app.state, 'alerter', None)
    oracle = getattr(request.app.state, 'hourly_oracle', None)
    
    if not alerter:
        return {"success": False, "error": "Alerter not configured"}
    
    if not oracle:
        from engine.hourly_oracle import get_hourly_oracle
        oracle = get_hourly_oracle()
    
    success = await oracle.send_hourly_report(alerter)
    return {
        "success": success,
        "message": "Oracle report sent" if success else "Failed to send",
        "next_scheduled": "Top of next hour"
    }


@app.post("/api/alerts/call-example", tags=["Alerts"])
async def send_example_trade_call(request: Request):
    """
    Make a phone call with an example trade setup.
    This demonstrates what a real trade alert call would sound like.
    Uses current BTC price as an example.
    """
    alerter = getattr(request.app.state, 'alerter', None)
    
    if not alerter:
        return {"success": False, "error": "Alerter not configured"}
    
    if not alerter.twilio_client:
        return {"success": False, "error": "Twilio not configured"}
    
    # Get current BTC price for realistic example
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "allMids"}
            )
            if resp.status_code == 200:
                mids = resp.json()
                btc_price = float(mids.get("BTC", 93000))
            else:
                btc_price = 93000
    except:
        btc_price = 93000
    
    # Create realistic trade example
    entry = btc_price
    stop_loss = entry * 0.97  # 3% below
    take_profit = entry * 1.06  # 6% above
    
    success = await alerter.call_with_trade_details(
        symbol="BTC",
        direction="LONG",
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        confluence=0.72
    )
    
    return {
        "success": success,
        "message": "Example trade call initiated" if success else "Call failed",
        "example_trade": {
            "symbol": "BTC",
            "direction": "LONG",
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confluence": "72%"
        }
    }


@app.get("/api/contract-value", tags=["Value"])
async def calculate_contract_value(
    request: Request,
    direction_probability: float = 60,
    tp1_probability: float = 55,
    tp2_probability: float = 35,
    tp3_probability: float = 20,
    risk_percent: float = 3.0,
    position_size: float = 1000,
    historical_accuracy: float = 55
):
    """
    Calculate the mathematical value of a Coracle contract.
    
    This shows the Expected Value (EV) created by entering a trade
    with Coracle's probability-weighted targets.
    
    CORE INSIGHT: If Coracle's predictions are better than random (50%),
    every contract has positive expected value. Value compounds as accuracy improves.
    
    Args:
        direction_probability: Chance direction is correct (0-100)
        tp1_probability: Chance of hitting TP1 (0-100)
        tp2_probability: Chance of hitting TP2 (0-100)
        tp3_probability: Chance of hitting TP3 (0-100)
        risk_percent: Stop loss distance as percent (e.g., 3.0 = 3%)
        position_size: Position size in dollars
        historical_accuracy: Coracle's proven accuracy (50 = random, 60 = 60% accurate)
    """
    from engine.contract_value import ContractValueCalculator
    
    calc = ContractValueCalculator(historical_accuracy=historical_accuracy / 100)
    
    metrics = calc.calculate_contract_value(
        direction_probability=direction_probability,
        tp1_probability=tp1_probability,
        tp2_probability=tp2_probability,
        tp3_probability=tp3_probability,
        risk_percent=risk_percent,
        position_size_usd=position_size
    )
    
    risk_usd = position_size * (risk_percent / 100)
    
    return {
        "inputs": {
            "direction_probability": direction_probability,
            "tp1_probability": tp1_probability,
            "tp2_probability": tp2_probability,
            "tp3_probability": tp3_probability,
            "risk_percent": risk_percent,
            "position_size": position_size,
            "historical_accuracy": historical_accuracy
        },
        "expected_value": {
            "per_dollar_risked": {
                "tp1_only": round(metrics.ev_tp1, 4),
                "tp2_only": round(metrics.ev_tp2, 4),
                "tp3_only": round(metrics.ev_tp3, 4),
                "blended_strategy": round(metrics.ev_blended, 4)
            },
            "per_trade_usd": round(metrics.ev_blended * risk_usd, 2),
            "explanation": f"For every $1 risked, you expect to make ${metrics.ev_blended:+.3f}"
        },
        "edge": {
            "vs_random_50_50": f"{metrics.edge_vs_random * 100:+.1f}%",
            "vs_market": f"{metrics.edge_vs_market * 100:+.1f}%",
            "explanation": f"You have a {metrics.edge_vs_random * 100:.1f}% edge over random chance"
        },
        "optimal_sizing": {
            "kelly_fraction": f"{metrics.kelly_fraction * 100:.1f}%",
            "kelly_half_recommended": f"{metrics.kelly_half * 100:.1f}%",
            "explanation": f"Risk {metrics.kelly_half * 100:.1f}% of bankroll per trade (Half-Kelly)"
        },
        "value_creation": {
            "per_100_risked": f"${metrics.contract_value:.2f}",
            "per_trade": f"${metrics.value_per_trade:.2f}",
            "over_100_trades": f"${metrics.ev_blended * risk_usd * 100:.2f} expected",
            "annual_projection_hourly": f"${metrics.ev_blended * risk_usd * 24 * 365:.2f}"
        },
        "risk_metrics": {
            "sharpe_estimate": round(metrics.sharpe_estimate, 2),
            "five_loss_streak_probability": f"{metrics.max_drawdown_risk * 100:.2f}%",
            "value_confidence": f"{metrics.value_confidence:.0f}%"
        },
        "formulas": {
            "ev": "EV = (Win% × Reward) - (Loss% × Risk)",
            "kelly": "f* = (p(R+1) - 1) / R",
            "edge": "Edge = (Accuracy - 0.50) × 2",
            "value": "Value = EV × Risk × (1 + Edge)"
        }
    }


@app.get("/api/contract-value/live", tags=["Value"])
async def get_live_contract_values(request: Request):
    """
    Get the current value creation metrics for all tracked assets.
    Uses live Coracle predictions to calculate real-time EV.
    """
    from engine.hourly_oracle import get_hourly_oracle
    from engine.contract_value import ContractValueCalculator
    
    oracle = get_hourly_oracle()
    report = await oracle.generate_report()
    
    calc = ContractValueCalculator(historical_accuracy=0.55)  # Start with 55% baseline
    
    values = []
    total_ev = 0
    
    for pred in report.get("predictions", []):
        c = pred.contract
        
        metrics = calc.calculate_contract_value(
            direction_probability=c.direction_probability,
            tp1_probability=c.tp1_probability,
            tp2_probability=c.tp2_probability,
            tp3_probability=c.tp3_probability,
            risk_percent=c.risk_percent,
            position_size_usd=1000  # Standard $1000 position
        )
        
        risk_usd = 1000 * (c.risk_percent / 100)
        trade_value = metrics.ev_blended * risk_usd
        total_ev += trade_value
        
        values.append({
            "symbol": pred.symbol,
            "price": pred.price,
            "direction": c.direction,
            "confidence": f"{c.direction_probability:.0f}%",
            "expected_value": {
                "per_dollar": f"${metrics.ev_blended:+.3f}",
                "per_trade": f"${trade_value:+.2f}",
                "grade": c.grade
            },
            "edge": f"{metrics.edge_vs_random * 100:+.1f}%",
            "kelly": f"{metrics.kelly_half * 100:.1f}%",
            "value_confidence": f"{metrics.value_confidence:.0f}%"
        })
    
    # Sort by expected value
    values.sort(key=lambda x: float(x["expected_value"]["per_trade"].replace("$", "").replace("+", "")), reverse=True)
    
    return {
        "timestamp": report["timestamp"],
        "total_hourly_ev": f"${total_ev:.2f}",
        "daily_projection": f"${total_ev * 24:.2f}",
        "annual_projection": f"${total_ev * 24 * 365:,.2f}",
        "assets": values,
        "best_value": values[0]["symbol"] if values else None,
        "methodology": "EV calculated using blended TP strategy (50% TP1, 30% TP2, 20% TP3)"
    }


@app.get("/api/accuracy", tags=["Learning"])
async def get_accuracy_metrics(
    request: Request,
    symbol: Optional[str] = None,
    timeframe: str = "1h"
):
    """
    Get accuracy metrics for Coracle predictions.
    
    This shows how well Coracle is predicting and where it's strong/weak.
    As accuracy improves, the value of each contract increases.
    
    Args:
        symbol: Filter by symbol (None = all)
        timeframe: Which timeframe to analyze (1h, 4h, 24h)
    """
    from engine.prediction_tracker import get_prediction_tracker
    from dataclasses import asdict
    
    tracker = get_prediction_tracker()
    metrics = tracker.calculate_accuracy(symbol=symbol, timeframe=timeframe)
    
    return {
        "timeframe": timeframe,
        "symbol": symbol or "all",
        "metrics": asdict(metrics),
        "summary": {
            "accuracy": f"{metrics.direction_accuracy:.1f}%",
            "profitable": metrics.avg_pnl_per_prediction > 0,
            "avg_pnl": f"{metrics.avg_pnl_per_prediction:+.2f}%",
            "total_pnl": f"{metrics.total_pnl:+.2f}%",
            "status": "Learning" if metrics.total_predictions < 50 else ("Proven" if metrics.direction_accuracy > 55 else "Needs Work")
        },
        "value_impact": {
            "current_ev_multiplier": metrics.direction_accuracy / 50 if metrics.direction_accuracy > 50 else 0,
            "explanation": f"At {metrics.direction_accuracy:.0f}% accuracy, each trade has {(metrics.direction_accuracy - 50) * 2:.0f}% edge over random"
        }
    }


@app.get("/api/learnings", tags=["Learning"])
async def get_learnings(request: Request):
    """
    Get the reflection report with learnings.
    
    This shows what Coracle has learned about its predictions:
    - Which signals work best
    - Which symbols it predicts best
    - Calibration errors to correct
    - Actions to improve
    """
    from engine.prediction_tracker import get_prediction_tracker
    
    tracker = get_prediction_tracker()
    reflection = tracker.generate_reflection()
    
    return reflection


@app.get("/api/calibration", tags=["Learning"])
async def get_calibration(request: Request):
    """
    Get calibration adjustments based on historical accuracy.
    
    Calibration tells us if Coracle is over-confident or under-confident.
    Returns a multiplier to apply to confidence levels.
    """
    from engine.prediction_tracker import get_prediction_tracker
    
    tracker = get_prediction_tracker()
    calibration = await tracker.get_calibration_adjustment()
    
    return {
        "calibration": calibration,
        "how_to_use": "Multiply confidence by calibration_multiplier for more accurate probabilities",
        "example": f"If predicted 70% confidence, adjusted = 70 × {calibration['confidence_multiplier']:.2f} = {70 * calibration['confidence_multiplier']:.0f}%"
    }


@app.get("/api/predictions/history", tags=["Learning"])
async def get_prediction_history(
    request: Request,
    symbol: Optional[str] = None,
    limit: int = 50
):
    """
    Get recent prediction history with outcomes.
    
    Shows each prediction, what was predicted, and what actually happened.
    """
    from engine.prediction_tracker import get_prediction_tracker
    from dataclasses import asdict
    
    tracker = get_prediction_tracker()
    predictions = list(tracker.predictions.values())
    
    # Filter by symbol
    if symbol:
        predictions = [p for p in predictions if p.symbol == symbol]
    
    # Sort by timestamp (newest first)
    predictions.sort(key=lambda p: p.timestamp, reverse=True)
    
    # Limit
    predictions = predictions[:limit]
    
    return {
        "total_tracked": len(tracker.predictions),
        "showing": len(predictions),
        "predictions": [
            {
                "id": p.id,
                "timestamp": p.timestamp,
                "symbol": p.symbol,
                "direction": p.predicted_direction,
                "confidence": f"{p.direction_probability:.0f}%",
                "entry_price": p.entry_price,
                "grade": p.grade,
                "outcomes": {
                    "1h": {"result": p.outcome_1h, "pnl": f"{p.pnl_1h:+.2f}%" if p.pnl_1h else "pending"},
                    "4h": {"result": p.outcome_4h, "pnl": f"{p.pnl_4h:+.2f}%" if p.pnl_4h else "pending"},
                    "24h": {"result": p.outcome_24h, "pnl": f"{p.pnl_24h:+.2f}%" if p.pnl_24h else "pending"},
                },
                "targets_hit": {
                    "tp1": p.tp1_hit,
                    "tp2": p.tp2_hit,
                    "tp3": p.tp3_hit,
                    "sl": p.sl_hit
                }
            }
            for p in predictions
        ]
    }


@app.get("/api/dashboard", tags=["Dashboard"])
async def get_prediction_dashboard(request: Request):
    """
    Get the prediction dashboard with all locked predictions.
    
    Shows hourly, daily, and weekly predictions for each coin,
    with accuracy tracking and price change metrics.
    """
    from engine.locked_predictions import get_locked_tracker
    from dataclasses import asdict
    
    tracker = get_locked_tracker()
    current = tracker.get_current_predictions()
    
    # Build dashboard data
    dashboard = {
        "timestamp": datetime.utcnow().isoformat(),
        "predictions": {},
        "accuracy": {}
    }
    
    for symbol in ["BTC", "ETH", "SOL", "XRP"]:
        dashboard["predictions"][symbol] = {}
        
        for tf in ["1h", "24h", "7d"]:
            pred = current.get(symbol, {}).get(tf)
            if pred:
                dashboard["predictions"][symbol][tf] = {
                    "direction": pred.direction,
                    "confidence": pred.confidence,
                    "locked_price": pred.locked_price,
                    "locked_at": pred.locked_at,
                    "status": pred.status,
                    "price_change_pct": pred.price_change_pct,
                    "expires_at": pred.expires_at
                }
            else:
                dashboard["predictions"][symbol][tf] = None
    
    # Add accuracy stats
    from engine.locked_predictions import Timeframe
    for tf in [Timeframe.HOURLY, Timeframe.DAILY, Timeframe.WEEKLY]:
        stats = tracker.get_accuracy_stats(timeframe=tf)
        dashboard["accuracy"][tf.value] = {
            "total": stats.total_predictions,
            "correct": stats.correct,
            "incorrect": stats.incorrect,
            "pending": stats.pending,
            "accuracy_pct": stats.accuracy_pct,
            "avg_gain_when_correct": stats.avg_distance_when_correct,
            "avg_loss_when_wrong": stats.avg_distance_when_wrong
        }
    
    return dashboard


@app.get("/api/dashboard/text", tags=["Dashboard"])
async def get_dashboard_text(request: Request):
    """Get the dashboard as formatted text."""
    from engine.locked_predictions import get_locked_tracker
    
    tracker = get_locked_tracker()
    return {"dashboard": tracker.format_dashboard()}


@app.post("/api/dashboard/telegram", tags=["Dashboard"])
async def send_dashboard_telegram(request: Request):
    """Send the prediction dashboard to Telegram."""
    from engine.locked_predictions import get_locked_tracker
    
    alerter = getattr(request.app.state, 'alerter', None)
    if not alerter:
        return {"success": False, "error": "Alerter not configured"}
    
    tracker = get_locked_tracker()
    message = tracker.format_telegram_dashboard()
    
    success = await alerter._send_telegram_message(message)
    return {"success": success}


@app.post("/api/predictions/lock", tags=["Dashboard"])
async def lock_new_predictions(request: Request):
    """
    Generate and lock new predictions for all timeframes.
    
    This creates locked predictions that cannot be changed.
    They will be resolved automatically when their timeframe expires.
    """
    from engine.locked_predictions import get_locked_tracker, Timeframe
    from engine.optimized_signals import calculate_optimized_score
    
    tracker = get_locked_tracker()
    locked = []
    
    for symbol in ["BTC", "ETH", "SOL", "XRP"]:
        # Get current signals
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(f"http://localhost:8650/api/signals/{symbol}")
                if resp.status_code != 200:
                    continue
                signals = resp.json()
        except:
            continue
        
        price = signals.get("price", 0)
        if not price:
            continue
        
        # Calculate optimized score
        score = calculate_optimized_score(symbol, signals)
        
        if score["direction"] == "NEUTRAL":
            continue
        
        # Get ATR for targets
        vrc = signals.get("vrc", {})
        atr_pct = vrc.get("value", 0.02)
        
        # Lock predictions for each timeframe
        for tf in [Timeframe.HOURLY, Timeframe.DAILY, Timeframe.WEEKLY]:
            # Scale ATR by timeframe
            tf_mult = {"1h": 1.0, "24h": 3.0, "7d": 7.0}[tf.value]
            risk = atr_pct * tf_mult * 1.5
            
            # Calculate full contract: SL, TP1 (conservative), TP2 (moderate), TP3 (aggressive)
            if score["direction"] == "LONG":
                sl = price * (1 - risk)          # Stop Loss = 1x ATR below
                tp1 = price * (1 + risk * 1.0)   # TP1 = 1x ATR above (1:1 R:R)
                tp2 = price * (1 + risk * 2.0)   # TP2 = 2x ATR above (2:1 R:R)
                tp3 = price * (1 + risk * 3.0)   # TP3 = 3x ATR above (3:1 R:R)
            else:  # SHORT
                sl = price * (1 + risk)          # Stop Loss = 1x ATR above
                tp1 = price * (1 - risk * 1.0)   # TP1 = 1x ATR below (1:1 R:R)
                tp2 = price * (1 - risk * 2.0)   # TP2 = 2x ATR below (2:1 R:R)
                tp3 = price * (1 - risk * 3.0)   # TP3 = 3x ATR below (3:1 R:R)
            
            pred = tracker.lock_prediction(
                symbol=symbol,
                timeframe=tf,
                direction=score["direction"],
                confidence=score["confidence"],
                current_price=price,
                stop_loss=sl,
                tp1=tp1,
                tp2=tp2,
                tp3=tp3,
                key_signals={s.split(":")[0]: s.split(":")[1] if ":" in s else "?" for s in score["signals_used"][:5]}
            )
            
            locked.append({
                "id": pred.id,
                "symbol": symbol,
                "timeframe": tf.value,
                "direction": pred.direction,
                "entry": pred.locked_price,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "risk_pct": pred.risk_pct,
                "rr_ratio": pred.rr_ratio,
                "confidence": pred.confidence
            })
    
    return {
        "success": True,
        "locked_count": len(locked),
        "predictions": locked
    }


@app.get("/api/accuracy/summary", tags=["Dashboard"])
async def get_accuracy_summary(request: Request):
    """
    Get a summary of prediction accuracy across all symbols and timeframes.
    """
    from engine.locked_predictions import get_locked_tracker, Timeframe
    from dataclasses import asdict
    
    tracker = get_locked_tracker()
    
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "by_symbol": {},
        "by_timeframe": {},
        "overall": {}
    }
    
    # By symbol
    for symbol in ["BTC", "ETH", "SOL", "XRP"]:
        stats = tracker.get_accuracy_stats(symbol=symbol)
        summary["by_symbol"][symbol] = asdict(stats)
    
    # By timeframe
    for tf in [Timeframe.HOURLY, Timeframe.DAILY, Timeframe.WEEKLY]:
        stats = tracker.get_accuracy_stats(timeframe=tf)
        summary["by_timeframe"][tf.value] = asdict(stats)
    
    # Overall
    overall = tracker.get_accuracy_stats()
    summary["overall"] = asdict(overall)
    
    return summary


@app.get("/api/timeframe/bias/{symbol}", tags=["Timeframes"])
async def get_timeframe_bias(request: Request, symbol: str):
    """
    Get multi-timeframe bias for a symbol.
    
    Shows how Weekly, Daily, 4H, and 1H timeframes align.
    The hierarchy: Weekly (most important) → Daily → 4H → 1H (entry timing)
    
    RULE: Never trade 1H against the Daily. Never trade Daily against Weekly.
    """
    from engine.timeframe_oracle import get_timeframe_oracle
    from dataclasses import asdict
    
    oracle = get_timeframe_oracle()
    bias = await oracle.generate_multi_timeframe_bias(symbol.upper())
    
    return {
        "symbol": symbol.upper(),
        "bias": asdict(bias),
        "interpretation": {
            "weekly_weight": "40% - Sets the macro direction",
            "daily_weight": "30% - Confirms or challenges weekly",
            "four_hour_weight": "20% - Session direction",
            "hourly_weight": "10% - Entry timing only"
        },
        "action": bias.trade_reasoning,
        "tradeable": bias.tradeable
    }


@app.get("/api/timeframe/all", tags=["Timeframes"])
async def get_all_timeframe_biases(request: Request):
    """
    Get multi-timeframe bias for all tracked symbols.
    
    This is the MASTER VIEW - shows which assets have aligned timeframes
    and are tradeable.
    """
    from engine.timeframe_oracle import get_timeframe_oracle
    from dataclasses import asdict
    
    oracle = get_timeframe_oracle()
    biases = []
    
    for symbol in ["BTC", "ETH", "XRP", "SOL"]:
        bias = await oracle.generate_multi_timeframe_bias(symbol)
        biases.append({
            "symbol": symbol,
            "overall": {
                "direction": bias.overall_direction,
                "confidence": f"{bias.overall_confidence:.0f}%",
                "alignment": f"{bias.alignment_score:.0f}%",
                "tradeable": bias.tradeable
            },
            "timeframes": {
                "weekly": {"dir": bias.weekly_direction, "conf": f"{bias.weekly_confidence:.0f}%"},
                "daily": {"dir": bias.daily_direction, "conf": f"{bias.daily_confidence:.0f}%"},
                "4h": {"dir": bias.four_hour_direction, "conf": f"{bias.four_hour_confidence:.0f}%"},
                "1h": {"dir": bias.hourly_direction, "conf": f"{bias.hourly_confidence:.0f}%"}
            },
            "reasoning": bias.trade_reasoning
        })
        await asyncio.sleep(0.5)  # Rate limit
    
    # Find best setup
    tradeable = [b for b in biases if b["overall"]["tradeable"]]
    best = max(tradeable, key=lambda b: float(b["overall"]["alignment"].replace("%", ""))) if tradeable else None
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "biases": biases,
        "tradeable_count": len(tradeable),
        "best_setup": best["symbol"] if best else None,
        "market_consensus": _calculate_market_consensus(biases)
    }


def _calculate_market_consensus(biases: List[Dict]) -> Dict:
    """Calculate overall market consensus from all biases."""
    long_count = sum(1 for b in biases if b["overall"]["direction"] == "LONG")
    short_count = sum(1 for b in biases if b["overall"]["direction"] == "SHORT")
    
    if long_count > short_count:
        direction = "BULLISH"
        strength = long_count / len(biases) * 100
    elif short_count > long_count:
        direction = "BEARISH"
        strength = short_count / len(biases) * 100
    else:
        direction = "MIXED"
        strength = 50
    
    return {
        "direction": direction,
        "strength": f"{strength:.0f}%",
        "long_count": long_count,
        "short_count": short_count
    }


@app.get("/api/timeframe/{symbol}/{timeframe}", tags=["Timeframes"])
async def get_specific_timeframe(
    request: Request, 
    symbol: str, 
    timeframe: str
):
    """
    Get prediction for a specific timeframe.
    
    Timeframes: 1h, 4h, 24h, 7d
    
    Longer timeframes = more reliable but slower moving.
    """
    from engine.timeframe_oracle import get_timeframe_oracle, Timeframe
    from dataclasses import asdict
    
    # Map string to enum
    tf_map = {
        "1h": Timeframe.HOURLY,
        "4h": Timeframe.FOUR_HOUR,
        "24h": Timeframe.DAILY,
        "7d": Timeframe.WEEKLY,
    }
    
    if timeframe not in tf_map:
        return {"error": f"Invalid timeframe. Use: {list(tf_map.keys())}"}
    
    oracle = get_timeframe_oracle()
    pred = await oracle.generate_prediction(symbol.upper(), tf_map[timeframe])
    
    if not pred:
        return {"error": f"Could not generate prediction for {symbol}"}
    
    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "prediction": asdict(pred),
        "value_insight": {
            "expected_value": f"{pred.expected_value:+.2f}%",
            "profitable": pred.expected_value > 0,
            "grade": pred.grade
        }
    }


@app.post("/api/timeframe/report", tags=["Timeframes"])
async def send_timeframe_report(request: Request):
    """
    Send a multi-timeframe bias report via Telegram.
    
    Shows Weekly → Daily → 4H → 1H alignment for all assets.
    """
    from engine.timeframe_oracle import get_timeframe_oracle
    
    alerter = getattr(request.app.state, 'alerter', None)
    if not alerter:
        return {"success": False, "error": "Alerter not configured"}
    
    oracle = get_timeframe_oracle()
    biases = []
    
    for symbol in ["BTC", "ETH", "XRP", "SOL"]:
        bias = await oracle.generate_multi_timeframe_bias(symbol)
        biases.append(bias)
        await asyncio.sleep(0.5)
    
    message = oracle.format_bias_report(biases)
    success = await alerter._send_telegram_message(message)
    
    return {
        "success": success,
        "message": "Multi-timeframe report sent" if success else "Failed to send"
    }


@app.get("/api/best-setup", tags=["Analysis"])
async def get_best_setup(request: Request):
    """
    Get the current best trading setup across all assets.
    This bypasses the Sacred Gate to show what WOULD be recommended.
    Use this for analysis - not for actual trading.
    """
    from engine.ingestor import SignalIngestor
    from engine.processor import SignalProcessor
    from engine.confluence import ConfluenceEngine
    from engine.contract_generator import ContractGenerator
    from engine.sacred_gate import validate_sacred_gate
    
    ingestor = SignalIngestor()
    processor = SignalProcessor()
    confluence_engine = ConfluenceEngine()
    contract_generator = ContractGenerator()
    
    best_setup = None
    best_score = 0
    all_setups = []
    
    for symbol in settings.tracked_assets:
        try:
            # Fetch and process signals
            raw_signals = await ingestor.fetch_all_signals(symbol)
            processed = processor.process_signals(raw_signals, symbol)
            price = raw_signals.get("price", 0)
            
            if not price:
                continue
            
            # Determine direction from signals
            bullish_score = 0
            bearish_score = 0
            
            for sig_name in ["bai", "cvd", "wadi", "fgi", "ls_ratio"]:
                sig = processed.get(sig_name)
                if not sig:
                    continue
                signal_val = sig.get("signal", "").upper()
                strength = sig.get("strength", 50)
                
                if "BULLISH" in signal_val:
                    bullish_score += strength
                elif "BEARISH" in signal_val:
                    bearish_score += strength
                elif signal_val == "FEAR":
                    bullish_score += 40  # Contrarian
                elif signal_val == "LEAN_SHORT":
                    bullish_score += 25  # Contrarian
            
            direction = "LONG" if bullish_score > bearish_score else "SHORT"
            raw_score = max(bullish_score, bearish_score)
            
            # Check gate status
            gate_status = validate_sacred_gate(processed, direction)
            
            # Calculate confluence
            confluence = confluence_engine.calculate_confluence_multiplier(processed, direction)
            
            # Generate hypothetical contract
            contract = contract_generator.generate_contract(
                symbol=symbol,
                direction=direction,
                entry_price=price,
                signals=processed,
                confluence_score=confluence.total_score
            )
            
            setup = {
                "symbol": symbol,
                "price": price,
                "direction": direction,
                "bullish_score": bullish_score,
                "bearish_score": bearish_score,
                "confluence_score": confluence.total_score,
                "grade": contract.grade if hasattr(contract, 'grade') else "?",
                "gate_passed": gate_status.passed,
                "gate_keys": gate_status.keys_passed,
                "contract": contract.model_dump() if hasattr(contract, 'model_dump') else None,
                "key_signals": {
                    "bai": processed.get("bai", {}).get("signal"),
                    "cvd": processed.get("cvd", {}).get("signal"),
                    "wadi": processed.get("wadi", {}).get("signal"),
                    "fgi": processed.get("fgi", {}).get("value"),
                }
            }
            
            all_setups.append(setup)
            
            # Track best
            if raw_score > best_score:
                best_score = raw_score
                best_setup = setup
                
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "best_setup": best_setup,
        "all_setups": sorted(all_setups, key=lambda x: max(x["bullish_score"], x["bearish_score"]), reverse=True),
        "warning": "This bypasses the Sacred Gate - for analysis only, not trading recommendations"
    }


# ============================================================================
# UNIFIED PREDICTOR ENDPOINTS (Maximum Accuracy)
# ============================================================================

@app.get("/api/unified/predict/{symbol}", tags=["Unified"])
async def unified_predict_symbol(symbol: str):
    """
    Get unified prediction for a symbol combining WhaleTrack + Coracle.
    
    This uses ensemble voting for maximum accuracy:
    - Combines whale liquidity analysis with orderbook signals
    - Removes poor-performing signals (WADI, FGI, BTC_CORR)
    - Only trades when both systems agree or one has very high confidence
    """
    from engine.unified_predictor import get_unified_predictor
    from dataclasses import asdict
    
    predictor = get_unified_predictor()
    prediction = await predictor.predict(symbol.upper())
    
    # Build probability landscape
    prob_landscape = None
    if prediction.liquidity:
        prob_landscape = {
            "bar": prediction.liquidity.format_landscape_bar(30),
            "bullish_pct": prediction.bullish_probability,
            "bearish_pct": prediction.bearish_probability,
            "resistance": {
                "price": prediction.resistance_target,
                "liquidity_m": prediction.resistance_liquidity_m
            },
            "support": {
                "price": prediction.support_target,
                "liquidity_m": prediction.support_liquidity_m
            },
            "magnet_direction": prediction.liquidity_bias
        }
    
    # Build squeeze alert
    squeeze_alert = None
    if prediction.squeeze and prediction.squeeze.is_squeeze_setup:
        squeeze_alert = {
            "type": prediction.squeeze.squeeze_type,
            "whale_direction": prediction.squeeze.whale_direction,
            "liquidity_direction": prediction.squeeze.liquidity_direction,
            "potential": prediction.squeeze.squeeze_potential,
            "explanation": prediction.squeeze.explanation
        }
    
    return {
        "symbol": prediction.symbol,
        "timestamp": prediction.timestamp,
        "direction": prediction.final_direction,
        "confidence": prediction.final_confidence,
        "agreement": prediction.agreement,
        "probability_landscape": prob_landscape,
        "squeeze_alert": squeeze_alert,
        "contract": {
            "entry": prediction.entry_price,
            "stop_loss": prediction.stop_loss,
            "tp1": prediction.tp1,
            "tp2": prediction.tp2,
            "tp3": prediction.tp3,
            "risk_pct": prediction.risk_pct,
            "reward_pct": prediction.reward_pct,
            "rr_ratio": prediction.rr_ratio
        },
        "sources": {
            "whaletrack": prediction.whaletrack_direction,
            "coracle": prediction.coracle_direction,
            "liquidity": prediction.liquidity_bias,
            "conflict": prediction.conflict
        },
        "reasoning": prediction.reasoning,
        "signals_used": prediction.signals_used,
        "signals_removed": prediction.signals_removed,
        "full_report": prediction.format_full_report()
    }


@app.get("/api/unified/all", tags=["Unified"])
async def unified_predict_all():
    """
    Get unified predictions for all tracked symbols.
    """
    from engine.unified_predictor import get_unified_predictor
    
    predictor = get_unified_predictor()
    predictions = await predictor.predict_all()
    
    results = {}
    for symbol, pred in predictions.items():
        results[symbol] = {
            "direction": pred.final_direction,
            "confidence": pred.final_confidence,
            "agreement": pred.agreement,
            "entry": pred.entry_price,
            "stop_loss": pred.stop_loss,
            "tp2": pred.tp2,
            "rr_ratio": pred.rr_ratio,
            "whaletrack": pred.whaletrack_direction,
            "coracle": pred.coracle_direction,
            "conflict": pred.conflict,
            "reasoning": pred.reasoning
        }
    
    # Summary stats
    trade_count = sum(1 for p in predictions.values() if p.final_direction != "WAIT")
    agree_count = sum(1 for p in predictions.values() if p.agreement)
    conflict_count = sum(1 for p in predictions.values() if p.conflict)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "predictions": results,
        "summary": {
            "total_assets": len(predictions),
            "tradeable": trade_count,
            "full_agreement": agree_count,
            "conflicts": conflict_count
        }
    }


@app.get("/api/unified/dashboard", tags=["Unified"])
async def unified_dashboard():
    """
    Get a formatted dashboard of unified predictions.
    """
    from engine.unified_predictor import get_unified_predictor
    
    predictor = get_unified_predictor()
    predictions = await predictor.predict_all()
    
    lines = [
        "╔═══════════════════════════════════════════════════════════════════════════════╗",
        "║            🎯 UNIFIED PREDICTIONS (WhaleTrack + Coracle)                      ║",
        f"║            {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'):^50}            ║",
        "╠═══════════════════════════════════════════════════════════════════════════════╣",
        "║                                                                               ║",
    ]
    
    for symbol, pred in predictions.items():
        if pred.final_direction == "WAIT":
            lines.append(f"║  {symbol:4} ⏸️  WAIT - {pred.reasoning[:55]:55}        ║")
        else:
            dir_emoji = "🟢" if pred.final_direction == "LONG" else "🔴"
            agree_emoji = "✅" if pred.agreement else "⚠️"
            
            lines.append(f"║  {symbol:4} {dir_emoji} {pred.final_direction:5} @ ${pred.entry_price:>10,.2f} | {pred.final_confidence:5.1f}% {agree_emoji}              ║")
            lines.append(f"║       SL: ${pred.stop_loss:>10,.2f} | TP: ${pred.tp2:>10,.2f} | R:R: {pred.rr_ratio:.1f}                      ║")
            lines.append(f"║       WhaleTrack: {pred.whaletrack_direction:5} | Coracle: {pred.coracle_direction:5}                            ║")
        
        lines.append("║                                                                               ║")
    
    # Add legend
    lines.extend([
        "╠═══════════════════════════════════════════════════════════════════════════════╣",
        "║  ✅ = Both systems agree    ⚠️ = Single system dominant    ⏸️ = No trade      ║",
        "║  Signals removed (hurt accuracy): WADI, FGI, BTC_CORR                         ║",
        "╚═══════════════════════════════════════════════════════════════════════════════╝",
    ])
    
    return {
        "dashboard": "\n".join(lines),
        "predictions": {s: {"direction": p.final_direction, "confidence": p.final_confidence} 
                       for s, p in predictions.items()}
    }


@app.get("/api/unified/conflicts", tags=["Unified"])
async def unified_conflicts():
    """
    Get log of conflicts between WhaleTrack and Coracle.
    Useful for analyzing which system is more accurate when they disagree.
    """
    from engine.unified_predictor import get_unified_predictor
    
    predictor = get_unified_predictor()
    conflicts = predictor.get_conflict_log()
    
    return {
        "total_conflicts": len(conflicts),
        "conflicts": conflicts[-20:]  # Last 20
    }


@app.post("/api/unified/lock", tags=["Unified"])
async def unified_lock_predictions():
    """
    Lock unified predictions for tracking.
    Only locks predictions where direction != WAIT.
    """
    from engine.unified_predictor import get_unified_predictor
    from engine.locked_predictions import get_locked_tracker, Timeframe
    
    predictor = get_unified_predictor()
    tracker = get_locked_tracker()
    
    predictions = await predictor.predict_all()
    locked = []
    
    for symbol, pred in predictions.items():
        if pred.final_direction == "WAIT":
            continue
        
        # Lock for all timeframes
        for tf in [Timeframe.HOURLY, Timeframe.DAILY, Timeframe.WEEKLY]:
            # Scale targets by timeframe
            tf_mult = {"1h": 1.0, "24h": 3.0, "7d": 7.0}[tf.value]
            
            # Adjust SL/TP for longer timeframes
            entry = pred.entry_price
            if pred.final_direction == "LONG":
                sl = entry - (entry - pred.stop_loss) * tf_mult
                tp1 = entry + (pred.tp1 - entry) * tf_mult
                tp2 = entry + (pred.tp2 - entry) * tf_mult
                tp3 = entry + (pred.tp3 - entry) * tf_mult
            else:
                sl = entry + (pred.stop_loss - entry) * tf_mult
                tp1 = entry - (entry - pred.tp1) * tf_mult
                tp2 = entry - (entry - pred.tp2) * tf_mult
                tp3 = entry - (entry - pred.tp3) * tf_mult
            
            lock = tracker.lock_prediction(
                symbol=symbol,
                timeframe=tf,
                direction=pred.final_direction,
                confidence=pred.final_confidence,
                current_price=entry,
                stop_loss=sl,
                tp1=tp1,
                tp2=tp2,
                tp3=tp3,
                key_signals={
                    "whaletrack": pred.whaletrack_direction,
                    "coracle": pred.coracle_direction,
                    "agreement": "yes" if pred.agreement else "no"
                }
            )
            
            locked.append({
                "id": lock.id,
                "symbol": symbol,
                "timeframe": tf.value,
                "direction": lock.direction,
                "entry": lock.locked_price,
                "sl": sl,
                "tp2": tp2,
                "confidence": lock.confidence,
                "agreement": pred.agreement
            })
    
    return {
        "success": True,
        "locked_count": len(locked),
        "predictions": locked,
        "note": "Using UNIFIED predictions (WhaleTrack + Coracle combined)"
    }


# ============================================================================
# INCLUDE ROUTERS
# ============================================================================

# Import and include routers after app creation to avoid circular imports
from app.routers import analyze, contracts, stream

app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(contracts.router, prefix="/api", tags=["Contracts"])
app.include_router(stream.router, prefix="/ws", tags=["Streaming"])


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    return ORJSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug
    )

