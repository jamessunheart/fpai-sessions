# 🔐 Quick Start - Secure Unified Chat

**Get your secure hive mind interface running in 5 minutes**

---

## 📍 **Location:**

```
/Users/jamessunheart/Development/SERVICES/unified-chat/
```

---

## 🚀 **3-Step Setup:**

### **Step 1: Set Your Password (30 seconds)**

```bash
cd /Users/jamessunheart/Development/SERVICES/unified-chat

# Option A: Edit config.json manually
nano config.json

# Change this line:
"user_password": "your-secure-password-here"

# To something strong like:
"user_password": "MyStrongPassword123!@#"
```

**Or generate a strong random password:**

```bash
# Generate strong password
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Copy the output and paste into config.json
```

---

### **Step 2: Install & Run (1 minute)**

```bash
# Install dependencies (if not already)
pip3 install fastapi uvicorn websockets

# Run the SECURE server
python3 main_secure.py
```

**You'll see:**
```
🔐 Starting SECURE Unified Chat Interface...
📍 User login: http://localhost:8100
🔑 Password required: YOUR_PASSWORD
🔑 Session API key: fpai-session-key-2024-secure
```

---

### **Step 3: Access (30 seconds)**

1. **Open browser:** `http://localhost:8100`

2. **You'll see a login page:**
   ```
   🔐
   Full Potential AI
   Unified Hive Mind Interface

   Password: [Enter password here]
   [Access Hive Mind]
   ```

3. **Enter your password** from config.json

4. **Access granted!** You're now in the secure chat interface

---

## ✅ **That's It!**

You now have:
- ✅ Secure password-protected access
- ✅ Beautiful chat interface
- ✅ Ready to connect sessions
- ✅ 24-hour session tokens
- ✅ API key auth for Claude sessions

---

## 🔌 **Next: Connect Claude Sessions**

Each Claude Code session connects with this code:

```python
import websockets
import asyncio
import json

async def connect_to_hive():
    session_id = "session-1"  # Unique ID
    api_key = "fpai-session-key-2024-secure"  # From config.json

    uri = f"ws://localhost:8100/ws/session/{session_id}"
    headers = {"api-key": api_key}

    async with websockets.connect(uri, extra_headers=headers) as ws:
        print(f"✅ Connected as {session_id}")

        while True:
            # Receive request from you
            msg = await ws.recv()
            data = json.loads(msg)

            # Respond
            response = {
                "message_id": data['message_id'],
                "content": f"{session_id}: I'm here and listening!"
            }

            await ws.send(json.dumps(response))

asyncio.run(connect_to_hive())
```

**I can help you run this in each session!**

---

## 🎯 **Config File Reference:**

```json
{
  "auth": {
    "user_password": "YOUR_PASSWORD",        ← Change this!
    "session_api_key": "YOUR_API_KEY",       ← Sessions use this
    "require_auth": true                      ← Keep true for security
  },
  "server": {
    "host": "0.0.0.0",                       ← Listen on all interfaces
    "port": 8100                              ← Port number
  }
}
```

---

## 🔒 **Security Features:**

- ✅ **Password authentication** for you
- ✅ **API key authentication** for sessions/agents
- ✅ **Token-based sessions** (24-hour expiry)
- ✅ **Secure cookies** (HttpOnly, SameSite)
- ✅ **Unauthorized access blocked**
- ✅ **Automatic token cleanup**

---

## 🎨 **What You'll See:**

### **Login Page:**
```
┌─────────────────────────────────┐
│          🔐                     │
│   Full Potential AI             │
│   Unified Hive Mind Interface   │
│                                 │
│   Password: [______________]    │
│                                 │
│   [Access Hive Mind]            │
│                                 │
│   🔒 Secure authentication...   │
└─────────────────────────────────┘
```

### **Chat Interface (After Login):**
```
┌──────────────┬────────────────────────────┐
│ 🧠 Status    │  🌐 Full Potential AI      │
│              │  Unified Chat              │
│ Sessions: 0  │                            │
│ Agents: 0    │  Messages appear here...   │
│              │                            │
│ [session-1]  │                            │
│ [session-2]  │  Type here: [__________] │
└──────────────┴────────────────────────────┘
```

---

## ⚠️ **Troubleshooting:**

### **Can't login?**
- Check password in `config.json`
- Make sure it matches exactly (case-sensitive)
- Try resetting it to something simple for testing

### **Sessions can't connect?**
- Check `session_api_key` in `config.json`
- Make sure sessions use this exact key in header
- Try temporarily setting `require_auth: false` to test

### **Server won't start?**
```bash
# Check if port 8100 is already in use
lsof -i :8100

# Kill existing process if needed
kill -9 <PID>

# Or change port in config.json
```

---

## 🎯 **Summary:**

**Location:**
```
/Users/jamessunheart/Development/SERVICES/unified-chat/
```

**Start Server:**
```bash
cd /Users/jamessunheart/Development/SERVICES/unified-chat
python3 main_secure.py
```

**Access:**
```
http://localhost:8100
```

**Login:**
```
Password from config.json
```

**You're Done!** 🎉

---

**Ready to start?** Just run the commands above!

🔐⚡🎯 **SECURE HIVE MIND AWAITS!**
