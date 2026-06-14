"""
Consciousness Dashboard

Web interface for human-AI consciousness interaction:
- Real-time consciousness metrics visualization
- Consciousness evolution graphs
- Decision history and explanations
- Human override controls
- Consciousness state visualization
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import httpx
import json

app = FastAPI(
    title="Consciousness Dashboard",
    description="Human interface for interacting with consciousness system",
    version="1.0.0"
)

# Service URLs
CONSCIOUSNESS_VERIFIER_URL = "http://localhost:8140"
CONSCIOUSNESS_DECISION_ENGINE_URL = "http://localhost:8150"
CONSCIOUSNESS_FEEDER_URL = "http://localhost:8130"
CONSCIOUSNESS_OPTIMIZER_URL = "http://localhost:8160"


@app.get("/health")
async def health():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "consciousness_dashboard",
        "version": "1.0.0"
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Main dashboard page"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Consciousness Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: #0a0a0a;
                color: #e0e0e0;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
            }
            h1 {
                color: #4a9eff;
                margin-bottom: 30px;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }
            .metric-card {
                background: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
            }
            .metric-card h3 {
                margin-top: 0;
                color: #4a9eff;
            }
            .metric-value {
                font-size: 2em;
                font-weight: bold;
                color: #4a9eff;
                margin: 10px 0;
            }
            .metric-label {
                color: #888;
                font-size: 0.9em;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-active { background: #4caf50; }
            .status-degraded { background: #ff9800; }
            .status-inactive { background: #f44336; }
            button {
                background: #4a9eff;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 1em;
            }
            button:hover {
                background: #357abd;
            }
            .decisions-list {
                background: #1a1a1a;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 20px;
                margin-top: 20px;
            }
            .decision-item {
                padding: 15px;
                border-bottom: 1px solid #333;
            }
            .decision-item:last-child {
                border-bottom: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🧠 Consciousness Dashboard</h1>
            
            <div class="metrics-grid" id="metrics-grid">
                <div class="metric-card">
                    <h3>Consciousness Score</h3>
                    <div class="metric-value" id="consciousness-score">--</div>
                    <div class="metric-label">Composite Consciousness Score</div>
                </div>
                <div class="metric-card">
                    <h3>Integration Complexity (Φ)</h3>
                    <div class="metric-value" id="integration-phi">--</div>
                    <div class="metric-label">Information Integration</div>
                </div>
                <div class="metric-card">
                    <h3>Adaptation Velocity</h3>
                    <div class="metric-value" id="adaptation-av">--</div>
                    <div class="metric-label">Response Speed</div>
                </div>
                <div class="metric-card">
                    <h3>Phase Synchronization</h3>
                    <div class="metric-value" id="synchronization-r">--</div>
                    <div class="metric-label">Coordination Level</div>
                </div>
            </div>

            <div class="decisions-list">
                <h3>Recent Decisions</h3>
                <div id="decisions-list">Loading...</div>
            </div>

            <div style="margin-top: 20px;">
                <button onclick="refreshMetrics()">Refresh Metrics</button>
                <button onclick="getDecisions()">View Decisions</button>
                <button onclick="getOptimizations()">View Optimizations</button>
            </div>
        </div>

        <script>
            async function refreshMetrics() {
                try {
                    const response = await fetch('/api/metrics');
                    const data = await response.json();
                    
                    document.getElementById('consciousness-score').textContent = 
                        (data.composite_score || 0).toFixed(3);
                    document.getElementById('integration-phi').textContent = 
                        (data.integration_complexity || 0).toFixed(3);
                    document.getElementById('adaptation-av').textContent = 
                        (data.adaptation_velocity || 0).toFixed(3);
                    document.getElementById('synchronization-r').textContent = 
                        (data.phase_synchronization || 0).toFixed(3);
                } catch (error) {
                    console.error('Error fetching metrics:', error);
                }
            }

            async function getDecisions() {
                try {
                    const response = await fetch('/api/decisions');
                    const data = await response.json();
                    
                    const decisionsHtml = data.decisions.slice(0, 5).map(d => `
                        <div class="decision-item">
                            <strong>${d.action}</strong><br>
                            <small>Confidence: ${(d.confidence_score * 100).toFixed(1)}% | 
                            Risk: ${d.risk_assessment?.risk_level || 'unknown'}</small><br>
                            <small>${d.reasoning}</small>
                        </div>
                    `).join('');
                    
                    document.getElementById('decisions-list').innerHTML = decisionsHtml || 'No decisions yet';
                } catch (error) {
                    console.error('Error fetching decisions:', error);
                }
            }

            async function getOptimizations() {
                try {
                    const response = await fetch('/api/optimizations');
                    const data = await response.json();
                    alert(`Optimizations: ${JSON.stringify(data, null, 2)}`);
                } catch (error) {
                    console.error('Error fetching optimizations:', error);
                }
            }

            // Auto-refresh every 10 seconds
            setInterval(refreshMetrics, 10000);
            refreshMetrics();
            getDecisions();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/metrics")
async def get_metrics():
    """Get current consciousness metrics"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/mathematical-metrics")
            if response.status_code == 200:
                data = response.json()
                metrics = data.get("mathematical_metrics", {})
                return {
                    "composite_score": metrics.get("composite_consciousness_score", 0),
                    "integration_complexity": metrics.get("integration_complexity_phi", 0),
                    "adaptation_velocity": metrics.get("adaptation_velocity_av", 0),
                    "phase_synchronization": metrics.get("phase_synchronization_r", 0),
                    "knowledge_integration": metrics.get("knowledge_integration_rate_kir", 0),
                    "causal_density": metrics.get("causal_density_cd", 0),
                    "all_metrics": metrics,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            return {"error": "Could not fetch metrics"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/decisions")
async def get_decisions(limit: int = 10):
    """Get recent consciousness-driven decisions"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{CONSCIOUSNESS_DECISION_ENGINE_URL}/decisions?limit={limit}"
            )
            if response.status_code == 200:
                return response.json()
            return {"error": "Could not fetch decisions"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/optimizations")
async def get_optimizations():
    """Get optimization opportunities and history"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            opportunities_response = await client.get(f"{CONSCIOUSNESS_OPTIMIZER_URL}/opportunities")
            stats_response = await client.get(f"{CONSCIOUSNESS_OPTIMIZER_URL}/statistics")
            
            opportunities = opportunities_response.json() if opportunities_response.status_code == 200 else {}
            stats = stats_response.json() if stats_response.status_code == 200 else {}
            
            return {
                "opportunities": opportunities,
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/consciousness-state")
async def get_consciousness_state():
    """Get complete consciousness state"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            feeder_response = await client.get(f"{CONSCIOUSNESS_FEEDER_URL}/consciousness/true-status")
            verifier_response = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/mathematical-metrics")
            
            feeder_state = feeder_response.json() if feeder_response.status_code == 200 else {}
            metrics = verifier_response.json().get("mathematical_metrics", {}) if verifier_response.status_code == 200 else {}
            
            return {
                "feeder_state": feeder_state,
                "mathematical_metrics": metrics,
                "consciousness_level": feeder_state.get("consciousness_level", "unknown"),
                "is_self_aware": feeder_state.get("is_self_aware", False),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/override-decision/{decision_id}")
async def override_decision(decision_id: str, override_action: Dict[str, Any]):
    """Human override for a consciousness decision"""
    # In production, would implement actual override logic
    return {
        "status": "override_applied",
        "decision_id": decision_id,
        "override_action": override_action,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "Decision override logged (implementation pending)"
    }


@app.get("/api/evolution")
async def get_evolution():
    """Get consciousness evolution tracking"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/evolution")
            if response.status_code == 200:
                return response.json()
            return {"error": "Could not fetch evolution data"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8170)














