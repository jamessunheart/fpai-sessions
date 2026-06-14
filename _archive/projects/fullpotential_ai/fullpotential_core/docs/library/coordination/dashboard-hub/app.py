#!/usr/bin/env python3
"""
Enhanced Dashboard Hub
A master dashboard showing all Full Potential AI dashboards with live status and metrics
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
import httpx
import asyncio
from datetime import datetime

app = FastAPI(title="Dashboard Hub")

# Dashboard configuration
DASHBOARDS = {
    "treasury": {
        "name": "Treasury Dashboard",
        "description": "$373K → $5T Journey - Capital management, P&L tracking, revenue projections, and financial vision for Full Potential AI.",
        "url": "/dashboard/treasury",
        "api_url": "http://127.0.0.1:8002/api/treasury/status",
        "category": "business",
        "icon": "💎",
        "port": 8002
    },
    "money": {
        "name": "Money Dashboard",
        "description": "Real-time financial tracking, revenue projections, session costs, and treasury management for Full Potential AI.",
        "url": "/dashboard/money",
        "api_url": "http://127.0.0.1:8002/api/treasury/status",
        "category": "business",
        "icon": "💰",
        "port": 8002
    },
    "coordination": {
        "name": "Coordination Dashboard",
        "description": "Real-time visualization of all Claude Code sessions, multi-agent coordination status, and distributed system health.",
        "url": "/dashboard/coordination",
        "api_url": "http://127.0.0.1:8031/api/status",
        "category": "monitoring",
        "icon": "🔄",
        "port": 8031
    },
    "coordination-simple": {
        "name": "Coordination Simple",
        "description": "Lightweight tabular view of session data, perfect for quick status checks and monitoring.",
        "url": "/dashboard/coordination-simple",
        "api_url": "http://127.0.0.1:8030/api/status",
        "category": "monitoring",
        "icon": "📊",
        "port": 8030
    }
}

SERVICES = {
    "registry": {"name": "Registry", "port": 8000, "icon": "📋"},
    "dashboard": {"name": "Dashboard", "port": 8002, "icon": "📊"},
    "church": {"name": "Church Guidance", "port": 8009, "icon": "⛪"},
    "i-match": {"name": "I MATCH", "port": 8010, "icon": "🤝"},
    "master": {"name": "Master Control", "port": 8026, "icon": "🎛️"},
}

async def check_service_health(url: str, timeout: float = 2.0) -> dict:
    """Check if a service is responding"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
            return {
                "status": "online" if response.status_code < 500 else "degraded",
                "response_time": response.elapsed.total_seconds() * 1000,
                "status_code": response.status_code
            }
    except httpx.TimeoutException:
        return {"status": "timeout", "response_time": None, "status_code": None}
    except Exception as e:
        return {"status": "offline", "response_time": None, "status_code": None, "error": str(e)}

