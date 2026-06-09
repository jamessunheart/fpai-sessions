#!/usr/bin/env python3
"""
Full Potential Dashboard
========================
One interface for James to see everything.

Features:
- Status bar (green dot, current activity)
- Feed (all reports, chronological)
- Actions (pending decisions)
- Settings (preferences)
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from typing import Optional, List, Dict
from datetime import datetime
import json
import logging

logger = logging.getLogger("dashboard")

router = APIRouter(tags=["dashboard"])


def get_dashboard_data() -> Dict:
    """Gather all data for the dashboard."""
    data = {
        "status": {},
        "feed": [],
        "actions": [],
        "trading": {}
    }
    
    # Get presence status
    try:
        from presence import get_presence_status, get_state_emoji, get_state_label
        status = get_presence_status()
        data["status"] = {
            "state": status.state.value,
            "emoji": get_state_emoji(status.state),
            "label": get_state_label(status.state),
            "activities_today": status.activities_today,
            "queued_items": status.queued_items,
            "channels": status.channels_monitoring
        }
    except Exception as e:
        logger.debug(f"Presence error: {e}")
        data["status"] = {"state": "online", "emoji": "🟢", "label": "Online"}
    
    # Get trading data
    try:
        import requests
        with open("/opt/fpai/hyperliquid_credentials.json") as f:
            creds = json.load(f)
        
        r = requests.post("https://api.hyperliquid.xyz/info",
            json={"type": "clearinghouseState", "user": creds["main_account"]}, timeout=5)
        state = r.json()
        
        margin = state.get("marginSummary", {})
        data["trading"] = {
            "value": float(margin.get("accountValue", 0)),
            "positions": [
                {
                    "symbol": p["position"]["coin"],
                    "side": "LONG" if float(p["position"]["szi"]) > 0 else "SHORT",
                    "pnl": float(p["position"].get("unrealizedPnl", 0))
                }
                for p in state.get("assetPositions", [])
                if float(p["position"]["szi"]) != 0
            ]
        }
    except Exception as e:
        logger.debug(f"Trading error: {e}")
        data["trading"] = {"value": 0, "positions": []}
    
    # Get pending signals
    try:
        from signals import get_signal_engine
        engine = get_signal_engine()
        pending = engine.get_pending_signals()
        
        for sig in pending[:5]:
            data["feed"].append({
                "type": "signal",
                "channel": sig.channel,
                "sender": sig.sender,
                "summary": sig.content_summary,
                "priority": sig.priority.value,
                "time": sig.received_at
            })
    except Exception as e:
        logger.debug(f"Signals error: {e}")
    
    # Get pending public requests
    try:
        from public import get_handler
        handler = get_handler()
        pending = handler.get_pending_requests()
        
        for req in pending[:5]:
            data["actions"].append({
                "id": req.id,
                "type": "request",
                "from": req.sender_name,
                "message": req.message[:100],
                "priority": req.priority.value,
                "time": req.created_at
            })
    except Exception as e:
        logger.debug(f"Public handler error: {e}")
    
    return data


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Full Potential</title>
    <style>
        :root {
            --bg: #0a0a0f;
            --card: #12121a;
            --border: #2a2a3a;
            --text: #e8e8f0;
            --text-dim: #8888aa;
            --accent: #4ade80;
            --accent-dim: #22c55e20;
            --warning: #fbbf24;
            --danger: #ef4444;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px 0;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }
        
        .logo {
            font-size: 20px;
            font-weight: 600;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--accent-dim);
            border-radius: 20px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--accent);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-text {
            font-size: 14px;
            color: var(--accent);
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .summary-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }
        
        .summary-card h3 {
            font-size: 12px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        
        .summary-card .value {
            font-size: 28px;
            font-weight: 600;
        }
        
        .summary-card .change {
            font-size: 14px;
            color: var(--accent);
        }
        
        .section {
            margin-bottom: 24px;
        }
        
        .section-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .feed {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .feed-item {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
        }
        
        .feed-item.priority-0 { border-left: 3px solid var(--danger); }
        .feed-item.priority-1 { border-left: 3px solid var(--warning); }
        .feed-item.priority-2 { border-left: 3px solid var(--accent); }
        
        .feed-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 8px;
        }
        
        .feed-source {
            font-size: 13px;
            color: var(--text-dim);
        }
        
        .feed-time {
            font-size: 12px;
            color: var(--text-dim);
        }
        
        .feed-content {
            font-size: 15px;
            line-height: 1.5;
        }
        
        .feed-sender {
            font-weight: 600;
            color: var(--accent);
        }
        
        .actions-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .action-item {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
        }
        
        .action-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }
        
        .action-from {
            font-weight: 600;
        }
        
        .action-content {
            font-size: 14px;
            color: var(--text-dim);
            margin-bottom: 12px;
        }
        
        .action-buttons {
            display: flex;
            gap: 8px;
        }
        
        .btn {
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            border: none;
        }
        
        .btn-primary {
            background: var(--accent);
            color: var(--bg);
        }
        
        .btn-secondary {
            background: var(--border);
            color: var(--text);
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--text-dim);
        }
        
        .positions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
        }
        
        .position {
            background: var(--border);
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 13px;
        }
        
        .position.positive { color: var(--accent); }
        .position.negative { color: var(--danger); }
        
        .input-area {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            gap: 12px;
        }
        
        .input-area input {
            flex: 1;
            padding: 12px 16px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
        }
        
        .input-area input:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        .refresh-btn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            cursor: pointer;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">Full Potential</div>
            <div class="status-badge">
                <div class="status-dot"></div>
                <span class="status-text" id="status-label">JAI Online</span>
            </div>
        </header>
        
        <div class="summary-cards">
            <div class="summary-card">
                <h3>Treasury</h3>
                <div class="value" id="treasury-value">$0</div>
                <div class="positions" id="positions"></div>
            </div>
            <div class="summary-card">
                <h3>Today</h3>
                <div class="value" id="activities-count">0</div>
                <div class="change">activities handled</div>
            </div>
            <div class="summary-card">
                <h3>Pending</h3>
                <div class="value" id="pending-count">0</div>
                <div class="change">items queued</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📬 Actions Needed</h2>
            <div class="actions-list" id="actions-list">
                <div class="empty-state">No actions needed right now</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📋 Recent Activity</h2>
            <div class="feed" id="feed">
                <div class="empty-state">No recent activity</div>
            </div>
        </div>
        
        <div class="section">
            <div class="input-area">
                <input type="text" id="message-input" placeholder="Message JAI...">
                <button class="btn btn-primary" onclick="sendMessage()">Send</button>
            </div>
        </div>
    </div>
    
    <button class="refresh-btn" onclick="refresh()">🔄 Refresh</button>
    
    <script>
        async function loadDashboard() {
            try {
                const response = await fetch('/dashboard/data');
                const data = await response.json();
                
                // Update status
                document.getElementById('status-label').textContent = 
                    `JAI ${data.status.label || 'Online'}`;
                
                // Update treasury
                document.getElementById('treasury-value').textContent = 
                    `$${(data.trading.value || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}`;
                
                // Update positions
                const positionsEl = document.getElementById('positions');
                positionsEl.innerHTML = '';
                (data.trading.positions || []).forEach(p => {
                    const div = document.createElement('div');
                    div.className = `position ${p.pnl >= 0 ? 'positive' : 'negative'}`;
                    div.textContent = `${p.symbol} ${p.side} ${p.pnl >= 0 ? '+' : ''}$${p.pnl.toFixed(2)}`;
                    positionsEl.appendChild(div);
                });
                
                // Update counts
                document.getElementById('activities-count').textContent = 
                    data.status.activities_today || 0;
                document.getElementById('pending-count').textContent = 
                    data.status.queued_items || 0;
                
                // Update actions
                const actionsEl = document.getElementById('actions-list');
                if (data.actions && data.actions.length > 0) {
                    actionsEl.innerHTML = '';
                    data.actions.forEach(action => {
                        actionsEl.innerHTML += `
                            <div class="action-item">
                                <div class="action-header">
                                    <span class="action-from">${action.from}</span>
                                    <span class="feed-time">${formatTime(action.time)}</span>
                                </div>
                                <div class="action-content">${action.message}</div>
                                <div class="action-buttons">
                                    <button class="btn btn-primary">Reply</button>
                                    <button class="btn btn-secondary">Later</button>
                                </div>
                            </div>
                        `;
                    });
                }
                
                // Update feed
                const feedEl = document.getElementById('feed');
                if (data.feed && data.feed.length > 0) {
                    feedEl.innerHTML = '';
                    data.feed.forEach(item => {
                        feedEl.innerHTML += `
                            <div class="feed-item priority-${item.priority}">
                                <div class="feed-header">
                                    <span class="feed-source">${item.channel}</span>
                                    <span class="feed-time">${formatTime(item.time)}</span>
                                </div>
                                <div class="feed-content">
                                    <span class="feed-sender">${item.sender}</span>
                                    ${item.summary}
                                </div>
                            </div>
                        `;
                    });
                }
                
            } catch (error) {
                console.error('Dashboard load error:', error);
            }
        }
        
        function formatTime(isoString) {
            if (!isoString) return '';
            const date = new Date(isoString);
            return date.toLocaleTimeString([], {hour: 'numeric', minute: '2-digit'});
        }
        
        async function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            if (!message) return;
            
            try {
                const response = await fetch('/api/message', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                
                const data = await response.json();
                input.value = '';
                alert(data.response || 'Message sent');
                
            } catch (error) {
                console.error('Send error:', error);
            }
        }
        
        function refresh() {
            loadDashboard();
        }
        
        // Initial load
        loadDashboard();
        
        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);
        
        // Send on Enter
        document.getElementById('message-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>
"""


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard page."""
    return DASHBOARD_HTML


@router.get("/dashboard/data")
async def dashboard_data():
    """Get dashboard data as JSON."""
    return get_dashboard_data()


@router.get("/admin/fullpotential", response_class=HTMLResponse)
async def admin_dashboard():
    """Admin dashboard alias."""
    return DASHBOARD_HTML








