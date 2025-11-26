"""
Full Potential AI - Unified Admin Hub
======================================
Central admin dashboard at fullpotential.ai/admin

Features:
- Password setup (for nginx basic auth)
- API Gateway usage & billing
- Service health monitoring
- Mission control
- System metrics

Port: 8888 (replaces admin-gate)
"""

import os
import subprocess
import json
import httpx
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, render_template_string, redirect, session, jsonify
from functools import wraps

app = Flask(__name__)
app.secret_key = os.getenv("ADMIN_SECRET_KEY", "fpai-admin-secret-change-me")

# Configuration
HTPASSWD_FILE = "/etc/nginx/.htpasswd"
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Service endpoints (internal)
SERVICES = {
    "api-gateway": {"port": 8400, "name": "API Gateway", "icon": "⚡"},
    "mission-hub": {"port": 8700, "name": "Mission Hub", "icon": "🎯"},
    "harvester": {"port": 8055, "name": "Harvester", "icon": "🌾"},
    "registry": {"port": 8000, "name": "Registry", "icon": "📦"},
    "orchestrator": {"port": 8001, "name": "Orchestrator", "icon": "🎭"},
    "dashboard": {"port": 8002, "name": "Dashboard", "icon": "📊"},
    "whaletrack": {"port": 8600, "name": "WhaleTrack", "icon": "🐋"},
    "website": {"port": 3001, "name": "Website", "icon": "🌐"},
}


def is_password_set():
    """Check if admin password is configured"""
    return os.path.exists(HTPASSWD_FILE) and os.path.getsize(HTPASSWD_FILE) > 0


def require_auth(f):
    """Require authentication for protected routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_password_set():
            return redirect('/admin/setup')
        # For now, rely on nginx basic auth
        # In future, could add session-based auth here
        return f(*args, **kwargs)
    return decorated


async def check_service_health(name: str, port: int) -> dict:
    """Check if a service is healthy"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"http://127.0.0.1:{port}/health")
            if response.status_code == 200:
                return {"status": "healthy", "data": response.json()}
            return {"status": "unhealthy", "code": response.status_code}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


def get_api_gateway_stats():
    """Get API Gateway usage stats"""
    try:
        usage_file = Path("/Users/jamessunheart/FPAI_Cockpit/SERVICES/api-gateway/data/usage.json")
        if not usage_file.exists():
            # Try server path
            usage_file = Path("/root/FPAI_Cockpit/SERVICES/api-gateway/data/usage.json")
        
        if usage_file.exists():
            usage = json.loads(usage_file.read_text())
            total_cost = sum(u.get("cost_usd", 0) for u in usage)
            total_tokens = sum(u.get("input_tokens", 0) + u.get("output_tokens", 0) for u in usage)
            return {
                "total_requests": len(usage),
                "total_cost": round(total_cost, 2),
                "total_tokens": total_tokens,
                "recent": usage[-10:][::-1] if usage else []
            }
    except Exception as e:
        pass
    return {"total_requests": 0, "total_cost": 0, "total_tokens": 0, "recent": []}


