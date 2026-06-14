#!/usr/bin/env python3
"""
Multi-Session Coordination Dashboard
Web interface for monitoring all Claude Code sessions with chat
"""

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path

app = FastAPI(title="Claude Code Coordination Dashboard")

COORDINATION_DIR = Path("/Users/jamessunheart/Development/docs/coordination")

def get_session_status():
    """Get comprehensive status of all sessions"""
    try:
        # Run the status aggregator
        result = subprocess.run(
            ["./docs/coordination/scripts/auto-status-aggregator.sh"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="/Users/jamessunheart/Development"
        )

        # Parse the output
        sessions = []

        # Get process info
        ps_result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )

        claude_processes = [
            line for line in ps_result.stdout.split('\n')
            if 'claude' in line.lower() and 'grep' not in line and line.strip()
        ]

        for line in claude_processes:
            parts = line.split()
            if len(parts) >= 11:
                sessions.append({
                    'pid': parts[1],
                    'cpu': parts[2],
                    'memory': parts[3],
                    'terminal': parts[6],
                    'time': parts[9],
                    'status': 'high' if float(parts[2]) > 50 else 'active' if float(parts[2]) > 10 else 'idle'
                })

        # Get registered sessions
        registered = []
        session_files = list((COORDINATION_DIR / "sessions").glob("session-*.json"))

        for session_file in session_files:
            try:
                with open(session_file) as f:
                    data = json.load(f)

                # Get latest heartbeat
                session_id = session_file.stem
                heartbeats = list((COORDINATION_DIR / "heartbeats").glob(f"*-{session_id}.json"))
                latest_hb = max(heartbeats, key=lambda p: p.stat().st_mtime) if heartbeats else None

                hb_data = {}
                if latest_hb:
                    with open(latest_hb) as hf:
                        hb_data = json.load(hf)

                registered.append({
                    'id': session_id,
                    'status': data.get('status', 'unknown'),
                    'work': data.get('current_work', 'unknown'),
                    'started': data.get('started', ''),
                    'action': hb_data.get('action', ''),
                    'phase': hb_data.get('phase', ''),
                    'progress': hb_data.get('progress', '')
                })
            except Exception as e:
                print(f"Error reading session {session_file}: {e}")

        # Get recent messages
        messages = []
        msg_files = sorted(
            (COORDINATION_DIR / "messages" / "broadcast").glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:10]

        for msg_file in msg_files:
            try:
                with open(msg_file) as f:
                    data = json.load(f)
                    messages.append({
                        'from': data.get('from', 'unknown'),
                        'subject': data.get('subject', ''),
                        'message': data.get('message', ''),
                        'timestamp': data.get('timestamp', '')
                    })
            except:
                pass

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
            'processes': sessions,
            'registered': registered,
            'messages': messages,
            'servers': servers,
            'total_sessions': len(sessions),
            'total_registered': len(registered),
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        print(f"Error getting status: {e}")
        return {'error': str(e)}

