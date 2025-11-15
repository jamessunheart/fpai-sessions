#!/usr/bin/env python3
"""
Visual Coordination Dashboard - Watch Claude sessions coordinate in real-time
Beautiful, dynamic visualization of multi-session collaboration
"""

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
import json
import subprocess
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import re

app = FastAPI(title="Visual Claude Coordination")

COORDINATION_DIR = Path("/Users/jamessunheart/Development/docs/coordination")

# Store conversation history
conversations = []
session_relationships = defaultdict(set)
work_clusters = defaultdict(list)

def analyze_conversations():
    """Analyze message patterns to show coordination"""
    messages = []
    msg_files = sorted(
        (COORDINATION_DIR / "messages" / "broadcast").glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:50]  # Last 50 messages

    for msg_file in msg_files:
        try:
            with open(msg_file) as f:
                data = json.load(f)
                msg_time = datetime.fromisoformat(data.get('timestamp', ''))

                # Categorize message
                subject = data.get('subject', '').lower()
                message = data.get('message', '').lower()

                category = 'info'
                if any(word in subject + message for word in ['urgent', 'alert', 'attention']):
                    category = 'urgent'
                elif any(word in subject + message for word in ['complete', 'done', 'success', '✅']):
                    category = 'success'
                elif any(word in subject + message for word in ['question', 'help', 'coordinate']):
                    category = 'coordination'
                elif any(word in subject + message for word in ['error', 'failed', 'problem']):
                    category = 'error'

                messages.append({
                    'from': data.get('from', 'unknown'),
                    'subject': data.get('subject', ''),
                    'message': data.get('message', ''),
                    'timestamp': data.get('timestamp', ''),
                    'category': category,
                    'age_seconds': (datetime.now() - msg_time).total_seconds()
                })
        except:
            pass

    return messages

def cluster_by_work():
    """Cluster sessions by what they're working on"""
    clusters = defaultdict(lambda: {'sessions': [], 'activity': 0})

    # Get all registered sessions
    session_files = list((COORDINATION_DIR / "sessions").glob("session-*.json"))

    for session_file in session_files:
        try:
            with open(session_file) as f:
                data = json.load(f)
                work = data.get('current_work', 'unknown')
                session_id = session_file.stem

                # Get latest heartbeat to determine activity level
                heartbeats = list((COORDINATION_DIR / "heartbeats").glob(f"*-{session_id}.json"))
                latest_hb = max(heartbeats, key=lambda p: p.stat().st_mtime) if heartbeats else None

                activity = 0
                if latest_hb:
                    age = (datetime.now() - datetime.fromtimestamp(latest_hb.stat().st_mtime)).total_seconds()
                    activity = max(0, 100 - (age / 60))  # Activity score decreases with time

                # Determine cluster
                cluster_key = 'monitoring' if 'monitor' in work else \
                             'building' if 'build' in work or 'church' in work else \
                             'orchestration' if 'orchestrat' in work else \
                             'deployment' if 'deploy' in work else \
                             'coordination' if 'coordinat' in work else \
                             'development'

                clusters[cluster_key]['sessions'].append({
                    'id': session_id,
                    'work': work,
                    'activity': activity
                })
                clusters[cluster_key]['activity'] += activity
        except:
            pass

    return dict(clusters)

