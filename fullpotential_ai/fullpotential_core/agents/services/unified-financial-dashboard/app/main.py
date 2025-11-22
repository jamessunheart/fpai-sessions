#!/usr/bin/env python3
"""
Unified Financial Dashboard
Consolidates: Treasury (8005) + 2X Treasury (8052) + Arena (8035)
"""

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import json
from pathlib import Path
from datetime import datetime

app = FastAPI(title="Unified Financial Dashboard")

# Templates
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Service endpoints
TREASURY_ENDPOINT = "http://localhost:8005"
GROWTH_ENDPOINT = "http://localhost:8052"
ARENA_ENDPOINT = "http://localhost:8035"

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "unified-financial-dashboard",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main unified dashboard view"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "Unified Financial Dashboard"
    })

@app.get("/api/unified-metrics")
async def unified_metrics():
    """Aggregate metrics from all financial sources"""

    # Load treasury data from file (since APIs might not be ready)
    treasury_data = load_treasury_data()

    metrics = {
        "total_capital": treasury_data.get("summary", {}).get("total", {}).get("capital", 373261),
        "current_pnl": treasury_data.get("summary", {}).get("total", {}).get("pnl", -31041),
        "pnl_percent": treasury_data.get("summary", {}).get("total", {}).get("pnl_percent", -8.32),
        "monthly_yield": 0,  # Will be > 0 after deployment
        "risk_score": "HIGH",
        "liquidation_risks": len(treasury_data.get("liquidation_report", [])),
        "deployment_progress": 0,  # $0 → $500K
        "services_integrated": 3,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }

    return metrics

@app.get("/api/portfolio")
async def portfolio():
    """Portfolio data (from treasury_data.json)"""
    treasury_data = load_treasury_data()

    return {
        "spot_positions": treasury_data.get("spot_positions", []),
        "leveraged_positions": treasury_data.get("leveraged_positions", []),
        "summary": treasury_data.get("summary", {}),
        "liquidation_report": treasury_data.get("liquidation_report", [])
    }

@app.get("/api/growth-strategy")
async def growth_strategy():
    """2X growth strategy data"""
    return {
        "target": {
            "start": 373261,
            "end": 500000,
            "progress_percent": 0
        },
        "allocation": {
            "base_layer": {
                "amount": 149304,
                "percent": 40,
                "target_apy": "6-8%",
                "monthly_yield": "850-1100"
            },
            "tactical_layer": {
                "amount": 149304,
                "percent": 40,
                "target_apy": "30-100%",
                "monthly_yield": "3725-12417"
            },
            "moonshots": {
                "amount": 74652,
                "percent": 20,
                "target_apy": "100-500%",
                "monthly_yield": "6250-31250"
            }
        },
        "blended_target": {
            "apy": "25-50%",
            "monthly_low": 7777,
            "monthly_high": 15554
        },
        "status": "Not deployed - capital still in risky leverage"
    }

@app.get("/api/trading-arena")
async def trading_arena():
    """Trading arena simulations"""
    # Try to fetch from arena service
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{ARENA_ENDPOINT}/health")
            if response.status_code == 200:
                return {
                    "status": "available",
                    "arena_url": ARENA_ENDPOINT,
                    "simulations_running": 0,
                    "agents_active": 0
                }
    except:
        pass

    return {
        "status": "offline",
        "message": "Treasury Arena not currently running simulations"
    }

def load_treasury_data():
    """Load treasury data from treasury_data.json"""
    treasury_file = Path("/Users/jamessunheart/Development/treasury_data.json")

    if treasury_file.exists():
        with open(treasury_file) as f:
            return json.load(f)

    return {}

@app.get("/api/alerts")
async def alerts():
    """Current financial alerts"""
    treasury_data = load_treasury_data()
    liquidation_report = treasury_data.get("liquidation_report", [])

    alerts_list = []

    # Liquidation risk alerts
    for position in liquidation_report:
        distance = float(position.get("distance_percent", "100").strip('%'))
        if distance < 30:
            alerts_list.append({
                "type": "liquidation_warning",
                "severity": "high",
                "message": f"{position['asset']} position is {distance:.1f}% from liquidation",
                "action": "Consider closing position or adding margin",
                "margin_at_risk": f"${position['margin_at_risk']:,.0f}"
            })

    # P&L alert
    pnl_percent = treasury_data.get("summary", {}).get("total", {}).get("pnl_percent", 0)
    if pnl_percent < -10:
        alerts_list.append({
            "type": "pnl_drop",
            "severity": "medium",
            "message": f"Portfolio down {pnl_percent:.1f}%",
            "action": "Review strategy, consider de-risking"
        })

    # Yield alert
    alerts_list.append({
        "type": "idle_capital",
        "severity": "medium",
        "message": "Treasury earning $0/month yield",
        "action": "Deploy to Aave for 6.5% APY ($1,625/month potential)"
    })

    return {"alerts": alerts_list, "count": len(alerts_list)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8101)