@app.get("/", response_class=HTMLResponse)
async def home():
    """Main dashboard page"""
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Claude Code Coordination Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }

        .container {
            max-width: 1800px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            text-align: center;
            padding: 30px;
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            margin-bottom: 30px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255,255,255,0.05);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
            text-align: center;
        }

        .stat-card h3 {
            font-size: 0.9em;
            color: #888;
            margin-bottom: 10px;
            text-transform: uppercase;
        }

        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }

        .grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }

        @media (max-width: 1200px) {
            .grid { grid-template-columns: 1fr; }
        }

        .panel {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }

        .panel h2 {
            margin-bottom: 20px;
            color: #667eea;
            font-size: 1.3em;
        }

        .session-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .session-item {
            background: rgba(255,255,255,0.03);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }

        .session-item.high { border-left-color: #f44336; }
        .session-item.active { border-left-color: #ff9800; }
        .session-item.idle { border-left-color: #4caf50; }

        .session-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }

        .session-details {
            font-size: 0.85em;
            color: #888;
        }

        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75em;
            font-weight: bold;
            text-transform: uppercase;
        }

        .badge.high { background: #f44336; color: white; }
        .badge.active { background: #ff9800; color: white; }
        .badge.idle { background: #4caf50; color: white; }

        .message-item {
            background: rgba(255,255,255,0.03);
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 3px solid #764ba2;
        }

        .message-header {
            font-weight: bold;
            margin-bottom: 5px;
            color: #667eea;
        }

        .message-body {
            font-size: 0.9em;
            color: #ccc;
        }

        .message-time {
            font-size: 0.75em;
            color: #666;
            margin-top: 5px;
        }

        .chat-container {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-top: 20px;
        }

        .chat-messages {
            height: 300px;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }

        .chat-input-container {
            display: flex;
            gap: 10px;
        }

        .chat-input {
            flex: 1;
            padding: 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 8px;
            color: white;
            font-size: 1em;
        }

        .chat-button {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 8px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .chat-button:hover {
            transform: translateY(-2px);
        }

        .server-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 10px;
        }

        .server-item {
            padding: 10px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            text-align: center;
        }

        .server-item.online { border: 2px solid #4caf50; }
        .server-item.offline { border: 2px solid #f44336; }

        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }

        .status-dot.online { background: #4caf50; }
        .status-dot.offline { background: #f44336; }

        .auto-refresh {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,0,0,0.5);
            padding: 10px 15px;
            border-radius: 8px;
            font-size: 0.85em;
            color: #4caf50;
        }

        .registered-session {
            background: rgba(102, 126, 234, 0.1);
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }

        .progress-bar {
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.1);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 8px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
        }

        ::-webkit-scrollbar {
            width: 8px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.05);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(102, 126, 234, 0.5);
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="auto-refresh">🔄 Auto-refreshing every 5s</div>

    <div class="container">
        <div class="header">
            <h1>🤖 Claude Code Coordination Dashboard</h1>
            <p>Real-time monitoring of all sessions</p>
            <p id="last-update" style="margin-top: 10px; color: #888; font-size: 0.9em;"></p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>Total Sessions</h3>
                <div class="value" id="total-sessions">-</div>
            </div>
            <div class="stat-card">
                <h3>Registered</h3>
                <div class="value" id="total-registered">-</div>
            </div>
            <div class="stat-card">
                <h3>Active Work</h3>
                <div class="value" id="active-work">-</div>
            </div>
            <div class="stat-card">
                <h3>System Health</h3>
                <div class="value" id="system-health">-</div>
            </div>
        </div>

        <div class="grid">
            <div class="panel">
                <h2>🖥️ Active Claude Processes</h2>
                <div class="session-list" id="processes"></div>
            </div>

            <div class="panel">
                <h2>📋 Registered Sessions</h2>
                <div class="session-list" id="registered"></div>
            </div>
        </div>

        <div class="grid">
            <div class="panel">
                <h2>💬 Recent Messages</h2>
                <div class="session-list" id="messages"></div>
            </div>

            <div class="panel">
                <h2>🌐 Server Status</h2>
                <div class="server-grid" id="servers"></div>
            </div>
        </div>

        <div class="chat-container">
            <h2 style="color: #667eea; margin-bottom: 15px;">💬 Send Message to All Sessions</h2>
            <div class="chat-messages" id="chat-messages">
                <div style="text-align: center; color: #666; margin-top: 100px;">
                    Send a broadcast message to all Claude Code sessions
                </div>
            </div>
            <div class="chat-input-container">
                <input type="text" class="chat-input" id="message-subject" placeholder="Subject...">
                <input type="text" class="chat-input" id="message-body" placeholder="Your message...">
                <button class="chat-button" onclick="sendMessage()">Send Broadcast</button>
            </div>
        </div>
    </div>

    <script>
        let ws;

        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };

            ws.onclose = function() {
                setTimeout(connectWebSocket, 3000);
            };
        }

        function updateDashboard(data) {
            // Update timestamp
            document.getElementById('last-update').textContent =
                `Last update: ${new Date(data.timestamp).toLocaleTimeString()}`;

            // Update stats
            document.getElementById('total-sessions').textContent = data.total_sessions;
            document.getElementById('total-registered').textContent = data.total_registered;
            document.getElementById('active-work').textContent =
                data.processes.filter(p => p.status !== 'idle').length;

            const onlineServers = Object.values(data.servers).filter(s => s).length;
            document.getElementById('system-health').textContent =
                `${onlineServers}/6`;

            // Update processes
            const processesHtml = data.processes.map(p => `
                <div class="session-item ${p.status}">
                    <div class="session-header">
                        <strong>${p.terminal} (PID: ${p.pid})</strong>
                        <span class="badge ${p.status}">${p.status}</span>
                    </div>
                    <div class="session-details">
                        CPU: ${p.cpu}% | Memory: ${p.memory}% | Time: ${p.time}
                    </div>
                </div>
            `).join('');
            document.getElementById('processes').innerHTML = processesHtml;

            // Update registered sessions
            const registeredHtml = data.registered.map(s => `
                <div class="registered-session">
                    <strong>${s.id}</strong>
                    <div style="margin-top: 8px; font-size: 0.9em;">
                        <div>📌 ${s.work}</div>
                        <div style="color: #888; margin-top: 4px;">
                            ${s.action} ${s.phase ? '- ' + s.phase : ''}
                        </div>
                        ${s.progress ? `
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${s.progress}"></div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `).join('') || '<div style="color: #666;">No registered sessions yet</div>';
            document.getElementById('registered').innerHTML = registeredHtml;

            // Update messages
            const messagesHtml = data.messages.map(m => `
                <div class="message-item">
                    <div class="message-header">${m.subject}</div>
                    <div class="message-body">${m.message}</div>
                    <div class="message-time">From: ${m.from} | ${new Date(m.timestamp).toLocaleString()}</div>
                </div>
            `).join('') || '<div style="color: #666;">No messages</div>';
            document.getElementById('messages').innerHTML = messagesHtml;

            // Update servers
            const serverNames = {
                '8000': 'Registry',
                '8001': 'Orchestrator',
                '8002': 'Dashboard',
                '8009': 'Church Guidance',
                '8010': 'I-Match',
                '8025': 'Credentials'
            };

            const serversHtml = Object.entries(data.servers).map(([port, online]) => `
                <div class="server-item ${online ? 'online' : 'offline'}">
                    <div class="status-dot ${online ? 'online' : 'offline'}"></div>
                    <div>${serverNames[port]}</div>
                    <div style="font-size: 0.8em; color: #888;">Port ${port}</div>
                </div>
            `).join('');
            document.getElementById('servers').innerHTML = serversHtml;
        }

        async function sendMessage() {
            const subject = document.getElementById('message-subject').value;
            const body = document.getElementById('message-body').value;

            if (!subject || !body) {
                alert('Please fill in both subject and message');
                return;
            }

            try {
                const response = await fetch('/send-message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ subject, message: body })
                });

                if (response.ok) {
                    document.getElementById('chat-messages').innerHTML += `
                        <div style="background: rgba(102, 126, 234, 0.2); padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                            <strong>✅ Broadcast sent!</strong><br>
                            <div style="font-size: 0.9em; margin-top: 5px;">
                                Subject: ${subject}<br>
                                Message: ${body}
                            </div>
                        </div>
                    `;
                    document.getElementById('chat-messages').scrollTop = document.getElementById('chat-messages').scrollHeight;
                    document.getElementById('message-subject').value = '';
                    document.getElementById('message-body').value = '';
                } else {
                    alert('Failed to send message');
                }
            } catch (error) {
                alert('Error sending message: ' + error);
            }
        }

        // Connect WebSocket
        connectWebSocket();

        // Fallback polling
        setInterval(async () => {
            const response = await fetch('/api/status');
            const data = await response.json();
            updateDashboard(data);
        }, 5000);

        // Initial load
        (async () => {
            const response = await fetch('/api/status');
            const data = await response.json();
            updateDashboard(data);
        })();
    </script>
</body>
</html>
    """
    return html

@app.get("/api/status")
async def api_status():
    """API endpoint for status data"""
    return get_session_status()

@app.post("/send-message")
async def send_message(request: Request):
    """Send broadcast message to all sessions"""
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

        return {'success': True, 'output': result.stdout}
    except Exception as e:
        return {'error': str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()

    try:
        while True:
            status = get_session_status()
            await websocket.send_json(status)
            await asyncio.sleep(5)
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)