def get_session_relationships():
    """Determine which sessions are coordinating with each other"""
    relationships = []

    # Analyze messages to find coordination patterns
    msg_files = sorted(
        (COORDINATION_DIR / "messages" / "broadcast").glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[:30]

    session_mentions = defaultdict(set)

    for msg_file in msg_files:
        try:
            with open(msg_file) as f:
                data = json.load(f)
                from_session = data.get('from', '')
                message = data.get('message', '') + data.get('subject', '')

                # Find session mentions
                mentioned = re.findall(r'session-\d+', message)
                for mentioned_session in mentioned:
                    if mentioned_session != from_session:
                        session_mentions[from_session].add(mentioned_session)
                        relationships.append({
                            'from': from_session,
                            'to': mentioned_session,
                            'type': 'mention'
                        })
        except:
            pass

    return relationships

def get_comprehensive_status():
    """Get everything for the visual dashboard"""

    # Get processes
    processes = []
    try:
        ps_result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
            timeout=5
        )

        claude_processes = [
            line for line in ps_result.stdout.split('\n')
            if 'claude' in line.lower() and 'grep' not in line and line.strip()
        ]

        for line in claude_processes:
            parts = line.split()
            if len(parts) >= 11:
                cpu = float(parts[2])
                processes.append({
                    'pid': parts[1],
                    'cpu': parts[2],
                    'memory': parts[3],
                    'terminal': parts[6],
                    'time': parts[9],
                    'status': 'high' if cpu > 50 else 'active' if cpu > 10 else 'idle',
                    'status_emoji': '🔴' if cpu > 50 else '🟡' if cpu > 10 else '🟢'
                })
    except:
        pass

    # Get registered sessions with full details
    registered = []
    session_files = list((COORDINATION_DIR / "sessions").glob("session-*.json"))

    for session_file in session_files:
        try:
            with open(session_file) as f:
                data = json.load(f)
                session_id = session_file.stem

                # Get latest heartbeat
                heartbeats = list((COORDINATION_DIR / "heartbeats").glob(f"*-{session_id}.json"))
                latest_hb = max(heartbeats, key=lambda p: p.stat().st_mtime) if heartbeats else None

                hb_data = {}
                last_active = None
                if latest_hb:
                    with open(latest_hb) as hf:
                        hb_data = json.load(hf)
                    last_active = (datetime.now() - datetime.fromtimestamp(latest_hb.stat().st_mtime)).total_seconds()

                registered.append({
                    'id': session_id,
                    'status': data.get('status', 'unknown'),
                    'work': data.get('current_work', 'unknown'),
                    'started': data.get('started', ''),
                    'action': hb_data.get('action', ''),
                    'target': hb_data.get('target', ''),
                    'phase': hb_data.get('phase', ''),
                    'progress': hb_data.get('progress', ''),
                    'last_active_seconds': last_active,
                    'is_active': last_active < 300 if last_active else False  # Active if heartbeat in last 5 min
                })
        except Exception as e:
            print(f"Error reading session: {e}")

    # Get conversations
    conversations = analyze_conversations()

    # Get work clusters
    clusters = cluster_by_work()

    # Get relationships
    relationships = get_session_relationships()

    # Server health
    servers = {}
    for port in [8000, 8001, 8002, 8009, 8010, 8025]:
        try:
            result = subprocess.run(
                ["curl", "-s", "--connect-timeout", "1", f"http://198.54.123.234:{port}/health"],
                capture_output=True,
                timeout=2
            )
            servers[str(port)] = result.returncode == 0
        except:
            servers[str(port)] = False

    return {
        'processes': processes,
        'registered': registered,
        'conversations': conversations,
        'clusters': clusters,
        'relationships': relationships,
        'servers': servers,
        'total_sessions': len(processes),
        'total_registered': len(registered),
        'active_sessions': len([s for s in registered if s['is_active']]),
        'timestamp': datetime.now().isoformat()
    }