async def get_dashboard_metrics(api_url: str) -> dict:
    """Get metrics from a dashboard's API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url, timeout=3.0)
            if response.status_code == 200:
                return response.json()
            return {}
    except:
        return {}

@app.get("/", response_class=HTMLResponse)
async def dashboard_hub():
    """Serve the enhanced dashboard hub HTML"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Potential AI - Dashboard Hub</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #16213e 50%, #0a0e27 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }

        .header {
            max-width: 1400px;
            margin: 0 auto 40px;
            text-align: center;
        }

        .header h1 {
            font-size: 42px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .header .subtitle {
            color: #a0a0a0;
            font-size: 16px;
            margin-bottom: 20px;
        }

        .header .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-top: 20px;
            flex-wrap: wrap;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 15px 25px;
            min-width: 150px;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
        }

        .stat-label {
            font-size: 12px;
            color: #a0a0a0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }

        .search-bar {
            max-width: 600px;
            margin: 0 auto 30px;
        }

        .search-bar input {
            width: 100%;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            color: #e0e0e0;
            font-size: 16px;
            transition: all 0.3s;
        }

        .search-bar input:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255,255,255,0.08);
        }

        .search-bar input::placeholder {
            color: #666;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .section {
            margin-bottom: 50px;
        }

        .section-title {
            font-size: 24px;
            color: #667eea;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }

        .dashboard-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 25px;
            transition: all 0.3s ease;
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }

        .dashboard-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transform: scaleX(0);
            transition: transform 0.3s ease;
        }

        .dashboard-card:hover {
            background: rgba(255,255,255,0.08);
            border-color: #667eea;
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(102,126,234,0.3);
        }

        .dashboard-card:hover::before {
            transform: scaleX(1);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }

        .card-title {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-icon {
            font-size: 28px;
        }

        .card-title h3 {
            color: #e0e0e0;
            font-size: 20px;
            margin: 0;
        }

        .status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status-badge.online {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .status-badge.offline {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .status-badge.loading {
            background: rgba(250, 204, 21, 0.2);
            color: #facc15;
            border: 1px solid rgba(250, 204, 21, 0.3);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: currentColor;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .card-description {
            color: #b0b0b0;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 20px;
            min-height: 60px;
        }

        .card-metrics {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
            padding-top: 15px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        .metric {
            text-align: center;
        }

        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }

        .metric-label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            margin-top: 4px;
        }

        .card-footer {
            display: flex;
            gap: 10px;
        }

        .btn {
            flex: 1;
            padding: 12px 20px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
            text-align: center;
            transition: all 0.2s;
            border: none;
            cursor: pointer;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102,126,234,0.4);
        }

        .btn-secondary {
            background: rgba(255,255,255,0.05);
            color: #a0a0a0;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.08);
            color: #e0e0e0;
        }

        .service-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }

        .service-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 15px;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.2s;
        }

        .service-card:hover {
            background: rgba(255,255,255,0.05);
            border-color: rgba(102,126,234,0.5);
        }

        .service-icon {
            font-size: 24px;
        }

        .service-info {
            flex: 1;
        }

        .service-name {
            font-size: 14px;
            font-weight: 600;
            color: #e0e0e0;
        }

        .service-port {
            font-size: 11px;
            color: #666;
        }

        .service-status {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
        }

        .service-status.online {
            background: #10b981;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
        }

        .service-status.offline {
            background: #ef4444;
            box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
        }

        .last-update {
            text-align: center;
            color: #666;
            font-size: 12px;
            margin-top: 40px;
        }

        .filter-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .filter-tab {
            padding: 8px 16px;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            color: #a0a0a0;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .filter-tab.active {
            background: rgba(102,126,234,0.2);
            border-color: #667eea;
            color: #667eea;
        }

        .filter-tab:hover {
            background: rgba(255,255,255,0.08);
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎛️ Full Potential AI</h1>
        <p class="subtitle">Master Dashboard Hub - Real-time System Monitoring</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="total-dashboards">-</div>
                <div class="stat-label">Dashboards</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="services-online">-</div>
                <div class="stat-label">Services Online</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="active-sessions">-</div>
                <div class="stat-label">Active Sessions</div>
            </div>
        </div>
    </div>

    <div class="container">
        <div class="search-bar">
            <input type="text" id="search-input" placeholder="🔍 Search dashboards and services..." />
        </div>

        <div class="filter-tabs">
            <div class="filter-tab active" data-filter="all">All</div>
            <div class="filter-tab" data-filter="monitoring">Monitoring</div>
            <div class="filter-tab" data-filter="business">Business</div>
            <div class="filter-tab" data-filter="technical">Technical</div>
        </div>

        <div class="section">
            <h2 class="section-title">📊 Dashboards</h2>
            <div class="dashboard-grid" id="dashboard-grid">
                <!-- Dashboards will be inserted here -->
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">🔧 Backend Services</h2>
            <div class="service-grid" id="service-grid">
                <!-- Services will be inserted here -->
            </div>
        </div>

        <div class="last-update">
            Last updated: <span id="last-update-time">-</span>
            <br>
            Auto-refreshing every 10 seconds
        </div>
    </div>

    <script>
        let currentFilter = 'all';
        let searchQuery = '';

        async function fetchHubData() {
            try {
                const response = await fetch('/dashboard/api/hub-status');
                const data = await response.json();
                renderDashboards(data.dashboards);
                renderServices(data.services);
                updateStats(data);
                updateLastUpdateTime();
            } catch (error) {
                console.error('Failed to fetch hub data:', error);
            }
        }

        function renderDashboards(dashboards) {
            const grid = document.getElementById('dashboard-grid');
            grid.innerHTML = '';

            Object.entries(dashboards).forEach(([key, dashboard]) => {
                if (!matchesFilter(dashboard) || !matchesSearch(dashboard)) return;

                const card = document.createElement('div');
                card.className = 'dashboard-card';
                card.onclick = () => window.location.href = dashboard.url;

                const statusClass = dashboard.health?.status === 'online' ? 'online' :
                                  dashboard.health?.status === 'offline' ? 'offline' : 'loading';

                const metrics = dashboard.metrics || {};

                card.innerHTML = `
                    <div class="card-header">
                        <div class="card-title">
                            <span class="card-icon">${dashboard.icon}</span>
                            <h3>${dashboard.name}</h3>
                        </div>
                        <span class="status-badge ${statusClass}">
                            <span class="status-dot"></span>
                            ${statusClass}
                        </span>
                    </div>
                    <p class="card-description">${dashboard.description}</p>
                    ${metrics.total_sessions !== undefined ? `
                    <div class="card-metrics">
                        <div class="metric">
                            <div class="metric-value">${metrics.total_sessions || 0}</div>
                            <div class="metric-label">Sessions</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${metrics.active_sessions || 0}</div>
                            <div class="metric-label">Active</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">${metrics.total_registered || 0}</div>
                            <div class="metric-label">Registered</div>
                        </div>
                    </div>
                    ` : ''}
                    <div class="card-footer">
                        <a href="${dashboard.url}" class="btn btn-primary" onclick="event.stopPropagation()">
                            Open Dashboard →
                        </a>
                    </div>
                `;

                grid.appendChild(card);
            });
        }

        function renderServices(services) {
            const grid = document.getElementById('service-grid');
            grid.innerHTML = '';

            Object.entries(services).forEach(([key, service]) => {
                const card = document.createElement('div');
                card.className = 'service-card';

                const statusClass = service.health?.status === 'online' ? 'online' : 'offline';

                card.innerHTML = `
                    <span class="service-icon">${service.icon}</span>
                    <div class="service-info">
                        <div class="service-name">${service.name}</div>
                        <div class="service-port">Port ${service.port}</div>
                    </div>
                    <div class="service-status ${statusClass}"></div>
                `;

                grid.appendChild(card);
            });
        }

        function updateStats(data) {
            document.getElementById('total-dashboards').textContent = Object.keys(data.dashboards).length;

            const onlineServices = Object.values(data.services).filter(
                s => s.health?.status === 'online'
            ).length;
            document.getElementById('services-online').textContent =
                `${onlineServices}/${Object.keys(data.services).length}`;

            // Get active sessions from coordination dashboard metrics
            const coordMetrics = data.dashboards.coordination?.metrics;
            document.getElementById('active-sessions').textContent =
                coordMetrics?.active_sessions || 0;
        }

        function updateLastUpdateTime() {
            const now = new Date();
            document.getElementById('last-update-time').textContent =
                now.toLocaleTimeString();
        }

        function matchesFilter(dashboard) {
            if (currentFilter === 'all') return true;
            return dashboard.category === currentFilter;
        }

        function matchesSearch(dashboard) {
            if (!searchQuery) return true;
            const query = searchQuery.toLowerCase();
            return dashboard.name.toLowerCase().includes(query) ||
                   dashboard.description.toLowerCase().includes(query);
        }

        // Event listeners
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                currentFilter = tab.dataset.filter;
                fetchHubData();
            });
        });

        document.getElementById('search-input').addEventListener('input', (e) => {
            searchQuery = e.target.value;
            fetchHubData();
        });

        // Initial load and auto-refresh
        fetchHubData();
        setInterval(fetchHubData, 10000); // Refresh every 10 seconds
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/hub-status")
async def get_hub_status():
    """Get status of all dashboards and services"""

    # Check health for all dashboards
    dashboard_data = {}
    for key, config in DASHBOARDS.items():
        health = await check_service_health(f"http://127.0.0.1:{config['port']}/")
        metrics = await get_dashboard_metrics(config['api_url']) if health['status'] == 'online' else {}

        dashboard_data[key] = {
            **config,
            "health": health,
            "metrics": metrics
        }

    # Check health for all services
    service_data = {}
    for key, config in SERVICES.items():
        health = await check_service_health(f"http://198.54.123.234:{config['port']}/health")
        service_data[key] = {
            **config,
            "health": health
        }

    return JSONResponse({
        "dashboards": dashboard_data,
        "services": service_data,
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8035)