# ============================================================
# HTML Templates
# ============================================================

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Hub - Full Potential AI</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Outfit', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        
        /* Header */
        .header {
            background: rgba(0,0,0,0.3);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .nav-links {
            display: flex;
            gap: 1.5rem;
        }
        
        .nav-links a {
            color: #888;
            text-decoration: none;
            font-size: 0.9rem;
            transition: color 0.2s;
        }
        
        .nav-links a:hover, .nav-links a.active {
            color: #00d4ff;
        }
        
        /* Main Content */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            color: #888;
            margin-bottom: 2rem;
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
        }
        
        .stat-card:hover {
            border-color: rgba(0,212,255,0.3);
            transform: translateY(-2px);
        }
        
        .stat-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #00d4ff;
        }
        
        .stat-label {
            color: #888;
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }
        
        /* Sections */
        .section {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        /* Services Grid */
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
        }
        
        .service-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            color: inherit;
        }
        
        .service-card:hover {
            background: rgba(255,255,255,0.08);
            border-color: rgba(0,212,255,0.3);
        }
        
        .service-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .service-name {
            font-weight: 500;
            margin-bottom: 0.25rem;
        }
        
        .service-status {
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 12px;
            display: inline-block;
        }
        
        .status-healthy { background: #22c55e33; color: #22c55e; }
        .status-unhealthy { background: #f59e0b33; color: #f59e0b; }
        .status-offline { background: #ef444433; color: #ef4444; }
        
        /* Table */
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        
        th {
            color: #888;
            font-weight: 500;
            font-size: 0.85rem;
        }
        
        /* Buttons */
        .btn {
            padding: 0.5rem 1rem;
            border-radius: 8px;
            border: none;
            font-weight: 500;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            color: white;
        }
        
        .btn-primary:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
        
        .btn-secondary {
            background: rgba(255,255,255,0.1);
            color: #e0e0e0;
        }
        
        /* Quick Actions */
        .quick-actions {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }
        
        /* Tabs */
        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 1rem;
        }
        
        .tab {
            padding: 0.5rem 1rem;
            border-radius: 8px;
            background: transparent;
            color: #888;
            border: none;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
        }
        
        .tab:hover {
            color: #e0e0e0;
        }
        
        .tab.active {
            background: rgba(0,212,255,0.2);
            color: #00d4ff;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Forms */
        .form-group {
            margin-bottom: 1rem;
        }
        
        .form-label {
            display: block;
            margin-bottom: 0.5rem;
            color: #888;
            font-size: 0.9rem;
        }
        
        .form-input {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            background: rgba(255,255,255,0.05);
            color: #e0e0e0;
            font-size: 1rem;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #00d4ff;
        }
        
        /* Alert */
        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .alert-success {
            background: #22c55e22;
            border: 1px solid #22c55e44;
            color: #22c55e;
        }
        
        .alert-error {
            background: #ef444422;
            border: 1px solid #ef444444;
            color: #ef4444;
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">⚡ Full Potential Admin</div>
        <nav class="nav-links">
            <a href="/admin" class="active">Dashboard</a>
            <a href="/admin/api-gateway">API Gateway</a>
            <a href="/admin/services">Services</a>
            <a href="/admin/setup">Security</a>
            <a href="/missions" target="_blank">Mission Hub →</a>
        </nav>
    </header>
    
    <div class="container">
        <h1>Admin Dashboard</h1>
        <p class="subtitle">System overview and quick actions</p>
        
        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon">⚡</div>
                <div class="stat-value">{{ stats.total_requests }}</div>
                <div class="stat-label">API Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💰</div>
                <div class="stat-value">${{ "%.2f"|format(stats.total_cost) }}</div>
                <div class="stat-label">Total Spend</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🔤</div>
                <div class="stat-value">{{ "{:,}".format(stats.total_tokens) }}</div>
                <div class="stat-label">Tokens Used</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">🟢</div>
                <div class="stat-value">{{ services_online }}/{{ services_total }}</div>
                <div class="stat-label">Services Online</div>
            </div>
        </div>
        
        <!-- Quick Actions -->
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">Quick Actions</h2>
            </div>
            <div class="quick-actions">
                <a href="/admin/api-gateway" class="btn btn-primary">📊 View API Usage</a>
                <a href="/missions" class="btn btn-secondary" target="_blank">🎯 Mission Hub</a>
                <a href="/services/harvester" class="btn btn-secondary" target="_blank">🌾 Harvester</a>
                <a href="/admin/setup" class="btn btn-secondary">🔐 Change Password</a>
            </div>
        </div>
        
        <!-- Services -->
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">Services</h2>
                <a href="/admin/services" class="btn btn-secondary">View All</a>
            </div>
            <div class="services-grid">
                {% for key, svc in services.items() %}
                <div class="service-card" onclick="window.open('http://{{ request.host.split(':')[0] }}:{{ svc.port }}', '_blank')">
                    <div class="service-icon">{{ svc.icon }}</div>
                    <div class="service-name">{{ svc.name }}</div>
                    <span class="service-status status-{{ svc.get('status', 'offline') }}">
                        {{ svc.get('status', 'checking...') }}
                    </span>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <!-- Recent API Usage -->
        <div class="section">
            <div class="section-header">
                <h2 class="section-title">Recent API Usage</h2>
                <a href="/admin/api-gateway" class="btn btn-secondary">View Details</a>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>User</th>
                        <th>Provider</th>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {% for u in stats.recent[:5] %}
                    <tr>
                        <td>{{ u.timestamp[:19] if u.timestamp else '-' }}</td>
                        <td>{{ u.user_id }}</td>
                        <td>{{ u.provider }}</td>
                        <td>{{ u.model[:25] }}...</td>
                        <td>{{ "{:,}".format(u.input_tokens + u.output_tokens) }}</td>
                        <td>${{ "%.4f"|format(u.cost_usd) }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" style="text-align: center; color: #666;">No API usage yet</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

SETUP_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Setup - Full Potential Admin</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Outfit', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        .card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 2.5rem;
            width: 100%;
            max-width: 420px;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        
        h1 {
            text-align: center;
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 2rem;
        }
        
        .form-group {
            margin-bottom: 1.25rem;
        }
        
        .form-label {
            display: block;
            margin-bottom: 0.5rem;
            color: #888;
            font-size: 0.9rem;
        }
        
        .form-input {
            width: 100%;
            padding: 0.875rem 1rem;
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 10px;
            background: rgba(255,255,255,0.05);
            color: #e0e0e0;
            font-size: 1rem;
        }
        
        .form-input:focus {
            outline: none;
            border-color: #00d4ff;
        }
        
        .form-input:disabled {
            background: rgba(255,255,255,0.02);
            color: #666;
        }
        
        .btn {
            width: 100%;
            padding: 0.875rem;
            border: none;
            border-radius: 10px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            color: white;
        }
        
        .btn-primary:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }
        
        .alert {
            padding: 1rem;
            border-radius: 10px;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }
        
        .alert-success {
            background: #22c55e22;
            border: 1px solid #22c55e44;
            color: #22c55e;
        }
        
        .alert-error {
            background: #ef444422;
            border: 1px solid #ef444444;
            color: #ef4444;
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        
        .status-set {
            background: #22c55e22;
            color: #22c55e;
        }
        
        .status-unset {
            background: #f59e0b22;
            color: #f59e0b;
        }
        
        .back-link {
            display: block;
            text-align: center;
            margin-top: 1.5rem;
            color: #888;
            text-decoration: none;
        }
        
        .back-link:hover {
            color: #00d4ff;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">⚡ Full Potential</div>
        <h1>🔐 Security Setup</h1>
        <p class="subtitle">Configure admin authentication</p>
        
        {% if message %}
            <div class="alert alert-{{ 'success' if status == 'success' else 'error' }}">
                {{ message }}
            </div>
        {% endif %}
        
        <div style="text-align: center;">
            {% if password_set %}
                <span class="status-badge status-set">✓ Password Configured</span>
            {% else %}
                <span class="status-badge status-unset">⚠ No Password Set</span>
            {% endif %}
        </div>
        
        <form method="POST">
            <div class="form-group">
                <label class="form-label">Username</label>
                <input type="text" name="username" value="admin" class="form-input" disabled>
            </div>
            
            <div class="form-group">
                <label class="form-label">{{ "New Password" if password_set else "Set Password" }}</label>
                <input type="password" name="password" class="form-input" placeholder="Minimum 8 characters" required minlength="8">
            </div>
            
            <button type="submit" class="btn btn-primary">
                {{ "Update Password" if password_set else "Set Password" }}
            </button>
        </form>
        
        {% if password_set %}
            <a href="/admin" class="back-link">← Back to Dashboard</a>
        {% endif %}
    </div>
</body>
</html>
"""

API_GATEWAY_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Gateway - Full Potential Admin</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Outfit', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        
        .header {
            background: rgba(0,0,0,0.3);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #00d4ff, #7c3aed);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .nav-links {
            display: flex;
            gap: 1.5rem;
        }
        
        .nav-links a {
            color: #888;
            text-decoration: none;
            font-size: 0.9rem;
            transition: color 0.2s;
        }
        
        .nav-links a:hover, .nav-links a.active {
            color: #00d4ff;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: #888; margin-bottom: 2rem; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: #00d4ff;
        }
        
        .stat-label {
            color: #888;
            font-size: 0.9rem;
            margin-top: 0.25rem;
        }
        
        .section {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        th, td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        
        th { color: #888; font-weight: 500; font-size: 0.85rem; }
        
        .provider-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.8rem;
            display: inline-block;
        }
        
        .provider-anthropic { background: #d97706aa; }
        .provider-openai { background: #10b981aa; }
        .provider-gemini { background: #3b82f6aa; }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">⚡ Full Potential Admin</div>
        <nav class="nav-links">
            <a href="/admin">Dashboard</a>
            <a href="/admin/api-gateway" class="active">API Gateway</a>
            <a href="/admin/services">Services</a>
            <a href="/admin/setup">Security</a>
        </nav>
    </header>
    
    <div class="container">
        <h1>⚡ API Gateway</h1>
        <p class="subtitle">Centralized AI API usage and billing</p>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ stats.total_requests }}</div>
                <div class="stat-label">Total Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${{ "%.2f"|format(stats.total_cost) }}</div>
                <div class="stat-label">Total Cost</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ "{:,}".format(stats.total_tokens) }}</div>
                <div class="stat-label">Total Tokens</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${{ "%.4f"|format(stats.total_cost / max(stats.total_requests, 1)) }}</div>
                <div class="stat-label">Avg Cost/Request</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">Usage by Provider</h2>
            <table>
                <thead>
                    <tr>
                        <th>Provider</th>
                        <th>Requests</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {% for provider, data in by_provider.items() %}
                    <tr>
                        <td><span class="provider-badge provider-{{ provider }}">{{ provider }}</span></td>
                        <td>{{ data.requests }}</td>
                        <td>{{ "{:,}".format(data.tokens) }}</td>
                        <td>${{ "%.4f"|format(data.cost_usd) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="4" style="text-align: center; color: #666;">No usage data</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">Recent Requests</h2>
            <table>
                <thead>
                    <tr>
                        <th>Time</th>
                        <th>User</th>
                        <th>Service</th>
                        <th>Provider</th>
                        <th>Model</th>
                        <th>Tokens</th>
                        <th>Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {% for u in stats.recent %}
                    <tr>
                        <td>{{ u.timestamp[:19] if u.timestamp else '-' }}</td>
                        <td>{{ u.user_id }}</td>
                        <td>{{ u.service_id }}</td>
                        <td><span class="provider-badge provider-{{ u.provider }}">{{ u.provider }}</span></td>
                        <td>{{ u.model[:30] }}...</td>
                        <td>{{ "{:,}".format(u.input_tokens + u.output_tokens) }}</td>
                        <td>${{ "%.4f"|format(u.cost_usd) }}</td>
                    </tr>
                    {% else %}
                    <tr><td colspan="7" style="text-align: center; color: #666;">No requests yet</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


# ============================================================
# Routes
# ============================================================

@app.route('/admin')
@app.route('/admin/')
def dashboard():
    """Main admin dashboard"""
    stats = get_api_gateway_stats()
    
    # Check service health (simplified - just check if port responds)
    services_online = 0
    for key, svc in SERVICES.items():
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', svc['port']))
            sock.close()
            if result == 0:
                SERVICES[key]['status'] = 'healthy'
                services_online += 1
            else:
                SERVICES[key]['status'] = 'offline'
        except:
            SERVICES[key]['status'] = 'offline'
    
    return render_template_string(
        ADMIN_TEMPLATE,
        stats=stats,
        services=SERVICES,
        services_online=services_online,
        services_total=len(SERVICES),
    )


@app.route('/admin/setup', methods=['GET', 'POST'])
def setup():
    """Password setup page"""
    message = None
    status = None
    
    if request.method == 'POST':
        password = request.form.get('password')
        username = "admin"
        
        if len(password) < 8:
            message = "Password must be at least 8 characters."
            status = "error"
        else:
            try:
                cmd = ["htpasswd", "-b", "-c", HTPASSWD_FILE, username, password]
                subprocess.run(cmd, check=True)
                subprocess.run(["systemctl", "reload", "nginx"], check=True)
                message = "Password updated successfully!"
                status = "success"
            except Exception as e:
                message = f"Error: {str(e)}"
                status = "error"
    
    return render_template_string(
        SETUP_TEMPLATE,
        message=message,
        status=status,
        password_set=is_password_set(),
    )


@app.route('/admin/api-gateway')
def api_gateway():
    """API Gateway usage dashboard"""
    stats = get_api_gateway_stats()
    
    # Group by provider
    by_provider = {}
    for u in stats.get('recent', []):
        provider = u.get('provider', 'unknown')
        if provider not in by_provider:
            by_provider[provider] = {'requests': 0, 'tokens': 0, 'cost_usd': 0}
        by_provider[provider]['requests'] += 1
        by_provider[provider]['tokens'] += u.get('input_tokens', 0) + u.get('output_tokens', 0)
        by_provider[provider]['cost_usd'] += u.get('cost_usd', 0)
    
    return render_template_string(
        API_GATEWAY_TEMPLATE,
        stats=stats,
        by_provider=by_provider,
    )


@app.route('/admin/services')
def services():
    """Services overview"""
    # Redirect to dashboard for now, can expand later
    return redirect('/admin')


@app.route('/admin/api/health')
def api_health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "admin-hub",
        "password_set": is_password_set(),
    })


# Legacy route compatibility
@app.route('/', methods=['GET', 'POST'])
def legacy_root():
    """Redirect legacy root to /admin or handle setup"""
    if request.method == 'POST' or not is_password_set():
        return setup()
    return redirect('/admin')


# ============================================================
# Run
# ============================================================

if __name__ == '__main__':
    print("🚀 Starting Admin Hub on port 8888...")
    app.run(host='0.0.0.0', port=8888, debug=False)

