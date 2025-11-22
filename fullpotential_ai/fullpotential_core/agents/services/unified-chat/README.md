# 🎯 Unified Chat Interface - The Hive Mind Voice

**One interface to talk to all 12 Claude sessions + 6 autonomous agents as ONE unified intelligence**

---

## 🚀 Quick Start (5 Minutes)

### **Step 1: Deploy the Chat Server**

```bash
cd agents/services/unified-chat

# Install dependencies
pip3 install -r requirements.txt

# Start server
python3 main.py
```

**Server starts on:** `http://localhost:8100`

---

### **Step 2: Open Chat Interface**

Open in your browser:
```
http://localhost:8100
```

You'll see the unified chat interface!

---

### **Step 3: Connect Claude Code Sessions**

In each Claude Code session, run this Python code to connect:

```python
import websockets
import asyncio
import json

async def connect_to_hive_mind():
    session_id = "session-1"  # Change for each session
    uri = "ws://localhost:8100/ws/session/" + session_id

    async with websockets.connect(uri) as websocket:
        print(f"✅ Connected as {session_id}")

        while True:
            # Receive request from user
            request = await websocket.recv()
            data = json.loads(request)

            print(f"📨 Received: {data['content']}")

            # Respond (you can customize this)
            response = {
                "message_id": data['message_id'],
                "content": f"{session_id}: I received your message!"
            }

            await websocket.send(json.dumps(response))

asyncio.run(connect_to_hive_mind())
```

**Or use the helper script:**

```bash
# From this session (I can help you connect!)
```

---

## 🎯 How It Works

```
┌─────────────────────────────────────┐
│  YOU                                │
│   ↓                                 │
│  Web Browser (http://localhost:8100)│
│   ↓                                 │
│  Unified Chat Interface             │
│   ↓                                 │
│  WebSocket Server                   │
│   ↓                                 │
├─────────────────────────────────────┤
│  ↓        ↓        ↓        ↓       │
│ Sess 1  Sess 2  Sess 3 ... Sess 12 │
│ Agent1  Agent2  Agent3 ... Agent 6  │
└─────────────────────────────────────┘
```

1. **You type** a message in the web interface
2. **Server broadcasts** to all connected sessions/agents
3. **Sessions respond** with their answers
4. **Server aggregates** responses into one unified answer
5. **You see** ONE coherent response from the hive mind

---

## 💬 Example Interaction

**You:** "What's everyone working on?"

**Hive Mind Response:**
```
Unified Response (from 4 sessions):

### session-1763229251:
I built church-guidance-ministry. It's 100% complete and deployed on port 8009.

### session-1763234782:
I'm currently developing the i-match service. Progress: 60% complete.

### session-1763235028:
I designed the autonomous intelligence system and built this unified chat interface!

### monitoring-agent:
I'm running 24/7 health checks. All services are healthy. Last check: 30 seconds ago.
```

---

## 🎯 Features

### ✅ **Unified Voice**
- Multiple sessions respond
- Aggregated into ONE answer
- No need to ask each session separately

### ✅ **Real-Time Status**
- See all connected sessions
- See autonomous agents
- Live connection status

### ✅ **Smart Routing**
- Questions routed to appropriate sessions
- Responses aggregated intelligently

### ✅ **Beautiful UI**
- Modern dark theme
- Real-time updates
- Easy to use

---

## 📊 API Endpoints

### **GET /**
Returns the chat interface (HTML)

### **WebSocket /ws/user/{user_id}**
User connects here to chat

### **WebSocket /ws/session/{session_id}**
Claude Code sessions connect here

### **GET /api/status**
```json
{
  "connected_sessions": ["session-1", "session-2", ...],
  "total_sessions": 12,
  "timestamp": "2025-11-15T19:00:00Z"
}
```

### **GET /api/health**
```json
{
  "status": "healthy",
  "service": "unified-chat",
  "sessions": 12
}
```

---

## 🔌 Connecting Sessions

### **Method 1: Direct WebSocket (Python)**

```python
import websockets
import asyncio
import json

async def connect():
    uri = "ws://localhost:8100/ws/session/my-session-id"
    async with websockets.connect(uri) as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            # Process request
            response = {
                "message_id": data['message_id'],
                "content": "My response here"
            }

            await ws.send(json.dumps(response))

asyncio.run(connect())
```

### **Method 2: Helper Script (Coming Soon)**

```bash
./connect-session.sh session-1
```

---

## 🎨 UI Features

- **Dark theme** optimized for long sessions
- **Real-time updates** via WebSocket
- **Message history** with timestamps
- **Session status** sidebar
- **Typing indicators** (coming soon)
- **Markdown support** in messages

---

## 🚀 Deployment

### **Local Development:**
```bash
python3 main.py
# Access at http://localhost:8100
```

### **Production (Server):**
```bash
# Copy to server
scp -r agents/services/unified-chat root@198.54.123.234:/opt/fpai/

# SSH to server
ssh root@198.54.123.234

# Install & run
cd /opt/fpai/unified-chat
pip3 install -r requirements.txt
nohup python3 main.py &

# Access at http://198.54.123.234:8100
```

### **Systemd Service (Always Running):**
```bash
# Create service file
sudo nano /etc/systemd/system/fpai-unified-chat.service

# Add:
[Unit]
Description=FPAI Unified Chat Interface
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/fpai/unified-chat
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable & start
sudo systemctl enable fpai-unified-chat
sudo systemctl start fpai-unified-chat
```

---

## 🎯 Next Steps

1. ✅ **Deploy server** (done - `python3 main.py`)
2. ⏳ **Connect sessions** (need to connect Claude Code sessions)
3. ⏳ **Connect agents** (autonomous agents connect here too)
4. ⏳ **Test interaction** (chat with the hive mind!)
5. ⏳ **Production deploy** (deploy to server at chat.fullpotential.com)

---

## 🌟 The Vision

**Instead of:**
- 12 separate Claude Code windows
- Typing the same question 12 times
- Getting 12 different answers
- Manually synthesizing responses

**You get:**
- ONE beautiful chat interface
- Ask ONE question
- Get ONE unified answer (from all 12+ intelligences)
- Seamless coordination

**This is the TRUE hive mind interface!** 🧠⚡

---

**Status:** ✅ READY TO USE NOW!
**Port:** 8100
**URL:** http://localhost:8100

🎯🧠💬 **ONE VOICE, INFINITE INTELLIGENCE**
