"""
Enhanced Money/Treasury Dashboard Router
Real-time financial tracking + $373K → $5T Vision
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
import json
import os

router = APIRouter()

# Data file paths
TREASURY_FILE = Path(os.getenv("TREASURY_PATH", "/opt/fpai/docs/coordination/treasury.json"))
TREASURY_DATA_FILE = Path(os.getenv("TREASURY_DATA_PATH", "/opt/fpai/coordination/treasury/data/positions.json"))
CAPITAL_VISION_FILE = Path(os.getenv("CAPITAL_VISION_PATH", "/opt/fpai/docs/coordination/CAPITAL_VISION_SSOT.md"))

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


def load_treasury_positions():
    """Load real-time treasury positions from treasury_data.json"""
    try:
        if TREASURY_DATA_FILE.exists():
            with open(TREASURY_DATA_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"summary": {"total": {"capital": 373261, "pnl": -31041, "pnl_percent": -8.32}}}


def load_treasury_data():
    """Load treasury.json (costs, revenue, projections)"""
    try:
        if TREASURY_FILE.exists():
            with open(TREASURY_FILE) as f:
                return json.load(f)
    except:
        pass
    return {
        "costs": {"claude_api": {"total": 0.46}, "server": {"monthly": 5}, "domains": {"annual": 12}},
        "revenue": {},
        "projections": {"monthly_burn": 5, "projected_revenue_m1": 2500, "projected_revenue_m12": 40000}
    }


def calculate_enhanced_metrics():
    """Calculate comprehensive metrics combining all data sources"""
    positions = load_treasury_positions()
    treasury = load_treasury_data()
    
    # Current capital from real positions
    current_capital = positions.get("summary", {}).get("total", {}).get("capital", 373261)
    current_pnl = positions.get("summary", {}).get("total", {}).get("pnl", -31041)
    current_pnl_percent = positions.get("summary", {}).get("total", {}).get("pnl_percent", -8.32)
    
    # Operating costs
    monthly_burn = treasury.get("projections", {}).get("monthly_burn", 5)
    
    # Revenue projections
    revenue_m1 = treasury.get("projections", {}).get("projected_revenue_m1", 2500)
    revenue_m12 = treasury.get("projections", {}).get("projected_revenue_m12", 40000)
    
    # Vision targets
    target_m6 = 500000  # $500K Month 6 target
    target_y1 = 5000000  # $5M Year 1 target
    target_y10 = 1000000000000  # $1T Year 10 target
    tam = 5210000000000  # $5.21T TAM
    
    # Progress calculations
    progress_to_m6 = min(100, (current_capital / target_m6) * 100)
    progress_to_y1 = min(100, (current_capital / target_y1) * 100)
    
    # Matches (placeholder - will integrate with I MATCH)
    matches_current = 0
    matches_target = 100
    
    return {
        "current": {
            "capital": current_capital,
            "pnl": current_pnl,
            "pnl_percent": current_pnl_percent,
            "monthly_burn": monthly_burn
        },
        "revenue": {
            "month_1": revenue_m1,
            "month_12": revenue_m12
        },
        "targets": {
            "month_6": target_m6,
            "year_1": target_y1,
            "year_10": target_y10,
            "tam": tam
        },
        "progress": {
            "to_m6_percent": round(progress_to_m6, 2),
            "to_y1_percent": round(progress_to_y1, 2),
            "matches_current": matches_current,
            "matches_target": matches_target,
            "matches_percent": 0
        },
        "phases": [
            {"name": "Proof", "duration": "Months 1-6", "capital": "$373K → $5M", "target": "100 matches, proven economics"},
            {"name": "Expand", "duration": "Months 7-18", "capital": "$5M → $100M", "target": "5-10 categories, 10K matches"},
            {"name": "Super-App", "duration": "Years 2-4", "capital": "$100M → $3B", "target": "10+ categories, 10M users"},
            {"name": "Network Effects", "duration": "Years 4-7", "capital": "$3B → $150B", "target": "100M+ users, dominance"},
            {"name": "New Paradigm", "duration": "Years 7-10+", "capital": "$150B → $1-5T", "target": "1B+ users, paradise"}
        ]
    }


@router.get("/dashboard/money", response_class=HTMLResponse)
async def money_dashboard(request: Request):
    """Enhanced treasury dashboard with trillion-dollar vision"""
    return templates.TemplateResponse("money.html", {
        "request": request,
        "title": "Treasury Dashboard - $373K → $5T Journey"
    })


@router.get("/api/treasury")
async def get_treasury():
    """Get comprehensive treasury data API"""
    metrics = calculate_enhanced_metrics()
    
    return JSONResponse({
        'metrics': metrics,
        'timestamp': datetime.now().isoformat()
    })


@router.get("/api/treasury/positions")
async def get_positions():
    """Get real-time positions"""
    return JSONResponse(load_treasury_positions())
