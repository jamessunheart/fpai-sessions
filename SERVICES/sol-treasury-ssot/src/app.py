"""
SOL Treasury SSOT - FastAPI Service
Real-time treasury dashboard and API
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .models import SOLDeposit, POTSpending, LiquidationEvent
from .treasury import treasury

app = FastAPI(
    title="SOL Treasury SSOT",
    description="Single Source of Truth for SOL-backed POT economy. Path to 2x growth.",
    version="1.0.0"
)

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def dashboard():
    """Treasury dashboard"""
    metrics = await treasury.get_metrics()
    strategy = treasury.get_growth_strategy()

    # Build HTML dashboard
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SOL Treasury SSOT - Path to 2x</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid rgba(255,255,255,0.2);
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 48px; margin-bottom: 10px; }}
        .header .tagline {{ font-size: 20px; opacity: 0.9; }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .metric-card h3 {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.8;
            margin-bottom: 10px;
        }}
        .metric-card .value {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-card .sub {{
            font-size: 14px;
            opacity: 0.7;
        }}

        .status-banner {{
            background: rgba(255,255,255,0.15);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 30px;
            font-size: 18px;
        }}
        .status-banner.leverageable {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        }}

        .progress-bar {{
            width: 100%;
            height: 30px;
            background: rgba(0,0,0,0.3);
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            transition: width 0.3s ease;
        }}

        .section {{
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
        }}
        .section h2 {{
            margin-bottom: 20px;
            font-size: 24px;
        }}

        .action-list {{
            list-style: none;
        }}
        .action-list li {{
            padding: 10px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .action-list li:before {{
            content: "→ ";
            font-weight: bold;
        }}

        .badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .badge.success {{ background: #38ef7d; color: #000; }}
        .badge.warning {{ background: #f093fb; color: #000; }}
        .badge.danger {{ background: #ff6b6b; color: #fff; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ SOL Treasury SSOT</h1>
            <div class="tagline">Single Source of Truth · Path to 2x Growth</div>
        </div>

        {
            f'<div class="status-banner leverageable">🎯 TIPPING POINT REACHED - Can Leverage SOL Without Selling!</div>'
            if metrics.can_leverage else
            f'<div class="status-banner">📈 {metrics.status.value.upper()} - Accumulating toward tipping point...</div>'
        }

        <div class="metrics-grid">
            <div class="metric-card">
                <h3>SOL Treasury</h3>
                <div class="value">{metrics.sol_balance:.2f} SOL</div>
                <div class="sub">${metrics.sol_value_usd:,.0f} USD @ ${metrics.sol_price_usd:.2f}/SOL</div>
            </div>

            <div class="metric-card">
                <h3>POT Economy</h3>
                <div class="value">{metrics.pot_outstanding:,.0f} POT</div>
                <div class="sub">Issued: {metrics.pot_total_issued:,.0f} · Redeemed: {metrics.pot_total_redeemed:,.0f}</div>
            </div>

            <div class="metric-card">
                <h3>Reserve Ratio</h3>
                <div class="value">{metrics.reserve_ratio * 100:.1f}%</div>
                <div class="sub">Target: {metrics.tipping_point_ratio * 100:.0f}% for leverage</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {min(100, metrics.reserve_ratio / metrics.tipping_point_ratio * 100):.0f}%">
                        {min(100, metrics.reserve_ratio / metrics.tipping_point_ratio * 100):.0f}%
                    </div>
                </div>
            </div>

            <div class="metric-card">
                <h3>Value Creation (2x Proof)</h3>
                <div class="value">{metrics.overall_roi_multiplier:.2f}x</div>
                <div class="sub">
                    ${metrics.total_value_created_usd:,.0f} created from {metrics.total_pot_spent:,.0f} POT spent
                    <br>
                    {
                        '<span class="badge success">✅ PROVEN</span>' if metrics.overall_roi_multiplier >= 2.0 else
                        '<span class="badge warning">⚠️ BUILDING</span>'
                    }
                </div>
            </div>

            <div class="metric-card">
                <h3>SOL Liquidation</h3>
                <div class="value">{metrics.sol_held_percent:.1f}%</div>
                <div class="sub">Held · {metrics.sol_liquidated_percent:.1f}% liquidated for vendors</div>
            </div>

            <div class="metric-card">
                <h3>Path to Tipping Point</h3>
                <div class="value">
                    {f'{metrics.days_to_tipping_point:.0f} days' if metrics.days_to_tipping_point else 'Calculating...'}
                </div>
                <div class="sub">Need {metrics.sol_needed_for_tipping_point:.2f} more SOL</div>
            </div>
        </div>

        <div class="section">
            <h2>📊 Growth Strategy - Path to 2x Treasury</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <h3>Weekly Growth Rate</h3>
                    <div class="value">
                        {f'{strategy.actual_growth_rate:.1f}%' if strategy.actual_growth_rate else 'N/A'}
                    </div>
                    <div class="sub">Target: {strategy.target_growth_rate:.0f}%/week for 2x in ~6 weeks</div>
                </div>

                <div class="metric-card">
                    <h3>Days to 2x Treasury</h3>
                    <div class="value">
                        {f'{strategy.days_to_2x} days' if strategy.days_to_2x else 'Calculating...'}
                    </div>
                    <div class="sub">At current growth rate</div>
                </div>

                <div class="metric-card">
                    <h3>Active Users</h3>
                    <div class="value">{strategy.active_users}</div>
                    <div class="sub">POT velocity: {strategy.pot_velocity:.1f} transactions/day</div>
                </div>

                <div class="metric-card">
                    <h3>Monthly Projection</h3>
                    <div class="value">
                        {f'{metrics.monthly_projection:.0f} SOL' if metrics.monthly_projection else 'N/A'}
                    </div>
                    <div class="sub">30-day forecast at current rate</div>
                </div>
            </div>

            <h3 style="margin-top: 30px; margin-bottom: 15px;">🎯 Recommended Actions</h3>
            <ul class="action-list">
                {''.join(f'<li>{action}</li>' for action in strategy.recommended_actions)}
            </ul>
        </div>

        <div class="section">
            <h2>🔗 Connected Services</h2>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">
                <div style="padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                    <strong>Treasury Arena</strong><br>
                    AI Competition<br>
                    {strategy.arena_allocated:.0f} SOL allocated<br>
                    Target: {strategy.arena_apy_target:.0f}% APY
                </div>
                <div style="padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                    <strong>Treasury Manager</strong><br>
                    DeFi Positions<br>
                    {strategy.defi_allocated:.0f} SOL allocated<br>
                    Target: {strategy.defi_apy_target:.0f}% APY
                </div>
                <div style="padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                    <strong>I-Match</strong><br>
                    Marketplace<br>
                    POT spending enabled<br>
                    15+ categories
                </div>
                <div style="padding: 15px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                    <strong>Jobs Platform</strong><br>
                    AI Recruiting<br>
                    POT payments (soon)<br>
                    Automated matching
                </div>
            </div>
        </div>

        <div style="text-align: center; padding: 30px; opacity: 0.6; font-size: 14px;">
            Last updated: {metrics.timestamp.strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
            <a href="/api/metrics" style="color: #fff;">API: /api/metrics</a> ·
            <a href="/api/strategy" style="color: #fff;">/api/strategy</a>
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
    """

    return HTMLResponse(content=html)


@app.get("/api/metrics")
async def get_metrics():
    """Get real-time treasury metrics (JSON)"""
    metrics = await treasury.get_metrics()
    return metrics


@app.get("/api/strategy")
async def get_strategy():
    """Get growth strategy and projections (JSON)"""
    strategy = treasury.get_growth_strategy()
    return strategy


@app.post("/api/deposit")
async def record_deposit(deposit: SOLDeposit):
    """Record new SOL deposit"""
    treasury.record_deposit(deposit)
    return {"status": "success", "deposit_id": deposit.id}


@app.post("/api/spending")
async def record_spending(spending: POTSpending):
    """Record POT spending"""
    treasury.record_spending(spending)
    return {"status": "success", "spending_id": spending.id}


@app.post("/api/liquidation")
async def record_liquidation(liquidation: LiquidationEvent):
    """Record SOL liquidation event"""
    treasury.record_liquidation(liquidation)
    return {"status": "success", "liquidation_id": liquidation.id}


@app.get("/health")
async def health():
    """Health check"""
    metrics = await treasury.get_metrics()
    return {
        "status": "healthy",
        "treasury_status": metrics.status,
        "sol_balance": metrics.sol_balance,
        "can_leverage": metrics.can_leverage
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8035)