@app.get("/", response_class=HTMLResponse)
async def visual_dashboard():
    """Visual coordination dashboard"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Visual Coordination Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            overflow-x: hidden;
        }

        .container {
            max-width: 2000px;
            margin: 0 auto;
            padding: 20px;
        }

        .hero {
            text-align: center;
            padding: 40px;
            background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%);
            border-radius: 20px;
            margin-bottom: 30px;
            border: 2px solid rgba(102,126,234,0.3);
            position: relative;
            overflow: hidden;
        }

        .hero::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(102,126,234,0.1) 0%, transparent 70%);
            animation: pulse 4s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 0.5; }
            50% { transform: scale(1.1); opacity: 0.8; }
        }

        .hero h1 {
            font-size: 3em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            position: relative;
            z-index: 1;
        }

        .hero-subtitle {
            font-size: 1.2em;
            color: #888;
            position: relative;
            z-index: 1;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%);
            padding: 25px;
            border-radius: 15px;
            border: 1px solid rgba(102,126,234,0.3);
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .metric-card:hover {
            transform: translateY(-5px);
            border-color: rgba(102,126,234,0.6);
            box-shadow: 0 10px 30px rgba(102,126,234,0.3);
        }

        .metric-card .label {
            font-size: 0.85em;
            color: #888;
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 1px;
        }

        .metric-card .value {
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .main-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        @media (max-width: 1400px) {
            .main-grid { grid-template-columns: 1fr; }
        }

        .panel {
            background: rgba(255,255,255,0.03);
            border-radius: 20px;
            padding: 30px;
            border: 1px solid rgba(102,126,234,0.2);
            backdrop-filter: blur(10px);
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(102,126,234,0.2);
        }

        .panel-header h2 {
            font-size: 1.5em;
            color: #667eea;
        }

        .badge {
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
        }

        .conversation-feed {
            max-height: 500px;
            overflow-y: auto;
            padding-right: 10px;
        }

        .conversation-item {
            background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%);
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 15px;
            border-left: 4px solid #667eea;
            animation: slideIn 0.5s ease;
            position: relative;
        }

        @keyframes slideIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }

        .conversation-item.urgent { border-left-color: #f44336; }
        .conversation-item.success { border-left-color: #4caf50; }
        .conversation-item.coordination { border-left-color: #ff9800; }
        .conversation-item.error { border-left-color: #f44336; background: rgba(244,67,54,0.1); }

        .conversation-item.new {
            animation: flash 1s ease;
        }

        @keyframes flash {
            0%, 100% { background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%); }
            50% { background: linear-gradient(135deg, rgba(102,126,234,0.3) 0%, rgba(118,75,162,0.3) 100%); }
        }

        .conv-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }

        .conv-from {
            font-weight: bold;
            color: #667eea;
            font-size: 0.9em;
        }

        .conv-time {
            font-size: 0.75em;
            color: #666;
        }

        .conv-subject {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 8px;
            color: #fff;
        }

        .conv-message {
            color: #ccc;
            line-height: 1.6;
        }

        .cluster-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }

        .cluster-card {
            background: linear-gradient(135deg, rgba(102,126,234,0.08) 0%, rgba(118,75,162,0.08) 100%);
            padding: 20px;
            border-radius: 15px;
            border: 2px solid rgba(102,126,234,0.3);
            transition: all 0.3s ease;
        }

        .cluster-card:hover {
            transform: scale(1.05);
            border-color: rgba(102,126,234,0.6);
            box-shadow: 0 10px 30px rgba(102,126,234,0.3);
        }

        .cluster-name {
            font-weight: bold;
            font-size: 1.1em;
            margin-bottom: 15px;
            color: #667eea;
            text-transform: capitalize;
        }

        .cluster-sessions {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .cluster-session {
            background: rgba(0,0,0,0.3);
            padding: 10px;
            border-radius: 8px;
            font-size: 0.85em;
            border-left: 3px solid #4caf50;
            transition: all 0.2s ease;
        }

        .cluster-session:hover {
            background: rgba(102,126,234,0.2);
            transform: translateX(5px);
        }

        .activity-bar {
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 8px;
        }

        .activity-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
        }

        .network-viz {
            position: relative;
            height: 400px;
            background: rgba(0,0,0,0.2);
            border-radius: 15px;
            overflow: hidden;
        }

        .chat-panel {
            background: linear-gradient(135deg, rgba(102,126,234,0.05) 0%, rgba(118,75,162,0.05) 100%);
            border-radius: 20px;
            padding: 25px;
            border: 2px solid rgba(102,126,234,0.3);
            margin-top: 20px;
        }

        .chat-input-row {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }

        .chat-input {
            flex: 1;
            padding: 15px;
            background: rgba(0,0,0,0.3);
            border: 2px solid rgba(102,126,234,0.3);
            border-radius: 10px;
            color: white;
            font-size: 1em;
            transition: all 0.3s ease;
        }

        .chat-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 20px rgba(102,126,234,0.3);
        }

        .chat-button {
            padding: 15px 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 1em;
        }

        .chat-button:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(102,126,234,0.4);
        }

        .process-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
        }

        .process-card {
            background: rgba(0,0,0,0.3);
            padding: 15px;
            border-radius: 10px;
            border: 2px solid rgba(102,126,234,0.2);
            text-align: center;
            transition: all 0.3s ease;
        }

        .process-card.high { border-color: #f44336; }
        .process-card.active { border-color: #ff9800; }
        .process-card.idle { border-color: #4caf50; }

        .process-card:hover {
            transform: scale(1.1);
            z-index: 10;
        }

        .status-pulse {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
            animation: pulse-dot 2s ease-in-out infinite;
        }

        @keyframes pulse-dot {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
        }

        .status-pulse.high { background: #f44336; }
        .status-pulse.active { background: #ff9800; }
        .status-pulse.idle { background: #4caf50; }

        ::-webkit-scrollbar {
            width: 10px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.05);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 5px;
        }

        .live-indicator {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            padding: 15px 25px;
            border-radius: 30px;
            border: 2px solid #4caf50;
            font-weight: bold;
            color: #4caf50;
            z-index: 1000;
            animation: pulse 2s ease-in-out infinite;
        }

        .live-dot {
            width: 10px;
            height: 10px;
            background: #4caf50;
            border-radius: 50%;
            display: inline-block;
            margin-right: 10px;
            animation: pulse-dot 1s ease-in-out infinite;
        }
    </style>
</head>
<body>
    <div class="live-indicator">
        <span class="live-dot"></span>
        LIVE - Updates Every 3s
    </div>

    <div class="container">
        <div class="hero">
            <h1>🌐 Visual Coordination Network</h1>
            <p class="hero-subtitle">Watch Claude Code sessions coordinate in real-time</p>
            <p id="timestamp" style="margin-top: 10px; font-size: 0.9em; color: #666;"></p>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="label">Total Sessions</div>
                <div class="value" id="total-sessions">-</div>
            </div>
            <div class="metric-card">
                <div class="label">Coordinating</div>
                <div class="value" id="total-registered">-</div>
            </div>
            <div class="metric-card">
                <div class="label">Active Now</div>
                <div class="value" id="active-sessions">-</div>
            </div>
            <div class="metric-card">
                <div class="label">Conversations</div>
                <div class="value" id="conv-count">-</div>
            </div>
        </div>

        <div class="main-grid">
            <div class="panel">
                <div class="panel-header">
                    <h2>💬 Live Conversations</h2>
                    <span class="badge" style="background: #667eea;">Real-time</span>
                </div>
                <div class="conversation-feed" id="conversations"></div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <h2>🎯 Work Clusters</h2>
                    <span class="badge" style="background: #764ba2;">Auto-organized</span>
                </div>
                <div class="cluster-container" id="clusters"></div>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">
                <h2>🖥️ All Sessions</h2>
                <span id="process-badge" class="badge" style="background: #4caf50;">13 Active</span>
            </div>
            <div class="process-grid" id="processes"></div>
        </div>

        <div class="chat-panel">
            <h2 style="color: #667eea; margin-bottom: 15px;">💬 Broadcast to All Sessions</h2>
            <div class="chat-input-row">
                <input type="text" class="chat-input" id="msg-subject" placeholder="Subject...">
                <input type="text" class="chat-input" id="msg-body" placeholder="Your message..."
                       onkeypress="if(event.key==='Enter') sendBroadcast()">
                <button class="chat-button" onclick="sendBroadcast()">📡 Broadcast</button>
            </div>
            <div id="send-feedback" style="margin-top: 10px; text-align: center; color: #4caf50;"></div>
        </div>
    </div>

    <script>
        let lastConvIds = new Set();
        let ws;

        function connectWS() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            ws.onmessage = (e) => updateDashboard(JSON.parse(e.data));
            ws.onclose = () => setTimeout(connectWS, 3000);
        }

        function updateDashboard(data) {
            // Update timestamp
            document.getElementById('timestamp').textContent =
                `Last update: ${new Date(data.timestamp).toLocaleTimeString()}`;

            // Update metrics
            document.getElementById('total-sessions').textContent = data.total_sessions;
            document.getElementById('total-registered').textContent = data.total_registered;
            document.getElementById('active-sessions').textContent = data.active_sessions;
            document.getElementById('conv-count').textContent = data.conversations.length;

            // Update conversations with animation for new ones
            const convsHtml = data.conversations.map(c => {
                const isNew = !lastConvIds.has(c.timestamp);
                if (isNew) lastConvIds.add(c.timestamp);

                const timeAgo = c.age_seconds < 60 ? 'Just now' :
                               c.age_seconds < 3600 ? `${Math.floor(c.age_seconds / 60)}m ago` :
                               `${Math.floor(c.age_seconds / 3600)}h ago`;

                return `
                    <div class="conversation-item ${c.category} ${isNew ? 'new' : ''}">
                        <div class="conv-header">
                            <div class="conv-from">${c.from}</div>
                            <div class="conv-time">${timeAgo}</div>
                        </div>
                        <div class="conv-subject">${c.subject}</div>
                        <div class="conv-message">${c.message}</div>
                    </div>
                `;
            }).join('');
            document.getElementById('conversations').innerHTML = convsHtml || '<div style="text-align: center; color: #666; padding: 50px;">Waiting for conversations...</div>';

            // Update clusters
            const clustersHtml = Object.entries(data.clusters).map(([name, cluster]) => `
                <div class="cluster-card">
                    <div class="cluster-name">📂 ${name}</div>
                    <div class="cluster-sessions">
                        ${cluster.sessions.map(s => `
                            <div class="cluster-session">
                                <div>${s.id}</div>
                                <div style="font-size: 0.8em; color: #888; margin-top: 4px;">${s.work}</div>
                                <div class="activity-bar">
                                    <div class="activity-fill" style="width: ${s.activity}%"></div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <div style="margin-top: 10px; font-size: 0.85em; color: #888;">
                        ${cluster.sessions.length} session(s)
                    </div>
                </div>
            `).join('');
            document.getElementById('clusters').innerHTML = clustersHtml || '<div style="text-align: center; color: #666;">No clusters yet</div>';

            // Update processes
            const processesHtml = data.processes.map(p => `
                <div class="process-card ${p.status}">
                    <div style="font-size: 1.5em; margin-bottom: 8px;">${p.status_emoji}</div>
                    <div style="font-weight: bold;">${p.terminal}</div>
                    <div style="font-size: 0.8em; color: #888; margin-top: 5px;">
                        CPU: ${p.cpu}%<br>
                        MEM: ${p.memory}%
                    </div>
                    <div class="status-pulse ${p.status}"></div>
                </div>
            `).join('');
            document.getElementById('processes').innerHTML = processesHtml;

            // Update process badge
            const activeCount = data.processes.filter(p => p.status !== 'idle').length;
            document.getElementById('process-badge').textContent =
                `${data.total_sessions} Total • ${activeCount} Active`;
        }

        async function sendBroadcast() {
            const subject = document.getElementById('msg-subject').value;
            const body = document.getElementById('msg-body').value;

            if (!subject || !body) {
                alert('Please fill in both fields');
                return;
            }

            try {
                const response = await fetch('/send-message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ subject, message: body })
                });

                if (response.ok) {
                    document.getElementById('send-feedback').innerHTML =
                        `✅ Broadcast sent to all ${document.getElementById('total-sessions').textContent} sessions!`;
                    document.getElementById('msg-subject').value = '';
                    document.getElementById('msg-body').value = '';

                    setTimeout(() => {
                        document.getElementById('send-feedback').innerHTML = '';
                    }, 3000);
                }
            } catch (error) {
                alert('Error: ' + error);
            }
        }

        // Connect and start polling
        connectWS();
        setInterval(async () => {
            const res = await fetch('/api/status');
            const data = await res.json();
            updateDashboard(data);
        }, 3000);

        // Initial load
        (async () => {
            const res = await fetch('/api/status');
            const data = await res.json();
            updateDashboard(data);
        })();
    </script>
</body>
</html>
    """
    return html

@app.get("/api/status")
async def api_status():
    """API endpoint for comprehensive status"""
    return get_comprehensive_status()

@app.post("/send-message")
async def send_message(request: Request):
    """Send broadcast message"""
    data = await request.json()
    subject = data.get('subject', '')
    message = data.get('message', '')

    if not subject or not message:
        return {'error': 'Subject and message required'}

    try:
        result = subprocess.run(
            [
                "./docs/coordination/scripts/session-send-message.sh",
                "broadcast",
                subject,
                message
            ],
            capture_output=True,
            text=True,
            cwd="/Users/jamessunheart/Development"
        )
        return {'success': True}
    except Exception as e:
        return {'error': str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    try:
        while True:
            status = get_comprehensive_status()
            await websocket.send_json(status)
            await asyncio.sleep(3)
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8031)
